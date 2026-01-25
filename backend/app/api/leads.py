from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.schemas.lead import LeadResponse
from app.models import Lead, Email
from pydantic import BaseModel

router = APIRouter(prefix="/api/leads", tags=["leads"])


class LeadListResponse(BaseModel):
    """Paginated lead list response."""
    leads: List[LeadResponse]
    total: int
    page: int
    per_page: int


@router.get("/run/{run_id}", response_model=LeadListResponse)
def get_run_leads(
    run_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    min_score: Optional[float] = Query(None, ge=0, le=1),
    email_status: Optional[str] = None,
    has_email: Optional[bool] = None,
    has_website: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get leads for a run with pagination and filters."""
    # Build query with optional join for email status filtering
    query = db.query(Lead).outerjoin(Email, Lead.id == Email.lead_id)
    query = query.filter(Lead.run_id == run_id)

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
        from app.models.email import EmailStatus
        query = query.filter((Email.id == None) | (Email.status.in_([EmailStatus.FAILED, EmailStatus.PENDING_APPROVAL])))
    elif email_status == "drafted":
        from app.models.email import EmailStatus
        query = query.filter(Email.status.in_([
            EmailStatus.DRAFTED,
            EmailStatus.APPROVED,
            EmailStatus.SENT
        ]))
    elif email_status:
        query = query.filter(Email.status == email_status)

    # Get total count BEFORE pagination
    total = query.count()

    # Apply pagination
    offset = (page - 1) * per_page
    leads = query.order_by(Lead.confidence_score.desc()).offset(offset).limit(per_page).all()

    # Build response with email status
    lead_responses = []
    for lead in leads:
        email_record = db.query(Email).filter(Email.lead_id == lead.id).first()

        lead_response = LeadResponse(
            id=lead.id,
            run_id=lead.run_id,
            business_name=lead.business_name,
            address=lead.address,
            website=lead.website,
            email=lead.email,
            phone=lead.phone,
            latitude=lead.latitude,
            longitude=lead.longitude,
            confidence_score=lead.confidence_score,
            sources=lead.sources,
            enrichment_data=lead.enrichment_data,
            created_at=lead.created_at,
            email_status=email_record.status.value if email_record else None,
            email_id=email_record.id if email_record else None,
        )
        lead_responses.append(lead_response)

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

    return LeadResponse(
        id=lead.id,
        run_id=lead.run_id,
        business_name=lead.business_name,
        address=lead.address,
        website=lead.website,
        email=lead.email,
        phone=lead.phone,
        latitude=lead.latitude,
        longitude=lead.longitude,
        confidence_score=lead.confidence_score,
        sources=lead.sources,
        enrichment_data=lead.enrichment_data,
        created_at=lead.created_at,
        email_status=email_record.status.value if email_record else None,
        email_id=email_record.id if email_record else None,
    )
