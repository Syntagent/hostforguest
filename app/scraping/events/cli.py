"""CLI for testing event scrapers without saving."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

import app.scraping.events.sites  # noqa: F401
from app.scraping.events.registry import get_event_scraper
from app.scraping.events.sources import load_national_event_sources


async def _run(slug: str, html_path: str | None) -> int:
    sources = {s["slug"]: s for s in load_national_event_sources()}
    source = sources.get(slug)
    if not source:
        print(f"Unknown slug: {slug}", file=sys.stderr)
        return 1

    scraper = get_event_scraper(source["scraper_class"], source)
    if html_path:
        html = open(html_path, encoding="utf-8").read()
        drafts = scraper.parse_listing(html, base_url=source["listing_url"])
    else:
        async with scraper.policy:
            drafts = await scraper.run()

    print(json.dumps([d.model_dump(mode="json") for d in drafts], indent=2, default=str))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Test event scraper")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--html", dest="html_path", default=None, help="Fixture HTML path")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args.slug, args.html_path)))


if __name__ == "__main__":
    main()
