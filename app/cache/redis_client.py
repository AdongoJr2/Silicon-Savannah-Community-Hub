"""
Redis cache client with connection pooling and JSON serialization.
"""
import json
from typing import Optional, Any
import redis
from redis.connection import ConnectionPool
from app.core.config import settings
from app.core.logging import logger


class RedisCache:
    """Redis cache client with connection pooling."""
    
    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
    
    def _get_client(self) -> redis.Redis:
        """Get or create Redis client with connection pooling."""
        if self._client is None:
            self._pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                max_connections=20
            )
            self._client = redis.Redis(connection_pool=self._pool)
            logger.info("Redis connection pool created")
        return self._client
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache by key.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        try:
            client = self._get_client()
            value = client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, expire: int = 300) -> bool:
        """
        Set value in cache with expiration.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            expire: Expiration time in seconds (default: 300)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = self._get_client()
            serialized = json.dumps(value, default=str)
            client.setex(key, expire, serialized)
            return True
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = self._get_client()
            client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Key pattern (e.g., 'events:*')
            
        Returns:
            Number of keys deleted
        """
        try:
            client = self._get_client()
            keys = client.keys(pattern)
            if keys:
                return client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis DELETE_PATTERN error for pattern {pattern}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            client = self._get_client()
            return client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False
    
    def close(self):
        """Close Redis connection pool."""
        if self._client:
            self._client.close()
            logger.info("Redis connection pool closed")


# Create a single instance to be imported throughout the app
cache = RedisCache()
