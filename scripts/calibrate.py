"""Interactive pixel → joint-angle calibration.

Capture 5+ samples: place a block at a known workspace position, jog the arm
to a good pick pose, confirm, and the script records (pixel_xy, joints). At
the end, fit an affine regression and write config/calibration.yaml.

Run on the Pi with the physical arm and camera:
    python -m scripts.calibrate
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import yaml

from dumme.calibration.regression import fit_affine
from dumme.utils.config import CONFIG_DIR
from dumme.utils.logging import get_logger

_log = get_logger("scripts.calibrate")

MIN_SAMPLES = 5
OUT_PATH: Path = CONFIG_DIR / "calibration.yaml"


def main() -> None:
    """Walk the user through 5+ captures, fit, write calibration.yaml."""
    raise NotImplementedError(
        "TODO(P3): implement interactive loop:\n"
        "  1. prompt user to place a block\n"
        "  2. open Camera, show preview, ask for (shoulder, elbow, radius_mm) reading\n"
        "  3. find block in frame via Vision.find(color)\n"
        "  4. append (pixel_xy, joints) sample\n"
        "  5. after MIN_SAMPLES, fit_affine for shoulder, elbow, radius_mm\n"
        "  6. write config/calibration.yaml with coefficients + timestamp\n"
        "Skeleton of step 5+6 is below — reuse fit_affine and yaml.safe_dump."
    )


def write_calibration(
    shoulder_coeffs: tuple[float, float, float],
    elbow_coeffs: tuple[float, float, float],
    radius_coeffs: tuple[float, float, float],
    captured_by: str = "calibrate.py",
) -> None:
    """Persist fitted coefficients to config/calibration.yaml."""
    existing = yaml.safe_load(OUT_PATH.read_text()) if OUT_PATH.is_file() else {}
    existing["affine"] = {
        "shoulder_deg": list(shoulder_coeffs),
        "elbow_deg": list(elbow_coeffs),
        "radius_mm": list(radius_coeffs),
    }
    existing["captured_at"] = dt.datetime.now(dt.UTC).isoformat()
    existing["captured_by"] = captured_by
    OUT_PATH.write_text(yaml.safe_dump(existing, sort_keys=False))
    _log.info("Wrote %s", OUT_PATH)


if __name__ == "__main__":
    main()


# Re-export fit_affine so `from scripts.calibrate import fit_affine` keeps working
# if anyone wires it up in tests.
__all__ = ["fit_affine", "write_calibration", "main"]
