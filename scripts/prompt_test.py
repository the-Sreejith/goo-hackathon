"""Run LLM.parse against 20 canonical phrasings and print a pass/fail grid.

Requires `llama-server` to be running (see docs/pi_setup.md §6.4). If the server
is unreachable, the script skips with a clear message rather than failing.

    python -m scripts.prompt_test
"""

from __future__ import annotations

import sys

from dumme.llm.client import LlamaClient
from dumme.llm.parser import LLM
from dumme.llm.schema import Command
from dumme.utils.logging import get_logger

_log = get_logger("scripts.prompt_test")

# 20 test cases: (utterance, expected Command).
CASES: list[tuple[str, Command]] = [
    ("pick up the red block and put it in the blue cup", Command("pick_and_place", "red", "blue")),
    ("grab the green one and drop it in red", Command("pick_and_place", "green", "red")),
    ("move the blue block to the green cup", Command("pick_and_place", "blue", "green")),
    ("put the red thing into the green bowl", Command("pick_and_place", "red", "green")),
    (
        "can you place the green item inside the blue container",
        Command("pick_and_place", "green", "blue"),
    ),
    ("take red and give it to blue", Command("pick_and_place", "red", "blue")),
    ("please drop the blue block in the red bowl", Command("pick_and_place", "blue", "red")),
    ("move red to blue", Command("pick_and_place", "red", "blue")),
    ("i want the green cube in the red cup", Command("pick_and_place", "green", "red")),
    ("swap the blue into red", Command("pick_and_place", "blue", "red")),
    ("go home", Command("home", None, None)),
    ("return to home pose", Command("home", None, None)),
    ("reset", Command("home", None, None)),
    ("dance for me", Command("unknown", None, None)),
    ("what time is it", Command("unknown", None, None)),
    ("tell me a joke", Command("unknown", None, None)),
    ("pick", Command("unknown", None, None)),  # too underspecified
    ("fetch me some coffee", Command("unknown", None, None)),
    ("RED block to BLUE cup", Command("pick_and_place", "red", "blue")),
    ("the red one into blue please", Command("pick_and_place", "red", "blue")),
]


def main() -> int:
    client = LlamaClient()
    if not client.healthy():
        print(
            f"llama-server not reachable at {client.base_url}. "
            "Start it first (see docs/pi_setup.md §6.4).",
            file=sys.stderr,
        )
        return 2

    llm = LLM(client=client)
    passed = 0
    for utterance, expected in CASES:
        try:
            got = llm.parse(utterance)
        except NotImplementedError as exc:
            print(f"SKIP (not implemented): {exc}")
            return 3
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL  ERROR  {utterance!r}: {exc}")
            continue
        status = "PASS" if got == expected else "FAIL"
        if got == expected:
            passed += 1
        print(f"{status:4s}  want={expected}  got={got}  <- {utterance!r}")

    print(f"\n{passed}/{len(CASES)} passed")
    return 0 if passed == len(CASES) else 1


if __name__ == "__main__":
    sys.exit(main())
