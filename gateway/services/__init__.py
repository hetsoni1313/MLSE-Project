"""Non-blocking request logging service."""

from __future__ import annotations

import asyncio
from typing import Any

from llmops_governance.logging.setup import get_logger
from llmops_governance.metrics.database import DatabaseManager
from llmops_governance.metrics.repository import RequestLogRepository

logger = get_logger(__name__)


class RequestLogger:
    """Async, non-blocking request logger that persists to the database.

    Uses fire-and-forget asyncio tasks to avoid blocking the response path.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        self._db = db_manager
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=10000)
        self._task: asyncio.Task | None = None  # type: ignore[type-arg]
        self._running = False

    async def start(self) -> None:
        """Start the background log writer."""
        self._running = True
        self._task = asyncio.create_task(self._writer_loop())
        logger.info("request_logger_started")

    async def stop(self) -> None:
        """Stop the background log writer, flushing remaining items."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        # Flush remaining
        await self._flush_queue()

    def log_request(self, data: dict[str, Any]) -> None:
        """Enqueue a request log entry (non-blocking)."""
        try:
            self._queue.put_nowait(data)
        except asyncio.QueueFull:
            logger.warning("request_log_queue_full", dropped_request_id=data.get("request_id"))

    async def log_request_sync(self, data: dict[str, Any]) -> None:
        """Directly persist a request log entry (blocking)."""
        try:
            async with self._db.get_session() as session:
                repo = RequestLogRepository(session)
                await repo.save(data)
        except Exception as e:
            logger.error("request_log_failed", error=str(e))

    async def _writer_loop(self) -> None:
        """Background loop that writes queued log entries to DB."""
        while self._running:
            try:
                data = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self.log_request_sync(data)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("request_logger_error", error=str(e))

    async def flush(self) -> None:
        """Flush all pending items in the queue to DB."""
        await self._flush_queue()

    async def _flush_queue(self) -> None:
        """Flush all remaining items in the queue."""
        while not self._queue.empty():
            try:
                data = self._queue.get_nowait()
                await self.log_request_sync(data)
            except Exception:
                break

