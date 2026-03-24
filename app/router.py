"""Request routing — delegates to CanaryController for traffic splitting."""

from fastapi import APIRouter

# TODO: Define /predict and /health endpoints
# Dependencies: ModelRegistry, CanaryController (injected, never imported directly)
router = APIRouter()
