from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.run import RunCreate, RunResponse, RunSummary
from app.models import Run, RunStatus
from app.jobs.queue import job_queue
import asyncio

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
    )

    db.add(run)
    db.commit()
    db.refresh(run)

    # Enqueue for processing
    await job_queue.enqueue(run.id)

    return RunResponse(
        id=run.id,
        status=run.status,
        location=run.location,
        category=run.category,
        require_approval=bool(run.require_approval),
        dry_run=bool(run.dry_run),
        total_leads=run.total_leads,
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
        error_message=run.error_message,
        created_at=run.created_at,
        updated_at=run.updated_at,
        completed_at=run.completed_at,
    )
