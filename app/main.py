"""FastAPI application entrypoint for the Real-Time Feature Store."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, field_validator

from app.ingestion import parse_message
from app.materialization import materialize

app = FastAPI(title="Real-Time Feature Store")


class IngestPayload(BaseModel):
    user_id: str
    timestamp: int
    watch_time_30d: float
    click_rate_7d: float
    session_count_14d: float
    genre_affinity_score: float
    recency_score: float

    @field_validator("user_id")
    @classmethod
    def user_id_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("user_id must not be empty")
        return v


def _get_delta_client():
    """Lazy factory for the Delta Lake client, driven by env vars."""
    import os

    from app.delta_client import DeltaClient

    path = os.environ.get("DELTA_TABLE_PATH", "data/delta")
    return DeltaClient(path)


def _get_redis_client():
    """Lazy factory for the Redis client, driven by env vars."""
    import os

    import redis

    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return redis.Redis.from_url(url)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/ingest", status_code=202)
async def ingest(payload: IngestPayload):
    import json

    raw = json.dumps(payload.model_dump()).encode()
    record = parse_message(raw)
    delta_client = _get_delta_client()
    redis_client = _get_redis_client()
    materialize(record, delta_client, redis_client)
    return {"accepted": True}
