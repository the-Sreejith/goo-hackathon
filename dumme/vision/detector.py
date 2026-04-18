"""Color-blob detector. Returns the largest contour per query, or None.

HSV ranges live in config/vision.yaml. Red wraps around H=0, so each color
can have multiple ranges that get OR'd together.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dumme.utils.logging import get_logger
from dumme.vision.camera import Camera

_log = get_logger(__name__)


@dataclass(frozen=True)
class Detection:
    """A single color-blob hit returned by Vision.find."""

    color: str
    pixel_xy: tuple[int, int]
    area_px: int


class Vision:
    """Wraps a Camera and an HSV-range config."""

    def __init__(self, camera: Camera, vision_cfg: dict[str, Any]) -> None:
        self.camera = camera
        self.colors: dict[str, list[dict[str, int]]] = {
            name: spec["ranges"] for name, spec in vision_cfg.get("colors", {}).items()
        }
        self.min_area: int = int(vision_cfg.get("min_contour_area_px", 500))
        self.morphology: dict[str, int] = vision_cfg.get("morphology", {})

    def find(self, color: str) -> Detection | None:
        """Capture one frame, mask by HSV, return the largest-contour Detection."""
        if color not in self.colors:
            raise KeyError(f"Unknown color '{color}'. Configured: {sorted(self.colors)}")
        raise NotImplementedError(
            "TODO(P2): frame = self.camera.frame(); hsv = cv2.cvtColor(frame, "
            "cv2.COLOR_BGR2HSV); build combined mask by OR'ing every range in "
            "self.colors[color]; apply erode/dilate per self.morphology; "
            "cv2.findContours → reject if max-area < self.min_area; "
            "return Detection(color, cv2.moments centroid, area_px)."
        )
