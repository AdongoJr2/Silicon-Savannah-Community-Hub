"""
Cache decorators for easy function result caching.
"""
import hashlib
import json
from functools import wraps
from typing import Callable, Any
from app.cache.redis_client import cache
from app.core.logging import logger


def cached(key_prefix: str, expire: int = 300):
    """
    Decorator to cache function results with configurable TTL.
    
    Args:
        key_prefix: Prefix for the cache key
        expire: Expiration time in seconds (default: 300 = 5 minutes)
        
    Usage:
        @cached('events', expire=300)
        async def get_events():
            return events
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Generate cache key from function args
            args_key = _generate_key_from_args(args, kwargs)
            cache_key = f"{key_prefix}:{args_key}"
            
            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_value
            
            # Call the function if cache miss
            logger.debug(f"Cache miss for key: {cache_key}")
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cache.set(cache_key, result, expire)
            
            return result
        return wrapper
    return decorator


def _generate_key_from_args(args: tuple, kwargs: dict) -> str:
    """
    Generate a unique cache key from function arguments.
    
    Args:
        args: Positional arguments
        kwargs: Keyword arguments
        
    Returns:
        MD5 hash of the arguments
    """
    # Skip first arg if it's 'self' or a session object
    filtered_args = []
    for arg in args:
        arg_type = str(type(arg))
        # Skip SQLAlchemy session objects
        if 'AsyncSession' not in arg_type and 'Session' not in arg_type:
            filtered_args.append(arg)
    
    # Create a string representation of args
    key_data = {
        'args': [str(arg) for arg in filtered_args],
        'kwargs': {k: str(v) for k, v in kwargs.items()}
    }
    key_string = json.dumps(key_data, sort_keys=True)
    
    # Return MD5 hash
    return hashlib.md5(key_string.encode()).hexdigest()
