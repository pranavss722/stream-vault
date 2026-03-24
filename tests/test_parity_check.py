"""Tests for scripts.parity_check — offline/online parity validation."""

import pytest

from scripts.parity_check import ParityReport, check_parity


def _make_features(
    watch_time_30d=120.5,
    click_rate_7d=0.045,
    session_count_14d=18.0,
    genre_affinity_score=0.87,
    recency_score=0.93,
):
    return {
        "watch_time_30d": watch_time_30d,
        "click_rate_7d": click_rate_7d,
        "session_count_14d": session_count_14d,
        "genre_affinity_score": genre_affinity_score,
        "recency_score": recency_score,
    }


class TestParityMatchingData:
    def test_zero_violations_on_identical_data(self):
        offline = {"u1": _make_features(), "u2": _make_features()}
        online = {"u1": _make_features(), "u2": _make_features()}
        report = check_parity(offline, online)
        assert isinstance(report, ParityReport)
        assert report.total_entities == 2
        assert report.violations == []
        assert report.violation_rate == 0.0
        assert report.drift is False


class TestParityThresholdViolation:
    def test_flags_user_when_delta_exceeds_tolerance(self):
        offline = {"u1": _make_features(watch_time_30d=100.0)}
        online = {"u1": _make_features(watch_time_30d=100.002)}
        report = check_parity(offline, online)
        assert "u1" in report.violations

    def test_flags_on_any_single_feature_exceeding(self):
        offline = {"u1": _make_features(recency_score=0.5)}
        online = {"u1": _make_features(recency_score=0.503)}
        report = check_parity(offline, online)
        assert "u1" in report.violations


class TestParityWithinTolerance:
    def test_does_not_flag_when_all_deltas_within_tolerance(self):
        offline = {"u1": _make_features(click_rate_7d=0.5000)}
        online = {"u1": _make_features(click_rate_7d=0.5009)}
        report = check_parity(offline, online)
        assert report.violations == []

    def test_boundary_exactly_at_tolerance_is_not_flagged(self):
        offline = {"u1": _make_features(genre_affinity_score=1.0)}
        online = {"u1": _make_features(genre_affinity_score=1.001)}
        report = check_parity(offline, online)
        assert report.violations == []


class TestParityViolationRate:
    def test_violation_rate_zero_when_no_violations(self):
        offline = {"u1": _make_features(), "u2": _make_features()}
        online = {"u1": _make_features(), "u2": _make_features()}
        report = check_parity(offline, online)
        assert report.violation_rate == 0.0

    def test_violation_rate_computed_correctly(self):
        offline = {
            "u1": _make_features(watch_time_30d=100.0),
            "u2": _make_features(),
        }
        online = {
            "u1": _make_features(watch_time_30d=200.0),  # drifted
            "u2": _make_features(),
        }
        report = check_parity(offline, online)
        assert report.violation_rate == pytest.approx(0.5)


class TestParityDriftFlag:
    def test_drift_true_when_violation_rate_exceeds_threshold(self):
        # 2 out of 3 entities drifted → 66.7% > 0.1%
        offline = {
            "u1": _make_features(watch_time_30d=1.0),
            "u2": _make_features(watch_time_30d=1.0),
            "u3": _make_features(),
        }
        online = {
            "u1": _make_features(watch_time_30d=999.0),
            "u2": _make_features(watch_time_30d=999.0),
            "u3": _make_features(),
        }
        report = check_parity(offline, online)
        assert report.drift is True

    def test_drift_false_when_violation_rate_below_threshold(self):
        # Build 1000 matching + 1 drifted = 0.1% exactly → not > 0.1%, so False
        offline = {f"u{i}": _make_features() for i in range(1000)}
        online = {f"u{i}": _make_features() for i in range(1000)}
        offline["u_bad"] = _make_features(watch_time_30d=0.0)
        online["u_bad"] = _make_features(watch_time_30d=999.0)
        report = check_parity(offline, online)
        # 1 / 1001 ≈ 0.000999 < 0.001 → drift False
        assert report.drift is False


class TestParityEmptyInput:
    def test_empty_input_returns_clean_report(self):
        report = check_parity({}, {})
        assert report.total_entities == 0
        assert report.violations == []
        assert report.violation_rate == 0.0
        assert report.drift is False

    def test_disjoint_keys_count_as_zero_entities(self):
        offline = {"u1": _make_features()}
        online = {"u2": _make_features()}
        report = check_parity(offline, online)
        assert report.total_entities == 0
        assert report.violations == []
