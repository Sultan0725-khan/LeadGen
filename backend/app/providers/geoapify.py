import httpx
from typing import List
from app.providers.base import BaseProvider, RawLead
from app.provider_config import provider_config


class GeoapifyProvider(BaseProvider):
    """Geoapify Places API provider (OSM-based)."""

    GEOAPIFY_BASE_URL = "https://api.geoapify.com/v2/places"

    @property
    def id(self) -> str:
        return "geoapify"

    @property
    def name(self) -> str:
        return "Geoapify"

    def is_available(self) -> bool:
        """Check if API key is configured."""
        api_key = provider_config.get_api_key("geoapify")
        return api_key is not None and provider_config.is_provider_enabled("geoapify")

    async def search(self, location: str, category: str, **kwargs) -> List[RawLead]:
        """Search Geoapify for businesses."""
        limit = kwargs.get("limit", 100)
        api_key = provider_config.get_api_key("geoapify")
        if not api_key:
            print("Geoapify: No API key configured")
            return []

        # Build category filter
        categories = self._map_category(category)

        # Geocode location first to get coordinates
        try:
            coords = await self._geocode_location(location, api_key)
            if not coords:
                print(f"Geoapify: Could not geocode location: {location}")
                return []

            lat, lon = coords

            # Search for places near coordinates
            params = {
                "categories": categories,
                "filter": f"circle:{lon},{lat},10000",  # 10km radius
                "limit": limit,
                "apiKey": api_key
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.GEOAPIFY_BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

            # Parse results
            leads = []
            for feature in data.get("features", []):
                lead = self._parse_feature(feature)
                if lead:
                    leads.append(lead)

            return leads

        except Exception as e:
            print(f"Geoapify error: {e}")
            return []

    async def _geocode_location(self, location: str, api_key: str) -> tuple[float, float] | None:
        """Geocode location string to coordinates."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.geoapify.com/v1/geocode/search",
                    params={"text": location, "apiKey": api_key, "limit": 1}
                )
                response.raise_for_status()
                data = response.json()

                if data.get("features"):
                    coords = data["features"][0]["geometry"]["coordinates"]
                    return coords[1], coords[0]  # lat, lon
                return None
        except Exception as e:
            print(f"Geoapify geocoding error: {e}")
            return None

    def _map_category(self, category: str) -> str:
        """Map generic category to Geoapify category."""
        category_map = {
            "restaurant": "catering.restaurant",
            "cafe": "catering.cafe",
            "café": "catering.cafe",
            "bar": "catering.bar",
            "hotel": "accommodation.hotel",
            "bakery": "commercial.food_and_drink",
        }

        category_lower = category.lower()
        return category_map.get(category_lower, "catering.restaurant")

    def _parse_feature(self, feature: dict) -> RawLead | None:
        """Parse Geoapify feature to RawLead."""
        properties = feature.get("properties", {})

        # Extract name
        name = properties.get("name")
        if not name:
            return None

        # Extract coordinates
        coords = feature.get("geometry", {}).get("coordinates", [])
        lon = coords[0] if len(coords) > 0 else None
        lat = coords[1] if len(coords) > 1 else None

        # Extract address
        address_parts = []
        if properties.get("street"):
            address_parts.append(properties["street"])
        if properties.get("city"):
            address_parts.append(properties["city"])
        if properties.get("postcode"):
            address_parts.append(properties["postcode"])

        address = ", ".join(address_parts) if address_parts else None

        # Extract contact info
        contact = properties.get("contact", {})
        phone = contact.get("phone")
        website = contact.get("website")
        email = contact.get("email")

        return RawLead(
            business_name=name,
            address=address,
            latitude=lat,
            longitude=lon,
            phone=phone,
            website=website,
            email=email,
            additional_data={
                "geoapify_id": properties.get("place_id"),
                "categories": properties.get("categories"),
            }
        )

    def calculate_credits(self, **kwargs) -> int:
        """
        Geoapify credits calculation:
        - Geocoding API: 1 credit
        - Places API: 1 credit per 20 places
        """
        limit = kwargs.get("limit", 1)
        import math
        places_credits = math.ceil(limit / 20)
        return 1 + places_credits  # 1 for geocoding + places credits

    def get_rate_limit(self) -> tuple[int, int]:
        """Geoapify rate limit: 3000 requests per day, ~2 per second."""
        return (2, 1)
