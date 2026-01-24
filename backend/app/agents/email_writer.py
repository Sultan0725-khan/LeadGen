from typing import Dict, Optional
from app.config import settings
from openai import AsyncOpenAI
import httpx
import re


class EmailWriter:
    """Tool to generate personalized outreach emails using LLM."""

    def __init__(self):
        self.llm_mode = settings.llm_mode.lower()

        if self.llm_mode == "openai":
            if not settings.openai_api_key:
                raise ValueError("OpenAI API key required when llm_mode='openai'")
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        elif self.llm_mode == "ollama":
            self.ollama_url = settings.ollama_base_url
            self.ollama_model = settings.ollama_model
        else:
            raise ValueError(f"Invalid llm_mode: {self.llm_mode}. Must be 'openai' or 'ollama'")

    async def generate_email(
        self,
        lead: Dict,
        run_location: str,
        run_category: str,
        language: str = "DE"
    ) -> Dict[str, str]:
        """
        Generate personalized email for a lead.

        Returns dict with 'subject' and 'body' keys.
        """
        # Build context for LLM
        context = self._build_context(lead, run_location, run_category)
        prompt = self._build_prompt(context, language)

        try:
            # Route to appropriate LLM provider
            if self.llm_mode == "openai":
                email_text = await self._generate_with_openai(prompt)
            elif self.llm_mode == "ollama":
                email_text = await self._generate_with_ollama(prompt)
            else:
                raise ValueError(f"Unknown LLM mode: {self.llm_mode}")

            # Parse subject and body
            subject, body = self._parse_email(email_text, language)

            # Add unsubscribe footer
            body_with_footer = self._add_unsubscribe_footer(body, language)

            return {
                "subject": subject,
                "body": body_with_footer
            }

        except Exception as e:
            business_name = lead.get("business_name", "")
            print(f"Error generating email for {business_name}: {e}")
            # Fallback to template
            return self._generate_fallback_email(lead, run_location, run_category, language)

    async def _generate_with_openai(self, prompt: str) -> str:
        """Generate email using OpenAI API."""
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert email copywriter specializing in B2B outreach for local businesses. "
                               "Write professional, friendly, and personalized emails that feel authentic and respectful."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()

    async def _generate_with_ollama(self, prompt: str) -> str:
        """Generate email using Ollama local LLM."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": f"""You are an expert email copywriter specializing in B2B outreach for local businesses. Write professional, friendly, and personalized emails that feel authentic and respectful.

{prompt}""",
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 500
                    }
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "").strip()

    def _build_context(self, lead: Dict, location: str, category: str) -> Dict:
        """Build context dict for email generation."""
        return {
            "business_name": lead.get("business_name", ""),
            "address": lead.get("address", ""),
            "location": location,
            "category": category,
            "has_website": bool(lead.get("website")),
            "has_social": bool(lead.get("enrichment_data", {}).get("social_links")),
        }

    def _build_prompt(self, context: Dict, language: str) -> str:
        """Build LLM prompt for email generation."""
        lang_name = "German" if language == "DE" else "English"

        prompt = f"""Write a short, professional outreach email in {lang_name} for the following business:

Business Name: {context['business_name']}
Location: {context['location']}
Category: {context['category']}

The email should:
1. Be 3-4 sentences max
2. Mention their specific business name and category
3. Briefly mention we have a service that could help grow their business
4. Ask if they'd be interested in a quick conversation
5. Sound friendly and authentic, not salesy

Format your response as:
Subject: [email subject]

[email body]

Do NOT include an unsubscribe line (we'll add that automatically)."""

        return prompt

    def _parse_email(self, email_text: str, language: str) -> tuple[str, str]:
        """Parse subject and body from LLM response."""
        # Look for "Subject:" or "Betreff:"
        subject_pattern = r'(?:Subject|Betreff):\s*(.+?)(?:\n|$)'
        subject_match = re.search(subject_pattern, email_text, re.IGNORECASE)

        if subject_match:
            subject = subject_match.group(1).strip()
            # Body is everything after subject line
            body = email_text[subject_match.end():].strip()
        else:
            # Fallback: first line is subject
            lines = email_text.strip().split('\n')
            subject = lines[0].strip()
            body = '\n'.join(lines[1:]).strip()

        return subject, body

    def _add_unsubscribe_footer(self, body: str, language: str) -> str:
        """Add unsubscribe footer to email body."""
        if language == "DE":
            footer = f"\n\n---\nUm sich von zukünftigen E-Mails abzumelden, antworten Sie mit 'ABMELDEN' oder kontaktieren Sie uns unter {settings.email_from_address}."
        else:
            footer = f"\n\n---\nTo unsubscribe from future emails, reply with 'UNSUBSCRIBE' or contact us at {settings.email_from_address}."

        return body + footer

    def _generate_fallback_email(
        self,
        lead: Dict,
        location: str,
        category: str,
        language: str
    ) -> Dict[str, str]:
        """Generate basic template email as fallback."""
        business_name = lead.get("business_name", "")

        if language == "DE":
            subject = f"Partnerschaft mit {business_name}"
            body = f"""Hallo {business_name} Team,

wir haben Ihr {category}-Unternehmen in {location} entdeckt und möchten Ihnen eine Möglichkeit vorstellen, Ihr Geschäft auszubauen.

Hätten Sie Interesse an einem kurzen Gespräch?

Mit freundlichen Grüßen,
{settings.email_from_name}"""
        else:
            subject = f"Partnership with {business_name}"
            body = f"""Hello {business_name} team,

We discovered your {category} business in {location} and would like to introduce an opportunity to grow your business.

Would you be interested in a brief conversation?

Best regards,
{settings.email_from_name}"""

        body_with_footer = self._add_unsubscribe_footer(body, language)

        return {
            "subject": subject,
            "body": body_with_footer
        }
