"""Vision.find smoke tests with synthetic BGR frames.

We don't need a real camera — a numpy array with a painted rectangle is
enough to exercise the full HSV → mask → morphology → contour pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pytest

from dumme.vision.detector import Detection, Vision

# Matches config/vision.yaml shape; kept inline to avoid coupling to yaml loader.
_VISION_CFG: dict[str, Any] = {
    "colors": {
        "red": {
            "ranges": [
                {"h_low": 0, "s_low": 120, "v_low": 70, "h_high": 10, "s_high": 255, "v_high": 255},
                {"h_low": 170, "s_low": 120, "v_low": 70, "h_high": 179, "s_high": 255, "v_high": 255},
            ]
        },
        "blue": {
            "ranges": [
                {"h_low": 100, "s_low": 120, "v_low": 70, "h_high": 130, "s_high": 255, "v_high": 255}
            ]
        },
        "green": {
            "ranges": [
                {"h_low": 40, "s_low": 70, "v_low": 50, "h_high": 80, "s_high": 255, "v_high": 255}
            ]
        },
    },
    "morphology": {"kernel_size": 5, "erode_iterations": 1, "dilate_iterations": 2},
    "min_contour_area_px": 500,
}


@dataclass
class StubCamera:
    """Returns a fixed frame. Signature-compatible with Camera.frame()."""

    _frame: np.ndarray

    def frame(self) -> np.ndarray:
        return self._frame


def _bgr_frame_with_rect(
    width: int,
    height: int,
    color_bgr: tuple[int, int, int],
    rect: tuple[int, int, int, int],
) -> np.ndarray:
    """Black frame with a filled rectangle in `color_bgr` at (x, y, w, h)."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    x, y, w, h = rect
    frame[y : y + h, x : x + w] = color_bgr
    return frame


@pytest.mark.unit
class TestVisionFind:
    def test_finds_blue_rectangle(self) -> None:
        x, y, w, h = 200, 150, 100, 80
        frame = _bgr_frame_with_rect(640, 480, (255, 0, 0), (x, y, w, h))  # BGR blue
        vision = Vision(camera=StubCamera(frame), vision_cfg=_VISION_CFG)  # type: ignore[arg-type]

        hit = vision.find("blue")
        assert isinstance(hit, Detection)
        assert hit.color == "blue"
        # Centroid within the rectangle bounds.
        cx, cy = hit.pixel_xy
        assert x <= cx <= x + w
        assert y <= cy <= y + h
        # Area within ±15% of the painted rect (morphology can erode a few px).
        expected = w * h
        assert 0.85 * expected <= hit.area_px <= 1.15 * expected

    def test_finds_green_rectangle(self) -> None:
        frame = _bgr_frame_with_rect(640, 480, (0, 255, 0), (50, 50, 120, 90))  # BGR green
        vision = Vision(camera=StubCamera(frame), vision_cfg=_VISION_CFG)  # type: ignore[arg-type]
        hit = vision.find("green")
        assert hit is not None and hit.color == "green"

    def test_red_handles_hue_wrap(self) -> None:
        """Pure red in BGR → H=0 in HSV, which only matches the 0..10 range,
        not the 170..179 range. The OR of both ranges must still produce a hit."""
        frame = _bgr_frame_with_rect(640, 480, (0, 0, 255), (300, 200, 100, 100))
        vision = Vision(camera=StubCamera(frame), vision_cfg=_VISION_CFG)  # type: ignore[arg-type]
        hit = vision.find("red")
        assert hit is not None and hit.color == "red"

    def test_blank_frame_returns_none(self) -> None:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        vision = Vision(camera=StubCamera(frame), vision_cfg=_VISION_CFG)  # type: ignore[arg-type]
        assert vision.find("red") is None

    def test_tiny_blob_below_min_area_is_none(self) -> None:
        # 10x10 = 100px blob, min_area=500.
        frame = _bgr_frame_with_rect(640, 480, (255, 0, 0), (100, 100, 10, 10))
        vision = Vision(camera=StubCamera(frame), vision_cfg=_VISION_CFG)  # type: ignore[arg-type]
        assert vision.find("blue") is None

    def test_unknown_color_raises(self) -> None:
        vision = Vision(camera=StubCamera(np.zeros((480, 640, 3), dtype=np.uint8)), vision_cfg=_VISION_CFG)  # type: ignore[arg-type]
        with pytest.raises(KeyError, match="Unknown color"):
            vision.find("purple")

    def test_largest_contour_wins(self) -> None:
        """Two blue rectangles of different sizes → returns the larger one."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[50:70, 50:70] = (255, 0, 0)  # 20x20 = 400px (under min_area)
        frame[200:300, 200:400] = (255, 0, 0)  # 100x200 = 20000px
        vision = Vision(camera=StubCamera(frame), vision_cfg=_VISION_CFG)  # type: ignore[arg-type]
        hit = vision.find("blue")
        assert hit is not None
        # Centroid should be inside the bigger rectangle.
        cx, cy = hit.pixel_xy
        assert 200 <= cx <= 400 and 200 <= cy <= 300
