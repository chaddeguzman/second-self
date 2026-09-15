"""Bounded, loopback-only Ollama provider using the standard library."""

from __future__ import annotations

import http.client
import ipaddress
import json
import os
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

from ..routing import ProviderCapability, ProviderLocality, RouteRequest, Sensitivity
from .base import (
    InferenceResult,
    ProviderError,
    ProviderHealth,
    ProviderHealthStatus,
)

DEFAULT_CONNECT_TIMEOUT = 2.0
DEFAULT_TOTAL_TIMEOUT = 60.0
DEFAULT_MAX_RESPONSE_BYTES = 1_048_576
MAX_PROMPT_BYTES = 262_144


@dataclass(frozen=True, slots=True)
class TransportResponse:
    """Bounded response returned by an injectable HTTP transport."""

    status: int
    body: bytes


class HttpTransport(Protocol):
    """Minimal transport boundary used by Ollama and faked in tests."""

    def request(
        self,
        method: str,
        url: str,
        body: bytes | None,
        *,
        connect_timeout: float,
        total_timeout: float,
        max_response_bytes: int,
    ) -> TransportResponse: ...


class HttpClientTransport:
    """Standard-library HTTP transport with separate connection/total bounds."""

    def request(
        self,
        method: str,
        url: str,
        body: bytes | None,
        *,
        connect_timeout: float,
        total_timeout: float,
        max_response_bytes: int,
    ) -> TransportResponse:
        parsed = urlparse(url)
        if parsed.scheme != "http" or parsed.hostname is None:
            raise ProviderError("Ollama endpoint is invalid.")
        started = time.monotonic()
        connection = http.client.HTTPConnection(
            parsed.hostname,
            parsed.port or 80,
            timeout=connect_timeout,
        )
        try:
            path = parsed.path or "/"
            if parsed.query:
                path = f"{path}?{parsed.query}"
            headers = {"Accept": "application/json"}
            if body is not None:
                headers["Content-Type"] = "application/json"
            connection.request(method, path, body=body, headers=headers)
            remaining = total_timeout - (time.monotonic() - started)
            if remaining <= 0:
                raise ProviderError("Ollama request timed out.")
            if connection.sock is not None:
                connection.sock.settimeout(remaining)
            response = connection.getresponse()
            payload = bytearray()
            while True:
                # TECHNICAL: Recalculate the remaining wall-clock budget before
                # every chunk. A slow trickle therefore cannot reset the total
                # timeout indefinitely, while the extra byte detects overflow.
                #
                # JUNIOR: The whole request shares one countdown clock; receiving
                # a small piece does not restart that clock.
                remaining = total_timeout - (time.monotonic() - started)
                if remaining <= 0:
                    raise ProviderError("Ollama request timed out.")
                if connection.sock is not None:
                    connection.sock.settimeout(remaining)
                chunk = response.read(min(65_536, max_response_bytes + 1 - len(payload)))
                if not chunk:
                    break
                payload.extend(chunk)
                if len(payload) > max_response_bytes:
                    raise ProviderError("Ollama response exceeded the size limit.")
            return TransportResponse(response.status, bytes(payload))
        except ProviderError:
            raise
        except (OSError, http.client.HTTPException, socket.timeout):
            raise ProviderError("Ollama request failed.") from None
        finally:
            connection.close()


@dataclass(frozen=True, slots=True)
class OllamaConfig:
    """Validated ignored-local configuration for one Ollama adapter."""

    endpoint: str
    model: str
    connect_timeout: float = DEFAULT_CONNECT_TIMEOUT
    total_timeout: float = DEFAULT_TOTAL_TIMEOUT
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES

    def __post_init__(self) -> None:
        parsed = urlparse(self.endpoint)
        if parsed.scheme != "http" or parsed.hostname is None:
            raise ValueError("Ollama endpoint must be loopback HTTP")
        try:
            loopback = parsed.hostname == "localhost" or ipaddress.ip_address(
                parsed.hostname
            ).is_loopback
        except ValueError:
            loopback = False
        if not loopback or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Ollama endpoint must be loopback HTTP")
        if parsed.path not in ("", "/"):
            raise ValueError("Ollama endpoint must not include a path")
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("Ollama model is required")
        if not 0 < self.connect_timeout <= self.total_timeout <= 300:
            raise ValueError("Ollama timeouts are invalid")
        if not 1_024 <= self.max_response_bytes <= 16_777_216:
            raise ValueError("Ollama response limit is invalid")


def load_ollama_config(config_path: Path) -> OllamaConfig:
    """Load Ollama settings from ignored local JSON with redacted failures."""
    try:
        if config_path.stat().st_size > 1_048_576:
            raise ValueError("configuration too large")
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("configuration must be an object")
        local_models = payload.get("local_models")
        ollama = local_models.get("ollama") if isinstance(local_models, dict) else None
        if not isinstance(ollama, dict):
            raise ValueError("configuration missing")
        endpoint = os.path.expandvars(ollama["endpoint"])
        model = ollama["model"]
        return OllamaConfig(
            endpoint=endpoint,
            model=model,
            connect_timeout=float(
                ollama.get("connect_timeout_seconds", DEFAULT_CONNECT_TIMEOUT)
            ),
            total_timeout=float(
                ollama.get("total_timeout_seconds", DEFAULT_TOTAL_TIMEOUT)
            ),
            max_response_bytes=int(
                ollama.get("max_response_bytes", DEFAULT_MAX_RESPONSE_BYTES)
            ),
        )
    except (KeyError, OSError, TypeError, ValueError):
        raise ProviderError("Ollama local configuration is missing or invalid.") from None


class OllamaProvider:
    """Local Ollama health and non-streaming inference adapter."""

    name = "ollama"

    def __init__(
        self, config: OllamaConfig, transport: HttpTransport | None = None
    ) -> None:
        self._config = config
        self._transport = transport or HttpClientTransport()

    @classmethod
    def from_config(
        cls, config_path: Path, transport: HttpTransport | None = None
    ) -> OllamaProvider:
        return cls(load_ollama_config(config_path), transport)

    def capability(self) -> ProviderCapability:
        health = self.health()
        return ProviderCapability(
            provider=self.name,
            locality=ProviderLocality.LOCAL,
            supported_operations=frozenset({"generate"}),
            available=health.ready,
            configured_model=self._config.model,
        )

    def health(self) -> ProviderHealth:
        try:
            response = self._request("GET", "/api/tags")
            payload = self._decode_object(response)
            models = payload.get("models")
            if not isinstance(models, list):
                raise ProviderError("Ollama health response was invalid.")
            names = {
                item.get("name")
                for item in models
                if isinstance(item, dict) and isinstance(item.get("name"), str)
            }
            if self._config.model not in names:
                return ProviderHealth(
                    ProviderHealthStatus.MISCONFIGURED,
                    "configured Ollama model is unavailable",
                )
            return ProviderHealth(ProviderHealthStatus.READY, "Ollama provider ready")
        except ProviderError:
            return ProviderHealth(
                ProviderHealthStatus.UNAVAILABLE, "optional Ollama provider unavailable"
            )

    def infer(self, request: RouteRequest, prompt: str) -> InferenceResult:
        if not isinstance(request, RouteRequest) or request.operation != "generate":
            raise ProviderError("Ollama request operation is unsupported.")
        if request.sensitivity is Sensitivity.PROHIBITED:
            raise ProviderError("Prohibited data cannot be submitted to a provider.")
        if not isinstance(prompt, str) or not prompt:
            raise ProviderError("Ollama prompt is invalid.")
        encoded_prompt = prompt.encode("utf-8")
        if len(encoded_prompt) > MAX_PROMPT_BYTES:
            raise ProviderError("Ollama prompt exceeded the size limit.")
        body = json.dumps(
            {"model": self._config.model, "prompt": prompt, "stream": False}
        ).encode("utf-8")
        response = self._request("POST", "/api/generate", body)
        payload = self._decode_object(response)
        text = payload.get("response")
        if not isinstance(text, str):
            raise ProviderError("Ollama response was invalid.")
        return InferenceResult(self.name, self._config.model, text)

    def _request(
        self, method: str, path: str, body: bytes | None = None
    ) -> TransportResponse:
        try:
            response = self._transport.request(
                method,
                f"{self._config.endpoint.rstrip('/')}{path}",
                body,
                connect_timeout=self._config.connect_timeout,
                total_timeout=self._config.total_timeout,
                max_response_bytes=self._config.max_response_bytes,
            )
        except ProviderError:
            raise
        except Exception:
            raise ProviderError("Ollama request failed.") from None
        if response.status != 200:
            raise ProviderError("Ollama request failed.")
        if len(response.body) > self._config.max_response_bytes:
            raise ProviderError("Ollama response exceeded the size limit.")
        return response

    @staticmethod
    def _decode_object(response: TransportResponse) -> dict[str, object]:
        try:
            payload = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise ProviderError("Ollama response was invalid.") from None
        if not isinstance(payload, dict):
            raise ProviderError("Ollama response was invalid.")
        return payload
