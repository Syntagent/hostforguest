"""
Redis caching service for performance optimization.

Provides caching layer for frequently accessed data
to reduce database load and improve response times.
"""

import logging
from typing import Optional, Any, Dict
import json
from datetime import timedelta

logger = logging.getLogger(__name__)

# Try to import Redis, fallback to in-memory cache if not available
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory cache")


class CacheService:
    """
    Caching service with Redis backend.
    
    Falls back to in-memory cache if Redis is not available.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize cache service.
        
        Args:
            redis_url: Optional Redis connection URL
        """
        self.redis_client: Optional[redis.Redis] = None
        self.in_memory_cache: Dict[str, Any] = {}
        self.use_redis = False
        
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.use_redis = True
                logger.info("Redis cache initialized")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}, using in-memory cache")
                self.use_redis = False
        else:
            logger.info("Using in-memory cache (Redis not configured)")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        try:
            if self.use_redis and self.redis_client:
                value = await self.redis_client.get(key)
                if value:
                    return json.loads(value)
            else:
                # In-memory cache
                if key in self.in_memory_cache:
                    entry = self.in_memory_cache[key]
                    # Check expiration
                    from datetime import datetime
                    if entry.get("expires_at") and entry["expires_at"] > datetime.utcnow():
                        return entry["value"]
                    else:
                        # Expired, remove it
                        del self.in_memory_cache[key]
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting from cache: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            True if set successfully, False otherwise
        """
        try:
            if self.use_redis and self.redis_client:
                serialized = json.dumps(value)
                if ttl:
                    await self.redis_client.setex(key, ttl, serialized)
                else:
                    await self.redis_client.set(key, serialized)
            else:
                # In-memory cache
                from datetime import datetime, timedelta
                entry = {
                    "value": value,
                    "expires_at": datetime.utcnow() + timedelta(seconds=ttl) if ttl else None
                }
                self.in_memory_cache[key] = entry
                
                # Clean up expired entries periodically
                if len(self.in_memory_cache) > 1000:
                    self._cleanup_expired()
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting cache: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            if self.use_redis and self.redis_client:
                await self.redis_client.delete(key)
            else:
                self.in_memory_cache.pop(key, None)
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting from cache: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Key pattern (e.g., "host:*")
            
        Returns:
            Number of keys deleted
        """
        try:
            if self.use_redis and self.redis_client:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    return await self.redis_client.delete(*keys)
                return 0
            else:
                # In-memory cache - simple pattern matching
                from datetime import datetime
                deleted = 0
                keys_to_delete = [
                    k for k in self.in_memory_cache.keys()
                    if self._match_pattern(k, pattern)
                ]
                for key in keys_to_delete:
                    del self.in_memory_cache[key]
                    deleted += 1
                return deleted
            
        except Exception as e:
            logger.error(f"Error deleting pattern from cache: {e}")
            return 0
    
    def _cleanup_expired(self) -> None:
        """Clean up expired entries from in-memory cache."""
        from datetime import datetime
        now = datetime.utcnow()
        expired_keys = [
            k for k, v in self.in_memory_cache.items()
            if v.get("expires_at") and v["expires_at"] <= now
        ]
        for key in expired_keys:
            del self.in_memory_cache[key]
    
    def _match_pattern(self, key: str, pattern: str) -> bool:
        """Simple pattern matching for in-memory cache."""
        if "*" in pattern:
            prefix = pattern.split("*")[0]
            return key.startswith(prefix)
        return key == pattern
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()


# Global cache service instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """
    Get global cache service instance.
    
    Returns:
        Cache service instance
    """
    global _cache_service
    if _cache_service is None:
        from app.core.config import settings
        redis_url = getattr(settings, "redis_url", None)
        _cache_service = CacheService(redis_url)
    return _cache_service

