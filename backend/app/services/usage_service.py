from sqlalchemy.orm import Session
from datetime import date
from app.models import ProviderUsage
from app.provider_config import provider_config

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
