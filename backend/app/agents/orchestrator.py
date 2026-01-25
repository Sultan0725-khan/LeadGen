from typing import Dict, List, Optional, Tuple
from datetime import datetime
from app.utils.timezone import get_german_now
from sqlalchemy.orm import Session
from app.models import Run, RunStatus, Lead, Email, EmailStatus, Log, LogLevel
from app.agents.lead_collector import LeadCollector
from app.agents.normalizer import Normalizer
from app.agents.enricher import Enricher
from app.agents.scorer import Scorer
from app.agents.email_writer import EmailWriter
from app.agents.email_sender import EmailSender
from app.services.usage_service import increment_provider_usage
import asyncio


class AgentOrchestrator:
    """Main orchestrator that coordinates all agentic tools for a run."""

    def __init__(self, db: Session):
        self.db = db
        self.lead_collector = LeadCollector()
        self.normalizer = Normalizer()
        self.enricher = Enricher()
        self.scorer = Scorer()
        self.email_writer = EmailWriter()
        self.email_sender = EmailSender()

    async def execute_run(self, run_id: str):
        """Execute a complete lead generation run."""
        # Get run from database
        run = self.db.query(Run).filter(Run.id == run_id).first()
        if not run:
            raise ValueError(f"Run {run_id} not found")

        try:
            # Update status to running
            run.status = RunStatus.RUNNING
            self.db.commit()
            self._log(run, LogLevel.INFO, "Run started")

            # Step 1: Collect leads from providers
            self._log(run, LogLevel.INFO, f"Collecting leads for {run.category} in {run.location}")
            raw_leads, usage_info = await self.lead_collector.collect(
                run.location,
                run.category,
                selected_providers=run.selected_providers,
                provider_limits=run.provider_limits
            )
            self._log(run, LogLevel.INFO, f"Collected {len(raw_leads)} raw leads")

            # Record credit usage in database
            for provider_id, credits in usage_info.items():
                await increment_provider_usage(provider_id, self.db, credits)
                self._log(run, LogLevel.INFO, f"Provider {provider_id} consumed {credits} credits")

            # Step 2: Normalize and deduplicate
            self._log(run, LogLevel.INFO, "Normalizing and deduplicating leads")
            normalized_leads = self.normalizer.normalize_and_dedupe(raw_leads)
            self._log(run, LogLevel.INFO, f"Normalized to {len(normalized_leads)} unique leads")

            # Step 3: Enrich leads (in parallel batches)
            self._log(run, LogLevel.INFO, "Enriching leads with website data")
            await self._enrich_leads(normalized_leads)

            # Step 4: Calculate confidence scores
            self._log(run, LogLevel.INFO, "Calculating confidence scores")
            for lead_data in normalized_leads:
                score = self.scorer.calculate_score(lead_data)
                lead_data["confidence_score"] = score

            # Step 5: Save leads to database
            self._log(run, LogLevel.INFO, "Saving leads to database")
            lead_records = self._save_leads(run, normalized_leads)

            # Step 6: Generate emails
            self._log(run, LogLevel.INFO, "Generating personalized emails")
            await self._generate_emails(run, lead_records)

            # Step 7: Send emails (if not requiring approval and not dry run)
            if not run.require_approval and not run.dry_run:
                self._log(run, LogLevel.INFO, "Sending emails")
                await self._send_emails(run)
            else:
                self._log(run, LogLevel.INFO, "Emails drafted, waiting for approval")

            # Mark run as completed
            run.status = RunStatus.COMPLETED
            run.completed_at = get_german_now()
            self._refresh_run_stats(run)
            self.db.commit()
            self._log(run, LogLevel.INFO, "Run completed successfully")

        except Exception as e:
            # Mark run as failed
            run.status = RunStatus.FAILED
            run.error_message = str(e)
            run.completed_at = get_german_now()
            self.db.commit()
            self._log(run, LogLevel.ERROR, f"Run failed: {str(e)}")
            raise

    async def _enrich_leads(self, leads: list):
        """Enrich leads in parallel batches."""
        # Process in batches of 5 to avoid overwhelming
        batch_size = 5
        for i in range(0, len(leads), batch_size):
            batch = leads[i:i+batch_size]
            tasks = [self.enricher.enrich(lead) for lead in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for lead, enrichment in zip(batch, results):
                if isinstance(enrichment, Exception):
                    print(f"Enrichment error for {lead.get('business_name')}: {enrichment}")
                    lead["enrichment_data"] = {}
                else:
                    lead["enrichment_data"] = enrichment

        if leads:
            run_id = leads[0]['run_id']
            self.db.query(Run).filter(Run.id == run_id).update({
                "total_websites": self.db.query(Lead).filter(
                    Lead.run_id == run_id,
                    Lead.website != None,
                    Lead.website != ""
                ).count()
            })
            self.db.commit()

    def _save_leads(self, run: Run, normalized_leads: list) -> list:
        """Save normalized leads to database."""
        lead_records = []

        for lead_data in normalized_leads:
            # Prioritize best email
            best_email = self.scorer.get_best_contact_email(lead_data)

            lead = Lead(
                run_id=run.id,
                business_name=lead_data.get("business_name", ""),
                address=lead_data.get("address"),
                website=lead_data.get("website"),
                email=best_email or lead_data.get("email"),
                phone=lead_data.get("phone"),
                latitude=lead_data.get("latitude"),
                longitude=lead_data.get("longitude"),
                confidence_score=lead_data.get("confidence_score", 0.0),
                sources=lead_data.get("sources", []),
                enrichment_data=lead_data.get("enrichment_data", {}),
                created_at=get_german_now(),
                updated_at=get_german_now()
            )

            self.db.add(lead)
            lead_records.append((lead, lead_data))

        self.db.commit()

        self.db.commit()
        self._refresh_run_stats(run)

        return lead_records

    async def _generate_emails(self, run: Run, lead_records: list):
        """Generate personalized emails for leads."""
        for lead, lead_data in lead_records:
            await self.generate_email_for_lead(lead, lead_data, run)

        # Refresh run stats after batch generation
        self._refresh_run_stats(run)

    async def generate_email_for_lead(
        self,
        lead: Lead,
        lead_data: dict,
        run: Run,
        force_status: Optional[EmailStatus] = None,
        language: str = "DE" # Default is DE
    ) -> Optional[Email]:
        """Generate a single personalized email for a lead."""
        if not lead.email:
            self._log(run, LogLevel.WARNING, f"No email for {lead.business_name}", lead_id=lead.id)
            return None

        # Use the provided language preference
        try:
            email_content = await self.email_writer.generate_email(
                lead_data, run.location, run.category, language
            )

            if force_status:
                status = force_status
            elif run.require_approval:
                status = EmailStatus.PENDING_APPROVAL
            elif run.dry_run:
                status = EmailStatus.DRAFTED
            else:
                status = EmailStatus.APPROVED

            email = self.db.query(Email).filter(Email.lead_id == lead.id).first()
            if email:
                email.subject = email_content["subject"]
                email.body = email_content["body"]
                email.status = status
                email.generated_at = get_german_now()
            else:
                email = Email(
                    lead_id=lead.id,
                    status=status,
                    subject=email_content["subject"],
                    body=email_content["body"],
                    language=language,
                    generated_at=get_german_now()
                )
                self.db.add(email)

            self.db.commit()
            # Do NOT update run.total_emails here; it should represent "Emails Found"
            return email
        except Exception as e:
            self._log(run, LogLevel.ERROR, f"Email generation failed for {lead.business_name}: {str(e)}", lead_id=lead.id)
            return None

    async def draft_targeted_emails(self, lead_ids: List[str], language: str = "DE") -> int:
        """Draft emails for a specific set of leads with language support."""
        leads = self.db.query(Lead).filter(Lead.id.in_(lead_ids)).all()
        if not leads:
            return 0

        # Run generation in parallel for performance
        tasks = []
        for lead in leads:
            run = self.db.query(Run).filter(Run.id == lead.run_id).first()
            lead_data = {
                "business_name": lead.business_name,
                "address": lead.address,
                "website": lead.website,
                "email": lead.email,
                "phone": lead.phone,
                "enrichment_data": lead.enrichment_data or {}
            }
            # When manually drafting, always set to DRAFTED so it's editable in UI
            tasks.append(self.generate_email_for_lead(
                lead, lead_data, run, force_status=EmailStatus.DRAFTED, language=language
            ))

        results = await asyncio.gather(*tasks)
        drafted_count = len([r for r in results if r is not None])

        # Refresh run stats after manual drafting
        run = self.db.query(Run).filter(Run.id == leads[0].run_id).first()
        if run:
            self._refresh_run_stats(run)

        return drafted_count

    async def _send_emails(self, run: Run):
        """Send approved emails."""
        emails = self.db.query(Email).join(Lead).filter(
            Lead.run_id == run.id,
            Email.status == EmailStatus.APPROVED
        ).all()

        for email in emails:
            lead = self.db.query(Lead).filter(Lead.id == email.lead_id).first()

            success, error = await self.email_sender.send_email(
                lead.email,
                email.subject,
                email.body,
                self.db,
                dry_run=run.dry_run
            )

            if success:
                email.status = EmailStatus.SENT
                email.sent_at = get_german_now()
                self._log(run, LogLevel.INFO, f"Email sent to {lead.business_name}", lead_id=lead.id)
            else:
                email.status = EmailStatus.FAILED
                email.error_message = error
                self._log(run, LogLevel.ERROR, f"Email send failed: {error}", lead_id=lead.id)

        self.db.commit()

    def _refresh_run_stats(self, run: Run):
        """Update all run-level statistics from current database state."""
        from app.models.email import Email, EmailStatus

        # Leads count
        run.total_leads = self.db.query(Lead).filter(Lead.run_id == run.id).count()

        # Website count
        run.total_websites = self.db.query(Lead).filter(
            Lead.run_id == run.id,
            Lead.website != None,
            Lead.website != ""
        ).count()

        # Email Found count
        run.total_emails = self.db.query(Lead).filter(
            Lead.run_id == run.id,
            Lead.email != None,
            Lead.email != ""
        ).count()

        # Drafts count (Generated non-failed, non-pending emails)
        run.total_drafts = self.db.query(Email).join(Lead).filter(
            Lead.run_id == run.id,
            Email.status.in_([EmailStatus.DRAFTED, EmailStatus.APPROVED, EmailStatus.SENT])
        ).count()

        self.db.commit()

    def _log(self, run: Run, level: LogLevel, message: str, lead_id: str = None):
        """Add a log entry."""
        log = Log(
            run_id=run.id,
            lead_id=lead_id,
            level=level,
            message=message,
            created_at=get_german_now()
        )
        self.db.add(log)
        self.db.commit()
        print(f"[{level.value.upper()}] {message}")
