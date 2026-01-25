import httpx
from typing import List, Tuple
from app.providers.base import BaseProvider, RawLead
from app.provider_config import provider_config


class TomTomProvider(BaseProvider):
    """TomTom Search API provider."""

    TOMTOM_BASE_URL = "https://api.tomtom.com/search/2/poiSearch"

    @property
    def id(self) -> str:
        return "tomtom"

    @property
    def name(self) -> str:
        return "TomTom"

    def is_available(self) -> bool:
        """Check if API key is configured."""
        api_key = provider_config.get_api_key("tomtom")
        return api_key is not None and provider_config.is_provider_enabled("tomtom")

    async def search(self, location: str, category: str, **kwargs) -> List[RawLead]:
        """Search TomTom for businesses."""
        api_key = provider_config.get_api_key("tomtom")
        if not api_key:
            print("TomTom: No API key configured")
            return []

        limit = kwargs.get("limit", 100)

        # Build query
        query = f"{category} in {location}"

        params = {
            "key": api_key,
            "limit": limit,
            "typeahead": "false"
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.TOMTOM_BASE_URL}/{query}.json"
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            # Parse results
            leads = []
            for result in data.get("results", []):
                lead = self._parse_result(result)
                if lead:
                    leads.append(lead)

            return leads

        except Exception as e:
            print(f"TomTom error: {e}")
            return []

    def _parse_result(self, result: dict) -> RawLead | None:
        """Parse TomTom result to RawLead."""
        poi = result.get("poi", {})
        name = poi.get("name")
        if not name:
            return None

        # Extract coordinates
        position = result.get("position", {})
        lat = position.get("lat")
        lon = position.get("lon")

        # Extract address
        address_obj = result.get("address", {})
        address = address_obj.get("freeformAddress")

        # Extract contact info
        # TomTom POI details might contain phone/website
        phone = None
        website = None

        # Some TomTom results have contact info under 'poi'
        if "phone" in poi:
            phone = poi["phone"]
        if "url" in poi:
            website = poi["url"]

        return RawLead(
            business_name=name,
            address=address,
            latitude=lat,
            longitude=lon,
            phone=phone,
            website=website,
            additional_data={
                "tomtom_id": result.get("id"),
                "categories": poi.get("categories"),
                "classification": poi.get("classifications"),
            }
        )

    def get_rate_limit(self) -> Tuple[int, int]:
        """TomTom rate limit: 2500 requests per day."""
        return (5, 1)  # Conservative 5 req/sec
