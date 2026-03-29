import asyncio
import os
import base64
import re
import json
from typing import List, Tuple, Optional
from app.providers.base import BaseProvider, RawLead
from app.config import settings
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig

class Crawl4AIProvider(BaseProvider):
    """Lead provider using Crawl4AI for browser-based scraping with email enrichment."""

    def __init__(self):
        self.screenshot_dir = os.path.join(os.getcwd(), "storage", "screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)

    @property
    def id(self) -> str:
        return "crawl4ai"

    @property
    def name(self) -> str:
        return "Crawl4AI (Google Maps)"

    def is_available(self) -> bool:
        return True

    async def search(self, location: str, category: str, **kwargs) -> List[RawLead]:
        """Search Google Maps using Crawl4AI with deep interactive extraction and email discovery."""
        limit = kwargs.get("limit", 10)
        query = f"{category} in {location}"
        url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"

        browser_config = BrowserConfig(headless=True)

        # JS to handle consent, scroll, and click leads for details
        js_code = """
        (async () => {
            const delay = (ms) => new Promise(r => setTimeout(r, ms));
            const startTime = Date.now();
            const MAX_TIME = 90000; // 90s safety timeout

            const createSignal = (data) => {
                const signal = document.createElement('div');
                signal.id = 'extraction-signal';
                signal.innerText = 'DATA_START' + JSON.stringify(data) + 'DATA_END';
                document.body.prepend(signal);
            };

            const handleConsent = async () => {
                const selectors = ['button#L2AGLb', 'button#introAgreeButton', 'div[role="none"] button', 'button', 'form[action*="consent.google.com"] button'];
                for (const sel of selectors) {
                    const btns = Array.from(document.querySelectorAll(sel));
                    const accept = btns.find(b => /Accept all|Alle akzeptieren|Ich stimme zu|Agree/i.test(b.innerText));
                    if (accept) {
                        accept.click();
                        return true;
                    }
                }
                // Try inside iframes
                const iframes = Array.from(document.querySelectorAll('iframe'));
                for (const frame of iframes) {
                    try {
                        const frameDoc = frame.contentDocument || frame.contentWindow.document;
                        const btns = Array.from(frameDoc.querySelectorAll('button'));
                        const accept = btns.find(b => /Accept all|Alle akzeptieren|Ich stimme zu|Agree/i.test(b.innerText));
                        if (accept) {
                            accept.click();
                            return true;
                        }
                    } catch (e) {}
                }
                return false;
            };

            try {
                // 1. Handle Consent with retries
                let consentHandled = false;
                for(let r=0; r<3; r++) {
                    if (await handleConsent()) {
                        consentHandled = true;
                        await delay(4000);
                        break;
                    }
                    await delay(2000);
                }

                // 2. Extract Leads
                const leadsData = [];
                const results = Array.from(document.querySelectorAll('a.hfpxzc')).slice(0, 5);

                if (results.length === 0) {
                    console.log("No results found yet, maybe still loading or blocked.");
                }

                for (let i = 0; i < results.length; i++) {
                    if (Date.now() - startTime > MAX_TIME) break;

                    const res = results[i];
                    try {
                        res.scrollIntoView();
                        await delay(500);
                        res.click();
                        await delay(3000);

                        const nameEl = document.querySelector('h1.DUwDvf');
                        let name = nameEl ? nameEl.innerText : res.getAttribute('aria-label');
                        if (name) name = name.split('·')[0].split('\\n')[0].trim();

                        const websiteLink = document.querySelector('a[data-item-id="authority"]');
                        const ratingEl = document.querySelector('span.ceNzR');
                        const addressBtn = document.querySelector('button[data-item-id="address"]');

                        leadsData.push({
                            name: name,
                            website: websiteLink ? websiteLink.href : null,
                            rating: ratingEl ? (ratingEl.ariaLabel || ratingEl.innerText) : null,
                            address: addressBtn ? addressBtn.innerText : null
                        });
                    } catch (e) { console.error("Error extracting lead " + i, e); }
                }
                createSignal(leadsData);
            } catch (globalE) {
                console.error("Global extraction error", globalE);
                createSignal([]);
            }
        })();
        """

        run_config = CrawlerRunConfig(
            screenshot=True,
            magic=True,
            js_code=js_code,
            wait_for="#extraction-signal",
            wait_for_timeout=180000
        )

        leads = []
        result = None
        import time
        import uuid
        screenshot_path = None

        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=run_config)

                if result and result.success and result.screenshot:
                    short_id = str(uuid.uuid4())[:8]
                    screenshot_name = f"search_{location.replace(' ', '_')}_{category.replace(' ', '_')}_{int(time.time())}_{short_id}.png"
                    screenshot_path = os.path.join(self.screenshot_dir, screenshot_name)
                    with open(screenshot_path, "wb") as f:
                        f.write(base64.b64decode(result.screenshot))
                    print(f"Screenshot saved to {screenshot_path}")

        except Exception as e:
            print(f"Crawl4AI deep extraction failed or timed out: {e}")

        # Process results - either from signal or heuristic
        data_found = False
        if result and result.success and result.markdown:
            if "DATA_START" in result.markdown and "DATA_END" in result.markdown:
                import json
                try:
                    raw_data = result.markdown.split("DATA_START")[1].split("DATA_END")[0].strip()
                    if raw_data.startswith("`"): raw_data = raw_data.strip("`").strip("json")
                    extracted_leads = json.loads(raw_data)

                    if extracted_leads:
                        for item in extracted_leads:
                            if not item.get("name"): continue
                            lead = RawLead(
                                business_name=item["name"],
                                website=item.get("website"),
                                address=item.get("address") or location,
                                additional_data={
                                    "provider": "crawl4ai_deep",
                                    "rating": item.get("rating"),
                                    "screenshot_path": screenshot_path
                                }
                            )
                            # Step: Email Discovery
                            if lead.website:
                                print(f"Found website for {lead.business_name}: {lead.website}. Discovery email...")
                                lead.email = await self._find_email_on_website(lead.website)
                            leads.append(lead)
                            if len(leads) >= limit: break
                        data_found = True
                except Exception as e:
                    print(f"Error parsing deep signal data: {e}")

        # Heuristic fallback if no data found via signal
        if not data_found:
            print("Deep extraction signal not found or empty. Falling back to heuristic parsing...")
            # If previous result failed or has no markdown, try a fresh simple run with consent bypass
            if not result or not result.success or not result.markdown or "Before you continue" in result.markdown:
                try:
                    # Minimal JS to bypass consent for fallback
                    consent_bypass_js = """
                    (async () => {
                        const delay = (ms) => new Promise(r => setTimeout(r, ms));
                        const selectors = ['button#L2AGLb', 'button#introAgreeButton', 'form[action*="consent.google.com"] button'];
                        for (const sel of selectors) {
                            const b = document.querySelector(sel);
                            if (b) { b.click(); await delay(2000); return; }
                        }
                        const btns = Array.from(document.querySelectorAll('button'));
                        const accept = btns.find(b => /Accept all|Alle akzeptieren/i.test(b.innerText));
                        if (accept) { accept.click(); await delay(2000); }
                    })();
                    """
                    async with AsyncWebCrawler(config=browser_config) as crawler:
                        result = await crawler.arun(
                            url=url,
                            config=CrawlerRunConfig(
                                magic=True,
                                js_code=consent_bypass_js,
                                wait_for="a.hfpxzc",
                                wait_for_timeout=60000
                            )
                        )
                except Exception as e:
                    print(f"Fallback crawl failed: {e}")
                    return []

            if result and result.success and result.markdown:
                lines = result.markdown.split("\n")
                current_business_names = set()

                # Potential separators and rating patterns
                rating_pattern = re.compile(r'^\d[.,]\d(\s?\([\d,.]+\))?$')  # Matches 4.5, 4.5(20), 4,5 (2,113)
                separators = ["·", "•", "|"]

                for i in range(len(lines)):
                    line = lines[i].strip()
                    if not line: continue

                    # If this line looks like a rating or has a separator, the previous line or the one before might be the name
                    is_detail_line = any(s in line for s in separators) or rating_pattern.match(line)

                    if is_detail_line:
                        # Look back up to 2 lines for a potential name
                        for j in range(1, 4): # Look back up to 3 lines now
                            if i - j >= 0:
                                potential_name = lines[i - j].strip()
                                # Clean up potential name (remove icon placeholders or leading symbols)
                                potential_name = re.sub(r'^[#\*\s]+', '', potential_name)
                                if "·" in potential_name: potential_name = potential_name.split("·")[0].strip()

                                # Validate potential name
                                if (potential_name and
                                    len(potential_name) > 2 and
                                    len(potential_name) < 80 and
                                    not potential_name.startswith("#") and
                                    not rating_pattern.match(potential_name) and
                                    not re.match(r'^[A-Z][a-z]+ (restaurant|cafe|bar|shop)$', potential_name) and
                                    not any(x.lower() in potential_name.lower() for x in ["results", "search", "filters", "sponsored", "gesponsert", "ad ", "ads", "", "menu", "directions", "feedback", "privacy", "terms", "dine-in", "takeaway", "delivery", "no-contact delivery"])):

                                    # Specific check: If the original line had a separator at the end, it's very likely a category, skip it as a name
                                    original_potential_line = lines[i - j].strip()
                                    if "·" in original_potential_line and original_potential_line.index("·") < len(original_potential_line) // 2:
                                         # If the separator is early in the line, it might be "Category · Address", so skip
                                         continue

                                    if potential_name not in current_business_names:
                                        lead = RawLead(
                                            business_name=potential_name,
                                            address=location,
                                            additional_data={"provider": "crawl4ai_heuristic", "screenshot_path": screenshot_path}
                                        )
                                        leads.append(lead)
                                        current_business_names.add(potential_name)
                                        break
                    if len(leads) >= limit: break

        return leads

    async def _find_email_on_website(self, url: str) -> Optional[str]:
        """Visit a website and look for an email address."""
        if not url or any(x in url for x in ["google.com", "facebook.com", "instagram.com", "twitter.com", "linkedin.com"]):
            return None

        try:
            browser_config = BrowserConfig(headless=True)
            run_config = CrawlerRunConfig(magic=True, wait_for_timeout=15000)

            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=run_config)
                if result.success and result.markdown:
                    # Look for mailto: links first
                    mailto_match = re.search(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', result.markdown)
                    if mailto_match:
                        return mailto_match.group(1).lower()

                    # Robust email regex
                    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                    emails = re.findall(email_pattern, result.markdown)
                    if emails:
                        # Filter out common junk image emails
                        valid_emails = [e for e in emails if not any(x in e.lower() for x in ['.png', '.jpg', '.jpeg', '.gif', '.svg'])]
                        if valid_emails:
                            return valid_emails[0].lower()
        except Exception as e:
            print(f"Error enrichment website {url}: {e}")

        return None

    def get_rate_limit(self) -> Tuple[int, int]:
        return (1, 5)
