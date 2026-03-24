"""End-to-end demo of the Stream Vault feature store pipeline."""

from __future__ import annotations

import sys
import time

import httpx
import numpy as np
import redis

from app.store import FEATURE_FIELDS
from scripts.parity_check import check_parity

API_BASE = "http://localhost:8000"
REDIS_HOST = "localhost"
REDIS_PORT = 6379
NUM_RECORDS = 100
SEED = 42


def check_prerequisites() -> redis.Redis:
    """Verify Redis and the API are reachable. Exit 1 if not."""
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping()
    except redis.ConnectionError:
        print(f"ERROR: Redis not reachable at {REDIS_HOST}:{REDIS_PORT}")
        print("Start the Docker stack first: docker-compose up -d")
        sys.exit(1)

    try:
        resp = httpx.get(f"{API_BASE}/health", timeout=5)
        resp.raise_for_status()
    except (httpx.ConnectError, httpx.HTTPStatusError):
        print(f"ERROR: API not reachable at {API_BASE}/health")
        print("Start the API first: uvicorn app.main:app --reload")
        sys.exit(1)

    print("Prerequisites OK: Redis and API are reachable.")
    return r


def generate_records(n: int) -> list[dict]:
    """Generate n synthetic feature records."""
    rng = np.random.default_rng(SEED)
    now_ms = int(time.time() * 1000)

    records = []
    for i in range(n):
        records.append(
            {
                "user_id": f"demo_user_{i:04d}",
                "timestamp": now_ms,
                "watch_time_30d": float(rng.uniform(0, 500)),
                "click_rate_7d": float(rng.uniform(0.0, 1.0)),
                "session_count_14d": float(rng.uniform(0, 100)),
                "genre_affinity_score": float(rng.uniform(0.0, 1.0)),
                "recency_score": float(rng.uniform(0.0, 1.0)),
            }
        )
    return records


def ingest_records(records: list[dict]) -> list[dict]:
    """POST each record to /ingest. Return list of successfully ingested records."""
    succeeded = []
    failed = 0

    with httpx.Client(base_url=API_BASE, timeout=10) as client:
        for i, record in enumerate(records, 1):
            try:
                resp = client.post("/ingest", json=record)
                if resp.status_code == 202:
                    succeeded.append(record)
                else:
                    failed += 1
            except httpx.HTTPError:
                failed += 1

            if i % 10 == 0 or i == len(records):
                print(f"Ingesting... {i}/{len(records)}")

    print(f"Ingested: {len(succeeded)}/{len(records)} succeeded, {failed} failed")
    return succeeded


def build_parity_dicts(
    records: list[dict], r: redis.Redis
) -> tuple[dict, dict]:
    """Build offline (from generated values) and online (from Redis) dicts."""
    offline = {}
    online = {}

    for record in records:
        uid = record["user_id"]
        key = f"features:{uid}"

        stored = r.hgetall(key)
        if not stored:
            continue

        offline[uid] = {f: record[f] for f in FEATURE_FIELDS}
        online[uid] = {f: float(stored[f]) for f in FEATURE_FIELDS}

    return offline, online


def main() -> int:
    r = check_prerequisites()

    print(f"\nGenerating {NUM_RECORDS} synthetic records...")
    records = generate_records(NUM_RECORDS)

    print(f"\nIngesting {NUM_RECORDS} records via POST /ingest...")
    succeeded = ingest_records(records)

    if not succeeded:
        print("ERROR: No records were ingested successfully.")
        return 1

    print("\nBuilding parity comparison...")
    offline, online = build_parity_dicts(succeeded, r)

    report = check_parity(offline, online)

    print("\n--- Parity Report ---")
    print(f"Entities checked: {report.total_entities}")
    print(f"Violations: {len(report.violations)}")
    print(f"Violation rate: {report.violation_rate:.5f}")
    print(f"Drift detected: {report.drift}")

    if report.drift:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
