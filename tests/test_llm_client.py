"""LlamaClient HTTP tests — no live server, all `requests` calls mocked."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from dumme.llm.client import CompletionRequest, LlamaClient


class _FakeResponse:
    def __init__(
        self, status_code: int, payload: dict[str, Any] | None = None
    ) -> None:
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if 400 <= self.status_code < 600:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.mark.unit
class TestComplete:
    def test_posts_to_completion_endpoint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}

        def fake_post(url: str, json: dict[str, Any], timeout: float) -> _FakeResponse:
            captured["url"] = url
            captured["json"] = json
            captured["timeout"] = timeout
            return _FakeResponse(200, {"content": "hello world"})

        monkeypatch.setattr("dumme.llm.client.requests.post", fake_post)

        client = LlamaClient(base_url="http://fake:8080")
        out = client.complete(CompletionRequest(prompt="hi", n_predict=20, temperature=0.2))

        assert out == "hello world"
        assert captured["url"] == "http://fake:8080/completion"
        assert captured["json"]["prompt"] == "hi"
        assert captured["json"]["n_predict"] == 20
        assert captured["json"]["temperature"] == 0.2

    def test_trailing_slash_stripped(self) -> None:
        client = LlamaClient(base_url="http://fake:8080/")
        assert client.base_url == "http://fake:8080"


@pytest.mark.unit
class TestHealthy:
    def test_health_200_returns_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "dumme.llm.client.requests.get",
            lambda url, timeout: _FakeResponse(200),
        )
        assert LlamaClient().healthy() is True

    def test_health_500_returns_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "dumme.llm.client.requests.get",
            lambda url, timeout: _FakeResponse(500),
        )
        assert LlamaClient().healthy() is False

    def test_connection_error_returns_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import requests

        def boom(*_a: Any, **_kw: Any) -> None:
            raise requests.ConnectionError("refused")

        monkeypatch.setattr("dumme.llm.client.requests.get", boom)
        assert LlamaClient().healthy() is False
