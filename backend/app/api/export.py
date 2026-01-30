from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Lead, Email, Log, Run
from app.models.email import EmailStatus
from typing import Optional
import csv
import io
import yaml
import os

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/run/{run_id}/csv")
def export_run_csv(run_id: str, email_status: Optional[str] = None, db: Session = Depends(get_db)):
    """Export run leads to CSV with optional status filter."""
    # Build query with optional join for email status filtering
    query = db.query(Lead).outerjoin(Email, Lead.id == Email.lead_id)
    query = query.filter(Lead.run_id == run_id)

    # Apply same filtering logic as in leads.py
    if email_status == "new":
        query = query.filter((Email.id == None) | (Email.status.in_([EmailStatus.FAILED, EmailStatus.PENDING_APPROVAL])))
    elif email_status == "drafted":
        query = query.filter(Email.status.in_([
            EmailStatus.DRAFTED,
            EmailStatus.APPROVED
        ]))
    elif email_status == "sent":
        query = query.filter(Email.status.in_([EmailStatus.SENT, EmailStatus.SFDX]))
    elif email_status:
        query = query.filter(Email.status == email_status)

    leads = query.all()
    run = db.query(Run).filter(Run.id == run_id).first()

    # Load CSV mapping configuration
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "mappingCSV.yaml")
    try:
        with open(config_path, "r") as f:
            mapping_config = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading CSV mapping: {e}")
        mapping_config = {"default": {}}

    # Get mapping for the current tab or default
    tab_mapping = mapping_config.get("tabs", {}).get(email_status, mapping_config.get("default", {}))
    headers = list(tab_mapping.keys())

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(headers)

    # Write data
    for lead in leads:
        email_record = db.query(Email).filter(Email.lead_id == lead.id).first()

        row = []
        for header in headers:
            field = tab_mapping[header]
            value = ""

            # Map database fields or computed values
            if field == "business_name":
                value = lead.business_name
            elif field == "first_name":
                value = lead.first_name or ""
            elif field == "last_name":
                value = lead.last_name or ""
            elif field == "address":
                value = lead.address or ""
            elif field == "website":
                value = lead.website or ""
            elif field == "email":
                value = lead.email or ""
            elif field == "phone":
                value = lead.phone or ""
            elif field == "confidence_score":
                value = lead.confidence_score
            elif field == "sources":
                value = ", ".join(lead.sources) if lead.sources else ""
            elif field == "email_status":
                value = email_record.status.value if email_record else "none"
            elif field == "email_subject":
                value = email_record.subject if email_record else ""
            elif field == "email_body":
                value = email_record.body if email_record else ""
            elif field == "notes":
                value = lead.notes or ""
            elif field == "category":
                value = run.category if run else ""
            elif field == "sfdc_id":
                value = lead.sfdc_id or ""
            elif field == "sfdc_status":
                value = lead.sfdc_status or ""
            elif field == "sfdc_error":
                value = lead.sfdc_error or ""
            elif field == "sent_at":
                value = email_record.sent_at.isoformat() if email_record and email_record.sent_at else ""
            elif field == "email_generated_at":
                value = email_record.generated_at.strftime("%d.%m.%y %H:%M") if email_record and email_record.generated_at else ""
            elif field == "created_at":
                value = lead.created_at.isoformat() if lead.created_at else ""
            elif field in ["instagram", "tiktok", "facebook", "linkedin", "twitter"]:
                social_links = lead.enrichment_data.get("social_links", {})
                value = social_links.get(field, "")
            elif field == "social_links":
                social_links = lead.enrichment_data.get("social_links", {})
                value = ", ".join([f"{k}: {v}" for k, v in social_links.items()])

            row.append(value)

        writer.writerow(row)

    # Generate dynamic filename: B2B + tab_name + datum + uhrzeit + LeadAgent
    from datetime import datetime
    now = datetime.now()
    date_str = now.strftime("%d-%m-%Y")
    time_str = now.strftime("%H:%M:%S")

    # Determine the tab label based on the requested email_status
    tab_label = "All-Leads"
    if email_status == "new":
        tab_label = "New-Leads"
    elif email_status == "drafted":
        tab_label = "Drafted-Emails"
    elif email_status == "sent":
        tab_label = "Sent-Emails"

    # Precise format as requested: B2B_[TabName]_[Date]_[Time]_LeadAgent.csv
    filename = f"B2B_{tab_label}_{date_str}_{time_str}_LeadAgent.csv"

    # Return CSV response
    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/run/{run_id}/logs")
def get_run_logs(run_id: str, db: Session = Depends(get_db)):
    """Get logs for a run."""
    logs = db.query(Log).filter(Log.run_id == run_id).order_by(Log.created_at.desc()).all()

    return [
        {
            "id": log.id,
            "level": log.level.value,
            "message": log.message,
            "lead_id": log.lead_id,
            "context": log.context,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]
