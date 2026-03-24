"""Feature validation module — schema and data-quality checks on incoming features."""

from __future__ import annotations

import math

from app.store import FEATURE_FIELDS, FeatureRecord


def validate_record(record: FeatureRecord) -> None:
    """Validate a FeatureRecord. Raises ValueError on any violation."""
    if not isinstance(record.timestamp, int) or record.timestamp <= 0:
        raise ValueError("timestamp must be a positive integer")

    for field in FEATURE_FIELDS:
        value = getattr(record, field)

        if math.isnan(value):
            raise ValueError(f"{field} must not be NaN")

        if value < 0:
            raise ValueError(f"{field} must not be negative")

    if record.watch_time_30d > 1_000_000:
        raise ValueError("watch_time_30d must not exceed 1,000,000")

    if record.click_rate_7d > 1.0:
        raise ValueError("click_rate_7d must not exceed 1.0")
