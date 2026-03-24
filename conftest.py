"""Root conftest — shared fixtures for integration tests."""

from __future__ import annotations

import shutil
import subprocess
import time

import pytest
import redis


@pytest.fixture(scope="session")
def docker_stack():
    """Start the Docker Compose stack, yield, then tear it down.

    Skips automatically if the `docker` binary is not on PATH.
    """
    if shutil.which("docker") is None:
        pytest.skip("docker binary not found on PATH")

    subprocess.run(
        ["docker-compose", "up", "-d"],
        check=True,
        capture_output=True,
    )
    time.sleep(10)

    yield

    subprocess.run(
        ["docker-compose", "down"],
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="session")
def api_base_url() -> str:
    return "http://localhost:8000"


@pytest.fixture(scope="session")
def redis_client() -> redis.Redis:
    return redis.Redis(host="localhost", port=6379, decode_responses=True)
