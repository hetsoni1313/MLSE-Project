"""Integration tests for the FastAPI gateway."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client with mock backends."""
    import os
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./data/test_llmops.db"
    os.environ["ADMIN_API_KEY"] = "test-key"
    os.environ["FAULT_INJECTION_ENABLED"] = "true"

    from gateway.main import create_app
    app = create_app()
    with TestClient(app) as c:
        yield c

    # Cleanup
    import pathlib
    test_db = pathlib.Path("./data/test_llmops.db")
    if test_db.exists():
        test_db.unlink()


class TestHealthEndpoints:
    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["gateway"] is True

    def test_ready(self, client):
        response = client.get("/ready")
        assert response.status_code == 200


class TestClassifyEndpoint:
    def test_classify_basic(self, client):
        response = client.post("/classify", json={
            "message": "I want to change my PIN number"
        })
        assert response.status_code == 200
        data = response.json()
        assert "prediction" in data
        assert "route" in data
        assert "latency_ms" in data

    def test_classify_with_ground_truth(self, client):
        response = client.post("/classify", json={
            "message": "How do I change my PIN?",
            "ground_truth": "change_pin",
        })
        assert response.status_code == 200

    def test_classify_empty_message_rejected(self, client):
        response = client.post("/classify", json={"message": ""})
        assert response.status_code == 422  # Validation error


class TestAdminEndpoints:
    def test_get_config_without_key(self, client):
        response = client.get("/admin/config")
        assert response.status_code == 401

    def test_get_config_with_key(self, client):
        response = client.get("/admin/config", headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        data = response.json()
        assert "routing" in data

    def test_update_config(self, client):
        response = client.put(
            "/admin/config",
            headers={"X-API-Key": "test-key"},
            json={"routing_mode": "shadow", "shadow_enabled": True, "reason": "test"},
        )
        assert response.status_code == 200


class TestMetricsEndpoint:
    def test_metrics(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data

