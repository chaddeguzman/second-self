"""Reusable health-check primitives for Second Self and ECHO."""

from .registry import FAIL, OK, WARN, HealthCheck, HealthRegistry, HealthResult
from .system import SystemHealthContext, build_system_health_registry

__all__ = [
    "FAIL",
    "OK",
    "WARN",
    "HealthCheck",
    "HealthRegistry",
    "HealthResult",
    "SystemHealthContext",
    "build_system_health_registry",
]
