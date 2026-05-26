"""
Scheduled tasks for Crawl4AI real-time Croatian tourism data monitoring.

Runs continuous monitoring of Croatian tourism sources and provides real-time
updates to hosts and guests.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from app.core.database import get_async_session
from app.services.crawl4ai_scraper_service import Crawl4AIScraperService
from app.services.ai_service import AIService
from app.models.content_source import ContentSource, SourceStatus, CROATIAN_TOURISM_SOURCES, ContentSourceCreate
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)


async def initialize_crawl4ai_sources():
    """
    Initialize Croatian tourism sources for Crawl4AI monitoring.

    This should be run once during system setup to create enhanced
    content sources optimized for Crawl4AI scraping.
    """
    logger.info("Initializing Crawl4AI Croatian tourism sources...")

    async for db in get_async_session():
        ai_service = AIService()

        async with Crawl4AIScraperService(db, ai_service) as scraper:
            created_sources = []

            # Enhanced source configurations for Crawl4AI
            enhanced_sources = [
                {
                    **source_config,
                    "headers": {
                        "User-Agent": "HostForGuest/1.0 Crawl4AI Croatian Tourism Monitor",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "hr,en;q=0.9",
                        "Accept-Encoding": "gzip, deflate",
                        "DNT": "1",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1"
                    },
                    "rate_limit_delay": 2,  # Respectful crawling
                    "timeout_seconds": 45,   # Allow for dynamic content loading
                    "max_retries": 3,
                    "quality_threshold": 0.8,  # Higher quality threshold for Crawl4AI
                    "requires_human_review": False  # Crawl4AI provides better extraction
                }
                for source_config in CROATIAN_TOURISM_SOURCES
            ]

            for source_config in enhanced_sources:
                try:
                    # Create ContentSourceCreate object
                    source_data = ContentSourceCreate(**source_config)

                    # Check if source already exists
                    existing_source = await db.execute(
                        select(ContentSource).where(ContentSource.url == source_data.url)
                    )
                    if existing_source.scalar_one_or_none():
                        logger.info(f"Source already exists: {source_data.name}")
                        continue

                    # Create the content source
                    source = await scraper.create_content_source(source_data)

                    if source:
                        created_sources.append(source)
                        logger.info(f"Initialized Crawl4AI source: {source.name}")
                    else:
                        logger.error(f"Failed to create Crawl4AI source: {source_config['name']}")

                except Exception as e:
                    logger.error(f"Error initializing Crawl4AI source {source_config['name']}: {e}")

            logger.info(f"Successfully initialized {len(created_sources)} Crawl4AI tourism sources")
            return created_sources


async def run_real_time_monitoring() -> Dict[str, Any]:
    """
    Run real-time monitoring of Croatian tourism sources using Crawl4AI.

    This function performs continuous monitoring with advanced extraction
    capabilities and immediate update processing.

    Returns:
        Dict: Real-time monitoring results
    """
    logger.info("Starting Crawl4AI real-time tourism monitoring")

    start_time = datetime.utcnow()
    results = {
        'task': 'crawl4ai_realtime_monitoring',
        'started_at': start_time,
        'completed_at': None,
        'duration_seconds': 0,
        'success': False,
        'sources_monitored': 0,
        'updates_extracted': 0,
        'real_time_notifications': 0,
        'extraction_strategies_used': [],
        'errors': []
    }

    try:
        async for db in get_async_session():
            # Initialize AI service
            ai_service = AIService()

            # Get active sources ready for real-time monitoring
            stmt = select(ContentSource).where(
                and_(
                    ContentSource.scraping_enabled == True,
                    ContentSource.status == SourceStatus.ACTIVE,
                    ContentSource.next_scrape <= datetime.utcnow()
                )
            )

            result = await db.execute(stmt)
            active_sources = result.scalars().all()

            if not active_sources:
                logger.info("No sources ready for real-time monitoring")
                results['success'] = True
                return results

            logger.info(f"Found {len(active_sources)} sources for real-time monitoring")

            async with Crawl4AIScraperService(db, ai_service) as scraper:
                # Monitor sources concurrently for better real-time performance
                monitoring_tasks = []
                for source in active_sources:
                    task = asyncio.create_task(
                        monitor_source_real_time(scraper, source),
                        name=f"monitor_{source.name}"
                    )
                    monitoring_tasks.append(task)

                # Wait for all monitoring tasks
                monitoring_results = await asyncio.gather(*monitoring_tasks, return_exceptions=True)

                # Process results
                total_updates = 0
                strategies_used = set()

                for i, monitor_result in enumerate(monitoring_results):
                    source = active_sources[i]

                    if isinstance(monitor_result, Exception):
                        error_msg = f"Error monitoring {source.name}: {monitor_result}"
                        logger.error(error_msg)
                        results['errors'].append(error_msg)
                    else:
                        updates_count, strategies = monitor_result
                        total_updates += updates_count
                        strategies_used.update(strategies)
                        results['sources_monitored'] += 1

                results.update({
                    'updates_extracted': total_updates,
                    'extraction_strategies_used': list(strategies_used),
                    'success': len(results['errors']) == 0
                })

                logger.info(f"Real-time monitoring completed: {results}")

    except Exception as e:
        error_msg = f"Critical error in real-time monitoring: {e}"
        logger.error(error_msg)
        results['errors'].append(error_msg)
        results['success'] = False

    finally:
        # Calculate duration
        end_time = datetime.utcnow()
        results['completed_at'] = end_time
        results['duration_seconds'] = (end_time - start_time).total_seconds()

        # Log final results
        if results['success']:
            logger.info(f"Real-time monitoring completed successfully in {results['duration_seconds']:.2f}s")
        else:
            logger.error(f"Real-time monitoring failed after {results['duration_seconds']:.2f}s")

    return results


async def monitor_source_real_time(scraper: Crawl4AIScraperService, source: ContentSource) -> tuple:
    """
    Monitor a single source for real-time updates.

    Args:
        scraper: Crawl4AI scraper service
        source: Content source to monitor

    Returns:
        tuple: (updates_count, strategies_used)
    """
    try:
        logger.debug(f"Real-time monitoring of {source.name}")

        # Use advanced scraping with multiple strategies
        updates = await scraper.scrape_source_advanced(source)

        # Track which strategies were successful
        strategies_used = []
        for update in updates:
            if hasattr(update, 'extraction_strategy'):
                strategies_used.append(update.extraction_strategy)

        # Process high-priority updates immediately
        high_priority_updates = [
            update for update in updates
            if update.relevance_score > 0.8 or update.content_type in ['events', 'opening_hours', 'weather_alerts']
        ]

        if high_priority_updates:
            logger.info(f"Found {len(high_priority_updates)} high-priority updates from {source.name}")
            # Here we could trigger immediate notifications

        return len(updates), list(set(strategies_used))

    except Exception as e:
        logger.error(f"Error in real-time monitoring of {source.name}: {e}")
        return 0, []


async def run_hourly_stream_update() -> Dict[str, Any]:
    """
    Run hourly streaming update to provide fresh data for live feeds.

    Returns:
        Dict: Streaming update results
    """
    logger.info("Starting hourly streaming update")

    start_time = datetime.utcnow()
    results = {
        'task': 'hourly_stream_update',
        'started_at': start_time,
        'completed_at': None,
        'duration_seconds': 0,
        'success': False,
        'stream_updates': 0,
        'sources_streamed': 0,
        'errors': []
    }

    try:
        async for db in get_async_session():
            ai_service = AIService()

            # Get high-priority sources for streaming
            stmt = select(ContentSource).where(
                and_(
                    ContentSource.scraping_enabled == True,
                    ContentSource.status == SourceStatus.ACTIVE,
                    ContentSource.city.in_(["Lovran", "Opatija", "Pula", "Rovinj"])  # Focus on key tourist areas
                )
            )

            result = await db.execute(stmt)
            stream_sources = result.scalars().all()

            if not stream_sources:
                logger.warning("No sources available for streaming update")
                results['success'] = True
                return results

            async with Crawl4AIScraperService(db, ai_service) as scraper:
                # Stream live updates
                stream_data = await scraper.stream_live_updates(stream_sources)

                results.update({
                    'stream_updates': len(stream_data),
                    'sources_streamed': len(stream_sources),
                    'success': True
                })

                logger.info(f"Hourly streaming update completed: {results}")

    except Exception as e:
        error_msg = f"Error in hourly streaming update: {e}"
        logger.error(error_msg)
        results['errors'].append(error_msg)
        results['success'] = False

    finally:
        end_time = datetime.utcnow()
        results['completed_at'] = end_time
        results['duration_seconds'] = (end_time - start_time).total_seconds()

    return results


async def cleanup_old_real_time_data(days_to_keep: int = 7) -> Dict[str, Any]:
    """
    Clean up old real-time data to maintain performance.

    Args:
        days_to_keep: Number of days of real-time data to keep

    Returns:
        Dict: Cleanup results
    """
    logger.info(f"Starting cleanup of real-time data older than {days_to_keep} days")

    results = {
        'task': 'cleanup_realtime_data',
        'timestamp': datetime.utcnow(),
        'days_to_keep': days_to_keep,
        'updates_deleted': 0,
        'notifications_deleted': 0,
        'success': False
    }

    try:
        async for db in get_async_session():
            from sqlalchemy import delete
            from app.models.content_source import ContentUpdate, HostNotification

            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            # Delete old real-time content updates
            delete_updates_stmt = delete(ContentUpdate).where(
                and_(
                    ContentUpdate.created_at < cutoff_date,
                    ContentUpdate.status != "approved"  # Keep approved content longer
                )
            )
            update_result = await db.execute(delete_updates_stmt)
            results['updates_deleted'] = update_result.rowcount

            # Delete old real-time notifications
            delete_notifications_stmt = delete(HostNotification).where(
                HostNotification.created_at < cutoff_date
            )
            notification_result = await db.execute(delete_notifications_stmt)
            results['notifications_deleted'] = notification_result.rowcount

            await db.commit()
            results['success'] = True

            logger.info(f"Real-time data cleanup completed: {results}")

    except Exception as e:
        logger.error(f"Error in real-time data cleanup: {e}")
        results['error'] = str(e)
        results['success'] = False

    return results


# Scheduler reporting helpers for real-time monitoring
async def log_realtime_task_execution(task_name: str, results: Dict[str, Any]):
    """
    Log real-time task results for local monitoring.

    Args:
        task_name: Name of the real-time task
        results: Task execution results
    """
    try:
        # Enhanced logging for real-time monitoring
        task_data = {
            "task_type": "realtime_monitoring",
            "task_name": task_name,
            "results": results,
            "performance_metrics": {
                "duration": results.get('duration_seconds', 0),
                "sources_processed": results.get('sources_monitored', 0),
                "updates_extracted": results.get('updates_extracted', 0),
                "success_rate": 1.0 if results.get('success', False) else 0.0
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        logger.info(f"CRAWL4AI_REALTIME_LOG: {task_name} - {task_data}")

    except Exception as e:
        logger.error(f"Error logging real-time task execution: {e}")


# Main execution functions for different environments
async def main_realtime_monitoring():
    """Main function for real-time monitoring - can be called by scheduler."""
    try:
        results = await run_real_time_monitoring()
        await log_realtime_task_execution("realtime_monitoring", results)
        return results
    except Exception as e:
        logger.error(f"Error in main real-time monitoring: {e}")
        await log_realtime_task_execution("realtime_monitoring", {"error": str(e), "success": False})
        raise


async def main_hourly_stream():
    """Main function for hourly streaming - can be called by scheduler."""
    try:
        results = await run_hourly_stream_update()
        await log_realtime_task_execution("hourly_stream_update", results)
        return results
    except Exception as e:
        logger.error(f"Error in main hourly stream: {e}")
        await log_realtime_task_execution("hourly_stream_update", {"error": str(e), "success": False})
        raise


if __name__ == "__main__":
    # This allows the script to be run directly for testing
    import sys

    if len(sys.argv) > 1:
        task = sys.argv[1]

        if task == "init":
            asyncio.run(initialize_crawl4ai_sources())
        elif task == "realtime":
            asyncio.run(main_realtime_monitoring())
        elif task == "stream":
            asyncio.run(main_hourly_stream())
        elif task == "cleanup":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            asyncio.run(cleanup_old_real_time_data(days))
        else:
            print("Usage: python crawl4ai_realtime_tasks.py [init|realtime|stream|cleanup]")
    else:
        print("Available tasks: init, realtime, stream, cleanup")
        print("Examples:")
        print("  python crawl4ai_realtime_tasks.py init      # Initialize Crawl4AI sources")
        print("  python crawl4ai_realtime_tasks.py realtime  # Run real-time monitoring")
        print("  python crawl4ai_realtime_tasks.py stream    # Run hourly stream update")
        print("  python crawl4ai_realtime_tasks.py cleanup 7 # Cleanup data older than 7 days")
