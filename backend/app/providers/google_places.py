import httpx
from typing import List, Tuple
from app.providers.base import BaseProvider, RawLead
from app.config import settings
import asyncio


class GooglePlacesProvider(BaseProvider):
    """Google Places API provider."""

    PLACES_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

    @property
    def id(self) -> str:
        return "google_places"

    @property
    def name(self) -> str:
        return "GooglePlaces"

    def is_available(self) -> bool:
        """Check if Google Places API key is configured."""
        api_key = provider_config.get_api_key("google_places") or settings.google_places_api_key
        return api_key is not None and provider_config.is_provider_enabled("google_places")

    async def search(self, location: str, category: str, **kwargs) -> List[RawLead]:
        """Search Google Places for businesses."""
        limit = kwargs.get("limit", 60)
        api_key = provider_config.get_api_key("google_places") or settings.google_places_api_key
        if not api_key:
            print("Google Places API key not configured")
            return []

        query = f"{category} in {location}"
        leads = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            next_page_token = None

            # Google Places returns up to 60 results (3 pages of 20)
            for page in range(3):
                await self._rate_limit()

                params = {
                    "query": query,
                    "key": api_key,
                }

                if next_page_token:
                    params["pagetoken"] = next_page_token

                try:
                    response = await client.get(self.PLACES_TEXT_SEARCH_URL, params=params)
                    response.raise_for_status()
                    data = response.json()
                except Exception as e:
                    print(f"Google Places error: {e}")
                    break

                # Parse results
                for place in data.get("results", []):
                    lead = self._parse_place(place)
                    if lead:
                        leads.append(lead)
                        if len(leads) >= limit:
                            return leads[:limit]

                # Check for next page
                next_page_token = data.get("next_page_token")
                if not next_page_token:
                    break

                # Wait before next page (required by Google)
                await asyncio.sleep(2)

        return leads

    def _parse_place(self, place: dict) -> RawLead | None:
        """Parse Google Places result to RawLead."""
        name = place.get("name")
        if not name:
            return None

        # Extract location
        geometry = place.get("geometry", {})
        location = geometry.get("location", {})
        lat = location.get("lat")
        lng = location.get("lng")

        # Extract address
        address = place.get("formatted_address")

        # Note: Google Places Text Search doesn't include contact info
        # We would need to make a Place Details request for each place
        # For now, we'll mark these as needing enrichment

        return RawLead(
            business_name=name,
            address=address,
            latitude=lat,
            longitude=lng,
            additional_data={
                "google_place_id": place.get("place_id"),
                "rating": place.get("rating"),
                "user_ratings_total": place.get("user_ratings_total"),
                "types": place.get("types", []),
            }
        )

    def get_rate_limit(self) -> Tuple[int, int]:
        """Google Places rate limit varies by quota; be conservative."""
        return (10, 1)  # 10 requests per second

    async def _rate_limit(self):
        """Rate limiting."""
        await asyncio.sleep(0.15)  # Conservative
