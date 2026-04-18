"""Shared dataclasses for the command pipeline.

Kept intentionally small — these types cross every module boundary, so any
churn here forces the whole team to rebase.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Action = Literal["pick_and_place", "home", "unknown"]
Color = Literal["red", "blue", "green"]


@dataclass(frozen=True)
class Command:
    """Structured form of a user utterance, emitted by the LLM parser."""

    action: Action
    target_color: Color | None
    dest_color: Color | None


@dataclass(frozen=True)
class ExecutionResult:
    """Returned from Orchestrator.execute. Goes to /command response and TTS."""

    ok: bool
    message: str


def ok(message: str = "Task complete.") -> ExecutionResult:
    return ExecutionResult(ok=True, message=message)


def fail(message: str) -> ExecutionResult:
    return ExecutionResult(ok=False, message=message)
