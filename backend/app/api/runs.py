from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.run import RunCreate, RunResponse, RunSummary
from app.models import Run, RunStatus, Lead, Email, Log
from app.jobs.queue import job_queue

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.post("/", response_model=RunResponse, status_code=201)
async def create_run(run_data: RunCreate, db: Session = Depends(get_db)):
    """Create a new lead generation run."""
    # Create run in database
    run = Run(
        location=run_data.location,
        category=run_data.category,
        require_approval=int(run_data.require_approval),
        dry_run=int(run_data.dry_run),
        status=RunStatus.QUEUED,
        selected_providers=run_data.providers or [],
        provider_limits=run_data.provider_limits or {},
    )

    db.add(run)
    db.commit()
    db.refresh(run)

    # Enqueue for processing
    job_queue.enqueue(run.id)

    return RunResponse(
        id=run.id,
        status=run.status,
        location=run.location,
        category=run.category,
        require_approval=bool(run.require_approval),
        dry_run=bool(run.dry_run),
        total_leads=run.total_leads,
        total_emails=run.total_emails or 0,
        total_websites=run.total_websites or 0,
        selected_providers=run.selected_providers or [],
        provider_limits=run.provider_limits or {},
        error_message=run.error_message,
        created_at=run.created_at,
        updated_at=run.updated_at,
        completed_at=run.completed_at,
    )


@router.get("/", response_model=List[RunSummary])
def list_runs(db: Session = Depends(get_db)):
    """List all runs."""
    runs = db.query(Run).order_by(Run.created_at.desc()).all()

    return [
        RunSummary(
            id=run.id,
            status=run.status,
            location=run.location,
            category=run.category,
            total_leads=run.total_leads,
            total_emails=run.total_emails or 0,
            total_websites=run.total_websites or 0,
            created_at=run.created_at,
        )
        for run in runs
    ]


@router.get("/{run_id}", response_model=RunResponse)
def get_run(run_id: str, db: Session = Depends(get_db)):
    """Get run details."""
    run = db.query(Run).filter(Run.id == run_id).first()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return RunResponse(
        id=run.id,
        status=run.status,
        location=run.location,
        category=run.category,
        require_approval=bool(run.require_approval),
        dry_run=bool(run.dry_run),
        total_leads=run.total_leads,
        total_emails=run.total_emails or 0,
        total_websites=run.total_websites or 0,
        selected_providers=run.selected_providers or [],
        provider_limits=run.provider_limits or {},
        error_message=run.error_message,
        created_at=run.created_at,
        updated_at=run.updated_at,
        completed_at=run.completed_at,
    )


@router.delete("/{run_id}", status_code=204)
def delete_run(run_id: str, db: Session = Depends(get_db)):
    """Delete a run and all associated data (leads, emails, logs)."""
    # Find the run
    run = db.query(Run).filter(Run.id == run_id).first()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    try:
        # Get lead IDs first
        lead_ids = [l.id for l in db.query(Lead).filter(Lead.run_id == run_id).all()]

        # Delete associated data in correct order (foreign key constraints)
        db.query(Log).filter(Log.run_id == run_id).delete(synchronize_session=False)
        if lead_ids:
            db.query(Email).filter(Email.lead_id.in_(lead_ids)).delete(synchronize_session=False)
        db.query(Lead).filter(Lead.run_id == run_id).delete(synchronize_session=False)

        # Delete the run itself
        db.delete(run)
        db.commit()

        print(f"Successfully deleted run {run_id}")

    except Exception as e:
        db.rollback()
        print(f"Error deleting run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete run: {str(e)}")

    return None
