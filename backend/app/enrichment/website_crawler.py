import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from typing import Optional, Dict, List
import asyncio


class WebsiteCrawler:
    """Website crawler that respects robots.txt."""

    def __init__(self):
        self._robots_cache: Dict[str, RobotFileParser] = {}

    async def can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt."""
        try:
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            robots_url = urljoin(base_url, "/robots.txt")

            # Check cache
            if base_url not in self._robots_cache:
                rp = RobotFileParser()
                rp.set_url(robots_url)

                # Fetch robots.txt
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.get(robots_url)
                        if response.status_code == 200:
                            rp.parse(response.text.splitlines())
                        else:
                            # No robots.txt, allow all
                            return True
                except:
                    # Error fetching robots.txt, allow by default
                    return True

                self._robots_cache[base_url] = rp

            rp = self._robots_cache[base_url]
            return rp.can_fetch("*", url)
        except:
            return True  # Allow on error

    async def fetch_page(self, url: str, user_agent: str = "LeadGenBot/1.0") -> Optional[str]:
        """Fetch webpage content if allowed by robots.txt."""
        if not await self.can_fetch(url):
            print(f"Blocked by robots.txt: {url}")
            return None

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                headers = {"User-Agent": user_agent}
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.text
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    async def crawl_homepage(self, url: str) -> Optional[BeautifulSoup]:
        """Crawl website homepage and return parsed HTML."""
        html = await self.fetch_page(url)
        if html:
            return BeautifulSoup(html, 'lxml')
        return None

    def find_contact_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Find likely contact/info page links."""
        links = []
        # Keywords for contact/impressum pages
        keywords = ['contact', 'kontakt', 'impressum', 'about', 'über', 'info', 'legal', 'rechtliches']

        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text().lower()

            # Check if text or href contains keywords
            if any(k in text or k in href.lower() for k in keywords):
                full_url = urljoin(base_url, href)
                # Keep only internal links
                if urlparse(full_url).netloc == urlparse(base_url).netloc:
                    links.append(full_url)

        # Sort and deduplicate, prioritizing contact/impressum
        sorted_links = sorted(list(set(links)), key=lambda l: any(k in l.lower() for k in ['contact', 'kontakt', 'impressum']))
        return sorted_links[:3] # Return top 3 candidates
