"""
Scheduled tasks for automated content scraping.

Integrates with Archon workflow to run weekly content updates
from Croatian tourism sources and notify hosts of relevant changes.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from app.core.database import get_async_session
from app.services.content_scraper_service import ContentScraperService
from app.services.ai_service import AIService
from app.models.content_source import CROATIAN_TOURISM_SOURCES, ContentSourceCreate

logger = logging.getLogger(__name__)


async def initialize_tourism_sources():
    """
    Initialize Croatian tourism sources for content monitoring.
    
    This should be run once during system setup to create the
    content sources that will be monitored weekly.
    """
    logger.info("Initializing Croatian tourism content sources...")
    
    async with get_async_session() as db:
        async with ContentScraperService(db) as scraper:
            
            created_sources = []
            
            for source_config in CROATIAN_TOURISM_SOURCES:
                try:
                    # Create ContentSourceCreate object
                    source_data = ContentSourceCreate(**source_config)
                    
                    # Create the content source
                    source = await scraper.create_content_source(source_data)
                    
                    if source:
                        created_sources.append(source)
                        logger.info(f"Initialized content source: {source.name}")
                    else:
                        logger.error(f"Failed to create source: {source_config['name']}")
                        
                except Exception as e:
                    logger.error(f"Error initializing source {source_config['name']}: {e}")
            
            logger.info(f"Successfully initialized {len(created_sources)} tourism content sources")
            return created_sources


async def run_weekly_content_scraping() -> Dict[str, Any]:
    """
    Run weekly content scraping for all Croatian tourism sources.
    
    This function is designed to be called by a scheduler (like cron)
    to automatically update content from tourism websites.
    
    Returns:
        Dict: Results summary for monitoring and logging
    """
    logger.info("Starting weekly Croatian tourism content scraping")
    
    start_time = datetime.utcnow()
    results = {
        'task': 'weekly_content_scraping',
        'started_at': start_time,
        'completed_at': None,
        'duration_seconds': 0,
        'success': False,
        'sources_processed': 0,
        'total_updates_found': 0,
        'host_notifications_sent': 0,
        'errors': []
    }
    
    try:
        async with get_async_session() as db:
            # Initialize AI service for content analysis
            ai_service = AIService()
            
            # Create content scraper service
            async with ContentScraperService(db, ai_service) as scraper:
                
                # Run the scheduled scraping
                scraping_results = await scraper.run_scheduled_scraping()
                
                # Update results
                results.update({
                    'sources_processed': scraping_results['sources_processed'],
                    'total_updates_found': scraping_results['total_updates'],
                    'host_notifications_sent': scraping_results['notifications_sent'],
                    'errors': scraping_results['errors']
                })
                
                # Mark as successful if no critical errors
                results['success'] = len(scraping_results['errors']) == 0
                
                logger.info(f"Weekly scraping completed successfully: {results}")
    
    except Exception as e:
        error_msg = f"Critical error in weekly content scraping: {e}"
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
            logger.info(f"Weekly content scraping completed successfully in {results['duration_seconds']:.2f}s")
        else:
            logger.error(f"Weekly content scraping failed after {results['duration_seconds']:.2f}s")
    
    return results


async def run_daily_content_health_check() -> Dict[str, Any]:
    """
    Run daily health check for content sources.
    
    Checks the status of content sources and reports any issues
    that need attention.
    
    Returns:
        Dict: Health check results
    """
    logger.info("Starting daily content source health check")
    
    results = {
        'task': 'daily_health_check',
        'timestamp': datetime.utcnow(),
        'total_sources': 0,
        'active_sources': 0,
        'error_sources': 0,
        'sources_needing_attention': [],
        'recommendations': []
    }
    
    try:
        async with get_async_session() as db:
            async with ContentScraperService(db) as scraper:
                
                # Get all content sources
                from sqlalchemy import select
                from app.models.content_source import ContentSource, SourceStatus
                
                stmt = select(ContentSource)
                result = await db.execute(stmt)
                sources = result.scalars().all()
                
                results['total_sources'] = len(sources)
                
                for source in sources:
                    if source.status == SourceStatus.ACTIVE:
                        results['active_sources'] += 1
                    elif source.status == SourceStatus.ERROR:
                        results['error_sources'] += 1
                        results['sources_needing_attention'].append({
                            'name': source.name,
                            'url': source.url,
                            'status': source.status,
                            'last_error': source.last_error,
                            'consecutive_failures': source.consecutive_failures
                        })
                    
                    # Check for sources that haven't been scraped recently
                    if source.last_scraped:
                        days_since_scrape = (datetime.utcnow() - source.last_scraped).days
                        if days_since_scrape > 14:  # Haven't scraped in 2 weeks
                            results['sources_needing_attention'].append({
                                'name': source.name,
                                'issue': f'Not scraped for {days_since_scrape} days',
                                'last_scraped': source.last_scraped
                            })
                
                # Generate recommendations
                if results['error_sources'] > 0:
                    results['recommendations'].append(
                        f"Review {results['error_sources']} sources in error status"
                    )
                
                if len(results['sources_needing_attention']) > 0:
                    results['recommendations'].append(
                        f"Check {len(results['sources_needing_attention'])} sources needing attention"
                    )
                
                logger.info(f"Health check completed: {results}")
    
    except Exception as e:
        logger.error(f"Error in daily health check: {e}")
        results['error'] = str(e)
    
    return results


async def cleanup_old_content_updates(days_to_keep: int = 90) -> Dict[str, Any]:
    """
    Clean up old content updates to prevent database bloat.
    
    Args:
        days_to_keep: Number of days of content updates to keep
        
    Returns:
        Dict: Cleanup results
    """
    logger.info(f"Starting cleanup of content updates older than {days_to_keep} days")
    
    results = {
        'task': 'cleanup_old_content',
        'timestamp': datetime.utcnow(),
        'days_to_keep': days_to_keep,
        'updates_deleted': 0,
        'notifications_deleted': 0,
        'success': False
    }
    
    try:
        async with get_async_session() as db:
            from sqlalchemy import delete
            from app.models.content_source import ContentUpdate, HostNotification
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Delete old content updates
            delete_updates_stmt = delete(ContentUpdate).where(
                ContentUpdate.created_at < cutoff_date
            )
            update_result = await db.execute(delete_updates_stmt)
            results['updates_deleted'] = update_result.rowcount
            
            # Delete old notifications
            delete_notifications_stmt = delete(HostNotification).where(
                HostNotification.created_at < cutoff_date
            )
            notification_result = await db.execute(delete_notifications_stmt)
            results['notifications_deleted'] = notification_result.rowcount
            
            await db.commit()
            results['success'] = True
            
            logger.info(f"Cleanup completed: deleted {results['updates_deleted']} updates and {results['notifications_deleted']} notifications")
    
    except Exception as e:
        logger.error(f"Error in cleanup task: {e}")
        results['error'] = str(e)
        results['success'] = False
    
    return results


# Archon Integration Functions
async def log_task_to_archon(task_name: str, results: Dict[str, Any]):
    """
    Log task results to Archon for monitoring and tracking.
    
    Args:
        task_name: Name of the task
        results: Task execution results
    """
    try:
        # This would integrate with the Archon API to log task execution
        # For now, we'll just log locally
        logger.info(f"ARCHON_TASK_LOG: {task_name} - {results}")
        
        # Future enhancement: Send to Archon API
        # await archon_api.log_task_execution(task_name, results)
        
    except Exception as e:
        logger.error(f"Error logging to Archon: {e}")


async def update_archon_task_status(task_id: str, status: str, notes: str = ""):
    """
    Update Archon task status.
    
    Args:
        task_id: Archon task ID
        status: New status
        notes: Optional notes
    """
    try:
        # This would integrate with the Archon API
        logger.info(f"ARCHON_STATUS_UPDATE: Task {task_id} -> {status}: {notes}")
        
        # Future enhancement: Update via Archon API
        # await archon_api.update_task_status(task_id, status, notes)
        
    except Exception as e:
        logger.error(f"Error updating Archon task status: {e}")


# Main execution functions for different environments
async def main_weekly_scraping():
    """Main function for weekly scraping - can be called by cron."""
    try:
        results = await run_weekly_content_scraping()
        await log_task_to_archon("weekly_content_scraping", results)
        return results
    except Exception as e:
        logger.error(f"Error in main weekly scraping: {e}")
        await log_task_to_archon("weekly_content_scraping", {"error": str(e), "success": False})
        raise


async def main_daily_health_check():
    """Main function for daily health check - can be called by cron."""
    try:
        results = await run_daily_content_health_check()
        await log_task_to_archon("daily_health_check", results)
        return results
    except Exception as e:
        logger.error(f"Error in main daily health check: {e}")
        await log_task_to_archon("daily_health_check", {"error": str(e), "success": False})
        raise


if __name__ == "__main__":
    # This allows the script to be run directly for testing
    import sys
    
    if len(sys.argv) > 1:
        task = sys.argv[1]
        
        if task == "init":
            asyncio.run(initialize_tourism_sources())
        elif task == "weekly":
            asyncio.run(main_weekly_scraping())
        elif task == "health":
            asyncio.run(main_daily_health_check())
        elif task == "cleanup":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 90
            asyncio.run(cleanup_old_content_updates(days))
        else:
            print("Usage: python content_scraper_tasks.py [init|weekly|health|cleanup]")
    else:
        print("Available tasks: init, weekly, health, cleanup")
        print("Example: python content_scraper_tasks.py weekly") 