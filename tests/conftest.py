"""Shared pytest fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def joint_limits() -> dict[str, list[float]]:
    return {
        "base_rotate": [0, 180],
        "shoulder": [30, 150],
        "elbow": [20, 160],
        "gripper": [25, 95],
        "turntable": [30, 150],
    }


@pytest.fixture
def sample_calibration_cfg() -> dict:
    return {
        "affine": {
            "shoulder_deg": [90.0, 0.0, 0.0],
            "elbow_deg": [90.0, 0.0, 0.0],
            "radius_mm": [120.0, 0.0, 0.0],
        },
        "turntable_gain_deg_per_deg": 1.0,
        "turntable_offset_deg": 0.0,
        "reach": {
            "r_min_mm": 50,
            "r_max_mm": 200,
            "theta_min_deg": -60,
            "theta_max_deg": 60,
        },
    }
