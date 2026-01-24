import re
from bs4 import BeautifulSoup
from typing import List, Dict, Set
from urllib.parse import urljoin, urlparse


class ContactExtractor:
    """Extract contact information from HTML."""

    # Email regex pattern
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

    # Phone regex patterns (German and international)
    PHONE_PATTERNS = [
        re.compile(r'\+49[\s\-]?\d{1,5}[\s\-]?\d{1,9}'),  # German +49
        re.compile(r'0\d{2,5}[\s\-/]?\d{2,9}'),  # German local
        re.compile(r'\+\d{1,3}[\s\-]?\d{1,14}'),  # International
    ]

    # Social media URL patterns
    SOCIAL_PATTERNS = {
        'instagram': re.compile(r'https?://(?:www\.)?instagram\.com/([A-Za-z0-9_.]+)'),
        'facebook': re.compile(r'https?://(?:www\.)?facebook\.com/([A-Za-z0-9.]+)'),
        'linkedin': re.compile(r'https?://(?:www\.)?linkedin\.com/(?:company|in)/([A-Za-z0-9\-]+)'),
        'twitter': re.compile(r'https?://(?:www\.)?(?:twitter|x)\.com/([A-Za-z0-9_]+)'),
        'tiktok': re.compile(r'https?://(?:www\.)?tiktok\.com/@([A-Za-z0-9_.]+)'),
    }

    def extract_emails(self, soup: BeautifulSoup) -> List[str]:
        """Extract email addresses from page."""
        emails: Set[str] = set()

        # Search in text
        text = soup.get_text()
        found = self.EMAIL_PATTERN.findall(text)
        emails.update(found)

        # Search in mailto links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('mailto:'):
                email = href.replace('mailto:', '').split('?')[0]
                if self.EMAIL_PATTERN.match(email):
                    emails.add(email)

        # Filter out common generic/invalid emails
        filtered_emails = [
            email for email in emails
            if not any(invalid in email.lower() for invalid in [
                'example.com', 'test.com', 'domain.com',
                '@sentry', '@google-analytics', 'noreply@'
            ])
        ]

        return list(filtered_emails)

    def extract_phones(self, soup: BeautifulSoup) -> List[str]:
        """Extract phone numbers from page."""
        phones: Set[str] = set()

        # Search in text
        text = soup.get_text()
        for pattern in self.PHONE_PATTERNS:
            found = pattern.findall(text)
            phones.update(found)

        # Search in tel links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('tel:'):
                phone = href.replace('tel:', '').strip()
                phones.add(phone)

        # Clean and normalize
        normalized = [self._normalize_phone(p) for p in phones]
        return list(set(normalized))

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number format."""
        # Remove common separators, keep + and digits
        return re.sub(r'[^\d+]', '', phone)

    def extract_social_links(self, soup: BeautifulSoup, base_url: str = "") -> Dict[str, str]:
        """Extract social media profile links."""
        social_links = {}

        # Find all links
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Make absolute URL
            full_url = urljoin(base_url, href)

            # Check against social patterns
            for platform, pattern in self.SOCIAL_PATTERNS.items():
                match = pattern.match(full_url)
                if match:
                    social_links[platform] = full_url
                    break

        return social_links

    def extract_all(self, soup: BeautifulSoup, base_url: str = "") -> Dict:
        """Extract all contact information."""
        return {
            "emails": self.extract_emails(soup),
            "phones": self.extract_phones(soup),
            "social_links": self.extract_social_links(soup, base_url),
        }
