"""Tests for app.store — dual-write interface (Delta Lake + Redis)."""

from unittest.mock import MagicMock, patch

import pytest

from app.store import FeatureRecord, write_features


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


class TestWriteFeaturesDualWrite:
    """write_features() must write to BOTH Delta Lake and Redis."""

    def test_calls_both_delta_and_redis(self):
        record = _make_record()
        delta_client = MagicMock()
        redis_client = MagicMock()

        write_features(record, delta_client, redis_client)

        delta_client.write.assert_called_once()
        redis_client.hset.assert_called_once()

    def test_raises_when_delta_fails(self):
        record = _make_record()
        delta_client = MagicMock()
        delta_client.write.side_effect = RuntimeError("delta down")
        redis_client = MagicMock()

        with pytest.raises(RuntimeError, match="delta down"):
            write_features(record, delta_client, redis_client)

        redis_client.hset.assert_not_called()

    def test_raises_when_redis_fails(self):
        record = _make_record()
        delta_client = MagicMock()
        redis_client = MagicMock()
        redis_client.hset.side_effect = RuntimeError("redis down")

        with pytest.raises(RuntimeError, match="redis down"):
            write_features(record, delta_client, redis_client)

        delta_client.write.assert_called_once()


class TestWriteFeaturesValidation:
    """write_features() must reject invalid records."""

    def test_raises_on_empty_user_id(self):
        record = _make_record(user_id="")
        delta_client = MagicMock()
        redis_client = MagicMock()

        with pytest.raises(ValueError, match="user_id"):
            write_features(record, delta_client, redis_client)

    @pytest.mark.parametrize(
        "missing_field",
        [
            "user_id",
            "timestamp",
            "watch_time_30d",
            "click_rate_7d",
            "session_count_14d",
            "genre_affinity_score",
            "recency_score",
        ],
    )
    def test_raises_on_none_required_field(self, missing_field):
        record = _make_record(**{missing_field: None})
        delta_client = MagicMock()
        redis_client = MagicMock()

        with pytest.raises(ValueError, match=missing_field):
            write_features(record, delta_client, redis_client)


class TestRedisKeyFormat:
    """Redis key must be 'features:{user_id}'."""

    def test_redis_key_format(self):
        record = _make_record(user_id="user_abc")
        delta_client = MagicMock()
        redis_client = MagicMock()

        write_features(record, delta_client, redis_client)

        call_args = redis_client.hset.call_args
        assert call_args[0][0] == "features:user_abc"


class TestDeltaLakeWrite:
    """Delta Lake write must include all 7 fields."""

    def test_delta_write_contains_all_fields(self):
        record = _make_record()
        delta_client = MagicMock()
        redis_client = MagicMock()

        write_features(record, delta_client, redis_client)

        call_args = delta_client.write.call_args
        written_data = call_args[0][0]  # first positional arg: the DataFrame
        expected_columns = {
            "user_id",
            "timestamp",
            "watch_time_30d",
            "click_rate_7d",
            "session_count_14d",
            "genre_affinity_score",
            "recency_score",
        }
        assert set(written_data.columns) == expected_columns
