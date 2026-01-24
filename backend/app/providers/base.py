from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class RawLead:
    """Raw lead data from a provider before normalization."""
    business_name: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    phone: str | None = None
    website: str | None = None
    email: str | None = None
    additional_data: Dict[str, Any] | None = None


class BaseProvider(ABC):
    """Base interface for lead source providers."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique provider ID (matches config)."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for tracking provenance."""
        pass

    @abstractmethod
    async def search(self, location: str, category: str, **kwargs) -> List[RawLead]:
        """
        Search for businesses matching location and category.

        Args:
            location: Geographic location (city, address, coordinates)
            category: Business category (restaurant, café, etc.)
            **kwargs: Additional provider-specific parameters

        Returns:
            List of raw leads
        """
        pass

    @abstractmethod
    def get_rate_limit(self) -> Tuple[int, int]:
        """
        Return rate limit as (requests, per_seconds).

        Returns:
            Tuple of (max_requests, time_window_seconds)
        """
        pass

    def is_available(self) -> bool:
        """Check if provider is configured and available."""
        return True
