"""Reusable health-check primitives for Second Self and ECHO."""

from .registry import FAIL, OK, WARN, HealthCheck, HealthRegistry, HealthResult

__all__ = [
    "FAIL",
    "OK",
    "WARN",
    "HealthCheck",
    "HealthRegistry",
    "HealthResult",
]
