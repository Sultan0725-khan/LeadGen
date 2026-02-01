import asyncio
import os
import sys

# Add the backend directory to sys.path to import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.providers.crawl4ai_provider import Crawl4AIProvider

async def test_crawl4ai():
    print("Testing Crawl4AIProvider...")
    provider = Crawl4AIProvider()

    # Increase limit for testing
    leads = await provider.search(location="Berlin", category="Restaurant", limit=5)

    print(f"\nFound {len(leads)} leads:")
    for i, lead in enumerate(leads):
        print(f"{i+1}. {lead.business_name}")
        print(f"   Address: {lead.address}")
        print(f"   Website: {lead.website}")
        print(f"   Email:   {lead.email}")
        print(f"   Rating:  {lead.additional_data.get('rating')} ({lead.additional_data.get('review_count')} reviews)")
        if lead.additional_data.get('screenshot_path'):
            print(f"   Screenshot: {lead.additional_data.get('screenshot_path')}")
        print("-" * 20)

if __name__ == "__main__":
    asyncio.run(test_crawl4ai())
