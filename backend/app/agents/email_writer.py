import os
import re
from typing import Dict, Optional
from app.config import settings
import httpx


class EmailWriter:
    """Tool to generate personalized outreach emails using Ollama exclusively with Corporate Identity."""

    def __init__(self):
        # We now use Ollama exclusively as requested
        self.ollama_url = settings.ollama_base_url
        self.ollama_model = settings.ollama_model

        # Load corporate identity context
        self.company_context = self._load_company_context()

        # Ensure archiving directory exists
        self.archive_dir = "/Users/sultankhan/DevOps/LeadGen/backend/generated_emails"
        if not os.path.exists(self.archive_dir):
            os.makedirs(self.archive_dir)

    def _load_company_context(self) -> str:
        """Load corporate tone and context from file."""
        context_path = "/Users/sultankhan/DevOps/LeadGen/backend/company_context.txt"
        try:
            if os.path.exists(context_path):
                with open(context_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            return ""
        except Exception as e:
            print(f"Warning: Could not load company_context.txt: {e}")
            return ""

    async def generate_email(
        self,
        lead: Dict,
        run_location: str,
        run_category: str,
        language: str = "DE"
    ) -> Dict[str, str]:
        """
        Generate personalized email for a lead using Ollama.
        """
        # Load corporate identity context based on language
        company_context = self._load_company_context_by_lang(language)

        # Build context for LLM
        context = self._build_context(lead, run_location, run_category)
        prompt = self._build_prompt(context, language)

        try:
            # Generate exclusively with Ollama
            email_text = await self._generate_with_ollama(prompt, company_context, language)

            # Parse subject and body
            subject, body = self._parse_email(email_text, language)

            # Add unsubscribe footer
            body_with_footer = self._add_unsubscribe_footer(body, language)

            # Archive the email locally
            self._archive_email(lead.get("business_name", "unknown"), subject, body_with_footer)

            return {
                "subject": subject,
                "body": body_with_footer
            }

        except Exception as e:
            business_name = lead.get("business_name", "")
            print(f"Error generating email for {business_name} with Ollama: {e}")
            # Fallback to template if local LLM fails
            return self._generate_fallback_email(lead, run_location, run_category, language)

    def _load_company_context_by_lang(self, language: str) -> str:
        """Load corporate tone and context from file based on language."""
        suffix = "GER" if language.upper() == "DE" else "EN"
        context_path = f"/Users/sultankhan/DevOps/LeadGen/backend/company_context{suffix}.txt"

        # Fallback to shared context if language-specific doesn't exist
        if not os.path.exists(context_path):
            context_path = "/Users/sultankhan/DevOps/LeadGen/backend/company_context.txt"

        try:
            if os.path.exists(context_path):
                with open(context_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            return "You are an expert B2B copywriter."
        except Exception as e:
            print(f"Warning: Could not load {context_path}: {e}")
            return "You are an expert B2B copywriter."

    async def _generate_with_ollama(self, prompt: str, company_context: str, language: str) -> str:
        """Generate email using Ollama local LLM."""
        lang_instruction = "AUSSCHLIESSLICH auf DEUTSCH" if language.upper() == "DE" else "EXCLUSIVELY in ENGLISH"

        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": f"""{company_context}

IMPORTANT: Write the email {lang_instruction}. Respond ONLY with the email subject and body.

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
            except Exception as e:
                print(f"Ollama connection error: {e}")
                raise

    def _archive_email(self, business_name: str, subject: str, body: str):
        """Save generated email to a local file for archiving."""
        try:
            # Clean filename
            clean_name = re.sub(r'[^\w\s-]', '', business_name).strip().replace(' ', '_')
            timestamp = os.popen('date +%Y%m%d_%H%M%S').read().strip()
            filename = f"{timestamp}_{clean_name}.txt"
            filepath = os.path.join(self.archive_dir, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"SUBJECT: {subject}\n")
                f.write("-" * 50 + "\n")
                f.write(body)

            print(f"Archived email to {filepath}")
        except Exception as e:
            print(f"Failed to archive email: {e}")

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

Format your response exactly as:
Subject: [email subject]

[email body]

Do NOT include an unsubscribe line."""

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
