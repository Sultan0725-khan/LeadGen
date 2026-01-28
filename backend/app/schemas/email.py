from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from app.models.email import EmailStatus


class EmailResponse(BaseModel):
    """Schema for email response."""
    id: str
    lead_id: str
    status: EmailStatus
    subject: str
    body: str
    language: str
    generated_at: datetime
    recipient_email: Optional[str] = None
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class EmailDraftRequest(BaseModel):
    """Request to draft emails for specific leads."""
    lead_ids: List[str]
    language: str = "DE"


class EmailUpdateRequest(BaseModel):
    """Request to update an email draft."""
    subject: str
    body: str
    recipient_email: Optional[str] = None


class EmailRedraftRequest(BaseModel):
    """Request to refine an email draft with a prompt."""
    prompt: str
