from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.schemas.email import EmailResponse
from app.models import Email, EmailStatus, Lead, Run
from app.agents.email_sender import EmailSender
import asyncio

router = APIRouter(prefix="/api/emails", tags=["emails"])


@router.post("/{email_id}/approve")
async def approve_email(email_id: str, db: Session = Depends(get_db)):
    """Approve an email for sending."""
    email = db.query(Email).filter(Email.id == email_id).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    if email.status != EmailStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=400, detail="Email is not pending approval")

    email.status = EmailStatus.APPROVED
    db.commit()

    # Get run to check if we should send immediately
    lead = db.query(Lead).filter(Lead.id == email.lead_id).first()
    run = db.query(Run).filter(Run.id == lead.run_id).first()

    # Send if not dry run
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
            email.sent_at = datetime.utcnow()
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

    return EmailResponse(
        id=email.id,
        lead_id=email.lead_id,
        status=email.status,
        subject=email.subject,
        body=email.body,
        language=email.language,
        generated_at=email.generated_at,
        sent_at=email.sent_at,
        error_message=email.error_message,
    )
