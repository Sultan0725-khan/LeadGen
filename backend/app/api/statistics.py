from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime, timedelta
from typing import Dict, Optional
import httpx

from app.database import get_db
from app.models import ProviderUsage, Run, Lead
from app.provider_config import provider_config

router = APIRouter(prefix="/api/stats", tags=["statistics"])


@router.get("/providers/{provider_id}")
async def get_provider_stats(provider_id: str, db: Session = Depends(get_db)):
    """Get usage statistics for a specific provider."""
    today = date.today()

    # Get today's usage from database
    usage = db.query(ProviderUsage).filter(
        ProviderUsage.provider_id == provider_id,
        ProviderUsage.date == today
    ).first()

    provider_cfg = provider_config.get_provider_config(provider_id)
    if not provider_cfg:
        raise HTTPException(status_code=404, detail="Provider not found")

    quota_limit = provider_cfg.get("quota_limit", 0)
    usage_count = usage.usage_count if usage else 0

    return {
        "provider_id": provider_id,
        "date": today.isoformat(),
        "usage_count": usage_count,
        "quota_limit": quota_limit,
        "quota_available": max(0, quota_limit - usage_count) if quota_limit > 0 else 999999,
        "quota_period": provider_cfg.get("quota_period", "daily")
    }


@router.post("/providers/{provider_id}/refresh")
async def refresh_provider_stats(provider_id: str, db: Session = Depends(get_db)):
    """Refresh statistics from external API (e.g., Geoapify)."""
    provider_cfg = provider_config.get_provider_config(provider_id)
    if not provider_cfg:
        raise HTTPException(status_code=404, detail="Provider not found")

    stats_url = provider_cfg.get("statistics_url")
    if not stats_url:
        raise HTTPException(status_code=400, detail="Provider does not have statistics URL")

    try:
        # Fetch from external API
        async with httpx.AsyncClient() as client:
            response = await client.get(stats_url, timeout=10.0)
            response.raise_for_status()
            external_stats = response.json()

        # Update database (implementation depends on API response structure)
        # This is a placeholder - adapt based on actual Geoapify response
        today = date.today()
        usage = db.query(ProviderUsage).filter(
            ProviderUsage.provider_id == provider_id,
            ProviderUsage.date == today
        ).first()

        if not usage:
            usage = ProviderUsage(
                provider_id=provider_id,
                date=today,
                quota_limit=provider_cfg.get("quota_limit", 0)
            )
            db.add(usage)

        # Extract usage from external stats (adjust based on actual API)
        if "usage" in external_stats:
            usage.usage_count = external_stats["usage"]

        db.commit()

        return {
            "success": True,
            "provider_id": provider_id,
            "external_stats": external_stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")


@router.get("/dashboard")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get overall dashboard statistics."""
    # Count total non-null emails and websites across all leads
    total_emails = db.query(func.count(Lead.id)).filter(
        Lead.email.isnot(None),
        Lead.email != ""
    ).scalar() or 0

    total_websites = db.query(func.count(Lead.id)).filter(
        Lead.website.isnot(None),
        Lead.website != ""
    ).scalar() or 0

    # Total leads
    total_leads = db.query(func.count(Lead.id)).scalar() or 0

    # Total runs
    total_runs = db.query(func.count(Run.id)).scalar() or 0

    # Recent runs (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_runs = db.query(func.count(Run.id)).filter(
        Run.created_at >= week_ago
    ).scalar() or 0

    return {
        "total_leads": total_leads,
        "total_emails": total_emails,
        "total_websites": total_websites,
        "total_runs": total_runs,
        "recent_runs": recent_runs,
        "email_coverage": round((total_emails / total_leads * 100), 1) if total_leads > 0 else 0,
        "website_coverage": round((total_websites / total_leads * 100), 1) if total_leads > 0 else 0
    }


async def increment_provider_usage(provider_id: str, db: Session, count: int = 1):
    """Helper function to increment provider usage count."""
    today = date.today()

    usage = db.query(ProviderUsage).filter(
        ProviderUsage.provider_id == provider_id,
        ProviderUsage.date == today
    ).first()

    provider_cfg = provider_config.get_provider_config(provider_id)
    quota_limit = provider_cfg.get("quota_limit", 0) if provider_cfg else 0

    if not usage:
        usage = ProviderUsage(
            provider_id=provider_id,
            date=today,
            usage_count=count,
            quota_limit=quota_limit
        )
        db.add(usage)
    else:
        usage.usage_count += count

    db.commit()
    return usage


async def check_provider_quota(provider_id: str, db: Session) -> bool:
    """Check if provider has available quota. Returns True if available, False if exceeded."""
    provider_cfg = provider_config.get_provider_config(provider_id)
    if not provider_cfg:
        return False

    quota_limit = provider_cfg.get("quota_limit", 0)
    if quota_limit == 0:  # Unlimited
        return True

    today = date.today()
    usage = db.query(ProviderUsage).filter(
        ProviderUsage.provider_id == provider_id,
        ProviderUsage.date == today
    ).first()

    usage_count = usage.usage_count if usage else 0
    return usage_count < quota_limit
