"""Canary controller — Bernoulli traffic splitting + automatic SLO-based rollback."""

# TODO: Implement CanaryController class
# - route_request() -> "champion" | "challenger" (Bernoulli draw, NOT feature flag)
# - check_slo() -> bool (p99 latency > 200ms OR error rate > 1% triggers rollback)
# - rollback() -> None (automatic on SLO breach, enforced HERE not in middleware)
