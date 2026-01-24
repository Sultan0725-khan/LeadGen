from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.run import RunStatus


class RunCreate(BaseModel):
    """Schema for creating a new run."""
    location: str
    category: str
    require_approval: bool = False
    dry_run: bool = False


class RunResponse(BaseModel):
    """Schema for run response."""
    id: str
    status: RunStatus
    location: str
    category: str
    require_approval: bool
    dry_run: bool
    total_leads: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RunSummary(BaseModel):
    """Summary schema for runs list."""
    id: str
    status: RunStatus
    location: str
    category: str
    total_leads: int
    created_at: datetime

    class Config:
        from_attributes = True
