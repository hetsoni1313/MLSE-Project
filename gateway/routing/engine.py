"""Intelligent routing engine with weighted, sticky, shadow, and canary modes.

The routing engine determines which backend (baseline or local) should
handle each incoming request based on the current routing configuration.
"""

from __future__ import annotations

import hashlib
import random
import threading
from enum import Enum

from gateway.routing.config import RoutingConfig
from llmops_governance.logging.setup import get_logger

logger = get_logger(__name__)


class Route(str, Enum):
    """Available routes for request handling."""

    BASELINE = "baseline"
    LOCAL = "local"
    SHADOW = "shadow"


class RoutingEngine:
    """Thread-safe routing engine supporting multiple routing strategies.

    Strategies:
        - baseline: All traffic to commercial API
        - weighted: Split traffic by percentage (with optional sticky hashing)
        - shadow: Client gets baseline, local runs in parallel for logging
        - canary: Gradual rollout using canary stages
    """

    def __init__(self, config: RoutingConfig | None = None) -> None:
        self._lock = threading.RLock()
        self._config = config or RoutingConfig()
        self._rolled_back = False

    @property
    def config(self) -> RoutingConfig:
        with self._lock:
            return self._config.model_copy()

    @property
    def is_rolled_back(self) -> bool:
        with self._lock:
            return self._rolled_back

    def update_config(self, new_config: RoutingConfig) -> RoutingConfig:
        """Atomically update the routing configuration.

        Args:
            new_config: New validated routing configuration.

        Returns:
            The previous configuration.
        """
        with self._lock:
            old = self._config
            self._config = new_config
            logger.info(
                "routing_config_updated",
                old_mode=old.mode,
                new_mode=new_config.mode,
                baseline_pct=new_config.baseline_percentage,
                local_pct=new_config.local_percentage,
            )
            return old

    def determine_route(
        self,
        user_id: str | None = None,
        request_id: str | None = None,
    ) -> Route:
        """Determine the route for a request.

        Args:
            user_id: Optional user ID for sticky routing.
            request_id: Optional request ID as fallback for hashing.

        Returns:
            The route decision (BASELINE, LOCAL, or SHADOW).
        """
        with self._lock:
            config = self._config

        # Shadow mode: always return SHADOW (baseline + silent local)
        if config.mode == "shadow" or config.shadow_enabled:
            return Route.SHADOW

        # Baseline only
        if config.mode == "baseline" or config.local_percentage == 0:
            return Route.BASELINE

        # Full local
        if config.baseline_percentage == 0:
            return Route.LOCAL

        # Weighted or canary with sticky routing
        if config.sticky_enabled and (user_id or request_id):
            return self._sticky_route(user_id or request_id or "", config)

        # Random weighted routing
        return self._weighted_route(config)

    def _sticky_route(self, key: str, config: RoutingConfig) -> Route:
        """Deterministic routing based on hash of user/request ID.

        Uses consistent hashing so the same key always maps to the same
        route under unchanged percentages.
        """
        hash_value = int(hashlib.sha256(key.encode()).hexdigest(), 16)
        bucket = hash_value % 100

        if bucket < config.local_percentage:
            return Route.LOCAL
        return Route.BASELINE

    def _weighted_route(self, config: RoutingConfig) -> Route:
        """Random weighted routing based on configured percentages."""
        if random.randint(0, 99) < config.local_percentage:  # noqa: S311
            return Route.LOCAL
        return Route.BASELINE

    def trigger_rollback(self) -> None:
        """Set routing to 100% baseline (automatic rollback)."""
        with self._lock:
            old = self._config
            self._config = RoutingConfig(
                mode="baseline",
                baseline_percentage=100,
                local_percentage=0,
                sticky_enabled=old.sticky_enabled,
                shadow_enabled=False,
            )
            self._rolled_back = True
            logger.warning(
                "routing_rollback_triggered",
                previous_mode=old.mode,
                previous_local_pct=old.local_percentage,
            )

    def recover_from_rollback(self, config: RoutingConfig) -> None:
        """Explicitly recover from a rollback state (admin action)."""
        with self._lock:
            self._config = config
            self._rolled_back = False
            logger.info(
                "routing_rollback_recovered",
                new_mode=config.mode,
                local_pct=config.local_percentage,
            )

    def advance_canary(self) -> int:
        """Advance to the next canary stage.

        Returns:
            The new local percentage.
        """
        with self._lock:
            config = self._config
            stages = config.canary_stages
            current = config.current_canary_stage

            if current >= len(stages) - 1:
                logger.info("canary_at_final_stage", stage=current)
                return config.local_percentage

            next_stage = current + 1
            local_pct = stages[next_stage]
            self._config = RoutingConfig(
                mode="canary",
                baseline_percentage=100 - local_pct,
                local_percentage=local_pct,
                sticky_enabled=config.sticky_enabled,
                canary_stages=stages,
                current_canary_stage=next_stage,
            )
            logger.info(
                "canary_advanced",
                stage=next_stage,
                local_pct=local_pct,
            )
            return local_pct

