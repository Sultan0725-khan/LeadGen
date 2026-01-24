from pydantic import BaseModel
from datetime import datetime
from typing import Optional
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
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True
