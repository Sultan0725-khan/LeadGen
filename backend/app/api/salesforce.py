from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.database import get_db
from app.models import Lead, Email
from app.models.email import EmailStatus
from app.services.salesforce import salesforce_service
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
    results = []

    for lead_id in request.lead_ids:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            results.append({"lead_id": lead_id, "success": False, "error": "Lead not found"})
            continue

        try:
            # Fetch existing email record if any
            email_record = db.query(Email).filter(Email.lead_id == lead.id).first()
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

            # Upsert in Salesforce (includes attaching email as file if email_content is not None)
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

            db.commit()

            results.append({
                "lead_id": lead_id,
                "success": True,
                "salesforce_id": sf_res.get("id"),
                "status": sf_res.get("status")
            })

        except Exception as e:
            logger.error(f"Failed to send lead {lead_id} to Salesforce: {str(e)}")
            results.append({"lead_id": lead_id, "success": False, "error": str(e)})

    return {"results": results}
