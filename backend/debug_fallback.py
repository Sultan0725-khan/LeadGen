import asyncio
import os
import base64
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig

async def main():
    url = "https://www.google.com/maps/search/Restaurant+in+Berlin"
    browser_config = BrowserConfig(headless=True)

    consent_bypass_js = """
    (async () => {
        const delay = (ms) => new Promise(r => setTimeout(r, ms));
        const selectors = ['button#L2AGLb', 'button#introAgreeButton', 'form[action*="consent.google.com"] button'];
        for (const sel of selectors) {
            const b = document.querySelectorAll(sel);
            if (b.length > 0) {
                console.log("Found button with selector: " + sel);
                b[0].click();
                await delay(4000);
                return;
            }
        }
        const btns = Array.from(document.querySelectorAll('button'));
        const accept = btns.find(b => /Accept all|Alle akzeptieren|Ich stimme zu/i.test(b.innerText));
        if (accept) {
            console.log("Found button by text: " + accept.innerText);
            accept.click();
            await delay(4000);
        }
    })();
    """

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Replicate Fallback logic with a wait_for to ensure results appear after consent bypass
        result = await crawler.arun(
            url=url,
            config=CrawlerRunConfig(
                magic=True,
                js_code=consent_bypass_js,
                wait_for="a.hfpxzc",
                wait_for_timeout=60000,
                screenshot=True
            )
        )

        if result.success:
            with open("fallback_markdown.txt", "w") as f:
                f.write(result.markdown)

            if result.screenshot:
                with open("fallback_debug.png", "wb") as f:
                    f.write(base64.b64decode(result.screenshot))
                print("Screenshot saved to fallback_debug.png")

            print(f"Markdown saved to fallback_markdown.txt (Length: {len(result.markdown)})")
            if "Before you continue" in result.markdown:
                print("STILL BLOCKED BY CONSENT WALL")
            else:
                print("Consent wall presumably bypassed.")
        else:
            print(f"Crawl failed: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(main())
