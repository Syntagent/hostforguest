
import aiohttp, asyncio, logging
from typing import Optional, Dict, List
from urllib.parse import quote

logger = logging.getLogger(__name__)

WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKI_RADIUS = 5000  # 5km radius for matching
WIKI_LIMIT = 10

async def wiki_geosearch(lat: float, lng: float, radius: int = WIKI_RADIUS) -> List[Dict]:
    """Search Wikipedia for articles near coordinates."""
    url = f"{WIKI_API}?action=query&list=geosearch&gscoord={lat}|{lng}&gsradius={radius}&gslimit={WIKI_LIMIT}&format=json&origin=*"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
                return data.get("query", {}).get("geosearch", [])
    except Exception as e:
        logger.warning(f"Wiki geosearch failed for {lat},{lng}: {e}")
        return []

async def wiki_get_page(pageid: int) -> Optional[Dict]:
    """Get Wikipedia page extract, image, and coordinates."""
    url = f"{WIKI_API}?action=query&prop=extracts|pageimages|coordinates&exintro=1&explaintext=1&pageids={pageid}&format=json&origin=*&pithumbsize=300"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
                pages = data.get("query", {}).get("pages", {})
                page = pages.get(str(pageid), {})
                if "missing" in page:
                    return None
                return {
                    "title": page.get("title", ""),
                    "extract": page.get("extract", ""),
                    "url": f"https://en.wikipedia.org/?curid={pageid}",
                    "image": page.get("thumbnail", {}).get("source", ""),
                    "pageid": pageid,
                }
    except Exception as e:
        logger.warning(f"Wiki page fetch failed for {pageid}: {e}")
        return None

async def enrich_attraction_wikipedia(name: str, lat: float, lng: float) -> Optional[Dict]:
    """Enrich an attraction with Wikipedia data. Matches by name similarity."""
    results = await wiki_geosearch(lat, lng)
    if not results:
        return None
    
    # Try exact match first, then fuzzy
    name_lower = name.lower().strip()
    
    for r in results:
        r_lower = r["title"].lower()
        # Exact match
        if name_lower == r_lower:
            page = await wiki_get_page(r["pageid"])
            if page:
                return page
        # Partial match (name in title or title in name)
        if name_lower in r_lower or r_lower in name_lower:
            # Check that overlap is substantial (avoid "Ika" matching "Ikarus")
            shorter = min(len(name_lower), len(r_lower))
            if shorter >= 3:
                page = await wiki_get_page(r["pageid"])
                if page:
                    return page
    
    return None

print("WIKIPEDIA SERVICE READY")
