from typing import List, Type
from app.providers.base import BaseProvider
from app.providers.osm_overpass import OSMOverpassProvider
from app.providers.google_places import GooglePlacesProvider


class ProviderRegistry:
    """Registry of available lead providers."""

    _providers: List[Type[BaseProvider]] = [
        OSMOverpassProvider,
        GooglePlacesProvider,
        # Add more providers here
    ]

    @classmethod
    def get_available_providers(cls) -> List[BaseProvider]:
        """Get all available and configured providers."""
        providers = []
        for provider_class in cls._providers:
            provider = provider_class()
            if provider.is_available():
                providers.append(provider)
        return providers

    @classmethod
    def get_provider_by_name(cls, name: str) -> BaseProvider | None:
        """Get a specific provider by name."""
        for provider_class in cls._providers:
            provider = provider_class()
            if provider.name == name and provider.is_available():
                return provider
        return None
