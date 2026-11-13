"""Timing utilities for latency measurement in sync and async contexts.

Provides context managers and decorators for measuring wall-clock execution
time with millisecond precision.
"""

from __future__ import annotations

import functools
import time
from types import TracebackType
from typing import Any, Callable, TypeVar

import structlog

__all__ = [
    "async_timer",
    "measure_latency",
    "sync_timer",
    "format_duration",
]

F = TypeVar("F", bound=Callable[..., Any])

logger = structlog.get_logger(__name__)


class async_timer:  # noqa: N801 – lowercase for context-manager convention
    """Async context manager that measures wall-clock time in milliseconds.

    Example::

        async with async_timer() as t:
            await some_coroutine()
        print(f"Took {t.elapsed_ms:.2f} ms")
    """

    __slots__ = ("_start", "_end")

    def __init__(self) -> None:
        self._start: float = 0.0
        self._end: float | None = None

    # -- async context manager protocol --

    async def __aenter__(self) -> "async_timer":
        self._start = time.perf_counter()
        self._end = None
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._end = time.perf_counter()

    # -- public API --

    @property
    def elapsed_ms(self) -> float:
        """Wall-clock elapsed time in milliseconds.

        If the context manager is still active the value reflects the
        time elapsed *so far*.
        """
        end = self._end if self._end is not None else time.perf_counter()
        return (end - self._start) * 1_000.0


class sync_timer:  # noqa: N801
    """Synchronous context manager that measures wall-clock time in milliseconds.

    Example::

        with sync_timer() as t:
            do_work()
        print(f"Took {t.elapsed_ms:.2f} ms")
    """

    __slots__ = ("_start", "_end")

    def __init__(self) -> None:
        self._start: float = 0.0
        self._end: float | None = None

    def __enter__(self) -> "sync_timer":
        self._start = time.perf_counter()
        self._end = None
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._end = time.perf_counter()

    @property
    def elapsed_ms(self) -> float:
        """Wall-clock elapsed time in milliseconds."""
        end = self._end if self._end is not None else time.perf_counter()
        return (end - self._start) * 1_000.0


def measure_latency(func: F) -> F:
    """Async decorator that logs function execution time in milliseconds.

    Uses :mod:`structlog` to emit an ``INFO``-level log entry containing
    the function name and elapsed milliseconds after every call.

    Args:
        func: An async callable to wrap.

    Returns:
        Wrapped async callable with latency logging.

    Example::

        @measure_latency
        async def fetch_data():
            ...
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception:
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1_000.0
            logger.info(
                "function_executed",
                function=func.__qualname__,
                elapsed_ms=round(elapsed_ms, 3),
            )

    return wrapper  # type: ignore[return-value]


def format_duration(ms: float) -> str:
    """Format milliseconds into a human-readable duration string.

    Rules:
    * < 1 000 ms  → ``"456ms"``
    * < 60 000 ms → ``"1.23s"``
    * ≥ 60 000 ms → ``"1m 23s"``

    Args:
        ms: Duration in milliseconds (must be ≥ 0).

    Returns:
        Human-readable duration string.

    Raises:
        ValueError: If *ms* is negative.
    """
    if ms < 0:
        raise ValueError(f"Duration must be non-negative, got {ms}")

    if ms < 1_000.0:
        return f"{ms:.0f}ms"

    seconds = ms / 1_000.0
    if seconds < 60.0:
        return f"{seconds:.2f}s"

    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    return f"{minutes}m {remaining_seconds}s"
