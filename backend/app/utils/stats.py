from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.run import Run
from app.models.lead import Lead
from app.models.email import Email, EmailStatus

def refresh_run_stats(run_id: str, db: Session):
    """
    Update all run-level statistics from current database state.
    This should be called whenever a lead or email status changes.
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        return

    # Leads count
    run.total_leads = db.query(Lead).filter(Lead.run_id == run.id).count()

    # Website count
    run.total_websites = db.query(Lead).filter(
        Lead.run_id == run.id,
        Lead.website != None,
        Lead.website != ""
    ).count()

    # Email Found count
    run.total_emails = db.query(Lead).filter(
        Lead.run_id == run.id,
        Lead.email != None,
        Lead.email != ""
    ).count()

    # Drafts count (Unique leads with a Generated non-failed, non-pending email)
    run.total_drafts = db.query(func.count(func.distinct(Lead.id))).join(Email).filter(
        Lead.run_id == run.id,
        Email.status.in_([EmailStatus.DRAFTED, EmailStatus.APPROVED])
    ).scalar() or 0

    # Sent count (Unique leads with a sent email/SFDX)
    run.total_sent = db.query(func.count(func.distinct(Lead.id))).join(Email).filter(
        Lead.run_id == run.id,
        Email.status.in_([EmailStatus.SENT, EmailStatus.SFDX])
    ).scalar() or 0

    db.commit()
