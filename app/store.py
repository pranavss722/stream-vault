"""Feature store module — dual-write interface for Delta Lake (offline) and Redis (online)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

FEATURE_FIELDS = (
    "watch_time_30d",
    "click_rate_7d",
    "session_count_14d",
    "genre_affinity_score",
    "recency_score",
)

ALL_FIELDS = ("user_id", "timestamp", *FEATURE_FIELDS)


@dataclass
class FeatureRecord:
    user_id: str
    timestamp: int
    watch_time_30d: float
    click_rate_7d: float
    session_count_14d: float
    genre_affinity_score: float
    recency_score: float


def _validate(record: FeatureRecord) -> None:
    for field in ALL_FIELDS:
        if getattr(record, field) is None:
            raise ValueError(f"{field} must not be None")
    if record.user_id == "":
        raise ValueError("user_id must not be empty")


def write_features(record: FeatureRecord, delta_client, redis_client) -> None:
    """Dual-write a feature record to Delta Lake (offline) and Redis (online).

    Writes to Delta first. If that succeeds, writes to Redis.
    If either write fails, the exception propagates — no silent partial writes.
    """
    _validate(record)

    df = pd.DataFrame([{field: getattr(record, field) for field in ALL_FIELDS}])
    delta_client.write(df)

    redis_client.hset(
        f"features:{record.user_id}",
        mapping={field: str(getattr(record, field)) for field in FEATURE_FIELDS},
    )
