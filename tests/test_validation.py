"""Tests for app.validation — feature record data-quality checks."""

import math

import pytest

from app.store import FeatureRecord
from app.validation import validate_record


def _make_record(**overrides) -> FeatureRecord:
    defaults = {
        "user_id": "user_123",
        "timestamp": 1700000000000,
        "watch_time_30d": 120.5,
        "click_rate_7d": 0.045,
        "session_count_14d": 18.0,
        "genre_affinity_score": 0.87,
        "recency_score": 0.93,
    }
    defaults.update(overrides)
    return FeatureRecord(**defaults)


class TestValidRecordPassesSilently:
    def test_valid_record(self):
        record = _make_record()
        validate_record(record)  # should not raise


class TestNegativeFeatures:
    @pytest.mark.parametrize(
        "field",
        [
            "watch_time_30d",
            "click_rate_7d",
            "session_count_14d",
            "genre_affinity_score",
            "recency_score",
        ],
    )
    def test_raises_on_negative_feature(self, field):
        record = _make_record(**{field: -1.0})
        with pytest.raises(ValueError, match=field):
            validate_record(record)


class TestTimestampValidation:
    def test_raises_on_zero_timestamp(self):
        record = _make_record(timestamp=0)
        with pytest.raises(ValueError, match="timestamp"):
            validate_record(record)

    def test_raises_on_negative_timestamp(self):
        record = _make_record(timestamp=-100)
        with pytest.raises(ValueError, match="timestamp"):
            validate_record(record)


class TestSanityCeilings:
    def test_raises_when_watch_time_exceeds_ceiling(self):
        record = _make_record(watch_time_30d=1_000_001.0)
        with pytest.raises(ValueError, match="watch_time_30d"):
            validate_record(record)

    def test_raises_when_click_rate_exceeds_one(self):
        record = _make_record(click_rate_7d=1.01)
        with pytest.raises(ValueError, match="click_rate_7d"):
            validate_record(record)


class TestNaNFeatures:
    @pytest.mark.parametrize(
        "field",
        [
            "watch_time_30d",
            "click_rate_7d",
            "session_count_14d",
            "genre_affinity_score",
            "recency_score",
        ],
    )
    def test_raises_on_nan_feature(self, field):
        record = _make_record(**{field: math.nan})
        with pytest.raises(ValueError, match=field):
            validate_record(record)
