"""Feature ingestion module — parses raw feature event payloads."""

from __future__ import annotations

import json

from app.store import ALL_FIELDS, FEATURE_FIELDS, FeatureRecord


def parse_message(raw: bytes) -> FeatureRecord:
    """Parse a JSON bytes payload into a FeatureRecord.

    Raises ValueError for any malformed input: bad JSON, missing fields,
    empty user_id, or non-castable numerics.
    """
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc

    for field in ALL_FIELDS:
        if field not in data:
            raise ValueError(f"missing required field: {field}")

    user_id = data["user_id"]
    if not user_id:
        raise ValueError("user_id must not be empty")

    try:
        timestamp = int(data["timestamp"])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"timestamp must be castable to int: {exc}") from exc

    numeric_values = {}
    for field in FEATURE_FIELDS:
        try:
            numeric_values[field] = float(data[field])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} must be castable to float: {exc}") from exc

    return FeatureRecord(
        user_id=str(user_id),
        timestamp=timestamp,
        **numeric_values,
    )
