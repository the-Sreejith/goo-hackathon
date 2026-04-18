"""Safety layer between Motion primitives and the PCA9685 driver.

Two independent responsibilities:
    1. Clamp joint angles to configured limits before any PWM write.
    2. Honour an E-stop flag — once set, every subsequent servo write is a no-op
       until explicitly cleared.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class JointLimitError(ValueError):
    joint: str
    requested: float
    clamped: float


def enforce_joint_limits(
    joint: str,
    angle_deg: float,
    limits: dict[str, tuple[float, float] | list[float]],
) -> float:
    """Clamp `angle_deg` into limits[joint]. Returns the clamped value.

    If the joint is not listed in `limits`, the value passes through unchanged.
    """
    bounds = limits.get(joint)
    if bounds is None:
        return float(angle_deg)
    lo, hi = float(bounds[0]), float(bounds[1])
    if lo > hi:
        raise ValueError(f"Invalid limits for {joint}: {bounds}")
    return max(lo, min(hi, float(angle_deg)))


class EstopFlag:
    """Thread-safe boolean. Tripping it makes every motion write a no-op."""

    def __init__(self, initial: bool = False) -> None:
        self._lock = threading.Lock()
        self._tripped = initial

    @property
    def tripped(self) -> bool:
        with self._lock:
            return self._tripped

    def set(self) -> None:
        with self._lock:
            self._tripped = True

    def clear(self) -> None:
        with self._lock:
            self._tripped = False


class Safety:
    """Bundles joint-limit config and the e-stop flag for injection into Motion."""

    def __init__(
        self,
        joint_limits: dict[str, tuple[float, float] | list[float]],
        estop: EstopFlag | None = None,
        rate_limit_deg_per_sec: float = 90.0,
    ) -> None:
        self.joint_limits = joint_limits
        self.estop = estop or EstopFlag()
        self.rate_limit_deg_per_sec = rate_limit_deg_per_sec

    def clamp(self, joint: str, angle_deg: float) -> float:
        return enforce_joint_limits(joint, angle_deg, self.joint_limits)

    def allowed(self) -> bool:
        """Return False when the e-stop is tripped — caller should refuse the write."""
        return not self.estop.tripped
