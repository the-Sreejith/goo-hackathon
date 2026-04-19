"""High-level motion primitives. The only module the orchestrator talks to.

All joint writes funnel through Safety.clamp and honour Safety.estop.
After every multi-joint primitive, call release_all() to stop SG90 jitter.
"""

from __future__ import annotations

import time
from typing import Any

from dumme.motion.driver import PCA9685Driver
from dumme.motion.safety import Safety
from dumme.utils.logging import get_logger

_STEP_SLEEP_S = 0.15  # per-joint settle delay after a PWM write

_log = get_logger(__name__)


def _us_for_angle(
    angle_deg: float,
    min_us: float,
    max_us: float,
    angle_range_deg: float = 180.0,
) -> float:
    """Linear interpolate 0..angle_range_deg to min_us..max_us."""
    pct = max(0.0, min(1.0, angle_deg / angle_range_deg))
    return min_us + pct * (max_us - min_us)


class Motion:
    """Movement verbs exposed to the orchestrator.

    `servo_cfg` is the dict from config/servos.yaml -> "servos" section.
    """

    def __init__(
        self,
        driver: PCA9685Driver,
        servo_cfg: dict[str, dict[str, Any]],
        safety: Safety,
    ) -> None:
        self.driver = driver
        self.servo_cfg = servo_cfg
        self.safety = safety
        self.base_angle_deg: float = servo_cfg.get("base_rotate", {}).get("home_deg", 90.0)
        self.turntable_angle_deg: float = servo_cfg.get("turntable", {}).get("home_deg", 90.0)

    # ── low-level joint control ───────────────────────────────────────────
    def _write_joint(self, joint: str, angle_deg: float) -> None:
        if not self.safety.allowed():
            _log.warning("E-stop tripped; refusing write to %s", joint)
            return
        cfg = self.servo_cfg.get(joint)
        if cfg is None:
            raise KeyError(f"Unknown servo joint: {joint}")
        clamped = self.safety.clamp(joint, angle_deg)
        pulse_us = _us_for_angle(clamped, cfg["min_us"], cfg["max_us"])
        self.driver.set_pulse_us(cfg["channel"], pulse_us)
        if joint == "base_rotate":
            self.base_angle_deg = clamped
        elif joint == "turntable":
            self.turntable_angle_deg = clamped

    # ── primitives ────────────────────────────────────────────────────────
    def home(self) -> None:
        """Drive all joints to their configured home_deg, then release PWM."""
        for joint, cfg in self.servo_cfg.items():
            self._write_joint(joint, float(cfg["home_deg"]))
            time.sleep(_STEP_SLEEP_S)
        self.release_all()

    def base_rotate(self, angle_deg: float) -> None:
        """Rotate the base (J1) — the arm's shoulder pivot relative to the chassis."""
        self._write_joint("base_rotate", angle_deg)

    def turntable_rotate(self, angle_deg: float) -> None:
        """Rotate the whole chassis on its turntable (MG90S)."""
        self._write_joint("turntable", angle_deg)

    def pick(self, r_mm: float, theta_deg: float) -> None:
        """Reach toward theta, close gripper, lift.

        Calibration-free placeholder: base_rotate to theta, drop to a fixed reach
        pose (shoulder/elbow mid-range), close gripper, lift. `r_mm` is accepted
        for API parity but ignored until calibration regression lands.
        """
        gripper_open = self._home_of("gripper")
        gripper_close = float(self.servo_cfg["gripper"].get("close_deg", 30.0))
        reach_shoulder = float(self.servo_cfg["shoulder"].get("reach_deg", 60.0))
        reach_elbow = float(self.servo_cfg["elbow"].get("reach_deg", 120.0))
        lift_shoulder = float(self.servo_cfg["shoulder"].get("lift_deg", 110.0))

        self._write_joint("gripper", gripper_open); time.sleep(_STEP_SLEEP_S)
        self._write_joint("base_rotate", theta_deg); time.sleep(_STEP_SLEEP_S)
        self._write_joint("shoulder", reach_shoulder); time.sleep(_STEP_SLEEP_S)
        self._write_joint("elbow", reach_elbow); time.sleep(_STEP_SLEEP_S * 2)
        self._write_joint("gripper", gripper_close); time.sleep(_STEP_SLEEP_S * 2)
        self._write_joint("shoulder", lift_shoulder); time.sleep(_STEP_SLEEP_S)

    def place(self, r_mm: float, theta_deg: float) -> None:
        """Reach toward theta, open gripper, lift.

        Mirror of pick — calibration-free; r_mm accepted but ignored for now.
        """
        gripper_open = self._home_of("gripper")
        reach_shoulder = float(self.servo_cfg["shoulder"].get("reach_deg", 60.0))
        reach_elbow = float(self.servo_cfg["elbow"].get("reach_deg", 120.0))
        lift_shoulder = float(self.servo_cfg["shoulder"].get("lift_deg", 110.0))

        self._write_joint("base_rotate", theta_deg); time.sleep(_STEP_SLEEP_S)
        self._write_joint("shoulder", reach_shoulder); time.sleep(_STEP_SLEEP_S)
        self._write_joint("elbow", reach_elbow); time.sleep(_STEP_SLEEP_S * 2)
        self._write_joint("gripper", gripper_open); time.sleep(_STEP_SLEEP_S)
        self._write_joint("shoulder", lift_shoulder); time.sleep(_STEP_SLEEP_S)

    def _home_of(self, joint: str) -> float:
        return float(self.servo_cfg[joint]["home_deg"])

    def release_all(self) -> None:
        """Zero PWM on every channel. Call after rest poses to stop jitter."""
        self.driver.release_all()

    def estop(self) -> None:
        """Freeze — trip the e-stop flag AND cut PWM."""
        self.safety.estop.set()
        self.driver.release_all()
        _log.warning("E-STOP engaged")

    # ── introspection (used by /status) ───────────────────────────────────
    def snapshot(self) -> dict[str, float | bool]:
        return {
            "base_angle_deg": self.base_angle_deg,
            "turntable_angle_deg": self.turntable_angle_deg,
            "estop": self.safety.estop.tripped,
        }
