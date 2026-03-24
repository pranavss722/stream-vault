"""Tests for app.main — FastAPI health and ingest endpoints."""

import json
from unittest.mock import MagicMock, patch

import pytest
import httpx

from app.main import app


@pytest.fixture
def valid_payload() -> dict:
    return {
        "user_id": "user_123",
        "timestamp": 1700000000000,
        "watch_time_30d": 120.5,
        "click_rate_7d": 0.045,
        "session_count_14d": 18.0,
        "genre_affinity_score": 0.87,
        "recency_score": 0.93,
    }


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealthEndpoint:
    @pytest.mark.anyio
    async def test_health_returns_200(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    @pytest.mark.anyio
    async def test_health_content_type_is_json(self, client):
        resp = await client.get("/health")
        assert resp.headers["content-type"] == "application/json"


class TestIngestEndpoint:
    @pytest.mark.anyio
    @patch("app.main.materialize")
    async def test_valid_payload_returns_202(self, mock_materialize, client, valid_payload):
        resp = await client.post("/ingest", json=valid_payload)
        assert resp.status_code == 202
        mock_materialize.assert_called_once()

    @pytest.mark.anyio
    async def test_malformed_json_returns_422(self, client):
        resp = await client.post(
            "/ingest",
            content=b"not json at all",
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_missing_required_field_returns_422(self, client, valid_payload):
        del valid_payload["user_id"]
        resp = await client.post("/ingest", json=valid_payload)
        assert resp.status_code == 422
