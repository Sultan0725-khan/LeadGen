from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from app.models.run import RunStatus


class RunCreate(BaseModel):
    """Schema for creating a new run."""
    location: str
    category: str
    require_approval: bool = False
    dry_run: bool = False
    providers: Optional[List[str]] = None  # Provider IDs to use (e.g., ["openstreetmap", "yelp"])
    provider_limits: Optional[dict] = None  # Dict of provider_id -> query limit


class RunResponse(BaseModel):
    """Schema for run response."""
    id: str
    status: RunStatus
    location: str
    category: str
    require_approval: bool
    dry_run: bool
    total_leads: int
    total_emails: int = 0
    total_websites: int = 0
    selected_providers: Optional[List[str]] = None
    provider_limits: Optional[dict] = None
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
    total_emails: int = 0
    total_websites: int = 0
    created_at: datetime

    class Config:
        from_attributes = True
