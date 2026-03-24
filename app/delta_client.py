"""Delta Lake writer client — thin wrapper around deltalake.write_deltalake."""

from __future__ import annotations

import pandas as pd
from deltalake import write_deltalake


class DeltaClient:
    """Appends DataFrames to a Delta Lake table at the configured path."""

    def __init__(self, path: str) -> None:
        self.path = path

    def write(self, df: pd.DataFrame) -> None:
        """Append a DataFrame to the Delta table.

        Raises RuntimeError wrapping any deltalake-specific exception.
        """
        try:
            write_deltalake(self.path, df, mode="append")
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc
