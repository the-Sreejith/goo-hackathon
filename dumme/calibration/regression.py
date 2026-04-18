"""Pixel → arm-pose regression.

We skip true inverse kinematics. Instead, we capture 5+ `(pixel_xy, joints)`
samples, fit an affine map `output = a0 + a1*px + a2*py`, and interpolate.
Good enough for a flat workspace at a fixed camera height.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

Coeffs = tuple[float, float, float]  # (a0, a1, a2)


def fit_affine(
    pixels: list[tuple[float, float]],
    values: list[float],
) -> Coeffs:
    """Least-squares fit value = a0 + a1*px + a2*py.

    Needs at least 3 non-collinear samples. More is better.
    """
    if len(pixels) != len(values):
        raise ValueError(f"pixels ({len(pixels)}) and values ({len(values)}) length mismatch")
    if len(pixels) < 3:
        raise ValueError("fit_affine needs at least 3 samples")
    x = np.asarray([[1.0, px, py] for px, py in pixels], dtype=float)
    y = np.asarray(values, dtype=float)
    coeffs, *_ = np.linalg.lstsq(x, y, rcond=None)
    return (float(coeffs[0]), float(coeffs[1]), float(coeffs[2]))


def _apply_affine(coeffs: Coeffs, pixel_xy: tuple[float, float]) -> float:
    a0, a1, a2 = coeffs
    px, py = pixel_xy
    return a0 + a1 * px + a2 * py


def pixel_to_polar(
    pixel_xy: tuple[int, int],
    turntable_angle_deg: float,
    calibration_cfg: dict[str, Any],
) -> tuple[float, float]:
    """Convert a camera pixel into absolute (r_mm, theta_deg) in chassis coords.

    Uses the affine fits from calibration_cfg['affine']['radius_mm'] (r) and a
    constant turntable offset/gain.
    """
    affine = calibration_cfg.get("affine", {})
    radius_coeffs = tuple(affine.get("radius_mm", (0.0, 0.0, 0.0)))
    if len(radius_coeffs) != 3:
        raise ValueError("calibration.affine.radius_mm must have 3 coefficients")
    r_mm = _apply_affine(radius_coeffs, pixel_xy)

    # theta — assume pixel_x is linear in angle relative to chassis center.
    # For the scaffold, use the same affine on pixel_x to produce a theta.
    shoulder_coeffs = tuple(affine.get("shoulder_deg", (0.0, 0.0, 0.0)))
    pixel_theta = _apply_affine(shoulder_coeffs, pixel_xy)

    gain = float(calibration_cfg.get("turntable_gain_deg_per_deg", 1.0))
    offset = float(calibration_cfg.get("turntable_offset_deg", 0.0))
    absolute_theta = pixel_theta + turntable_angle_deg * gain + offset
    return (float(r_mm), float(absolute_theta))


@dataclass
class Calibration:
    """Bundle of regression coefficients + reach envelope. Loaded from YAML."""

    raw: dict[str, Any]

    def in_reach(self, r_mm: float, theta_deg: float) -> bool:
        reach = self.raw.get("reach", {})
        r_ok = float(reach.get("r_min_mm", 0)) <= r_mm <= float(reach.get("r_max_mm", 1e9))
        t_ok = (
            float(reach.get("theta_min_deg", -180))
            <= theta_deg
            <= float(reach.get("theta_max_deg", 180))
        )
        return r_ok and t_ok

    def pixel_to_polar(
        self, pixel_xy: tuple[int, int], turntable_angle_deg: float
    ) -> tuple[float, float]:
        return pixel_to_polar(pixel_xy, turntable_angle_deg, self.raw)
