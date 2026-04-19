"""Eval-only conftest: write a per-case JSON report for prompt regression tracking.

Emits `eval_report.json` at repo root when any eval test runs, with shape:
    {
      "summary": {"total": N, "passed": N, "accuracy": 0.95},
      "cases": [{"id": "...", "outcome": "passed|failed", "duration_s": 0.12}]
    }

Used by CI / local runs to diff accuracy across prompt edits. Safe to delete;
no test or module depends on it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

_REPORT_PATH = Path(__file__).resolve().parents[2] / "eval_report.json"
_ACCUMULATOR: dict[str, Any] = {"cases": []}


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Capture the 'call' phase of each eval test."""
    if report.when != "call":
        return
    if "tests/eval/" not in report.nodeid:
        return
    _ACCUMULATOR["cases"].append(
        {
            "id": report.nodeid.split("::", 1)[-1],
            "outcome": report.outcome,
            "duration_s": round(report.duration, 3),
        }
    )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    cases = _ACCUMULATOR["cases"]
    if not cases:
        return  # no eval tests ran → no artifact
    total = len(cases)
    passed = sum(1 for c in cases if c["outcome"] == "passed")
    summary = {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "accuracy": round(passed / total, 4) if total else 0.0,
    }
    _REPORT_PATH.write_text(
        json.dumps({"summary": summary, "cases": cases}, indent=2) + "\n"
    )
