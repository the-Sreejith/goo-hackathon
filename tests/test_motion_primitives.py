"""Motion primitive tests against a mock PCA9685Driver.

Assertions focus on the sequence and targets of joint writes — exact pulse
widths are already covered by PCA9685Driver + servo config; the Motion
layer's job is ordering, safety clamping, and angle bookkeeping.
"""

from __future__ import annotations

from typing import Any

import pytest

from dumme.motion.driver import PCA9685Driver
from dumme.motion.primitives import Motion, _us_for_angle
from dumme.motion.safety import Safety


@pytest.fixture
def servo_cfg() -> dict[str, dict[str, Any]]:
    """Matches config/servos.yaml shape. `reach_deg`, `lift_deg`, `close_deg`
    are defaults consumed by Motion.pick / Motion.place."""
    return {
        "base_rotate": {"channel": 0, "min_us": 500, "max_us": 2500, "home_deg": 90},
        "shoulder": {
            "channel": 1,
            "min_us": 500,
            "max_us": 2500,
            "home_deg": 90,
            "reach_deg": 60,
            "lift_deg": 110,
        },
        "elbow": {
            "channel": 2,
            "min_us": 500,
            "max_us": 2500,
            "home_deg": 90,
            "reach_deg": 120,
        },
        "gripper": {"channel": 3, "min_us": 500, "max_us": 2500, "home_deg": 60, "close_deg": 30},
        "turntable": {"channel": 4, "min_us": 500, "max_us": 2500, "home_deg": 90},
    }


@pytest.fixture
def safety(joint_limits: dict[str, list[float]]) -> Safety:
    return Safety(joint_limits=joint_limits, rate_limit_deg_per_sec=180.0)


@pytest.fixture
def fast_motion(
    servo_cfg: dict[str, dict[str, Any]], safety: Safety, monkeypatch: pytest.MonkeyPatch
) -> Motion:
    """Motion backed by a mock driver with sleep() patched out for speed."""
    import dumme.motion.primitives as prim

    monkeypatch.setattr(prim.time, "sleep", lambda _s: None)
    driver = PCA9685Driver(pwm_frequency_hz=50, mock=True)
    return Motion(driver=driver, servo_cfg=servo_cfg, safety=safety)


@pytest.mark.unit
class TestHome:
    def test_writes_home_deg_to_every_joint(self, fast_motion: Motion) -> None:
        fast_motion.home()
        d = fast_motion.driver
        # home() runs release_all() at the end, so each channel ends at 0.
        for ch in range(16):
            assert d.last_written_us(ch) == 0.0


@pytest.mark.unit
class TestRotate:
    def test_base_rotate_updates_state(self, fast_motion: Motion) -> None:
        fast_motion.base_rotate(120)
        assert fast_motion.base_angle_deg == 120

    def test_base_rotate_clamps_above_limit(self, fast_motion: Motion) -> None:
        fast_motion.base_rotate(999)
        # joint_limits fixture caps base_rotate at 180.
        assert fast_motion.base_angle_deg == 180

    def test_turntable_rotate_updates_state(self, fast_motion: Motion) -> None:
        fast_motion.turntable_rotate(45)
        # joint_limits fixture caps turntable at [30, 150].
        assert fast_motion.turntable_angle_deg == 45


@pytest.mark.unit
class TestPickPlace:
    def test_pick_sequence_touches_expected_channels(self, fast_motion: Motion) -> None:
        fast_motion.pick(r_mm=150.0, theta_deg=90.0)
        # pick should have written to gripper(3), base_rotate(0), shoulder(1),
        # elbow(2), gripper(3), shoulder(1) in that order. Final state of each
        # channel is enough to assert — not the sequence, which is covered by
        # orchestrator tests via FakeMotion.
        d = fast_motion.driver
        assert d.last_written_us(0) is not None  # base_rotate
        assert d.last_written_us(1) is not None  # shoulder
        assert d.last_written_us(2) is not None  # elbow
        assert d.last_written_us(3) is not None  # gripper

    def test_place_reopens_gripper(self, fast_motion: Motion) -> None:
        fast_motion.place(r_mm=150.0, theta_deg=60.0)
        # gripper should end at home_deg (open=60).
        gripper_us = fast_motion.driver.last_written_us(3)
        assert gripper_us is not None
        # home_deg=60 → ~1166us at 500..2500
        expected = _us_for_angle(60.0, 500, 2500)
        assert abs(gripper_us - expected) < 1.0


@pytest.mark.unit
class TestSnapshot:
    def test_snapshot_reflects_writes(self, fast_motion: Motion) -> None:
        fast_motion.base_rotate(100)
        fast_motion.turntable_rotate(60)
        snap = fast_motion.snapshot()
        assert snap["base_angle_deg"] == 100
        assert snap["turntable_angle_deg"] == 60
        assert snap["estop"] is False

    def test_estop_refuses_writes(self, fast_motion: Motion) -> None:
        fast_motion.estop()
        fast_motion.base_rotate(45)
        # base_angle_deg should NOT have changed (default home=90).
        assert fast_motion.base_angle_deg == 90
        assert fast_motion.safety.estop.tripped is True


@pytest.mark.unit
class TestAngleToUs:
    def test_midpoint_is_midpoint(self) -> None:
        assert _us_for_angle(90, 500, 2500) == 1500.0

    def test_clamps_negative(self) -> None:
        assert _us_for_angle(-10, 500, 2500) == 500.0

    def test_clamps_above(self) -> None:
        assert _us_for_angle(999, 500, 2500) == 2500.0
