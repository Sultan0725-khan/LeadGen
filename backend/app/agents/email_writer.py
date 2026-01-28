import os
import re
import time
import asyncio
from typing import Dict, Optional
import httpx
from app.config import settings


class EmailWriter:
    """Tool to generate personalized outreach emails using Ollama exclusively with Corporate Identity."""

    def __init__(self):
        # We now use Ollama exclusively as requested
        self.ollama_url = settings.ollama_base_url
        self.ollama_model = settings.ollama_model

        # Load corporate identity context
        self.company_context = self._load_company_context()

        # Persistent client for Ollama to avoid connection overhead/intermittency
        # Increased timeout to 300s for DeepSeek reasoning tasks
        self.client = httpx.AsyncClient(
            timeout=60.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )

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

    async def redraft_email(
        self,
        lead: Dict,
        current_subject: str,
        current_body: str,
        custom_prompt: str,
        language: str = "DE"
    ) -> Dict[str, str]:
        """
        Rewrite an existing email draft based on a custom prompt using Ollama.
        """
        company_context = self._load_company_context_by_lang(language)

        refine_prompt = f"""Rewrite the following email according to these instructions: "{custom_prompt}"

Original Subject: {current_subject}
Original Body:
{current_body}

Business Name: {lead.get('business_name', '')}
Category: {lead.get('category', '')}

Maintain the corporate identity but incorporate the specific feedback above.
Respond exactly as:
Subject: [new subject]

[new body]"""

        try:
            print(f"DEBUG: Requesting redraft for {lead.get('business_name')} with prompt: {custom_prompt}")
            email_text = await self._generate_with_ollama(refine_prompt, company_context, language)
            print(f"DEBUG: Raw Ollama redraft response: {email_text}")

            subject, body = self._parse_email(email_text, language)

            # Check if parsing actually changed anything or returned reasonable content
            if not subject or not body or (subject == current_subject and body == current_body):
                print("Warning: Redraft returned identical or empty content.")
                # We still return the parsed result, but the UI might want to know

            # Ensure footer is there if it was stripped
            if "Um sich von zukünftigen" not in body and "To unsubscribe" not in body:
                body = self._add_unsubscribe_footer(body, language)

            return {
                "subject": subject,
                "body": body
            }
        except Exception as e:
            print(f"Error redrafting email: {e}")
            raise # Propagate error so UI can show it

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
        """Generate email using Ollama local LLM with retry logic."""
        lang_instruction = "AUSSCHLIESSLICH auf DEUTSCH" if language.upper() == "DE" else "EXCLUSIVELY in ENGLISH"

        url = f"{self.ollama_url}/api/generate"
        payload = {
            "model": self.ollama_model,
            "prompt": f"{company_context}\n\nIMPORTANT: Write the email {lang_instruction}. Respond ONLY with the email subject and body.\n\n{prompt}",
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 1024
            }
        }

        max_retries = 2
        for attempt in range(max_retries + 1):
            start_time = time.time()
            try:
                print(f"DEBUG: Ollama request start (Attempt {attempt+1}/{max_retries+1}) for model {self.ollama_model}")
                response = await self.client.post(url, json=payload)
                duration = time.time() - start_time

                print(f"DEBUG: Ollama responded in {duration:.2f}s with status {response.status_code}")
                response.raise_for_status()

                result = response.json()
                raw_response = result.get("response", "").strip()

                if not raw_response:
                    print("WARNING: Ollama returned an empty response.")
                    if attempt < max_retries:
                        continue
                    return ""

                # Strip DeepSeek's <think> blocks if present
                clean_response = re.sub(r'<think>.*?</think>', '', raw_response, flags=re.DOTALL).strip()
                return clean_response

            except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as e:
                duration = time.time() - start_time
                print(f"ERROR: Ollama request failed after {duration:.2f}s: {type(e).__name__}")
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    print(f"DEBUG: Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                raise
            except Exception as e:
                print(f"ERROR: Unexpected Ollama error: {type(e).__name__}: {e}")
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
        """Parse subject and body from LLM response, handling conversational filler."""
        # Clean text from potential markdown bolding or common prefixes
        text = email_text.strip()

        # Look for "Subject:" or "Betreff:" (case insensitive, allowing for optional markdown markers)
        subject_pattern = r'(?:\*\*|#)?\s*(?:Subject|Betreff):\s*(.*?)(?:\n|$)'
        subject_match = re.search(subject_pattern, text, re.IGNORECASE)

        if subject_match:
            subject = subject_match.group(1).strip()
            # Body is everything after the end of the subject line
            body = text[subject_match.end():].strip()

            # Clean up potential "Body:" or "Nachricht:" labels at start of body
            body = re.sub(r'^(?:\*\*|#)?\s*(?:Body|Message|Nachricht|Text|Inhalt):\s*', '', body, flags=re.IGNORECASE).strip()
        else:
            # Fallback: if no label is found, we assume first non-empty line is subject if it's short
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            if lines and len(lines[0]) < 100:
                subject = lines[0].strip()
                body = '\n'.join(lines[1:]).strip()
            else:
                subject = "Draft Email"
                body = text

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
