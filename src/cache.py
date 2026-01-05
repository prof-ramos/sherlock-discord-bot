"""In-memory LRU cache with TTL for LLM responses.

Provides caching for API responses to reduce latency and costs
for repeated similar queries.
"""

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol


class MessageLike(Protocol):
    """Protocol for message objects used in caching."""

    user: str
    text: str


logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Entrada individual do cache."""

    value: Any
    created_at: float = field(default_factory=time.time)
    hits: int = 0


class LRUCache:
    """Cache LRU com TTL para respostas da LLM.

    Args:
        max_size: Número máximo de entradas no cache
        ttl_seconds: Tempo de vida em segundos para cada entrada
    """

    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0, "expirations": 0}
        self._lock = threading.Lock()

    def _hash_key(
        self,
        messages: Sequence[MessageLike],
        model: str,
        temperature: float = 1.0,
        max_tokens: int = 512,
    ) -> str:
        """Generates a unique hash for the combination of messages + model config.

        Incorporates model parameters (temperature, max_tokens) into the hash to
        ensure different configurations for the same prompt result in separate cache entries.
        """
        # Take the last 5 messages for the hash
        recent_messages = messages[-5:] if len(messages) > 5 else messages

        # Build a list of message properties to hash
        msg_parts = []
        for m in recent_messages:
            user = getattr(m, "user", "unknown")
            text = getattr(m, "text", str(m))
            msg_parts.append(f"{user}:{text}")

        convo_str = "|".join(msg_parts)
        content = f"{model}:{temperature}:{max_tokens}:{convo_str}"

        # Use a longer SHA-256 hex prefix to further reduce collision risk
        return hashlib.sha256(content.encode()).hexdigest()

    def get(
        self, messages: Sequence[Any], model: str, temperature: float = 1.0, max_tokens: int = 512
    ) -> Optional[Any]:
        """Retrieves a response from the cache."""
        key = self._hash_key(messages, model, temperature, max_tokens)
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats["misses"] += 1
                return None

            # Check TTL
            if time.time() - entry.created_at > self.ttl_seconds:
                del self._cache[key]
                self._stats["misses"] += 1
                self._stats["expirations"] += 1
                logger.debug("🗑️ Cache entry expired for key %s", key[:8])
                return None

            # Move to end (most recent) - LRU
            self._cache.move_to_end(key)
            entry.hits += 1
            self._stats["hits"] += 1
            logger.debug("🎯 Cache HIT for key %s (hits: %d)", key[:8], entry.hits)
            return entry.value

    def set(
        self,
        messages: Sequence[Any],
        model: str,
        value: Any,
        temperature: float = 1.0,
        max_tokens: int = 512,
    ) -> None:
        """Stores a response in the cache."""
        key = self._hash_key(messages, model, temperature, max_tokens)
        with self._lock:
            if key in self._cache:
                # If key already exists, just update it and move to end
                self._cache[key] = CacheEntry(value=value)
                self._cache.move_to_end(key)
                logger.debug("💾 Cache UPDATE for key %s", key[:8])
                return

            # Remove oldest entry if limit reached
            if len(self._cache) >= self.max_size:
                oldest_key, _ = self._cache.popitem(last=False)
                self._stats["evictions"] += 1
                logger.debug("🗑️ Cache evicted oldest entry: %s", oldest_key[:8])

            self._cache[key] = CacheEntry(value=value)
            logger.debug("💾 Cache SET for key %s (size: %d)", key[:8], len(self._cache))

    def clear(self) -> None:
        """Clears the entire cache."""
        with self._lock:
            self._cache.clear()
            logger.info("🧹 Cache cleared")

    @property
    def stats(self) -> dict[str, Any]:
        """Returns cache statistics."""
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0.0
            return {
                **self._stats,
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
                "hit_rate": f"{hit_rate:.1f}%",
            }

    def log_stats(self) -> None:
        """Logs cache statistics."""
        s = self.stats
        logger.info(
            "📦 Cache Stats: size=%d/%d, hits=%d, misses=%d, hit_rate=%s",
            s["size"],
            s["max_size"],
            s["hits"],
            s["misses"],
            s["hit_rate"],
        )


# Global instance of the response cache
try:
    from src.constants import CACHE_MAX_SIZE, CACHE_TTL_SECONDS

    response_cache = LRUCache(max_size=CACHE_MAX_SIZE, ttl_seconds=CACHE_TTL_SECONDS)
    logger.debug(
        "⚙️ Cache initialized with settings: max_size=%d, ttl=%ds", CACHE_MAX_SIZE, CACHE_TTL_SECONDS
    )
except ImportError as e:
    # Fallback to default values if constants not available
    logger.warning("⚠️ Could not import cache settings from constants, using defaults: %s", e)
    response_cache = LRUCache(max_size=100, ttl_seconds=3600)
