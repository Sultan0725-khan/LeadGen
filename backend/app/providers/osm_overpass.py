import httpx
from typing import List, Tuple
from app.providers.base import BaseProvider, RawLead
import asyncio


class OSMOverpassProvider(BaseProvider):
    """OpenStreetMap Overpass API provider."""

    OVERPASS_URL = "https://overpass-api.de/api/interpreter"

    # OSM tag mappings for common categories
    CATEGORY_TAGS = {
        "restaurant": "amenity=restaurant",
        "café": "amenity=cafe",
        "cafe": "amenity=cafe",
        "bar": "amenity=bar",
        "kebab": "cuisine=kebab",
        "pizza": "cuisine=pizza",
        "bakery": "shop=bakery",
        "hotel": "tourism=hotel",
    }

    @property
    def name(self) -> str:
        return "OpenStreetMap"

    async def search(self, location: str, category: str, **kwargs) -> List[RawLead]:
        """Search OSM for businesses via Overpass API."""

        # Build Overpass query
        tag_filter = self._get_tag_filter(category)
        query = self._build_query(location, tag_filter)

        # Execute query with rate limiting
        await self._rate_limit()

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.OVERPASS_URL,
                    data={"data": query}
                )
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                print(f"OSM Overpass error: {e}")
                return []

        # Parse results
        leads = []
        for element in data.get("elements", []):
            lead = self._parse_element(element)
            if lead:
                leads.append(lead)

        return leads

    def _get_tag_filter(self, category: str) -> str:
        """Get OSM tag filter for category."""
        category_lower = category.lower()

        # Check exact matches
        if category_lower in self.CATEGORY_TAGS:
            return self.CATEGORY_TAGS[category_lower]

        # Fallback: search in name or cuisine
        return f"amenity~'restaurant|cafe|bar|fast_food'"

    def _build_query(self, location: str, tag_filter: str) -> str:
        """Build Overpass QL query."""
        # Try to geocode location to get bounding box
        # For simplicity, use a search area by name
        query = f"""
        [out:json][timeout:25];
        area[name="{location}"]->.searchArea;
        (
          node[{tag_filter}](area.searchArea);
          way[{tag_filter}](area.searchArea);
          relation[{tag_filter}](area.searchArea);
        );
        out body;
        >;
        out skel qt;
        """
        return query

    def _parse_element(self, element: dict) -> RawLead | None:
        """Parse OSM element to RawLead."""
        tags = element.get("tags", {})

        # Extract name
        name = tags.get("name")
        if not name:
            return None

        # Extract coordinates
        lat = element.get("lat")
        lon = element.get("lon")

        # For ways/relations, use center coordinates if available
        if not lat and "center" in element:
            lat = element["center"].get("lat")
            lon = element["center"].get("lon")

        # Extract address
        address_parts = []
        if "addr:street" in tags:
            street = tags["addr:street"]
            if "addr:housenumber" in tags:
                street = f"{street} {tags['addr:housenumber']}"
            address_parts.append(street)
        if "addr:city" in tags:
            address_parts.append(tags["addr:city"])
        if "addr:postcode" in tags:
            address_parts.append(tags["addr:postcode"])

        address = ", ".join(address_parts) if address_parts else None

        # Extract contact info
        phone = tags.get("phone") or tags.get("contact:phone")
        website = tags.get("website") or tags.get("contact:website")
        email = tags.get("email") or tags.get("contact:email")

        return RawLead(
            business_name=name,
            address=address,
            latitude=lat,
            longitude=lon,
            phone=phone,
            website=website,
            email=email,
            additional_data={
                "osm_id": element.get("id"),
                "osm_type": element.get("type"),
                "tags": tags,
            }
        )

    def get_rate_limit(self) -> Tuple[int, int]:
        """OSM Overpass rate limit: ~2 requests per second."""
        return (2, 1)

    async def _rate_limit(self):
        """Simple rate limiting with sleep."""
        await asyncio.sleep(0.6)  # ~2 requests/second
