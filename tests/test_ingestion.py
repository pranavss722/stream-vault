"""Tests for app.ingestion — Kafka message parsing."""

import json

import pytest

from app.store import FeatureRecord
from app.ingestion import parse_message


def _make_payload(**overrides) -> bytes:
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
    return json.dumps(defaults).encode()


class TestParseMessageValid:
    def test_returns_feature_record(self):
        record = parse_message(_make_payload())
        assert isinstance(record, FeatureRecord)
        assert record.user_id == "user_123"
        assert record.timestamp == 1700000000000
        assert record.watch_time_30d == 120.5
        assert record.click_rate_7d == 0.045
        assert record.session_count_14d == 18.0
        assert record.genre_affinity_score == 0.87
        assert record.recency_score == 0.93


class TestParseMessageMissingFields:
    @pytest.mark.parametrize(
        "field",
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
    def test_raises_on_missing_field(self, field):
        payload = json.loads(_make_payload())
        del payload[field]
        raw = json.dumps(payload).encode()
        with pytest.raises(ValueError, match=field):
            parse_message(raw)


class TestParseMessageUserId:
    def test_raises_on_empty_user_id(self):
        raw = _make_payload(user_id="")
        with pytest.raises(ValueError, match="user_id"):
            parse_message(raw)

    def test_raises_on_missing_user_id(self):
        payload = json.loads(_make_payload())
        del payload["user_id"]
        raw = json.dumps(payload).encode()
        with pytest.raises(ValueError, match="user_id"):
            parse_message(raw)


class TestParseMessageInvalidJson:
    def test_raises_on_garbage_bytes(self):
        with pytest.raises(ValueError, match="[Jj][Ss][Oo][Nn]"):
            parse_message(b"not json at all")

    def test_raises_on_truncated_json(self):
        with pytest.raises(ValueError, match="[Jj][Ss][Oo][Nn]"):
            parse_message(b'{"user_id": "abc",')


class TestParseMessageNumericCasting:
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
    def test_raises_on_non_castable_numeric(self, field):
        raw = _make_payload(**{field: "not_a_number"})
        with pytest.raises(ValueError, match=field):
            parse_message(raw)

    def test_string_numeric_is_cast_to_float(self):
        record = parse_message(_make_payload(watch_time_30d="42.5"))
        assert record.watch_time_30d == 42.5
