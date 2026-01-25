from sqlalchemy import Column, String, Integer, Date
from datetime import date
from app.utils.timezone import get_german_now
from app.database import Base


class ProviderUsage(Base):
    """Track API usage for providers with quotas."""
    __tablename__ = "provider_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_id = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False, default=lambda: get_german_now().date(), index=True)
    usage_count = Column(Integer, default=0, nullable=False)
    quota_limit = Column(Integer, nullable=True)  # Daily or monthly limit

    def __repr__(self):
        return f"<ProviderUsage(provider={self.provider_id}, date={self.date}, usage={self.usage_count}/{self.quota_limit})>"
