"""Tests for app.delta_client — Delta Lake writer wrapper."""

from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from app.delta_client import DeltaClient


class TestDeltaClientConstructor:
    def test_stores_path(self):
        client = DeltaClient("/tmp/delta")
        assert client.path == "/tmp/delta"


class TestDeltaClientWrite:
    @patch("app.delta_client.write_deltalake")
    def test_calls_write_deltalake_with_correct_args(self, mock_write):
        client = DeltaClient("/tmp/delta")
        df = pd.DataFrame({"a": [1]})

        client.write(df)

        mock_write.assert_called_once_with("/tmp/delta", df, mode="append")

    @patch("app.delta_client.write_deltalake")
    def test_raises_runtime_error_on_failure(self, mock_write):
        mock_write.side_effect = Exception("disk full")
        client = DeltaClient("/tmp/delta")
        df = pd.DataFrame({"a": [1]})

        with pytest.raises(RuntimeError, match="disk full"):
            client.write(df)
