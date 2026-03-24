# application/services/cache_service.py
import hashlib
import json
import threading
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SimpleCache:
    """Simple in-memory cache with timeout"""
    
    def __init__(self, timeout=300):
        self.cache = {}
        self.timeout = timeout
        self._lock = threading.Lock()
    
    def get(self, key):
        with self._lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                if datetime.now().timestamp() - timestamp < self.timeout:
                    return value
                del self.cache[key]
        return None
    
    def set(self, key, value):
        with self._lock:
            self.cache[key] = (value, datetime.now().timestamp())
    
    def delete(self, key):
        with self._lock:
            if key in self.cache:
                del self.cache[key]
    
    def clear(self):
        with self._lock:
            self.cache.clear()


class CacheService:
    """Service wrapper for cache operations"""
    
    def __init__(self, timeout=300):
        self.cache = SimpleCache(timeout=timeout)
        self.timeout = timeout
    
    def get_or_set(self, key, func, *args, **kwargs):
        """Get from cache or execute function and cache result"""
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        
        result = func(*args, **kwargs)
        self.cache.set(key, result)
        return result
    
    def invalidate(self, key):
        """Invalidate cache key"""
        self.cache.delete(key)
    
    def invalidate_pattern(self, pattern):
        """Invalidate all keys matching pattern"""
        with self.cache._lock:
            keys_to_delete = [k for k in self.cache.cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self.cache.cache[key]
    
    def generate_key(self, *args, **kwargs):
        """Generate cache key from arguments"""
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
        return hashlib.md5(json.dumps(key_parts).encode()).hexdigest()