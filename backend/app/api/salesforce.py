from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.database import get_db
from app.models import Lead, Email
from app.models.email import EmailStatus
from app.services.salesforce import salesforce_service
from app.utils.stats import refresh_run_stats
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/salesforce", tags=["salesforce"])

class SendLeadsRequest(BaseModel):
    lead_ids: List[str]

@router.post("/send-leads")
async def send_leads_to_salesforce(
    request: SendLeadsRequest,
    db: Session = Depends(get_db)
):
    """Send selected leads to Salesforce and update their status."""
    logger.info(f"Bulk Salesforce sync requested for {len(request.lead_ids)} leads: {request.lead_ids}")
    results = []

    # Pre-fetch all leads and their emails to avoid session issues during async calls
    leads = db.query(Lead).filter(Lead.id.in_(request.lead_ids)).all()
    lead_map = {l.id: l for l in leads}

    # Pre-fetch emails for these leads
    emails = db.query(Email).filter(Email.lead_id.in_(request.lead_ids)).all()
    email_map = {e.lead_id: e for e in emails}

    for lead_id in request.lead_ids:
        lead = lead_map.get(lead_id)
        if not lead:
            results.append({"lead_id": lead_id, "success": False, "error": "Lead not found"})
            continue

        try:
            logger.info(f"Processing lead {lead_id} ({lead.business_name}) for Salesforce")
            # Fetch existing email record if any
            email_record = email_map.get(lead.id)
            email_content = None
            if email_record:
                email_content = {
                    "subject": email_record.subject,
                    "body": email_record.body
                }

            # Prepare data for Salesforce
            sf_data = {
                "FirstName": lead.business_name.split(' ')[0] if ' ' in lead.business_name else "",
                "LastName": lead.business_name.split(' ', 1)[1] if ' ' in lead.business_name else lead.business_name,
                "Company": lead.business_name,
                "Website": lead.website,
                "Email": lead.email,
                "Phone": lead.phone,
                "LeadSource": "Byte2Bite",
                "Notes": lead.notes
            }

            # Upsert in Salesforce
            sf_res = await salesforce_service.upsert_lead_by_email(sf_data, email_content=email_content)

            # Update local status to SFDX
            if not email_record:
                email_record = Email(
                    lead_id=lead.id,
                    status=EmailStatus.SFDX,
                    subject="Salesforce Transfer",
                    body="Lead sent to Salesforce",
                )
                db.add(email_record)
            else:
                email_record.status = EmailStatus.SFDX

            # Update the lead record as well for UI consistency
            lead.sfdc_status = "success"
            lead.sfdc_id = sf_res.get("id")
            lead.sfdc_error = None

            # We commit inside the loop to ensure progress is saved even if subsequent ones fail
            # This is safer for partial batch success
            db.commit()

            results.append({
                "lead_id": lead_id,
                "success": True,
                "salesforce_id": sf_res.get("id"),
                "status": sf_res.get("status")
            })
            logger.info(f"Successfully synced lead {lead_id} to Salesforce")

        except Exception as e:
            logger.error(f"Failed to send lead {lead_id} to Salesforce: {str(e)}")
            results.append({"lead_id": lead_id, "success": False, "error": str(e)})
            lead.sfdc_status = "failed"
            lead.sfdc_error = str(e)
            db.commit() # Save the failure status

    if leads:
        refresh_run_stats(leads[0].run_id, db)

    return {"results": results}
