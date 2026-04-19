"""USB-webcam (UVC) capture via OpenCV V4L2. Single-shot + MJPEG generator.

The plan originally called for `picamera2` against a CSI ribbon camera; the
actual build uses a USB webcam surfaced at /dev/video0, so we drive it with
OpenCV's V4L2 backend.
"""

from __future__ import annotations

import time
from collections.abc import Iterator

import numpy as np

from dumme.utils.logging import get_logger

_log = get_logger(__name__)

MJPEG_BOUNDARY = "dumme-frame"


class Camera:
    """Thin abstraction over cv2.VideoCapture. Mock mode returns solid-color frames."""

    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        framerate: int = 15,
        exposure_us: int | None = None,
        device_index: int = 0,
        mock: bool = False,
    ) -> None:
        self.width = width
        self.height = height
        self.framerate = framerate
        self.exposure_us = exposure_us
        self.device_index = device_index
        self.mock = mock
        self._cam = None  # cv2.VideoCapture instance, lazy-init

        if not mock:
            self._open()

    def _open(self) -> None:
        import cv2

        cam = cv2.VideoCapture(self.device_index, cv2.CAP_V4L2)
        if not cam.isOpened():
            raise RuntimeError(f"cv2.VideoCapture({self.device_index}) failed to open")

        cam.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cam.set(cv2.CAP_PROP_FPS, self.framerate)
        if self.exposure_us is not None:
            cam.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # 1 = manual on V4L2
            cam.set(cv2.CAP_PROP_EXPOSURE, self.exposure_us)

        for _ in range(3):  # discard warm-up frames
            cam.read()

        self._cam = cam
        _log.info(
            "camera open /dev/video%d %dx%d@%dfps",
            self.device_index,
            self.width,
            self.height,
            self.framerate,
        )

    def close(self) -> None:
        if self._cam is not None:
            try:
                self._cam.release()
            except Exception as exc:
                _log.warning("camera release failed: %s", exc)
            self._cam = None

    def frame(self) -> np.ndarray:
        """Capture one BGR frame as a numpy array (OpenCV convention)."""
        if self.mock:
            return np.full((self.height, self.width, 3), 64, dtype=np.uint8)
        ok, frame = self._cam.read()
        if not ok or frame is None:
            raise RuntimeError("VideoCapture.read() returned no frame")
        return frame

    def mjpeg_frames(self) -> Iterator[bytes]:
        """Yield MJPEG multipart chunks for a FastAPI StreamingResponse."""
        import cv2

        period = 1.0 / max(self.framerate, 1)
        header = (
            b"--" + MJPEG_BOUNDARY.encode() + b"\r\n" + b"Content-Type: image/jpeg\r\n\r\n"
        )
        while True:
            frame = self.frame()
            ok, jpg = cv2.imencode(".jpg", frame)
            if not ok:
                continue
            yield header + jpg.tobytes() + b"\r\n"
            time.sleep(period)
