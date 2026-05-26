"""
Real-time Croatian tourism data API endpoints.

Provides live data feeds from Croatian tourism sources using Crawl4AI
for immediate integration with host recommendations and guest information.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.services.crawl4ai_scraper_service import Crawl4AIScraperService
from app.services.ai_service import AIService
from app.services.events_feed_service import EventsFeedService
from app.models.content_source import ContentType
from app.models.content_source import ContentSource, ContentUpdate, SourceStatus
from app.models.host import Host
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


# Response Models
class RealTimeUpdateResponse(BaseModel):
    """Response model for real-time updates."""
    id: str
    title: str
    content: str
    content_type: str
    url: Optional[str]
    publication_date: Optional[str]
    relevant_cities: List[str]
    relevant_regions: List[str]
    keywords: List[str]
    quality_score: float
    relevance_score: float
    created_at: str
    source_name: Optional[str]


class LiveStreamResponse(BaseModel):
    """Response model for live stream updates."""
    update_id: str
    source_name: str
    content_type: str
    title: str
    summary: str
    url: Optional[str]
    timestamp: str
    relevance_score: float
    cities: List[str]
    regions: List[str]


class DataSourceStatus(BaseModel):
    """Response model for data source status."""
    source_id: str
    name: str
    url: str
    status: str
    last_scraped: Optional[str]
    next_scrape: Optional[str]
    total_scrapes: int
    successful_scrapes: int
    failed_scrapes: int
    consecutive_failures: int
    last_error: Optional[str]


class RealTimeDataSummary(BaseModel):
    """Summary of real-time data availability."""
    total_sources: int
    active_sources: int
    recent_updates_24h: int
    recent_updates_1h: int
    content_types_available: List[str]
    cities_covered: List[str]
    last_update_time: Optional[str]


# Public Endpoints (No Authentication Required)

@router.get("/updates", response_model=List[RealTimeUpdateResponse])
async def get_real_time_updates(
    db: AsyncSession = Depends(get_db),
    city: Optional[str] = Query(None, description="Filter by city (e.g., 'Lovran', 'Opatija')"),
    content_types: Optional[str] = Query(None, description="Comma-separated content types"),
    hours: int = Query(24, description="Hours back to look for updates", ge=1, le=168),
    limit: int = Query(50, description="Maximum number of updates", ge=1, le=100)
):
    """
    Get real-time tourism updates from Croatian sources.
    
    Args:
        db: Database session
        city: Filter by specific city
        content_types: Filter by content types (events,attractions,opening_hours,etc.)
        hours: How many hours back to look for updates
        limit: Maximum number of updates to return
        
    Returns:
        List[RealTimeUpdateResponse]: Recent tourism updates
    """
    try:
        logger.info(f"Getting real-time updates: city={city}, content_types={content_types}, hours={hours}")
        
        feed = EventsFeedService(db)
        content_type_list = None
        if content_types:
            content_type_list = [ct.strip() for ct in content_types.split(",")]

        updates = await feed.get_updates(
            city=city,
            content_types=content_type_list,
            hours=hours,
            limit=limit,
        )

        logger.info(f"Retrieved {len(updates)} real-time updates")
        return updates
            
    except Exception as e:
        logger.error(f"Error getting real-time updates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve real-time updates: {str(e)}"
        )


@router.get("/stream", response_model=List[LiveStreamResponse])
async def get_live_stream_updates(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    sources: Optional[str] = Query(None, description="Comma-separated source names to monitor"),
    regions: Optional[str] = Query(None, description="Comma-separated regions (Istria,Kvarner,etc.)")
):
    """
    Get live streaming updates from active Croatian tourism sources.
    
    Args:
        background_tasks: Background task handler
        db: Database session
        sources: Specific sources to monitor
        regions: Specific regions to monitor
        
    Returns:
        List[LiveStreamResponse]: Live streaming updates
    """
    try:
        logger.info(f"Starting live stream: sources={sources}, regions={regions}")
        
        # Get active sources
        stmt = select(ContentSource).where(
            and_(
                ContentSource.scraping_enabled == True,
                ContentSource.status == SourceStatus.ACTIVE
            )
        )
        
        # Apply source filter
        if sources:
            source_names = [s.strip() for s in sources.split(",")]
            stmt = stmt.where(ContentSource.name.in_(source_names))
        
        # Apply region filter
        if regions:
            region_names = [r.strip() for r in regions.split(",")]
            stmt = stmt.where(ContentSource.region.in_(region_names))
        
        result = await db.execute(stmt)
        active_sources = result.scalars().all()
        
        if not active_sources:
            logger.warning("No active sources found for live streaming")
            return []
        
        # Initialize AI service and scraper
        ai_service = AIService()
        
        async with Crawl4AIScraperService(db, ai_service) as scraper:
            # Stream live updates
            stream_updates = await scraper.stream_live_updates(active_sources)
            
            logger.info(f"Generated {len(stream_updates)} live stream updates")
            return stream_updates
            
    except Exception as e:
        logger.error(f"Error getting live stream updates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get live stream updates: {str(e)}"
        )


@router.get("/sources/status", response_model=List[DataSourceStatus])
async def get_data_sources_status(
    db: AsyncSession = Depends(get_db)
):
    """
    Get status of all Croatian tourism data sources.
    
    Args:
        db: Database session
        
    Returns:
        List[DataSourceStatus]: Status of all data sources
    """
    try:
        # Get all content sources
        stmt = select(ContentSource)
        result = await db.execute(stmt)
        sources = result.scalars().all()
        
        status_list = []
        for source in sources:
            status_list.append(DataSourceStatus(
                source_id=str(source.id),
                name=source.name,
                url=source.url,
                status=source.status,
                last_scraped=source.last_scraped.isoformat() if source.last_scraped else None,
                next_scrape=source.next_scrape.isoformat() if source.next_scrape else None,
                total_scrapes=source.total_scrapes or 0,
                successful_scrapes=source.successful_scrapes or 0,
                failed_scrapes=source.failed_scrapes or 0,
                consecutive_failures=source.consecutive_failures or 0,
                last_error=source.last_error
            ))
        
        logger.info(f"Retrieved status for {len(status_list)} data sources")
        return status_list
        
    except Exception as e:
        logger.error(f"Error getting data sources status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve data sources status"
        )


@router.get("/summary", response_model=RealTimeDataSummary)
async def get_real_time_data_summary(
    db: AsyncSession = Depends(get_db)
):
    """
    Get summary of real-time data availability.
    
    Args:
        db: Database session
        
    Returns:
        RealTimeDataSummary: Summary of available real-time data
    """
    try:
        # Get source statistics
        sources_stmt = select(ContentSource)
        sources_result = await db.execute(sources_stmt)
        all_sources = sources_result.scalars().all()
        
        total_sources = len(all_sources)
        active_sources = len([s for s in all_sources if s.status == SourceStatus.ACTIVE])
        
        # Get recent updates
        now = datetime.utcnow()
        updates_24h_stmt = select(ContentUpdate).where(
            ContentUpdate.created_at >= now - timedelta(hours=24)
        )
        updates_24h_result = await db.execute(updates_24h_stmt)
        recent_updates_24h = len(updates_24h_result.scalars().all())
        
        updates_1h_stmt = select(ContentUpdate).where(
            ContentUpdate.created_at >= now - timedelta(hours=1)
        )
        updates_1h_result = await db.execute(updates_1h_stmt)
        recent_updates_1h = len(updates_1h_result.scalars().all())
        
        # Get available content types and cities
        content_types = set()
        cities = set()
        last_update_time = None
        
        for source in all_sources:
            if source.content_types:
                content_types.update(source.content_types)
            if source.city:
                cities.add(source.city)
            if source.last_scraped and (not last_update_time or source.last_scraped > last_update_time):
                last_update_time = source.last_scraped
        
        summary = RealTimeDataSummary(
            total_sources=total_sources,
            active_sources=active_sources,
            recent_updates_24h=recent_updates_24h,
            recent_updates_1h=recent_updates_1h,
            content_types_available=list(content_types),
            cities_covered=list(cities),
            last_update_time=last_update_time.isoformat() if last_update_time else None
        )
        
        logger.info(f"Generated real-time data summary: {summary}")
        return summary
        
    except Exception as e:
        logger.error(f"Error getting real-time data summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate real-time data summary"
        )


# Administrative Endpoints (Future: Add authentication)

@router.post("/sources/refresh")
async def refresh_data_sources(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    source_ids: Optional[str] = Query(None, description="Comma-separated source IDs to refresh")
):
    """
    Manually refresh data from Croatian tourism sources.
    
    Args:
        background_tasks: Background task handler
        db: Database session
        source_ids: Specific source IDs to refresh (optional)
        
    Returns:
        Dict: Refresh operation status
    """
    try:
        logger.info(f"Manual refresh requested for sources: {source_ids}")
        
        # Get sources to refresh
        stmt = select(ContentSource).where(ContentSource.status == SourceStatus.ACTIVE)
        
        if source_ids:
            source_id_list = [s.strip() for s in source_ids.split(",")]
            stmt = stmt.where(ContentSource.id.in_(source_id_list))
        
        result = await db.execute(stmt)
        sources_to_refresh = result.scalars().all()
        
        if not sources_to_refresh:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active sources found to refresh"
            )
        
        # Add background task to perform refresh
        async def refresh_task():
            ai_service = AIService()
            async with Crawl4AIScraperService(db, ai_service) as scraper:
                for source in sources_to_refresh:
                    try:
                        await scraper.scrape_source_advanced(source)
                        logger.info(f"Refreshed source: {source.name}")
                    except Exception as e:
                        logger.error(f"Error refreshing source {source.name}: {e}")
        
        background_tasks.add_task(refresh_task)
        
        return {
            "message": f"Refresh started for {len(sources_to_refresh)} sources",
            "sources": [{"id": str(s.id), "name": s.name} for s in sources_to_refresh],
            "status": "in_progress"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting manual refresh: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start manual refresh"
        )


@router.post("/sources/init")
async def initialize_tourism_sources(db: AsyncSession = Depends(get_db)):
    """Register Croatian tourism sources (idempotent)."""
    try:
        feed = EventsFeedService(db)
        result = await feed.ensure_tourism_sources()
        seed = await feed.seed_regional_events_if_needed()
        return {"success": True, "sources": result, "seed": seed}
    except Exception as e:
        logger.error(f"Failed to init tourism sources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize tourism sources",
        )


@router.post("/events/bootstrap")
async def bootstrap_events_feed(
    db: AsyncSession = Depends(get_db),
    city: Optional[str] = Query("Lovran", description="City focus for seeded events"),
):
    """Init sources, seed regional events, return availability summary."""
    try:
        feed = EventsFeedService(db)
        return await feed.bootstrap_feed(city=city)
    except Exception as e:
        logger.error(f"Events bootstrap failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bootstrap events feed",
        )


@router.get("/events", response_model=List[RealTimeUpdateResponse])
async def get_events_updates(
    db: AsyncSession = Depends(get_db),
    city: Optional[str] = Query(None, description="Filter by city"),
    hours: int = Query(168, ge=1, le=720),
    limit: int = Query(30, ge=1, le=100),
):
    """Convenience endpoint: recent events only."""
    feed = EventsFeedService(db)
    return await feed.get_updates(
        city=city,
        content_types=[ContentType.EVENTS],
        hours=hours,
        limit=limit,
    )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for real-time data service.
    
    Returns:
        Dict: Health status
    """
    return {
        "status": "healthy",
        "service": "real-time-croatian-tourism-data",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "features": [
            "real-time-updates",
            "live-streaming",
            "multi-source-aggregation",
            "croatian-tourism-focus",
            "crawl4ai-integration"
        ]
    } 