import asyncio
import re
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig

async def main():
    url = "https://www.google.com/maps/search/Restaurant+in+Berlin"
    browser_config = BrowserConfig(headless=True)
    run_config = CrawlerRunConfig(magic=True)

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=run_config)
        if result.success and result.markdown:
            with open("raw_markdown.txt", "w") as f:
                f.write(result.markdown)
            print("Markdown saved to raw_markdown.txt")
        else:
            print(f"Crawl failed: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(main())
