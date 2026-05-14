"""
Playwright scraper script for advanced web scraping.

Uses Playwright MCP for complex JavaScript-heavy Croatian tourism sites
that require browser automation for proper content extraction.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.playwright_service import PlaywrightMCPService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def scrape_tourism_site(url: str):
    """
    Scrape a Croatian tourism site using Playwright MCP.
    
    Args:
        url: URL to scrape
    """
    service = PlaywrightMCPService()
    
    logger.info(f"Starting Playwright scrape of: {url}")
    
    result = await service.scrape_with_playwright(
        url=url,
        wait_for_selector="body"
    )
    
    if result:
        logger.info(f"Successfully scraped {url}")
        logger.info(f"Screenshot saved: {result.get('screenshot')}")
        return result
    else:
        logger.error(f"Failed to scrape {url}")
        return None


async def main():
    """Main function for command-line usage."""
    if len(sys.argv) < 2:
        print("Usage: python playwright_scraper.py <url>")
        sys.exit(1)
    
    url = sys.argv[1]
    result = await scrape_tourism_site(url)
    
    if result:
        print(f"Scraping successful: {result}")
    else:
        print("Scraping failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

