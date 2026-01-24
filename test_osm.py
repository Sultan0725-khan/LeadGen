import asyncio
import sys
sys.path.insert(0, '/Users/sultankhan/.gemini/antigravity/playground/spectral-shepard/LeadGen/backend')

from app.providers.osm_overpass import OSMOverpassProvider

async def test_osm():
    provider = OSMOverpassProvider()
    print(f"Testing OSM Overpass for: Berlin, restaurant")
    leads = await provider.search("Berlin", "restaurant")
    print(f"\nFound {len(leads)} leads:")
    for i, lead in enumerate(leads[:5], 1):
        print(f"{i}. {lead.business_name} - {lead.address}")

asyncio.run(test_osm())
