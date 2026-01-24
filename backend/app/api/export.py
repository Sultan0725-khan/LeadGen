from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Lead, Email, Log
import csv
import io

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/run/{run_id}/csv")
def export_run_csv(run_id: str, db: Session = Depends(get_db)):
    """Export run leads to CSV."""
    # Get all leads for the run
    leads = db.query(Lead).filter(Lead.run_id == run_id).all()

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
        email_status = email_record.status.value if email_record else "none"

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
            email_status,
            social_str,
        ])

    # Return CSV response
    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=leads_{run_id}.csv"}
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
