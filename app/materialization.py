"""Feature materialization module — orchestrates validation then dual-write."""

from __future__ import annotations

from app.store import FeatureRecord, write_features
from app.validation import validate_record


def materialize(record: FeatureRecord, delta_client, redis_client) -> None:
    """Validate a feature record, then dual-write to offline and online stores.

    Calls validate_record first. If validation passes, calls write_features.
    Exceptions from either step propagate to the caller.
    """
    validate_record(record)
    write_features(record, delta_client, redis_client)
