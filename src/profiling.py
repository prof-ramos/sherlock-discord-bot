"""Performance profiling utilities for Sherlock Discord Bot.

Provides decorators and utilities for measuring execution time and
collecting performance metrics.
"""

import asyncio
import functools
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class PerformanceMetrics:
    """Armazena métricas de performance por função."""

    call_count: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = field(default_factory=lambda: float("inf"))
    max_time_ms: float = 0.0

    @property
    def avg_time_ms(self) -> float:
        """Calcula tempo médio de execução."""
        return self.total_time_ms / self.call_count if self.call_count > 0 else 0.0

    def record(self, elapsed_ms: float) -> None:
        """Registra uma nova medição."""
        self.call_count += 1
        self.total_time_ms += elapsed_ms
        self.min_time_ms = min(self.min_time_ms, elapsed_ms)
        self.max_time_ms = max(self.max_time_ms, elapsed_ms)


# Global registry for metrics
_metrics: dict[str, PerformanceMetrics] = defaultdict(PerformanceMetrics)
_metrics_lock: Optional[asyncio.Lock] = None
_metrics_sync_lock = threading.Lock()


def _get_metrics_lock() -> asyncio.Lock:
    """Lazy initialization of the asyncio lock to ensure it's in the correct event loop."""
    global _metrics_lock
    if _metrics_lock is None:
        _metrics_lock = asyncio.Lock()
    return _metrics_lock


def timed(func: F) -> F:
    """Decorator that measures execution time of async functions.

    Usage:
        @timed
        async def my_function():
            ...
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            return await func(*args, **kwargs)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            async with _get_metrics_lock():
                # Also acquire sync lock for cross-context safety
                with _metrics_sync_lock:
                    metrics = _metrics[func.__qualname__]
                    metrics.record(elapsed_ms)
            logger.debug("⏱️ %s completed in %.2fms", func.__qualname__, elapsed_ms)

    return wrapper  # type: ignore[return-value]


def timed_sync(func: F) -> F:
    """Decorator that measures execution time of synchronous functions.

    Usage:
        @timed_sync
        def my_function():
            ...
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            # Note: We only use sync lock here as this is a sync context
            with _metrics_sync_lock:
                metrics = _metrics[func.__qualname__]
                metrics.record(elapsed_ms)
            logger.debug("⏱️ %s completed in %.2fms", func.__qualname__, elapsed_ms)

    return wrapper  # type: ignore[return-value]


async def get_metrics_summary() -> dict[str, dict[str, Any]]:
    """Returns a summary of collected metrics.

    Returns:
        Dict with metrics per function: calls, avg_ms, min_ms, max_ms
    """
    async with _get_metrics_lock():
        with _metrics_sync_lock:
            # Create a copy to avoid concurrency issues during iteration
            metrics_copy = dict(_metrics)

    return {
        name: {
            "calls": m.call_count,
            "avg_ms": round(m.avg_time_ms, 2),
            "min_ms": round(m.min_time_ms, 2) if m.min_time_ms != float("inf") else 0,
            "max_ms": round(m.max_time_ms, 2),
            "total_ms": round(m.total_time_ms, 2),
        }
        for name, m in metrics_copy.items()
    }


async def reset_metrics() -> None:
    """Resets all collected metrics."""
    async with _get_metrics_lock():
        with _metrics_sync_lock:
            _metrics.clear()


async def log_metrics_summary() -> None:
    """Logs a summary of collected metrics."""
    summary = await get_metrics_summary()
    if not summary:
        logger.info("📊 No performance metrics collected yet.")
        return

    logger.info("📊 Performance Metrics Summary:")
    for name, data in sorted(summary.items(), key=lambda x: x[1]["total_ms"], reverse=True):
        logger.info(
            "   %s: %d calls, avg=%.2fms, min=%.2fms, max=%.2fms",
            name,
            data["calls"],
            data["avg_ms"],
            data["min_ms"],
            data["max_ms"],
        )
