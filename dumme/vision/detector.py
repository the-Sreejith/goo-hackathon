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

        import cv2
        import numpy as np

        frame = self.camera.frame()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for r in self.colors[color]:
            lower = np.array([r["h_low"], r["s_low"], r["v_low"]], dtype=np.uint8)
            upper = np.array([r["h_high"], r["s_high"], r["v_high"]], dtype=np.uint8)
            mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lower, upper))

        k = int(self.morphology.get("kernel_size", 5))
        kernel = np.ones((k, k), dtype=np.uint8)
        mask = cv2.erode(mask, kernel, iterations=int(self.morphology.get("erode_iterations", 1)))
        mask = cv2.dilate(mask, kernel, iterations=int(self.morphology.get("dilate_iterations", 2)))

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        largest = max(contours, key=cv2.contourArea)
        area = int(cv2.contourArea(largest))
        if area < self.min_area:
            return None
        moments = cv2.moments(largest)
        if moments["m00"] == 0:
            return None
        cx = int(moments["m10"] / moments["m00"])
        cy = int(moments["m01"] / moments["m00"])
        return Detection(color=color, pixel_xy=(cx, cy), area_px=area)
