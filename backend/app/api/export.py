from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Lead, Email, Log
from app.models.email import EmailStatus
from typing import Optional
import csv
import io

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

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        "Business Name",
        "Address",
        "Website",
        "Email",
        "Phone",
        "Latitude",
        "Longitude",
        "Confidence Score",
        "Sources",
        "Email Status",
        "Social Links",
    ])

    # Write data
    for lead in leads:
        email_record = db.query(Email).filter(Email.lead_id == lead.id).first()
        current_lead_status = email_record.status.value if email_record else "none"

        social_links = lead.enrichment_data.get("social_links", {})
        social_str = ", ".join([f"{k}: {v}" for k, v in social_links.items()])

        writer.writerow([
            lead.business_name,
            lead.address or "",
            lead.website or "",
            lead.email or "",
            lead.phone or "",
            lead.latitude or "",
            lead.longitude or "",
            lead.confidence_score,
            ", ".join(lead.sources),
            current_lead_status,
            social_str,
        ])

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
