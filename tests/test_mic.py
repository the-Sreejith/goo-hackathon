"""Mic: mock-mode transcripts + graceful fallback when the Vosk model is absent."""

from __future__ import annotations

from pathlib import Path

import pytest

from dumme.io.mic import Mic


@pytest.mark.unit
class TestMockMode:
    def test_returns_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DUMME_MOCK_UTTERANCE", "pick up the red block")
        mic = Mic(mock=True)
        assert mic.listen() == "pick up the red block"

    def test_strips_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DUMME_MOCK_UTTERANCE", "  go home  \n")
        assert Mic(mock=True).listen() == "go home"

    def test_empty_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DUMME_MOCK_UTTERANCE", raising=False)
        assert Mic(mock=True).listen() == ""

    def test_available_in_mock(self) -> None:
        assert Mic(mock=True).available is True


@pytest.mark.unit
class TestModelMissing:
    def test_not_available_without_model(self, tmp_path: Path) -> None:
        mic = Mic(model_path=tmp_path / "does-not-exist", mock=False)
        assert mic.available is False

    def test_listen_raises_without_model(self, tmp_path: Path) -> None:
        mic = Mic(model_path=tmp_path / "does-not-exist", mock=False)
        with pytest.raises(RuntimeError, match="Vosk model not found"):
            mic.listen()

    def test_listen_raises_with_none_path(self) -> None:
        mic = Mic(model_path=None, mock=False)
        with pytest.raises(RuntimeError, match="Vosk model not found"):
            mic.listen()
