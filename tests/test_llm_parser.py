"""Tests for JSON extraction and Command coercion — no live LLM required."""

from __future__ import annotations

import pytest

from dumme.llm.parser import _coerce_to_command, _extract_json
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
