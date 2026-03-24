# Stream Vault

![Python](https://img.shields.io/badge/python-3.11-blue.svg) ![License](https://img.shields.io/badge/license-MIT-green.svg)

A production-grade streaming feature store with dual-write consistency, TDD discipline, and a GPT-4o pre-commit drift guard.

## Architecture

```
Kafka ──> ingestion.py ──> validation.py ──> materialization.py ──> store.py ──┬──> Delta Lake (offline)
         (parse JSON)    (schema + range    (orchestrate)        (dual-write) │
                          checks)                                             └──> Redis (online)

Scheduled (background):
  parity_check.py ──> reads Delta Lake + Redis ──> flags drift if >0.1% of entities exceed ±0.001 tolerance
```

All feature writes follow a strict pipeline: parse, validate, then dual-write to both stores atomically. If either store write fails, the error propagates immediately — no silent partial writes. Parity validation runs as a scheduled background job, never inline on the write path.

## Tech Stack

| Component | Technology | Why |
|---|---|---|
| Stream ingestion | Kafka (partitioned by user_id) | Per-entity ordering guarantees materialization consistency |
| Offline store | Delta Lake on MinIO | Append-only with time-travel; S3-compatible object storage |
| Online store | Redis | Sub-millisecond reads for real-time inference serving |
| API | FastAPI + Pydantic | Automatic request validation, 422 error handling, async support |
| Drift guard | OpenAI GPT-4o via pre-commit hook | Catches dual-write violations and schema drift before code lands |
| Tests | pytest + unittest.mock | 69 unit tests + 4 integration tests, all TDD-driven |
| Lint | ruff | Fast, single-tool replacement for flake8/isort/pycodestyle |

## Feature Schema

| Field | Type | Description |
|---|---|---|
| `user_id` | `str` | Entity key identifying the user |
| `timestamp` | `int` | Event time in epoch milliseconds |
| `watch_time_30d` | `float` | Total watch time in the last 30 days (minutes) |
| `click_rate_7d` | `float` | Click-through rate over the last 7 days (0.0 to 1.0) |
| `session_count_14d` | `float` | Number of sessions in the last 14 days |
| `genre_affinity_score` | `float` | Affinity score for the user's preferred genre (0.0 to 1.0) |
| `recency_score` | `float` | Recency-weighted engagement score (0.0 to 1.0) |

This schema models a streaming recommendation feature set. Validation enforces non-negative values, a sanity ceiling of 1,000,000 on `watch_time_30d`, a 0.0-1.0 range on `click_rate_7d`, and rejects NaN on all numerical fields.

## Getting Started

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- An OpenAI API key (optional; the pre-commit drift guard skips automatically without one)

### Setup

```bash
cp .env.example .env
# Edit .env and fill in your values (OPENAI_API_KEY, DELTA_TABLE_PATH, etc.)

docker-compose up -d
pip install -e ".[dev]"
```

### Generate Sample Data

```bash
python scripts/generate_synthetic_data.py
```

### Run the End-to-End Demo

```bash
docker-compose up -d
uvicorn app.main:app --reload &
python demo.py
```

### Run Tests

```bash
pytest                    # 69 unit tests (integration tests auto-skipped)
pytest -m integration     # 4 integration tests (requires Docker stack running)
```

### Run the API

```bash
uvicorn app.main:app --reload
```

The API exposes two endpoints:

- `GET /health` — returns `{"status": "ok"}` (200)
- `POST /ingest` — accepts a JSON body matching the feature schema, returns 202 on success

## Design Decisions

**Kafka partitioned by user_id.** All feature updates for a given user land on the same Kafka partition. This guarantees that events are consumed in order, which is critical for materialization consistency. Without per-entity ordering, a stale feature update could overwrite a newer one, corrupting the online store state that serves real-time inference.

**Dual-write with Delta-first ordering.** Every feature write goes to Delta Lake first, then Redis. If the Delta write fails, Redis is never touched — this prevents the online store from diverging ahead of the offline store. If Redis fails after a successful Delta write, the error propagates to the caller. The offline store is the source of truth; the online store is a read-optimized projection of it.

**Parity check is scheduled, not inline.** Comparing offline and online stores on every write would add unacceptable latency to the hot path and couple the write pipeline to a read-heavy validation step. Instead, `parity_check.py` runs as a scheduled background job that compares all shared entities within a tolerance of 0.001 absolute delta per feature. Drift is flagged when more than 0.1% of entities exceed the threshold, allowing for normal floating-point serialization noise while catching real divergence.

## Pre-Commit Drift Detection

The `.git/hooks/pre-commit` hook runs `scripts/drift_detection.py --check` on every commit that includes staged Python files. The script extracts the staged diff via `git diff --cached`, sends it to OpenAI GPT-4o, and checks for three classes of violations:

1. **Single-store writes** — any write to Delta Lake or Redis that is not a dual-write to both.
2. **Schema drift** — changes to feature record fields without a corresponding migration or validation update.
3. **Inline parity checks** — parity validation logic added to the write path instead of as a scheduled check.

GPT-4o responds with a JSON object containing `critical` issues (which block the commit) and `warnings` (which are printed but do not block).

To bypass the hook, either unset `OPENAI_API_KEY` (the script prints a warning and exits 0) or use `git commit --no-verify`. The hook is non-blocking if the script is missing or if the API call fails for any reason (network, timeout, rate limit).

## Project Structure

```
.
├── app/
│   ├── __init__.py              # Package marker
│   ├── main.py                  # FastAPI app with /health and /ingest endpoints
│   ├── ingestion.py             # Parses raw JSON bytes into FeatureRecord
│   ├── validation.py            # Schema and range checks on FeatureRecord
│   ├── materialization.py       # Orchestrates validation then dual-write
│   ├── store.py                 # Dual-write to Delta Lake + Redis, FeatureRecord dataclass
│   └── delta_client.py          # Thin wrapper around deltalake.write_deltalake
├── scripts/
│   ├── __init__.py              # Package marker
│   ├── drift_detection.py       # GPT-4o pre-commit hook for diff review
│   └── parity_check.py          # Scheduled offline/online parity validation
├── tests/
│   ├── __init__.py              # Package marker
│   ├── test_health.py           # FastAPI endpoint tests (health + ingest)
│   ├── test_store.py            # Dual-write, validation, Redis key format tests
│   ├── test_validation.py       # Range, NaN, timestamp, sanity ceiling tests
│   ├── test_ingestion.py        # JSON parsing, missing fields, type casting tests
│   ├── test_materialization.py  # Call ordering, error propagation tests
│   ├── test_delta_client.py     # DeltaClient write and error wrapping tests
│   ├── test_parity_check.py     # Tolerance, drift threshold, empty input tests
│   └── test_integration.py      # Live Docker stack tests (auto-skipped by default)
├── data/
│   └── .gitkeep                 # Placeholder for local Delta Lake storage
├── .claude/
│   └── CLAUDE.md                # Development workflow and architectural rules
├── .git/
│   └── hooks/
│       └── pre-commit           # GPT-4o drift detection hook
├── conftest.py                  # Root-level fixtures for integration tests
├── docker-compose.yml           # Kafka, Zookeeper, Redis, MinIO services
├── pyproject.toml               # Dependencies, pytest config, ruff config
├── .env.example                 # Environment variable placeholders
├── .gitignore                   # Python, IDE, and data exclusions
└── README.md                    # This file
```

## Author

**Pranav Saravanan**
- GitHub: [@pranavss722](https://github.com/pranavss722)
- Email: pranavss722@gmail.com
