"""Safety: joint-limit clamping + e-stop flag behaviour."""

from __future__ import annotations

import pytest

from dumme.motion.safety import EstopFlag, Safety, enforce_joint_limits


@pytest.mark.unit
class TestEnforceJointLimits:
    def test_clamps_above(self, joint_limits: dict) -> None:
        assert enforce_joint_limits("shoulder", 200.0, joint_limits) == 150.0

    def test_clamps_below(self, joint_limits: dict) -> None:
        assert enforce_joint_limits("shoulder", -10.0, joint_limits) == 30.0

    def test_passes_through_in_range(self, joint_limits: dict) -> None:
        assert enforce_joint_limits("elbow", 90.0, joint_limits) == 90.0

    def test_unknown_joint_passthrough(self, joint_limits: dict) -> None:
        # Safety shouldn't invent constraints for joints it doesn't know about.
        assert enforce_joint_limits("mystery", 999.0, joint_limits) == 999.0

    def test_invalid_limits_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid limits"):
            enforce_joint_limits("x", 0.0, {"x": (100, 10)})


@pytest.mark.unit
class TestEstopFlag:
    def test_default_not_tripped(self) -> None:
        assert EstopFlag().tripped is False

    def test_set_trips_flag(self) -> None:
        flag = EstopFlag()
        flag.set()
        assert flag.tripped is True

    def test_clear_untrips_flag(self) -> None:
        flag = EstopFlag(initial=True)
        assert flag.tripped is True
        flag.clear()
        assert flag.tripped is False


@pytest.mark.unit
class TestSafetyFacade:
    def test_allowed_when_not_tripped(self, joint_limits: dict) -> None:
        safety = Safety(joint_limits=joint_limits)
        assert safety.allowed() is True

    def test_not_allowed_when_tripped(self, joint_limits: dict) -> None:
        safety = Safety(joint_limits=joint_limits)
        safety.estop.set()
        assert safety.allowed() is False

    def test_clamp_delegates(self, joint_limits: dict) -> None:
        safety = Safety(joint_limits=joint_limits)
        assert safety.clamp("shoulder", 999.0) == 150.0
