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
from uuid import UUID
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.auth import require_host_or_maintenance_job_secret
from app.core.database import get_db
from app.api.v1.hosts import get_current_host
from app.services.crawl4ai_scraper_service import Crawl4AIScraperService
from app.services.ai_service import AIService
from app.services.events_feed_service import EventsFeedService
from app.services.event_ingestion_service import EventIngestionService
from app.services.event_source_discovery_agent import EventSourceDiscoveryAgent
from app.services.host_service import HostService
from app.models.content_source import ContentType
from app.models.content_source import ContentSource, ContentUpdate, SourceStatus
from app.models.event_source_proposal import EventSourceProposal
from app.models.host import Host
from pydantic import BaseModel, Field
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter()


# Response Models
class RealTimeUpdatePublicResponse(BaseModel):
    """Anonymous tourism feed row — no crawler timestamps or scoring metadata."""

    model_config = {"extra": "ignore"}

    id: str
    title: str
    content: str
    url: Optional[str] = None
    publication_date: Optional[str] = None
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    venue_name: Optional[str] = None
    relevant_cities: List[str] = Field(default_factory=list)
    relevant_regions: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class RealTimeUpdateResponse(BaseModel):
    """Response model for real-time updates."""
    id: str
    title: str
    content: str
    content_type: str
    url: Optional[str]
    publication_date: Optional[str]
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    venue_name: Optional[str] = None
    relevant_cities: List[str]
    relevant_regions: List[str]
    keywords: List[str]
    quality_score: Optional[float] = None
    relevance_score: Optional[float] = None
    created_at: str
    source_name: Optional[str]
    is_demo_seed: Optional[bool] = None


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


class EventSourceProposalResponse(BaseModel):
    """GET /realtime/sources/proposals row."""
    id: str
    proposed_name: str
    proposed_url: str
    source_type: str
    confidence: float
    reasoning: Optional[str] = None
    status: str
    city: Optional[str] = None
    region: Optional[str] = None


class EventSourceProposalApproveResponse(BaseModel):
    """POST /realtime/sources/proposals/{id}/approve."""
    success: bool = True
    source_id: str
    name: str


class EventSourceProposalRejectResponse(BaseModel):
    """POST /realtime/sources/proposals/{id}/reject."""
    success: bool = True


class EventSourceHealthResponse(BaseModel):
    """GET /realtime/sources/health row — mirrors frontend EventSourceHealth."""

    source_id: str
    name: str
    url: str
    status: str
    last_scraped: Optional[str] = None
    consecutive_failures: int
    last_error: Optional[str] = None
    total_scrapes: int
    successful_scrapes: int
    maintenance_hint: Optional[str] = None


class RealtimeSourceRefreshItem(BaseModel):
    """Single source in POST /realtime/sources/refresh response."""

    id: str
    name: str


class RealtimeSourcesRefreshResponse(BaseModel):
    """POST /realtime/sources/refresh status envelope."""

    message: str
    sources: List[RealtimeSourceRefreshItem]
    status: str


class RealtimeSourcesInitResponse(BaseModel):
    """POST /realtime/sources/init success envelope."""

    model_config = {"extra": "allow"}

    success: bool
    sources: Dict[str, Any]
    seed: Dict[str, Any]


class EventsBootstrapResponse(BaseModel):
    """POST /realtime/events/bootstrap summary."""

    model_config = {"extra": "allow"}

    sources: Optional[Dict[str, Any]] = None
    seed: Optional[Dict[str, Any]] = None
    purge: Optional[Any] = None
    expired_past: Optional[Any] = None
    sync: Optional[Dict[str, Any]] = None
    coordinates: Optional[Dict[str, Any]] = None
    events_available: int


class DiscoverSourcesResponse(BaseModel):
    """POST /realtime/sources/discover success envelope."""

    model_config = {"extra": "allow"}

    success: bool
    context: Optional[Dict[str, Any]] = None
    proposals_created: int
    proposal_ids: Optional[List[str]] = None


class EventSourceScrapeResponse(BaseModel):
    """POST /realtime/sources/{source_id}/scrape result."""

    model_config = {"extra": "allow"}

    slug: str
    success: bool
    events_found: Optional[int] = None
    events_upserted: Optional[int] = None
    source_id: Optional[str] = None
    error: Optional[str] = None


# Public Endpoints (No Authentication Required)

@router.get(
    "/updates",
    response_model=List[RealTimeUpdatePublicResponse],
    response_model_exclude_none=True,
)
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
    regions: Optional[str] = Query(None, description="Comma-separated regions (Istria,Kvarner,etc.)"),
    _auth: None = Depends(require_host_or_maintenance_job_secret),
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
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_host_or_maintenance_job_secret),
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
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_host_or_maintenance_job_secret),
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


# Administrative Endpoints (host session or X-Maintenance-Job-Secret)

@router.post("/sources/refresh", response_model=RealtimeSourcesRefreshResponse)
async def refresh_data_sources(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    source_ids: Optional[str] = Query(None, description="Comma-separated source IDs to refresh"),
    _auth: None = Depends(require_host_or_maintenance_job_secret),
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


@router.post("/sources/init", response_model=RealtimeSourcesInitResponse)
async def initialize_tourism_sources(
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_host_or_maintenance_job_secret),
):
    """Register Croatian tourism sources (idempotent)."""
    try:
        feed = EventsFeedService(db)
        result = await feed.ensure_tourism_sources()
        seed = await feed.seed_regional_events_if_needed()
        return RealtimeSourcesInitResponse(success=True, sources=result, seed=seed)
    except Exception as e:
        logger.error(f"Failed to init tourism sources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize tourism sources",
        )


@router.post("/events/bootstrap", response_model=EventsBootstrapResponse)
async def bootstrap_events_feed(
    db: AsyncSession = Depends(get_db),
    city: Optional[str] = Query("Lovran", description="City focus for seeded events"),
    sync_mode: Optional[str] = Query(
        None,
        description="all | regional | none — default from EVENTS_SYNC_MODE env (regional)",
    ),
    _auth: None = Depends(require_host_or_maintenance_job_secret),
):
    """Init sources, seed regional events, return availability summary."""
    try:
        feed = EventsFeedService(db)
        return await feed.bootstrap_feed(city=city, sync_mode=sync_mode)
    except Exception as e:
        logger.error(f"Events bootstrap failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bootstrap events feed",
        )


@router.get("/events", response_model=List[RealTimeUpdateResponse])
async def get_events_updates(
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_host_or_maintenance_job_secret),
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
        omit_internal_scores=False,
    )


@router.get("/sources/health", response_model=List[EventSourceHealthResponse])
async def get_sources_health(
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_host_or_maintenance_job_secret),
):
    """Per-source scrape health for event monitors."""
    feed = EventsFeedService(db)
    return await feed.get_source_health()


@router.post("/sources/discover", response_model=DiscoverSourcesResponse)
async def discover_event_sources(
    db: AsyncSession = Depends(get_db),
    current_host: Host = Depends(get_current_host),
):
    """Run discovery agent for host property location."""
    host_service = HostService(db)
    profile = await host_service.get_host_profile(current_host.id)
    agent = EventSourceDiscoveryAgent(db)
    return await agent.discover_for_host(current_host, profile)


@router.get("/sources/proposals", response_model=List[EventSourceProposalResponse])
async def list_source_proposals(
    db: AsyncSession = Depends(get_db),
    current_host: Host = Depends(get_current_host),
    status_filter: Optional[str] = Query("pending"),
):
    stmt = select(EventSourceProposal).where(EventSourceProposal.host_id == current_host.id)
    if status_filter:
        stmt = stmt.where(EventSourceProposal.status == status_filter)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [
        EventSourceProposalResponse(
            id=str(p.id),
            proposed_name=p.proposed_name,
            proposed_url=p.proposed_url,
            source_type=p.source_type,
            confidence=p.confidence,
            reasoning=p.reasoning,
            status=p.status,
            city=p.city,
            region=p.region,
        )
        for p in rows
    ]


@router.post(
    "/sources/proposals/{proposal_id}/approve",
    response_model=EventSourceProposalApproveResponse,
)
async def approve_source_proposal(
    proposal_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_host: Host = Depends(get_current_host),
):
    agent = EventSourceDiscoveryAgent(db)
    source = await agent.approve_proposal(proposal_id, current_host.id)
    if not source:
        raise HTTPException(status_code=404, detail="Proposal not found or not pending")
    return EventSourceProposalApproveResponse(
        success=True,
        source_id=str(source.id),
        name=source.name,
    )


@router.post(
    "/sources/proposals/{proposal_id}/reject",
    response_model=EventSourceProposalRejectResponse,
)
async def reject_source_proposal(
    proposal_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_host: Host = Depends(get_current_host),
):
    agent = EventSourceDiscoveryAgent(db)
    ok = await agent.reject_proposal(proposal_id, current_host.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return EventSourceProposalRejectResponse(success=True)


@router.post("/sources/{source_id}/scrape", response_model=EventSourceScrapeResponse)
async def scrape_single_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_host_or_maintenance_job_secret),
):
    """Manual scrape for a content source linked to national registry slug."""
    row = await db.execute(select(ContentSource).where(ContentSource.id == source_id))
    source = row.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    selectors = source.scraping_selectors or {}
    slug = selectors.get("slug")
    if not slug:
        from app.scraping.events.sources import load_national_event_sources

        src_url = (source.url or "").rstrip("/")
        for defn in load_national_event_sources():
            reg_url = (defn.get("url") or "").rstrip("/")
            if defn.get("name") == source.name or (
                src_url and reg_url and (src_url in reg_url or reg_url in src_url)
            ):
                slug = defn["slug"]
                break
    if not slug:
        raise HTTPException(status_code=400, detail="Source has no event scraper slug")
    ingestion = EventIngestionService(db)
    return await ingestion.sync_source(str(slug))


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