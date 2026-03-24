"""Scheduled parity validation between offline and online feature stores."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.store import FEATURE_FIELDS

TOLERANCE = 0.001
DRIFT_THRESHOLD = 0.001


@dataclass
class ParityReport:
    total_entities: int
    violations: list[str] = field(default_factory=list)
    violation_rate: float = 0.0
    drift: bool = False


def check_parity(
    offline: dict[str, dict[str, float]],
    online: dict[str, dict[str, float]],
) -> ParityReport:
    """Compare offline and online feature values for all shared entities.

    Flags a user_id if any feature's absolute delta exceeds TOLERANCE.
    Sets drift=True if the violation rate exceeds DRIFT_THRESHOLD.
    """
    common_ids = sorted(set(offline) & set(online))
    total = len(common_ids)

    violations = []
    for uid in common_ids:
        off = offline[uid]
        on = online[uid]
        for feat in FEATURE_FIELDS:
            if abs(off[feat] - on[feat]) > TOLERANCE:
                violations.append(uid)
                break

    rate = len(violations) / total if total > 0 else 0.0

    return ParityReport(
        total_entities=total,
        violations=violations,
        violation_rate=rate,
        drift=rate > DRIFT_THRESHOLD,
    )
