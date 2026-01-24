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
    db: Session = Depends(get_db)
):
    """Get leads for a run with pagination and filters."""
    # Build query
    query = db.query(Lead).filter(Lead.run_id == run_id)

    # Apply filters
    if min_score is not None:
        query = query.filter(Lead.confidence_score >= min_score)

    # Get total count
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
        )
        lead_responses.append(lead_response)

    # Filter by email status if requested
    if email_status:
        lead_responses = [l for l in lead_responses if l.email_status == email_status]

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
    )
