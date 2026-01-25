import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.enrichment.website_crawler import WebsiteCrawler
from app.enrichment.contact_extractor import ContactExtractor

async def test_crawler(url):
    print(f"Testing crawler on: {url}")
    crawler = WebsiteCrawler()
    extractor = ContactExtractor()

    # 1. Fetch homepage
    soup = await crawler.crawl_homepage(url)
    if not soup:
        print("Failed to fetch homepage")
        return

    # 2. Find contact/info links
    contact_links = crawler.find_contact_links(soup, url)
    print(f"Found {len(contact_links)} candidate info links: {contact_links}")

    # 3. Extract from homepage
    print("\n--- Homepage Data ---")
    data = extractor.extract_all(soup, url)
    print(f"Emails: {data['emails']}")
    print(f"Phones: {data['phones']}")
    print(f"Social: {data['social_links']}")

    # 4. Extract from subpages
    for link in contact_links:
        print(f"\n--- Checking subpage: {link} ---")
        sub_html = await crawler.fetch_page(link)
        if sub_html:
            from bs4 import BeautifulSoup
            sub_soup = BeautifulSoup(sub_html, 'lxml')
            sub_data = extractor.extract_all(sub_soup, link)
            print(f"Emails: {sub_data['emails']}")
            print(f"Phones: {sub_data['phones']}")
            print(f"Social: {sub_data['social_links']}")

if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.digitalinberlin.de/"
    asyncio.run(test_crawler(target_url))
