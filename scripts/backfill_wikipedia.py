
"""Backfill Wikipedia data for all attractions."""
import asyncio, sys, os
sys.path.insert(0, "/app")

from app.services.wikipedia_service import enrich_attraction_wikipedia
from app.core.database import get_db_url
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

async def backfill():
    url = get_db_url()
    engine = create_async_engine(url)
    
    async with AsyncSession(engine) as db:
        # Get attractions without Wikipedia data
        result = await db.execute(text(
            "SELECT id, name, latitude, longitude FROM attractions "
            "WHERE wikipedia_pageid IS NULL AND latitude IS NOT NULL"
        ))
        rows = result.fetchall()
        print(f"Found {len(rows)} attractions to enrich")
        
        enriched = 0
        for row in rows:
            a_id, name, lat, lng = row
            if not lat or not lng:
                continue
            
            wiki = await enrich_attraction_wikipedia(name, lat, lng)
            if wiki:
                await db.execute(text(
                    "UPDATE attractions SET wikipedia_pageid=:pid, wikipedia_extract=:extract, "
                    "wikipedia_url=:url, wikipedia_image=:img WHERE id=:id"
                ), {
                    "pid": wiki["pageid"],
                    "extract": wiki["extract"][:2000],
                    "url": wiki["url"],
                    "img": wiki["image"],
                    "id": a_id,
                })
                enriched += 1
                print(f"  {name} → {wiki['title']}")
            
            if enriched % 5 == 0 and enriched > 0:
                await db.commit()
        
        await db.commit()
        print(f"Enriched {enriched}/{len(rows)} attractions")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(backfill())
