"""
Health check router (EP-002).

Provides a lightweight health endpoint for load balancer / readiness probes.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()


@router.post("/health")
async def health_check() -> dict:
    """Health check endpoint (EP-002).

    Returns 200 OK with a timestamp. Used by load balancers and
    orchestration tools (Kubernetes, Docker) to determine service health.
    """
    return {
        "status": "healthy",
        "service": "meeting-transcript-analyzer",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
