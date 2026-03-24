"""Tests for app.materialization — orchestrates validation then dual-write."""

from unittest.mock import MagicMock, call, patch

import pytest

from app.store import FeatureRecord
from app.materialization import materialize


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


@patch("app.materialization.write_features")
@patch("app.materialization.validate_record")
class TestMaterializeCallOrder:
    """materialize() must call validate_record then write_features, in that order."""

    def test_calls_validate_then_write(self, mock_validate, mock_write):
        record = _make_record()
        delta = MagicMock()
        redis = MagicMock()

        materialize(record, delta, redis)

        mock_validate.assert_called_once_with(record)
        mock_write.assert_called_once_with(record, delta, redis)

        # Verify ordering: validate was called before write
        manager = MagicMock()
        manager.attach_mock(mock_validate, "validate")
        manager.attach_mock(mock_write, "write")
        # Re-run to check ordering via a single mock manager
        mock_validate.reset_mock()
        mock_write.reset_mock()
        materialize(record, delta, redis)
        assert manager.mock_calls == [
            call.validate(record),
            call.write(record, delta, redis),
        ]


@patch("app.materialization.write_features")
@patch("app.materialization.validate_record")
class TestMaterializeValidationFailure:
    """If validate_record raises, materialize must propagate and not call write."""

    def test_raises_on_validation_error(self, mock_validate, mock_write):
        mock_validate.side_effect = ValueError("bad timestamp")
        record = _make_record()
        delta = MagicMock()
        redis = MagicMock()

        with pytest.raises(ValueError, match="bad timestamp"):
            materialize(record, delta, redis)

        mock_write.assert_not_called()


@patch("app.materialization.write_features")
@patch("app.materialization.validate_record")
class TestMaterializeWriteFailure:
    """If write_features raises, materialize must propagate the exception."""

    def test_raises_on_write_error(self, mock_validate, mock_write):
        mock_write.side_effect = RuntimeError("redis down")
        record = _make_record()
        delta = MagicMock()
        redis = MagicMock()

        with pytest.raises(RuntimeError, match="redis down"):
            materialize(record, delta, redis)


@patch("app.materialization.write_features")
@patch("app.materialization.validate_record")
class TestMaterializePassesCorrectRecord:
    """materialize() must forward the exact FeatureRecord it received."""

    def test_passes_same_record_to_both(self, mock_validate, mock_write):
        record = _make_record(user_id="user_xyz")
        delta = MagicMock()
        redis = MagicMock()

        materialize(record, delta, redis)

        passed_to_validate = mock_validate.call_args[0][0]
        passed_to_write = mock_write.call_args[0][0]
        assert passed_to_validate is record
        assert passed_to_write is record
