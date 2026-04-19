"""End-to-end eval: utterance → Command via the live llama-server.

Shares the CASES list with scripts/prompt_test.py so we have one canonical
eval set. Skips entirely when llama-server isn't reachable — keeps the
default pytest run green on dev boxes.

Run explicitly:
    pytest -m eval
"""

from __future__ import annotations

import pytest

from dumme.llm.client import LlamaClient
from dumme.llm.parser import LLM
from dumme.llm.schema import Command
from scripts.prompt_test import CASES


@pytest.fixture(scope="module")
def llm() -> LLM:
    client = LlamaClient()
    if not client.healthy():
        pytest.skip(f"llama-server unreachable at {client.base_url}")
    return LLM(client=client)


@pytest.mark.eval
@pytest.mark.parametrize(
    ("utterance", "expected"),
    CASES,
    ids=[f"{i:02d}:{u[:40]!r}" for i, (u, _) in enumerate(CASES)],
)
def test_utterance_parses_to_expected(
    llm: LLM, utterance: str, expected: Command
) -> None:
    """Each canonical phrasing should parse to its expected Command."""
    got = llm.parse(utterance)
    assert got == expected, f"utterance={utterance!r} expected={expected} got={got}"
