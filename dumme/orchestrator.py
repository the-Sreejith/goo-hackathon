"""The command → action loop. The only module that knows the pipeline shape.

Pseudocode (PLAN.md §3.5):
    1. Parse utterance → Command (already done by caller — we take Command).
    2. If action == home: motion.home(); return ok().
    3. If action == unknown: return fail('did not understand').
    4. Sweep + detect target; if missed → fail politely.
    5. Translate target pixel → (r, theta); motion.pick.
    6. Sweep + detect destination; if missed → home + fail.
    7. motion.place; motion.home; return ok().
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dumme.calibration.regression import Calibration
from dumme.llm.schema import Command, ExecutionResult, fail, ok
from dumme.motion.primitives import Motion
from dumme.utils.logging import get_logger
from dumme.vision.detector import Detection, Vision

_log = get_logger(__name__)


@dataclass(frozen=True)
class SweepConfig:
    """Turntable sweep parameters for `sweep_and_detect`."""

    theta_min_deg: float = -60.0
    theta_max_deg: float = 60.0
    step_deg: float = 15.0
    settle_seconds: float = 0.3


class Orchestrator:
    """Glues Motion + Vision + Calibration. Stateless between invocations."""

    def __init__(
        self,
        motion: Motion,
        vision: Vision,
        calibration: Calibration,
        sweep: SweepConfig | None = None,
        on_status: Any = None,  # optional callback: str -> None (for TTS or UI toast)
    ) -> None:
        self.motion = motion
        self.vision = vision
        self.calibration = calibration
        self.sweep = sweep or SweepConfig()
        self.on_status = on_status
        self.last_result: ExecutionResult | None = None

    # ── public API ────────────────────────────────────────────────────────
    def execute(self, cmd: Command) -> ExecutionResult:
        """Run the Command end-to-end. Returns an ExecutionResult either way."""
        try:
            result = self._execute_inner(cmd)
        except NotImplementedError as exc:
            _log.warning("Pipeline step not yet implemented: %s", exc)
            result = fail(f"Not yet implemented: {exc}")
        except Exception as exc:  # noqa: BLE001 — top-level safety net
            _log.exception("Orchestrator error")
            self.motion.release_all()
            result = fail(f"Internal error: {exc}")
        self.last_result = result
        return result

    # ── internals ─────────────────────────────────────────────────────────
    def _execute_inner(self, cmd: Command) -> ExecutionResult:
        self._status(f"Parsed: {cmd}")
        if cmd.action == "home":
            self.motion.home()
            return ok("Home pose.")
        if cmd.action == "unknown":
            return fail("I didn't understand that.")
        if cmd.action == "pick_and_place":
            return self._pick_and_place(cmd)
        return fail(f"Unsupported action: {cmd.action}")

    def _pick_and_place(self, cmd: Command) -> ExecutionResult:
        if cmd.target_color is None or cmd.dest_color is None:
            return fail("Missing target or destination color.")

        self._status(f"Looking for {cmd.target_color} block…")
        target_hit = self.sweep_and_detect(cmd.target_color)
        if target_hit is None:
            return fail(f"I can't see the {cmd.target_color} object.")
        self._status(f"Found {cmd.target_color} block.")

        r, theta = self.calibration.pixel_to_polar(
            target_hit.pixel_xy, self.motion.turntable_angle_deg
        )
        if not self.calibration.in_reach(r, theta):
            return fail(f"The {cmd.target_color} object is out of reach.")
        self.motion.pick(r, theta)

        self._status(f"Looking for {cmd.dest_color} cup…")
        dest_hit = self.sweep_and_detect(cmd.dest_color)
        if dest_hit is None:
            self.motion.home()
            return fail(f"I can't see the {cmd.dest_color} destination.")

        r2, theta2 = self.calibration.pixel_to_polar(
            dest_hit.pixel_xy, self.motion.turntable_angle_deg
        )
        if not self.calibration.in_reach(r2, theta2):
            self.motion.home()
            return fail(f"The {cmd.dest_color} destination is out of reach.")
        self.motion.place(r2, theta2)
        self.motion.home()
        return ok("Task complete.")

    def sweep_and_detect(self, color: str) -> Detection | None:
        """Rotate the turntable in steps from theta_min to theta_max, returning the first hit."""
        import time

        theta = self.sweep.theta_min_deg
        while theta <= self.sweep.theta_max_deg:
            self.motion.turntable_rotate(theta)
            time.sleep(self.sweep.settle_seconds)
            hit = self.vision.find(color)
            if hit is not None:
                return hit
            theta += self.sweep.step_deg
        return None

    def _status(self, msg: str) -> None:
        _log.info(msg)
        if self.on_status is not None:
            try:
                self.on_status(msg)
            except Exception as exc:  # noqa: BLE001 — status side-channel is cosmetic
                _log.debug("on_status callback failed: %s", exc)
