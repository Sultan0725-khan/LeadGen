from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, List


class LeadResponse(BaseModel):
    """Schema for lead response."""
    id: str
    run_id: str
    business_name: str
    address: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    confidence_score: float
    sources: List[str]
    enrichment_data: Dict
    notes: Optional[str] = None
    created_at: datetime
    email_status: Optional[str] = None  # From related email record
    email_id: Optional[str] = None

    class Config:
        from_attributes = True


class LeadUpdate(BaseModel):
    """Schema for updating lead info."""
    business_name: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
