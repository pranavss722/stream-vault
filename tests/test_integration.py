"""Integration tests — require the live Docker stack."""

from __future__ import annotations

import pytest
import httpx

from scripts.parity_check import check_parity

VALID_PAYLOAD = {
    "user_id": "user_integ_01",
    "timestamp": 1700000000000,
    "watch_time_30d": 120.5,
    "click_rate_7d": 0.045,
    "session_count_14d": 18.0,
    "genre_affinity_score": 0.87,
    "recency_score": 0.93,
}

FEATURE_FIELDS = (
    "watch_time_30d",
    "click_rate_7d",
    "session_count_14d",
    "genre_affinity_score",
    "recency_score",
)

pytestmark = pytest.mark.integration


@pytest.mark.anyio
async def test_health_returns_ok(docker_stack, api_base_url):
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_ingest_returns_202(docker_stack, api_base_url):
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        resp = await client.post("/ingest", json=VALID_PAYLOAD)
    assert resp.status_code == 202


@pytest.mark.anyio
async def test_redis_has_correct_values_after_ingest(docker_stack, api_base_url, redis_client):
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        resp = await client.post("/ingest", json=VALID_PAYLOAD)
    assert resp.status_code == 202

    key = f"features:{VALID_PAYLOAD['user_id']}"
    assert redis_client.exists(key), f"Redis key {key} not found"

    stored = redis_client.hgetall(key)
    for field in FEATURE_FIELDS:
        expected = VALID_PAYLOAD[field]
        actual = float(stored[field])
        assert abs(actual - expected) <= 0.001, (
            f"{field}: expected {expected}, got {actual}"
        )


@pytest.mark.anyio
async def test_parity_reports_no_drift_after_ingest(docker_stack, api_base_url, redis_client):
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        resp = await client.post("/ingest", json=VALID_PAYLOAD)
    assert resp.status_code == 202

    uid = VALID_PAYLOAD["user_id"]
    offline = {
        uid: {f: VALID_PAYLOAD[f] for f in FEATURE_FIELDS},
    }

    stored = redis_client.hgetall(f"features:{uid}")
    online = {
        uid: {f: float(stored[f]) for f in FEATURE_FIELDS},
    }

    report = check_parity(offline, online)
    assert report.drift is False
    assert report.violations == []
