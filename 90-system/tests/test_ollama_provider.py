"""Hermetic tests for the bounded Ollama provider adapter."""

from __future__ import annotations

import json

import pytest

from second_self.providers import (
    OllamaConfig,
    OllamaProvider,
    ProviderError,
    ProviderHealthStatus,
    load_ollama_config,
)
from second_self.providers.ollama import MAX_PROMPT_BYTES, TransportResponse
from second_self.routing import DataOrigin, DataOriginKind, RouteRequest, Sensitivity


class FakeTransport:
    """In-memory transport that records bounds and never opens a socket."""

    def __init__(self, response=None, error: Exception | None = None) -> None:
        self.response = response or TransportResponse(200, b"{}")
        self.error = error
        self.calls: list[dict[str, object]] = []

    def request(
        self,
        method,
        url,
        body,
        *,
        connect_timeout,
        total_timeout,
        max_response_bytes,
    ):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "body": body,
                "connect_timeout": connect_timeout,
                "total_timeout": total_timeout,
                "max_response_bytes": max_response_bytes,
            }
        )
        if self.error:
            raise self.error
        return self.response


def config(**overrides) -> OllamaConfig:
    values = {"endpoint": "http://127.0.0.1:11434", "model": "local-model"}
    values.update(overrides)
    return OllamaConfig(**values)


def request(sensitivity=Sensitivity.SENSITIVE) -> RouteRequest:
    return RouteRequest(
        "generate",
        sensitivity,
        (DataOrigin(DataOriginKind.MEMORY, "synthetic"),),
    )


def test_loads_endpoint_model_and_bounds_from_ignored_config(tmp_path):
    config_path = tmp_path / ".second-self.local.json"
    config_path.write_text(
        json.dumps(
            {
                "local_models": {
                    "ollama": {
                        "endpoint": "http://localhost:11434",
                        "model": "configured-model",
                        "connect_timeout_seconds": 1.5,
                        "total_timeout_seconds": 20,
                        "max_response_bytes": 4096,
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    loaded = load_ollama_config(config_path)

    assert loaded == OllamaConfig(
        "http://localhost:11434", "configured-model", 1.5, 20.0, 4096
    )


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://127.0.0.1:11434",
        "http://192.168.1.2:11434",
        "http://example.com:11434",
        "http://user:password@127.0.0.1:11434",
        "http://127.0.0.1:11434/api",
    ],
)
def test_rejects_non_loopback_or_unsafe_endpoint(endpoint):
    with pytest.raises(ValueError, match="Ollama endpoint"):
        config(endpoint=endpoint)


@pytest.mark.parametrize(
    "payload", ["not-json", "[]", "{}", '{"local_models": {}}']
)
def test_corrupt_or_missing_config_is_redacted(tmp_path, payload):
    config_path = tmp_path / "private-config.json"
    config_path.write_text(payload, encoding="utf-8")

    with pytest.raises(ProviderError) as error:
        load_ollama_config(config_path)

    assert str(error.value) == "Ollama local configuration is missing or invalid."
    assert str(tmp_path) not in str(error.value)


def test_health_ready_reports_capability_and_explicit_bounds():
    transport = FakeTransport(
        TransportResponse(200, b'{"models": [{"name": "local-model"}]}')
    )
    provider = OllamaProvider(
        config(connect_timeout=1.25, total_timeout=15, max_response_bytes=8192),
        transport,
    )

    health = provider.health()
    capability = provider.capability()

    assert health.status is ProviderHealthStatus.READY
    assert capability.available is True
    assert capability.provider == "ollama"
    assert capability.supported_operations == frozenset({"generate"})
    assert transport.calls[0]["connect_timeout"] == 1.25
    assert transport.calls[0]["total_timeout"] == 15
    assert transport.calls[0]["max_response_bytes"] == 8192


def test_missing_model_is_misconfigured():
    provider = OllamaProvider(
        config(), FakeTransport(TransportResponse(200, b'{"models": []}'))
    )

    health = provider.health()

    assert health.status is ProviderHealthStatus.MISCONFIGURED
    assert "local-model" not in health.detail


@pytest.mark.parametrize(
    "transport",
    [
        FakeTransport(error=ProviderError("timed out at C:/private")),
        FakeTransport(TransportResponse(200, b"not-json")),
        FakeTransport(TransportResponse(500, b'{"error": "private"}')),
        FakeTransport(TransportResponse(200, b"x" * 2048)),
    ],
)
def test_health_failures_are_unavailable_and_redacted(transport):
    provider = OllamaProvider(config(max_response_bytes=1024), transport)

    health = provider.health()

    assert health.status is ProviderHealthStatus.UNAVAILABLE
    assert "private" not in health.detail
    assert "127.0.0.1" not in health.detail


def test_inference_is_non_streaming_bounded_and_returns_text():
    transport = FakeTransport(
        TransportResponse(200, b'{"response": "synthetic answer"}')
    )
    provider = OllamaProvider(config(), transport)

    result = provider.infer(request(), "synthetic prompt")

    assert result.text == "synthetic answer"
    sent = json.loads(transport.calls[0]["body"])
    assert sent == {
        "model": "local-model",
        "prompt": "synthetic prompt",
        "stream": False,
    }
    assert transport.calls[0]["url"] == "http://127.0.0.1:11434/api/generate"


def test_prohibited_request_denies_before_transport():
    transport = FakeTransport()
    provider = OllamaProvider(config(), transport)

    with pytest.raises(ProviderError, match="Prohibited"):
        provider.infer(request(Sensitivity.PROHIBITED), "must not leave")

    assert transport.calls == []


def test_unsupported_operation_denies_before_transport():
    transport = FakeTransport()
    provider = OllamaProvider(config(), transport)
    unsupported = RouteRequest(
        "summarize",
        Sensitivity.PUBLIC,
        (DataOrigin(DataOriginKind.PUBLIC, "synthetic"),),
    )

    with pytest.raises(ProviderError, match="unsupported"):
        provider.infer(unsupported, "synthetic prompt")

    assert transport.calls == []


def test_oversized_prompt_denies_before_transport():
    transport = FakeTransport()
    provider = OllamaProvider(config(), transport)

    with pytest.raises(ProviderError, match="size limit"):
        provider.infer(request(), "x" * (MAX_PROMPT_BYTES + 1))

    assert transport.calls == []


def test_inference_failure_never_includes_response_body():
    private_body = b'{"error": "raw private response"}'
    provider = OllamaProvider(config(), FakeTransport(TransportResponse(500, private_body)))

    with pytest.raises(ProviderError) as error:
        provider.infer(request(), "raw private prompt")

    assert "raw private" not in str(error.value)
