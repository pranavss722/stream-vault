"""Generate synthetic feature data matching the FeatureRecord schema."""

from __future__ import annotations

import time

import numpy as np
import pandas as pd

SEED = 42
NUM_ROWS = 1000
OUTPUT_PATH = "data/features_sample.parquet"


def main() -> None:
    rng = np.random.default_rng(SEED)

    now_ms = int(time.time() * 1000)

    df = pd.DataFrame(
        {
            "user_id": [f"user_{i:04d}" for i in range(NUM_ROWS)],
            "timestamp": rng.integers(now_ms - 86_400_000, now_ms, size=NUM_ROWS),
            "watch_time_30d": rng.uniform(0, 500, size=NUM_ROWS),
            "click_rate_7d": rng.uniform(0.0, 1.0, size=NUM_ROWS),
            "session_count_14d": rng.uniform(0, 100, size=NUM_ROWS),
            "genre_affinity_score": rng.uniform(0.0, 1.0, size=NUM_ROWS),
            "recency_score": rng.uniform(0.0, 1.0, size=NUM_ROWS),
        }
    )

    df.to_parquet(OUTPUT_PATH, index=False)
    print(f"Generated {NUM_ROWS} rows -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
