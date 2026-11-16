"""Structured logging setup using :mod:`structlog`.

Configures a processor chain that produces JSON or human-readable console
output, integrates with Python's standard :mod:`logging` module so that
third-party libraries also emit structured output, and supports optional
key-value redaction and file-based log sinks.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from typing import Any

import structlog

__all__ = [
    "RedactProcessor",
    "configure_logging",
    "get_logger",
]

# Sentinel to detect re-configuration
_CONFIGURED = False

# Default keys whose values should be redacted when the redaction processor
# is active (e.g. API keys, tokens, passwords).
_DEFAULT_REDACT_KEYS: frozenset[str] = frozenset(
    {
        "api_key",
        "api_secret",
        "password",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
    }
)


class RedactProcessor:
    """A structlog processor that replaces sensitive values with ``[REDACTED]``.

    Any event-dict key whose lowered name appears in *redact_keys* will
    have its value replaced.  Key matching is case-insensitive.

    Args:
        redact_keys: Iterable of key names to redact.  Merged with a
            small built-in set of common secret-field names.
    """

    REPLACEMENT: str = "[REDACTED]"

    def __init__(self, redact_keys: list[str] | None = None) -> None:
        extra = frozenset(k.lower() for k in redact_keys) if redact_keys else frozenset()
        self._keys: frozenset[str] = _DEFAULT_REDACT_KEYS | extra

    def __call__(
        self,
        _logger: Any,
        _method_name: str,
        event_dict: dict[str, Any],
    ) -> dict[str, Any]:
        """Process an event dict, replacing redacted keys' values."""
        for key in list(event_dict.keys()):
            if key.lower() in self._keys:
                event_dict[key] = self.REPLACEMENT
        return event_dict


def configure_logging(
    log_level: str = "INFO",
    json_output: bool = True,
    log_file: str | None = None,
    redact_keys: list[str] | None = None,
) -> None:
    """Set up :mod:`structlog` and the standard-library root logger.

    This function is idempotent—calling it more than once reconfigures
    the logging stack.

    Args:
        log_level: Minimum log level (e.g. ``"DEBUG"``, ``"INFO"``).
        json_output: If ``True`` (default) events are rendered as JSON
            objects.  If ``False`` a coloured console renderer is used.
        log_file: Optional path to a log file.  When provided an
            additional :class:`~logging.handlers.RotatingFileHandler` is
            attached (max 10 MB, 5 backups).
        redact_keys: Extra key names whose values should be replaced
            with ``[REDACTED]`` in log output.
    """
    global _CONFIGURED  # noqa: PLW0603

    level = getattr(logging, log_level.upper(), logging.INFO)

    # ── Standard-library root logger ──────────────────────────────────
    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers to allow reconfiguration
    root.handlers.clear()

    # Console handler (always present)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    root.addHandler(console_handler)

    # Optional rotating file handler
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        root.addHandler(file_handler)

    # ── Shared processor chain ────────────────────────────────────────
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        RedactProcessor(redact_keys=redact_keys),
    ]

    # ── Renderer ──────────────────────────────────────────────────────
    if json_output:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()  # type: ignore[assignment]

    # ── structlog configuration ───────────────────────────────────────
    structlog.configure(
        processors=[
            *shared_processors,
            # Prepare for stdlib integration
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # ── Formatter for stdlib handlers ─────────────────────────────────
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    for handler in root.handlers:
        handler.setFormatter(formatter)

    _CONFIGURED = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a :class:`~structlog.stdlib.BoundLogger` bound with *name*.

    If :func:`configure_logging` has not been called yet, a default
    configuration (``INFO`` level, JSON output) is applied automatically
    so that callers always get a usable logger.

    Args:
        name: Logger name, typically ``__name__`` of the calling module.

    Returns:
        A bound structlog logger.
    """
    if not _CONFIGURED:
        configure_logging()

    return structlog.get_logger(name)
