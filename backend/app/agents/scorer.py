from typing import Dict


class Scorer:
    """Tool to calculate confidence scores for leads."""

    # Personal email domains to flag
    PERSONAL_EMAIL_DOMAINS = {
        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
        'icloud.com', 'aol.com', 'gmx.de', 'web.de', 'freenet.de'
    }

    def calculate_score(self, lead: Dict) -> float:
        """
        Calculate confidence score (0-1) based on data completeness and quality.

        Scoring criteria:
        - Has website: +0.3
        - Has business email: +0.4
        - Has phone: +0.2
        - Has social profiles: +0.1
        - Multiple sources: +0.1
        - Has enrichment data: -0.1 (already claimed by specific items)
        """
        score = 0.0

        # Website
        if lead.get("website"):
            score += 0.3

        # Email (prefer business emails)
        email = lead.get("email")
        enrichment_emails = lead.get("enrichment_data", {}).get("emails", [])

        has_business_email = False
        if email and not self._is_personal_email(email):
            has_business_email = True

        if not has_business_email:
            for e in enrichment_emails:
                if not self._is_personal_email(e):
                    has_business_email = True
                    break

        if has_business_email:
            score += 0.4
        elif email or enrichment_emails:
            # Has email but it's personal
            score += 0.2

        # Phone
        phone = lead.get("phone")
        enrichment_phones = lead.get("enrichment_data", {}).get("phones", [])
        if phone or enrichment_phones:
            score += 0.2

        # Social profiles
        social_links = lead.get("enrichment_data", {}).get("social_links", {})
        if social_links:
            score += 0.1

        # Multiple sources (data verification)
        sources = lead.get("sources", [])
        if len(sources) > 1:
            score += 0.1

        # Cap at 1.0
        return min(score, 1.0)

    def _is_personal_email(self, email: str) -> bool:
        """Check if email uses a personal domain."""
        if not email:
            return False

        domain = email.split('@')[-1].lower()
        return domain in self.PERSONAL_EMAIL_DOMAINS

    def get_best_contact_email(self, lead: Dict) -> str | None:
        """Get the best contact email (prefer business emails)."""
        email = lead.get("email")
        enrichment_emails = lead.get("enrichment_data", {}).get("emails", [])

        # Check primary email first
        if email and not self._is_personal_email(email):
            return email

        # Check enrichment emails
        for e in enrichment_emails:
            if not self._is_personal_email(e):
                return e

        # Fallback to any email
        if email:
            return email
        if enrichment_emails:
            return enrichment_emails[0]

        return None
