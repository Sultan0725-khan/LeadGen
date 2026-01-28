from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from app.database import get_db
from app.schemas.email import EmailResponse, EmailDraftRequest, EmailUpdateRequest, EmailRedraftRequest
from app.models import Email, EmailStatus, Lead, Run
from app.agents.email_sender import EmailSender
from app.agents.orchestrator import AgentOrchestrator
from app.utils.timezone import get_german_now
from app.services.salesforce import salesforce_service
from app.api.salesforce import SendLeadsRequest
from app.utils.stats import refresh_run_stats
import asyncio

router = APIRouter(prefix="/api/emails", tags=["emails"])


@router.post("/draft")
async def draft_emails(request: EmailDraftRequest, db: Session = Depends(get_db)):
    """Draft emails for specific leads."""
    orchestrator = AgentOrchestrator(db)
    count = await orchestrator.draft_targeted_emails(request.lead_ids, language=request.language)
    return {"status": "success", "drafted_count": count}


@router.put("/{email_id}", response_model=EmailResponse)
def update_email(email_id: str, request: EmailUpdateRequest, db: Session = Depends(get_db)):
    """Update an email draft."""
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    email.subject = request.subject
    email.body = request.body
    email.generated_at = get_german_now()

    if request.recipient_email:
        lead = db.query(Lead).filter(Lead.id == email.lead_id).first()
        if lead:
            lead.email = request.recipient_email

    db.commit()
    db.refresh(email)

    # Attach recipient email to response object
    email.recipient_email = request.recipient_email
    return email


@router.post("/{email_id}/redraft", response_model=EmailResponse)
async def redraft_email(email_id: str, request: EmailRedraftRequest, db: Session = Depends(get_db)):
    """Refine an existing email draft with custom input."""
    orchestrator = AgentOrchestrator(db)
    email = await orchestrator.redraft_targeted_email(email_id, request.prompt)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found or redraft failed")
    return email


@router.post("/send-bulk")
async def send_bulk_emails(request: SendLeadsRequest, db: Session = Depends(get_db)):
    """Send multiple emails in bulk."""
    print(f"Bulk email send requested for {len(request.lead_ids)} leads")
    results = []
    sender = EmailSender()

    # Pre-fetch for better performance and session safety
    leads = db.query(Lead).filter(Lead.id.in_(request.lead_ids)).all()
    lead_map = {l.id: l for l in leads}

    emails = db.query(Email).filter(Email.lead_id.in_(request.lead_ids)).all()
    email_map = {e.lead_id: e for e in emails}

    for lead_id in request.lead_ids:
        email = email_map.get(lead_id)
        if not email:
            print(f"No email draft found for lead {lead_id}")
            results.append({"lead_id": lead_id, "success": False, "error": "Email draft not found"})
            continue

        lead = lead_map.get(lead_id)
        if not lead or not lead.email:
            print(f"No email address for lead {lead_id}")
            results.append({"lead_id": lead_id, "success": False, "error": "Lead or lead email not found"})
            continue

        print(f"Sending email for lead {lead_id} ({lead.business_name})")
        success, error = await sender.send_email(
            lead.email,
            email.subject,
            email.body,
            db,
            dry_run=False
        )

        if success:
            email.status = EmailStatus.SENT
            email.sent_at = get_german_now()

            # Chain Salesforce Integration
            try:
                print(f"Syncing lead {lead_id} to Salesforce after email send")
                sf_lead_data = {
                    "FirstName": lead.business_name.split(' ')[0] if ' ' in lead.business_name else "",
                    "LastName": lead.business_name.split(' ', 1)[1] if ' ' in lead.business_name else lead.business_name,
                    "Company": lead.business_name,
                    "Website": lead.website,
                    "Email": lead.email,
                    "Phone": lead.phone,
                    "LeadSource": "Byte2Bite",
                    "Notes": lead.notes
                }
                email_content = {"subject": email.subject, "body": email.body}
                sf_result = await salesforce_service.upsert_lead_by_email(sf_lead_data, email_content)

                lead.sfdc_status = "success"
                lead.sfdc_id = sf_result.get("id")
            except Exception as sf_err:
                print(f"Salesforce chain failed for lead {lead_id}: {sf_err}")
                lead.sfdc_status = "failed"

            db.commit()
            refresh_run_stats(lead.run_id, db)
            results.append({"lead_id": lead_id, "success": True})
            print(f"Finished processing lead {lead_id}")
        else:
            email.status = EmailStatus.FAILED
            email.error_message = error
            db.commit()
            results.append({"lead_id": lead_id, "success": False, "error": error})

    # Refresh stats for the run(s) affected
    if leads:
        refresh_run_stats(leads[0].run_id, db)

    return {"status": "success", "results": results}


@router.post("/{email_id}/send")
async def send_specific_email(email_id: str, db: Session = Depends(get_db)):
    """Send a specific email immediately."""
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    lead = db.query(Lead).filter(Lead.id == email.lead_id).first()
    if not lead or not lead.email:
        raise HTTPException(status_code=400, detail="Lead has no email address")

    sender = EmailSender()
    success, error = await sender.send_email(
        lead.email,
        email.subject,
        email.body,
        db,
        dry_run=False
    )

    if success:
        email.status = EmailStatus.SENT
        email.sent_at = get_german_now()

        # Chain Salesforce Integration
        try:
            print(f"Starting Salesforce sync for lead {lead.id} ({lead.business_name})...")
            sf_lead_data = {
                "FirstName": lead.business_name.split(' ')[0] if ' ' in lead.business_name else "",
                "LastName": lead.business_name.split(' ', 1)[1] if ' ' in lead.business_name else lead.business_name,
                "Company": lead.business_name,
                "Website": lead.website,
                "Email": lead.email,
                "Phone": lead.phone,
                "LeadSource": "Byte2Bite",
                "Notes": lead.notes
            }
            email_content = {"subject": email.subject, "body": email.body}
            sf_result = await salesforce_service.upsert_lead_by_email(sf_lead_data, email_content)

            lead.sfdc_status = "success"
            lead.sfdc_id = sf_result.get("id")
            print(f"Successfully synced lead {lead.id} to Salesforce (ID: {lead.sfdc_id})")
        except Exception as sf_err:
            print(f"Salesforce synchronization failed for lead {lead.id}: {sf_err}")
            lead.sfdc_status = "failed"
    else:
        email.status = EmailStatus.FAILED
        email.error_message = error

    db.commit()
    refresh_run_stats(lead.run_id, db)
    return {"status": "success" if success else "failed", "error": error}


@router.post("/{email_id}/approve")
async def approve_email(email_id: str, db: Session = Depends(get_db)):
    """Approve an email for sending (compat with old flow)."""
    email = db.query(Email).filter(Email.id == email_id).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    if email.status != EmailStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=400, detail="Email is not pending approval")

    email.status = EmailStatus.APPROVED
    db.commit()

    lead = db.query(Lead).filter(Lead.id == email.lead_id).first()
    run = db.query(Run).filter(Run.id == lead.run_id).first()
    refresh_run_stats(lead.run_id, db)

    if not run.dry_run:
        sender = EmailSender()
        success, error = await sender.send_email(
            lead.email,
            email.subject,
            email.body,
            db,
            dry_run=False
        )

        if success:
            email.status = EmailStatus.SENT
            email.sent_at = get_german_now()
        else:
            email.status = EmailStatus.FAILED
            email.error_message = error

        db.commit()

    return {"status": "approved", "sent": not run.dry_run}


@router.post("/{email_id}/suppress")
def suppress_email(email_id: str, db: Session = Depends(get_db)):
    """Suppress an email from sending."""
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    email.status = EmailStatus.SUPPRESSED
    db.commit()
    return {"status": "suppressed"}


@router.get("/{email_id}", response_model=EmailResponse)
def get_email(email_id: str, db: Session = Depends(get_db)):
    """Get email details."""
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    # Manually attach lead email for the response schema
    lead = db.query(Lead).filter(Lead.id == email.lead_id).first()
    email.recipient_email = lead.email if lead else None

    return email
