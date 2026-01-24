from typing import Dict
from app.enrichment.website_crawler import WebsiteCrawler
from app.enrichment.contact_extractor import ContactExtractor


class Enricher:
    """Tool to enrich leads with website data and social profiles."""

    def __init__(self):
        self.crawler = WebsiteCrawler()
        self.extractor = ContactExtractor()

    async def enrich(self, lead: Dict) -> Dict:
        """
        Enrich a lead with website contact data.

        Returns enrichment data dict with emails, phones, social links.
        """
        website = lead.get("website")

        if not website:
            return {}

        # Ensure website has scheme
        if not website.startswith(('http://', 'https://')):
            website = f'https://{website}'

        print(f"Enriching {lead.get('business_name')} from {website}")

        # Crawl homepage
        soup = await self.crawler.crawl_homepage(website)

        if not soup:
            print(f"Could not crawl {website}")
            return {}

        # Extract all contact information
        enrichment_data = self.extractor.extract_all(soup, website)

        # Filter out already known contacts to avoid duplication
        existing_email = lead.get("email")
        existing_phone = lead.get("phone")

        if existing_email and existing_email in enrichment_data.get("emails", []):
            enrichment_data["emails"].remove(existing_email)

        if existing_phone:
            normalized_existing = self._normalize_phone(existing_phone)
            enrichment_data["phones"] = [
                p for p in enrichment_data.get("phones", [])
                if self._normalize_phone(p) != normalized_existing
            ]

        print(f"Found: {len(enrichment_data.get('emails', []))} emails, "
              f"{len(enrichment_data.get('phones', []))} phones, "
              f"{len(enrichment_data.get('social_links', {}))} social profiles")

        return enrichment_data

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone for comparison."""
        import re
        return re.sub(r'[^\d+]', '', phone)
