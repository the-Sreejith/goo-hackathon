"""Tests for JSON extraction and Command coercion — no live LLM required."""

from __future__ import annotations

import pytest

from dumme.llm.client import CompletionRequest, LlamaClient
from dumme.llm.parser import LLM, _coerce_to_command, _extract_json
from dumme.llm.schema import Command


@pytest.mark.unit
class TestExtractJson:
    def test_plain_object(self) -> None:
        assert _extract_json('{"a": 1}') == '{"a": 1}'

    def test_leading_prose(self) -> None:
        text = 'Sure, here is the JSON: {"action":"home","target_color":null,"dest_color":null}'
        assert _extract_json(text) == '{"action":"home","target_color":null,"dest_color":null}'

    def test_markdown_fenced(self) -> None:
        text = '```json\n{"action":"home","target_color":null,"dest_color":null}\n```'
        assert _extract_json(text) == '{"action":"home","target_color":null,"dest_color":null}'

    def test_no_object(self) -> None:
        assert _extract_json("no json here") is None

    def test_nested_object(self) -> None:
        assert _extract_json('foo {"a": {"b": 1}} bar') == '{"a": {"b": 1}}'


@pytest.mark.unit
class TestCoerceCommand:
    def test_valid_pick_and_place(self) -> None:
        cmd = _coerce_to_command(
            {"action": "pick_and_place", "target_color": "red", "dest_color": "blue"}
        )
        assert cmd == Command("pick_and_place", "red", "blue")

    def test_valid_home(self) -> None:
        cmd = _coerce_to_command({"action": "home", "target_color": None, "dest_color": None})
        assert cmd == Command("home", None, None)

    def test_invalid_action(self) -> None:
        cmd = _coerce_to_command({"action": "explode", "target_color": None, "dest_color": None})
        assert cmd is None

    def test_invalid_color(self) -> None:
        cmd = _coerce_to_command(
            {"action": "pick_and_place", "target_color": "purple", "dest_color": "blue"}
        )
        assert cmd is None

    def test_missing_field(self) -> None:
        cmd = _coerce_to_command({"action": "pick_and_place"})
        assert cmd is None


class _StubClient:
    """Minimal LlamaClient double: returns pre-canned completions in order."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[CompletionRequest] = []

    def complete(self, req: CompletionRequest) -> str:
        self.calls.append(req)
        return self._responses.pop(0) if self._responses else ""


@pytest.mark.unit
class TestLLMParse:
    _PROMPT = "User: {{UTTERANCE}}"

    def test_parses_valid_response_on_first_try(self) -> None:
        client = _StubClient(
            ['{"action":"home","target_color":null,"dest_color":null}']
        )
        llm = LLM(client=client, prompt_template=self._PROMPT)  # type: ignore[arg-type]
        assert llm.parse("go home") == Command("home", None, None)
        assert len(client.calls) == 1
        assert "go home" in client.calls[0].prompt

    def test_retries_once_on_invalid_then_succeeds(self) -> None:
        client = _StubClient(
            [
                "i am a chatbot hello",  # no JSON → triggers retry
                '{"action":"pick_and_place","target_color":"red","dest_color":"blue"}',
            ]
        )
        llm = LLM(client=client, prompt_template=self._PROMPT, max_retries=1)  # type: ignore[arg-type]
        assert llm.parse("red to blue") == Command("pick_and_place", "red", "blue")
        assert len(client.calls) == 2
        # Second prompt should include the retry reminder.
        assert "REMINDER" in client.calls[1].prompt

    def test_unparseable_after_retries_returns_unknown(self) -> None:
        client = _StubClient(["not json", "still not json"])
        llm = LLM(client=client, prompt_template=self._PROMPT, max_retries=1)  # type: ignore[arg-type]
        assert llm.parse("???") == Command("unknown", None, None)

    def test_client_exception_returns_unknown(self) -> None:
        class BoomClient:
            def complete(self, _req: CompletionRequest) -> str:
                raise RuntimeError("connection refused")

        llm = LLM(client=BoomClient(), prompt_template=self._PROMPT)  # type: ignore[arg-type]
        assert llm.parse("anything") == Command("unknown", None, None)
