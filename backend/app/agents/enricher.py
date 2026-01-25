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

        print(f"Enriching {lead.get('business_name')} from {website}")

        # Crawl homepage (now returns soup and actual successful URL)
        result = await self.crawler.crawl_homepage(website)

        if not result:
            print(f"Could not crawl {website} (tried all variants)")
            return {}

        soup, actual_url = result

        # Extract all contact information from homepage
        enrichment_data = self.extractor.extract_all(soup, actual_url)

        # If no email found on homepage, try subpages
        if not enrichment_data.get("emails"):
            contact_links = self.crawler.find_contact_links(soup, actual_url)
            if contact_links:
                print(f"No emails on homepage of {lead.get('business_name')}, checking subpages: {contact_links}")
                for link in contact_links:
                    sub_result = await self.crawler.crawl_homepage(link)
                    if sub_result:
                        sub_soup, sub_url = sub_result
                        sub_data = self.extractor.extract_all(sub_soup, link)
                        # Merge data
                        enrichment_data["emails"].extend(sub_data.get("emails", []))
                        enrichment_data["phones"].extend(sub_data.get("phones", []))
                        enrichment_data["social_links"].update(sub_data.get("social_links", {}))

                        # Stop if we found an email
                        if enrichment_data["emails"]:
                            print(f"Found email on subpage {link}")
                            break

        # Deduplicate
        enrichment_data["emails"] = list(set(enrichment_data.get("emails", [])))
        enrichment_data["phones"] = list(set(enrichment_data.get("phones", [])))

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
