"""Tests for profiling module."""

import pytest
from src.profiling import (
    PerformanceMetrics,
    get_metrics_summary,
    reset_metrics,
    timed,
    timed_sync,
)


class TestPerformanceMetrics:
    """Tests for PerformanceMetrics dataclass."""

    def test_initial_state(self):
        """New metrics should have zero values."""
        metrics = PerformanceMetrics()
        assert metrics.call_count == 0
        assert metrics.total_time_ms == 0.0
        assert metrics.avg_time_ms == 0.0

    def test_record_single(self):
        """Recording a single measurement updates metrics correctly."""
        metrics = PerformanceMetrics()
        metrics.record(100.0)
        assert metrics.call_count == 1
        assert metrics.total_time_ms == 100.0
        assert metrics.avg_time_ms == 100.0
        assert metrics.min_time_ms == 100.0
        assert metrics.max_time_ms == 100.0

    def test_record_multiple(self):
        """Multiple recordings calculate averages correctly."""
        metrics = PerformanceMetrics()
        metrics.record(50.0)
        metrics.record(150.0)
        assert metrics.call_count == 2
        assert metrics.total_time_ms == 200.0
        assert metrics.avg_time_ms == 100.0
        assert metrics.min_time_ms == 50.0
        assert metrics.max_time_ms == 150.0


class TestTimedDecorator:
    """Tests for @timed async decorator."""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """Reset metrics before each test."""
        await reset_metrics()

    @pytest.mark.asyncio
    async def test_timed_records_execution(self):
        """@timed should record function execution time."""

        @timed
        async def sample_func():
            return "result"

        result = await sample_func()
        assert result == "result"

        summary = await get_metrics_summary()
        # __qualname__ includes full path like 'Class.method.<locals>.func'
        assert any("sample_func" in key for key in summary)
        matching_key = [k for k in summary if "sample_func" in k][0]
        assert summary[matching_key]["calls"] == 1
        assert summary[matching_key]["avg_ms"] >= 0


class TestTimedSyncDecorator:
    """Tests for @timed_sync sync decorator."""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """Reset metrics before each test."""
        await reset_metrics()

    @pytest.mark.asyncio
    async def test_timed_sync_records_execution(self):
        """@timed_sync should record function execution time."""

        @timed_sync
        def sample_sync_func():
            return 42

        result = sample_sync_func()
        assert result == 42

        summary = await get_metrics_summary()
        # __qualname__ includes full path
        assert any("sample_sync_func" in key for key in summary)
        assert summary[[k for k in summary if "sample_sync_func" in k][0]]["calls"] == 1


class TestGetMetricsSummary:
    """Tests for get_metrics_summary function."""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """Reset metrics before each test."""
        await reset_metrics()

    @pytest.mark.asyncio
    async def test_empty_summary(self):
        """Empty metrics should return empty dict."""
        assert await get_metrics_summary() == {}

    @pytest.mark.asyncio
    async def test_summary_format(self):
        """Summary should have correct format."""

        @timed
        async def test_func():
            pass

        await test_func()
        summary = await get_metrics_summary()
        # __qualname__ includes full path like 'Class.method.<locals>.test_func'
        assert any("test_func" in key for key in summary)
        matching_key = [k for k in summary if "test_func" in k][0]

        assert "calls" in summary[matching_key]
        assert "avg_ms" in summary[matching_key]
        assert "min_ms" in summary[matching_key]
        assert "max_ms" in summary[matching_key]
        assert "total_ms" in summary[matching_key]
