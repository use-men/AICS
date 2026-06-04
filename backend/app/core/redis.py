"""
Redis client and verification code helpers.
Falls back to in-memory cache when Redis is unavailable.
"""

import random
import string
import time
import logging

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---- Redis client singleton ----

_redis: redis.Redis | None = None
_redis_available = True  # assume available until proven otherwise

# ---- In-memory fallback cache ----

_memory_cache: dict[str, tuple[str, float]] = {}  # key -> (value, expire_timestamp)


def _memory_get(key: str) -> str | None:
    """Get value from memory cache, auto-expire."""
    item = _memory_cache.get(key)
    if item is None:
        return None
    value, expire_at = item
    if time.time() > expire_at:
        del _memory_cache[key]
        return None
    return value


def _memory_setex(key: str, ttl: int, value: str) -> None:
    """Set value in memory cache with TTL."""
    _memory_cache[key] = (value, time.time() + ttl)


def _memory_delete(key: str) -> None:
    """Delete value from memory cache."""
    _memory_cache.pop(key, None)


def _memory_exists(key: str) -> bool:
    """Check if key exists in memory cache."""
    return _memory_get(key) is not None


# ---- Public API ----

async def get_redis() -> redis.Redis:
    global _redis, _redis_available
    if _redis is None and _redis_available:
        try:
            _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            await _redis.ping()
        except Exception as e:
            logger.warning("Redis unavailable, using in-memory cache: %s", e)
            _redis_available = False
            _redis = None
    if _redis is None:
        raise RuntimeError("Redis not available")
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None


# ---- Verification code helpers ----

CODE_TTL_SECONDS = 300  # 5 minutes
CODE_LENGTH = 6


async def generate_and_store_code(identifier: str, purpose: str = "login") -> str:
    code = "".join(random.choices(string.digits, k=CODE_LENGTH))
    redis_key = f"verify_code:{purpose}:{identifier}"
    try:
        r = await get_redis()
        await r.setex(redis_key, CODE_TTL_SECONDS, code)
    except Exception:
        logger.info("Using in-memory cache for code: %s", redis_key)
        _memory_setex(redis_key, CODE_TTL_SECONDS, code)
    return code


async def verify_code(identifier: str, code: str, purpose: str = "login") -> bool:
    redis_key = f"verify_code:{purpose}:{identifier}"
    try:
        r = await get_redis()
        stored = await r.get(redis_key)
        if stored is None:
            return False
        if stored != code:
            return False
        await r.delete(redis_key)
        return True
    except Exception:
        stored = _memory_get(redis_key)
        if stored is None:
            return False
        if stored != code:
            return False
        _memory_delete(redis_key)
        return True


async def code_exists(identifier: str, purpose: str = "login") -> bool:
    redis_key = f"verify_code:{purpose}:{identifier}"
    try:
        r = await get_redis()
        return await r.exists(redis_key) > 0
    except Exception:
        return _memory_exists(redis_key)
