"""Orchestrator dispatch tests using hand-rolled fakes for Motion/Vision/Calibration.

We don't use unittest.mock so the call-sequence assertions read as a list
of primitive method names (easier to skim when the pipeline changes).
"""

from __future__ import annotations

from typing import Any

import pytest

from dumme.llm.schema import Command
from dumme.orchestrator import Orchestrator, SweepConfig
from dumme.vision.detector import Detection


class FakeMotion:
    """Records every primitive call in .calls; snapshots mutable angles."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.turntable_angle_deg: float = 0.0
        self.base_angle_deg: float = 90.0

    def home(self) -> None:
        self.calls.append(("home", ()))

    def base_rotate(self, angle_deg: float) -> None:
        self.calls.append(("base_rotate", (angle_deg,)))
        self.base_angle_deg = angle_deg

    def turntable_rotate(self, angle_deg: float) -> None:
        self.calls.append(("turntable_rotate", (angle_deg,)))
        self.turntable_angle_deg = angle_deg

    def pick(self, r_mm: float, theta_deg: float) -> None:
        self.calls.append(("pick", (r_mm, theta_deg)))

    def place(self, r_mm: float, theta_deg: float) -> None:
        self.calls.append(("place", (r_mm, theta_deg)))

    def release_all(self) -> None:
        self.calls.append(("release_all", ()))

    def snapshot(self) -> dict[str, Any]:
        return {
            "base_angle_deg": self.base_angle_deg,
            "turntable_angle_deg": self.turntable_angle_deg,
            "estop": False,
        }


class FakeVision:
    """Returns canned Detections keyed by color; records every .find() call."""

    def __init__(self, hits: dict[str, Detection | None]) -> None:
        self.hits = hits
        self.calls: list[str] = []

    def find(self, color: str) -> Detection | None:
        self.calls.append(color)
        return self.hits.get(color)


class FakeCalibration:
    """Echoes pixel_xy to (r, theta) — keeps tests free of regression math."""

    def __init__(self, in_reach: bool = True) -> None:
        self._in_reach = in_reach
        self.reach_queries: list[tuple[float, float]] = []
        self.pixel_queries: list[tuple[tuple[int, int], float]] = []

    def pixel_to_polar(
        self, pixel_xy: tuple[int, int], turntable_angle_deg: float
    ) -> tuple[float, float]:
        self.pixel_queries.append((pixel_xy, turntable_angle_deg))
        # r from pixel_x, theta from pixel_y — arbitrary but deterministic.
        return (float(pixel_xy[0]), float(pixel_xy[1]))

    def in_reach(self, r_mm: float, theta_deg: float) -> bool:
        self.reach_queries.append((r_mm, theta_deg))
        return self._in_reach


@pytest.fixture
def tight_sweep() -> SweepConfig:
    """One-shot sweep config — asserts we don't wind through many steps."""
    return SweepConfig(
        theta_min_deg=0.0, theta_max_deg=0.0, step_deg=1.0, settle_seconds=0.0
    )


@pytest.mark.unit
class TestOrchestratorDispatch:
    def test_home_calls_motion_home_once(self, tight_sweep: SweepConfig) -> None:
        motion, vision, cal = FakeMotion(), FakeVision({}), FakeCalibration()
        orch = Orchestrator(
            motion=motion, vision=vision, calibration=cal, sweep=tight_sweep  # type: ignore[arg-type]
        )
        result = orch.execute(Command("home", None, None))
        assert result.ok is True
        assert result.message == "Home pose."
        assert [c[0] for c in motion.calls] == ["home"]
        assert vision.calls == []

    def test_unknown_does_no_motion(self, tight_sweep: SweepConfig) -> None:
        motion, vision, cal = FakeMotion(), FakeVision({}), FakeCalibration()
        orch = Orchestrator(
            motion=motion, vision=vision, calibration=cal, sweep=tight_sweep  # type: ignore[arg-type]
        )
        result = orch.execute(Command("unknown", None, None))
        assert result.ok is False
        assert motion.calls == []
        assert vision.calls == []

    def test_pick_and_place_happy_path(self, tight_sweep: SweepConfig) -> None:
        hits = {
            "red": Detection(color="red", pixel_xy=(100, 200), area_px=1000),
            "blue": Detection(color="blue", pixel_xy=(300, 400), area_px=1000),
        }
        motion, vision, cal = FakeMotion(), FakeVision(hits), FakeCalibration(in_reach=True)
        orch = Orchestrator(
            motion=motion, vision=vision, calibration=cal, sweep=tight_sweep  # type: ignore[arg-type]
        )
        result = orch.execute(Command("pick_and_place", "red", "blue"))

        assert result.ok is True
        assert result.message == "Task complete."
        sequence = [c[0] for c in motion.calls]
        # turntable_rotate is called once per color for sweep_and_detect.
        assert sequence == [
            "turntable_rotate",  # sweep for red
            "pick",
            "turntable_rotate",  # sweep for blue
            "place",
            "home",
        ]
        assert vision.calls == ["red", "blue"]
        assert len(cal.pixel_queries) == 2

    def test_target_not_found_returns_fail_no_pick(
        self, tight_sweep: SweepConfig
    ) -> None:
        motion, vision, cal = (
            FakeMotion(),
            FakeVision({"red": None, "blue": None}),
            FakeCalibration(),
        )
        orch = Orchestrator(
            motion=motion, vision=vision, calibration=cal, sweep=tight_sweep  # type: ignore[arg-type]
        )
        result = orch.execute(Command("pick_and_place", "red", "blue"))
        assert result.ok is False
        assert "red" in result.message
        assert "pick" not in [c[0] for c in motion.calls]

    def test_missing_colors_fail_fast(self, tight_sweep: SweepConfig) -> None:
        motion, vision, cal = FakeMotion(), FakeVision({}), FakeCalibration()
        orch = Orchestrator(
            motion=motion, vision=vision, calibration=cal, sweep=tight_sweep  # type: ignore[arg-type]
        )
        result = orch.execute(Command("pick_and_place", None, None))
        assert result.ok is False
        assert motion.calls == []
        assert vision.calls == []

    def test_out_of_reach_target_no_pick(self, tight_sweep: SweepConfig) -> None:
        hits = {"red": Detection(color="red", pixel_xy=(100, 200), area_px=1000)}
        motion, vision, cal = FakeMotion(), FakeVision(hits), FakeCalibration(in_reach=False)
        orch = Orchestrator(
            motion=motion, vision=vision, calibration=cal, sweep=tight_sweep  # type: ignore[arg-type]
        )
        result = orch.execute(Command("pick_and_place", "red", "blue"))
        assert result.ok is False
        assert "out of reach" in result.message
        assert "pick" not in [c[0] for c in motion.calls]

    def test_exception_in_motion_is_caught_and_released(
        self, tight_sweep: SweepConfig
    ) -> None:
        class Exploding(FakeMotion):
            def home(self) -> None:
                raise RuntimeError("servo stuck")

        motion = Exploding()
        orch = Orchestrator(
            motion=motion, vision=FakeVision({}), calibration=FakeCalibration(), sweep=tight_sweep  # type: ignore[arg-type]
        )
        result = orch.execute(Command("home", None, None))
        assert result.ok is False
        assert "servo stuck" in result.message
        # Orchestrator's safety net should have released PWM on any crash.
        assert ("release_all", ()) in motion.calls
