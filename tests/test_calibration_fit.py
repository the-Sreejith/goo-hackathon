"""Regression math — synthetic pixel → value samples, recover coefficients."""

from __future__ import annotations

import pytest

from dumme.calibration.regression import Calibration, fit_affine, pixel_to_polar


@pytest.mark.unit
class TestFitAffine:
    def test_recovers_planted_coefficients(self) -> None:
        # truth: value = 10 + 0.5*x - 0.25*y
        pixels = [(0.0, 0.0), (100.0, 0.0), (0.0, 100.0), (100.0, 100.0), (50.0, 50.0)]
        values = [10.0, 60.0, -15.0, 35.0, 22.5]
        a0, a1, a2 = fit_affine(pixels, values)
        assert a0 == pytest.approx(10.0, abs=1e-6)
        assert a1 == pytest.approx(0.5, abs=1e-6)
        assert a2 == pytest.approx(-0.25, abs=1e-6)

    def test_rejects_mismatched_lengths(self) -> None:
        with pytest.raises(ValueError, match="length mismatch"):
            fit_affine([(0.0, 0.0)], [1.0, 2.0])

    def test_rejects_too_few_samples(self) -> None:
        with pytest.raises(ValueError, match="at least 3"):
            fit_affine([(0.0, 0.0), (1.0, 1.0)], [1.0, 2.0])


@pytest.mark.unit
class TestPixelToPolar:
    def test_constant_fit_returns_constant(self, sample_calibration_cfg: dict) -> None:
        r, theta = pixel_to_polar((100, 100), 0.0, sample_calibration_cfg)
        assert r == pytest.approx(120.0)
        assert theta == pytest.approx(90.0)

    def test_turntable_offset_added_to_theta(self, sample_calibration_cfg: dict) -> None:
        _r, theta = pixel_to_polar((0, 0), 30.0, sample_calibration_cfg)
        # shoulder_coeffs=(90, 0, 0) → pixel_theta=90; gain=1 offset=0 turntable=30 → 120.
        assert theta == pytest.approx(120.0)


@pytest.mark.unit
class TestCalibrationReach:
    def test_in_reach_true(self, sample_calibration_cfg: dict) -> None:
        cal = Calibration(raw=sample_calibration_cfg)
        assert cal.in_reach(120.0, 0.0) is True

    def test_out_of_reach_radius(self, sample_calibration_cfg: dict) -> None:
        cal = Calibration(raw=sample_calibration_cfg)
        assert cal.in_reach(400.0, 0.0) is False

    def test_out_of_reach_theta(self, sample_calibration_cfg: dict) -> None:
        cal = Calibration(raw=sample_calibration_cfg)
        assert cal.in_reach(120.0, 90.0) is False
