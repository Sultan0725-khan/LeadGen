import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.enrichment.website_crawler import WebsiteCrawler
from app.agents.enricher import Enricher

async def test_resilience(url):
    print(f"Testing crawler resilience for: {url}")
    crawler = WebsiteCrawler()

    # 1. Test variant generation
    variants = crawler.generate_url_variants(url)
    print(f"Generated variants: {variants}")

    # 2. Test actual crawling
    result = await crawler.crawl_homepage(url)
    if result:
        soup, actual_url = result
        print(f"✅ SUCCESSFULLY reached {actual_url}")

        # 3. Test enrichment flow
        enricher = Enricher()
        lead = {"business_name": "Test Restaurant", "website": url}
        data = await enricher.enrich(lead)
        print(f"Enriched Data: {data}")
    else:
        print(f"❌ FAILED to reach any variant for {url}")

if __name__ == "__main__":
    # Test with the user's problematic URL (WITHOUT scheme to see if it generates correctly)
    target = "restaurant-lindos-bremen.de"
    asyncio.run(test_resilience(target))
