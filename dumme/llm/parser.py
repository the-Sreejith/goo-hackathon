"""Parse user utterances into `Command` via Gemma.

Strategy:
    1. Fill the prompt template (config/prompts/command_parser.txt) with the
       user utterance.
    2. Send to LlamaClient. Gemma returns a completion string.
    3. Extract the first `{...}` block using a balanced-brace scan, tolerant
       of leading/trailing prose or markdown fences.
    4. Validate against the schema. On failure, retry ONCE with a reminder.
    5. If still invalid, return Command(action="unknown", ...).
"""

from __future__ import annotations

import json
import re
from typing import get_args

from dumme.llm.client import CompletionRequest, LlamaClient
from dumme.llm.schema import Action, Color, Command
from dumme.utils.config import load_prompt
from dumme.utils.logging import get_logger

_UTTERANCE_PLACEHOLDER = "{{UTTERANCE}}"
_RETRY_REMINDER = (
    "\n\nREMINDER: return ONLY the JSON object described in the schema. "
    "No prose, no markdown, no trailing text.\n"
)

_log = get_logger(__name__)

_JSON_OBJECT_RE = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.DOTALL)
_VALID_ACTIONS: set[str] = set(get_args(Action))
_VALID_COLORS: set[str] = set(get_args(Color))


def _extract_json(text: str) -> str | None:
    """Return the first JSON object substring in `text`, or None."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE)
    match = _JSON_OBJECT_RE.search(text)
    return match.group(0) if match else None


def _coerce_to_command(payload: dict) -> Command | None:
    # Require all three fields to be EXPLICITLY present; missing keys = malformed.
    required_keys = {"action", "target_color", "dest_color"}
    if not required_keys.issubset(payload.keys()):
        return None
    action = payload["action"]
    target = payload["target_color"]
    dest = payload["dest_color"]
    if action not in _VALID_ACTIONS:
        return None
    if target is not None and target not in _VALID_COLORS:
        return None
    if dest is not None and dest not in _VALID_COLORS:
        return None
    return Command(action=action, target_color=target, dest_color=dest)


class LLM:
    """High-level: utterance in, Command out."""

    def __init__(
        self,
        client: LlamaClient,
        prompt_template: str | None = None,
        max_retries: int = 1,
    ) -> None:
        self.client = client
        self.prompt_template = prompt_template or load_prompt("command_parser")
        self.max_retries = max_retries

    def parse(self, utterance: str) -> Command:
        """Convert a natural-language utterance into a validated Command."""
        base_prompt = self.prompt_template.replace(_UTTERANCE_PLACEHOLDER, utterance)
        reminder = ""
        last_content = ""

        for attempt in range(self.max_retries + 1):
            prompt = base_prompt + reminder
            try:
                last_content = self.client.complete(
                    CompletionRequest(
                        prompt=prompt,
                        n_predict=128,
                        temperature=0.1,
                        stop=("\n\n", "User:", "```"),
                    )
                )
            except Exception as exc:
                _log.warning("LLM call failed (attempt %d): %s", attempt, exc)
                break

            cmd = self._try_coerce(last_content)
            if cmd is not None:
                return cmd

            _log.warning(
                "LLM output invalid on attempt %d: %r", attempt, last_content[:200]
            )
            reminder = _RETRY_REMINDER

        return Command(action="unknown", target_color=None, dest_color=None)

    @staticmethod
    def _try_coerce(content: str) -> Command | None:
        json_str = _extract_json(content)
        if not json_str:
            return None
        try:
            payload = json.loads(json_str)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        return _coerce_to_command(payload)
