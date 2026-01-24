from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from typing import List

from app.schemas.provider import ProviderInfo
from app.provider_config import provider_config
from app.database import get_db
from app.models import ProviderUsage

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("/", response_model=List[ProviderInfo])
def list_providers(db: Session = Depends(get_db)):
    """Get list of all available providers with their configuration and current usage."""
    # Get today's usage for all providers
    today = date.today()
    usage_records = db.query(ProviderUsage).filter(
        ProviderUsage.date == today
    ).all()

    usage_data = {record.provider_id: record.usage_count for record in usage_records}

    return provider_config.get_all_providers_info(usage_data)


@router.get("/enabled", response_model=List[str])
def list_enabled_providers():
    """Get list of enabled provider IDs."""
    return provider_config.get_enabled_providers()
