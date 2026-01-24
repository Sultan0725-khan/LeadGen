from pydantic import BaseModel
from typing import List, Optional


class ProviderInfo(BaseModel):
    """Schema for provider information."""
    id: str
    name: str
    description: str
    enabled: bool
    requires_api_key: bool
    free_tier: bool
    daily_limit: str
    quota_limit: int
    quota_used: int
    quota_period: str
    quota_available: int
    query_limit: int
    statistics_url: Optional[str] = None
