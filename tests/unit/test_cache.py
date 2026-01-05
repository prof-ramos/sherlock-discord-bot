"""Tests for cache module."""

import time

from src.cache import CacheEntry, LRUCache


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_default_values(self):
        """CacheEntry should have correct defaults."""
        entry = CacheEntry(value="test")
        assert entry.value == "test"
        assert entry.hits == 0
        assert entry.created_at > 0


class TestLRUCache:
    """Tests for LRUCache class."""

    def test_get_miss(self):
        """Cache miss should return None."""
        cache = LRUCache(max_size=10, ttl_seconds=60)
        result = cache.get([], "model")
        assert result is None
        assert cache.stats["misses"] == 1

    def test_set_and_get(self):
        """Setting and getting a value should work."""
        cache = LRUCache(max_size=10, ttl_seconds=60)

        # Mock messages with user/text attributes
        class MockMessage:
            def __init__(self, user, text):
                self.user = user
                self.text = text

        messages = [MockMessage("user1", "hello")]
        cache.set(messages, "gpt-4", "response")

        result = cache.get(messages, "gpt-4")
        assert result == "response"
        assert cache.stats["hits"] == 1

    def test_different_models_different_keys(self):
        """Different models should have different cache keys."""
        cache = LRUCache(max_size=10, ttl_seconds=60)

        class MockMessage:
            def __init__(self, user, text):
                self.user = user
                self.text = text

        messages = [MockMessage("user1", "hello")]
        cache.set(messages, "gpt-4", "response-gpt4")
        cache.set(messages, "gpt-3.5", "response-gpt35")

        assert cache.get(messages, "gpt-4") == "response-gpt4"
        assert cache.get(messages, "gpt-3.5") == "response-gpt35"

    def test_ttl_expiration(self):
        """Expired entries should be evicted."""
        cache = LRUCache(max_size=10, ttl_seconds=0)  # Immediate expiration

        class MockMessage:
            def __init__(self, user, text):
                self.user = user
                self.text = text

        messages = [MockMessage("user", "test")]
        cache.set(messages, "model", "value")

        # Sleep a tiny bit to ensure expiration
        time.sleep(0.01)

        result = cache.get(messages, "model")
        assert result is None
        assert cache.stats["expirations"] >= 1

    def test_lru_eviction(self):
        """LRU eviction should remove oldest entry when full."""
        cache = LRUCache(max_size=2, ttl_seconds=60)

        class MockMessage:
            def __init__(self, user, text):
                self.user = user
                self.text = text

        # Add 3 entries to a cache with max_size=2
        cache.set([MockMessage("a", "1")], "m", "v1")
        cache.set([MockMessage("b", "2")], "m", "v2")
        cache.set([MockMessage("c", "3")], "m", "v3")

        # First entry should be evicted
        assert cache.get([MockMessage("a", "1")], "m") is None
        assert cache.get([MockMessage("b", "2")], "m") == "v2"
        assert cache.get([MockMessage("c", "3")], "m") == "v3"

    def test_clear(self):
        """Clear should empty the cache."""
        cache = LRUCache(max_size=10, ttl_seconds=60)

        class MockMessage:
            def __init__(self, user, text):
                self.user = user
                self.text = text

        cache.set([MockMessage("u", "t")], "m", "v")
        cache.clear()
        assert cache.stats["size"] == 0

    def test_stats(self):
        """Stats should return correct information."""
        cache = LRUCache(max_size=100, ttl_seconds=3600)
        stats = cache.stats

        assert "hits" in stats
        assert "misses" in stats
        assert "size" in stats
        assert "max_size" in stats
        assert "ttl_seconds" in stats
        assert "hit_rate" in stats
