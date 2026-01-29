from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Annotated
from app.database import get_db
from app.schemas.lead import LeadResponse, LeadUpdate
from app.models import Lead, Email, EmailStatus
from app.config import settings
from pydantic import BaseModel

router = APIRouter(prefix="/api/leads", tags=["leads"])


class LeadListResponse(BaseModel):
    """Paginated lead list response."""
    leads: List[LeadResponse]
    total: int
    page: int
    per_page: int


def _to_response(lead: Lead, email_record: Optional[Email]) -> LeadResponse:
    """Helper to convert Lead model to LeadResponse schema."""
    return LeadResponse(
        id=lead.id,
        run_id=lead.run_id,
        business_name=lead.business_name,
        first_name=lead.first_name,
        last_name=lead.last_name,
        address=lead.address,
        website=lead.website,
        email=lead.email,
        phone=lead.phone,
        latitude=lead.latitude,
        longitude=lead.longitude,
        confidence_score=lead.confidence_score,
        sources=lead.sources,
        enrichment_data=lead.enrichment_data,
        notes=lead.notes,
        created_at=lead.created_at,
        email_status=email_record.status.value if email_record else None,
        email_id=email_record.id if email_record else None,
        email_error=email_record.error_message if email_record else None,
        sfdc_status=lead.sfdc_status,
        sfdc_id=lead.sfdc_id,
        sfdc_error=lead.sfdc_error,
        sfdc_instance_url=settings.sfdc_instance_url
    )


@router.get("/run/{run_id}", response_model=LeadListResponse)
def get_run_leads(
    run_id: str,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=200)] = 50,
    min_score: Annotated[Optional[float], Query(ge=0, le=1)] = None,
    email_status: Optional[str] = None,
    has_email: Optional[bool] = None,
    has_website: Optional[bool] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get leads for a run with pagination and filters."""
    # Build query with optional join for email status filtering
    query = db.query(Lead).outerjoin(Email, Lead.id == Email.lead_id)
    query = query.filter(Lead.run_id == run_id)

    if q:
        query = query.filter(Lead.business_name.ilike(f"%{q}%"))

    # Apply filters
    if min_score is not None:
        query = query.filter(Lead.confidence_score >= min_score)

    if has_email is True:
        query = query.filter(Lead.email != None)
    elif has_email is False:
        query = query.filter(Lead.email == None)

    if has_website is True:
        query = query.filter(Lead.website != None)
    elif has_website is False:
        query = query.filter(Lead.website == None)

    # Email status filtering (server-side for proper pagination)
    if email_status == "new":
        query = query.filter((Email.id == None) | (Email.status.in_([EmailStatus.FAILED, EmailStatus.PENDING_APPROVAL])))
    elif email_status == "drafted":
        query = query.filter(Email.status.in_([
            EmailStatus.DRAFTED,
            EmailStatus.APPROVED
        ]))
    elif email_status == "sent":
        query = query.filter(Email.status.in_([EmailStatus.SENT, EmailStatus.SFDX]))
    elif email_status:
        query = query.filter(Email.status == email_status)

    # Get total count BEFORE pagination
    total = query.count()

    # Apply pagination and sorting
    offset = (page - 1) * per_page

    if email_status == "sent":
        # Sort by latest email activity
        leads = query.order_by(Email.sent_at.desc()).offset(offset).limit(per_page).all()
    elif email_status == "drafted":
        # Sort by latest generated draft
        leads = query.order_by(Email.generated_at.desc()).offset(offset).limit(per_page).all()
    else:
        leads = query.order_by(Lead.confidence_score.desc()).offset(offset).limit(per_page).all()

    # Build response with email status
    lead_responses = []
    for lead in leads:
        email_record = db.query(Email).filter(Email.lead_id == lead.id).first()
        lead_responses.append(_to_response(lead, email_record))

    return LeadListResponse(
        leads=lead_responses,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: str, db: Session = Depends(get_db)):
    """Get a specific lead."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    email_record = db.query(Email).filter(Email.lead_id == lead.id).first()
    return _to_response(lead, email_record)


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(lead_id: str, lead_update: LeadUpdate, db: Session = Depends(get_db)):
    """Update a specific lead."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Update fields
    update_data = lead_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(lead, key, value)

    db.commit()
    db.refresh(lead)

    email_record = db.query(Email).filter(Email.lead_id == lead.id).first()
    return _to_response(lead, email_record)
