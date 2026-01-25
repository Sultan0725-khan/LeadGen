from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from app.database import get_db
from app.schemas.email import EmailResponse, EmailDraftRequest, EmailUpdateRequest
from app.models import Email, EmailStatus, Lead, Run
from app.agents.email_sender import EmailSender
from app.agents.orchestrator import AgentOrchestrator
from app.utils.timezone import get_german_now
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
    db.commit()
    db.refresh(email)
    return email


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
    else:
        email.status = EmailStatus.FAILED
        email.error_message = error

    db.commit()
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
    return email
