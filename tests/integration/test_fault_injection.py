"""Integration tests for fault injection, fallback, and automatic rollback."""

from __future__ import annotations

import os
import pathlib
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from gateway.backends import ModelBackend, PredictionResult
from gateway.backends.fault_injection import FaultInjectionBackend
from gateway.main import create_app


def _make_dummy_backend(name: str = "mock-local", prediction: str = "change_pin") -> AsyncMock:
    backend = AsyncMock(spec=ModelBackend)
    backend.name = name
    backend.predict.return_value = PredictionResult(
        prediction=prediction,
        latency_ms=45.0,
        model_name=name,
        valid_output=True,
        input_tokens=15,
        output_tokens=5,
    )
    backend.health_check.return_value = True
    return backend


class TestFaultInjectionBackendUnit:
    """Unit tests for the FaultInjectionBackend wrapper."""

    @pytest.mark.asyncio
    async def test_unavailable_fault(self, monkeypatch):
        monkeypatch.setenv("FAULT_INJECTION_ENABLED", "true")
        wrapped = _make_dummy_backend()
        fault_backend = FaultInjectionBackend(wrapped)
        fault_backend.set_fault("unavailable", True)

        result = await fault_backend.predict("I need help")
        assert result.error == "[FAULT INJECTION] Server unavailable"
        assert not result.valid_output
        assert not await fault_backend.health_check()

    @pytest.mark.asyncio
    async def test_invalid_output_fault(self, monkeypatch):
        monkeypatch.setenv("FAULT_INJECTION_ENABLED", "true")
        wrapped = _make_dummy_backend()
        fault_backend = FaultInjectionBackend(wrapped)
        fault_backend.set_fault("invalid_output", True, invalid_output_rate=1.0)

        result = await fault_backend.predict("I need help")
        assert result.prediction == "INVALID_INJECTED_LABEL"
        assert not result.valid_output
        assert result.metadata.get("fault_injected") == "invalid_output"

    @pytest.mark.asyncio
    async def test_degraded_accuracy_fault(self, monkeypatch):
        monkeypatch.setenv("FAULT_INJECTION_ENABLED", "true")
        wrapped = _make_dummy_backend(prediction="change_pin")
        fault_backend = FaultInjectionBackend(wrapped)
        fault_backend.set_fault("degraded_accuracy", True, degraded_accuracy_rate=1.0)

        result = await fault_backend.predict("I want to change my PIN")
        # Should be a Banking77 label other than change_pin
        assert result.prediction != "change_pin"
        assert result.valid_output is True
        assert result.metadata.get("fault_injected") == "degraded_accuracy"

    @pytest.mark.asyncio
    async def test_error_rate_fault(self, monkeypatch):
        monkeypatch.setenv("FAULT_INJECTION_ENABLED", "true")
        wrapped = _make_dummy_backend()
        fault_backend = FaultInjectionBackend(wrapped)
        fault_backend.set_fault("error_rate", True, error_rate_pct=1.0)

        result = await fault_backend.predict("Test")
        assert result.error == "[FAULT INJECTION] Random error"
        assert not result.valid_output

    @pytest.mark.asyncio
    async def test_disabled_does_not_modify_behavior(self, monkeypatch):
        monkeypatch.setenv("FAULT_INJECTION_ENABLED", "true")
        wrapped = _make_dummy_backend(prediction="change_pin")
        fault_backend = FaultInjectionBackend(wrapped)
        fault_backend.set_fault("unavailable", True)
        fault_backend.disable()

        result = await fault_backend.predict("Test")
        assert result.prediction == "change_pin"
        assert result.error is None


@pytest.fixture
def fault_gateway_client():
    """Create a gateway test client with fault injection enabled."""
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./data/test_fault_llmops.db"
    os.environ["ADMIN_API_KEY"] = "admin-secret-test"
    os.environ["FAULT_INJECTION_ENABLED"] = "true"

    app = create_app()
    with TestClient(app) as client:
        yield client

    test_db = pathlib.Path("./data/test_fault_llmops.db")
    if test_db.exists():
        test_db.unlink()


class TestFaultGatewayIntegration:
    """Integration tests for gateway admin controls and fault tolerance."""

    def test_fault_endpoints_authorization(self, fault_gateway_client):
        # Missing key
        res = fault_gateway_client.post("/admin/faults", json={"action": "enable"})
        assert res.status_code == 401

        # Invalid key
        res = fault_gateway_client.post(
            "/admin/faults",
            headers={"X-API-Key": "wrong-key"},
            json={"action": "enable"},
        )
        assert res.status_code == 403

        # Valid key
        res = fault_gateway_client.post(
            "/admin/faults",
            headers={"X-API-Key": "admin-secret-test"},
            json={"action": "enable"},
        )
        assert res.status_code == 200
        assert res.json().get("status") == "enabled"

    def test_local_server_unavailable_triggers_fallback(self, fault_gateway_client):
        """When local server has unavailable fault, classify falls back to baseline."""
        # 1. Route 100% to local
        res = fault_gateway_client.put(
            "/admin/config",
            headers={"X-API-Key": "admin-secret-test"},
            json={
                "routing_mode": "weighted",
                "baseline_percentage": 0,
                "local_percentage": 100,
                "reason": "Test full local",
            },
        )
        assert res.status_code == 200

        # 2. Inject unavailable fault into local backend
        res = fault_gateway_client.post(
            "/admin/faults",
            headers={"X-API-Key": "admin-secret-test"},
            json={"action": "set", "fault_type": "unavailable", "enabled": True},
        )
        assert res.status_code == 200

        # 3. Send classify request
        res = fault_gateway_client.post(
            "/classify",
            json={"message": "I lost my physical card yesterday"},
        )
        assert res.status_code == 200
        data = res.json()
        # Fallback to baseline should have kicked in
        assert data["fallback_used"] is True
        assert data["route"] == "baseline"
        assert "[FAULT INJECTION] Server unavailable" in (data["fallback_reason"] or "")

    def test_manual_rollback_trigger_and_recovery(self, fault_gateway_client):
        """Test check-rollback and reset-rollback endpoints."""
        # Trigger immediate rollback evaluation
        res = fault_gateway_client.post(
            "/admin/check-rollback",
            headers={"X-API-Key": "admin-secret-test"},
        )
        assert res.status_code == 200
        assert "result" in res.json()

        # Reset rollback endpoint test
        res = fault_gateway_client.post(
            "/admin/reset-rollback",
            headers={"X-API-Key": "admin-secret-test"},
            json={"routing_mode": "weighted", "baseline_percentage": 80, "local_percentage": 20},
        )
        assert res.status_code == 200

        # Rollback history endpoint
        res = fault_gateway_client.get(
            "/admin/rollback-history",
            headers={"X-API-Key": "admin-secret-test"},
        )
        assert res.status_code == 200
        assert "rollback_events" in res.json()
