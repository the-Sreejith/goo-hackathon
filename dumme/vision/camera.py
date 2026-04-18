"""picamera2 wrapper. Provides single-shot capture + MJPEG frame generator."""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np

from dumme.utils.logging import get_logger

_log = get_logger(__name__)

# MJPEG multipart boundary — used by FastAPI /stream to frame JPEG chunks.
MJPEG_BOUNDARY = "dumme-frame"


class Camera:
    """Thin abstraction over Picamera2. Mock mode returns solid-color frames."""

    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        framerate: int = 15,
        exposure_us: int | None = None,
        mock: bool = False,
    ) -> None:
        self.width = width
        self.height = height
        self.framerate = framerate
        self.exposure_us = exposure_us
        self.mock = mock
        self._cam = None  # Picamera2 instance, lazy-init

        if not mock:
            self._open()

    def _open(self) -> None:
        raise NotImplementedError(
            "TODO(P2): from picamera2 import Picamera2; create self._cam with "
            "main={'size': (self.width, self.height), 'format': 'RGB888'}; "
            "apply self.exposure_us if set; self._cam.start()."
        )

    def close(self) -> None:
        if self._cam is not None:
            try:
                self._cam.stop()
            except Exception as exc:
                _log.warning("camera stop failed: %s", exc)

    def frame(self) -> np.ndarray:
        """Capture one BGR frame as a numpy array (OpenCV convention)."""
        if self.mock:
            return np.full((self.height, self.width, 3), 64, dtype=np.uint8)
        raise NotImplementedError(
            "TODO(P2): arr = self._cam.capture_array('main'); "
            "return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)."
        )

    def mjpeg_frames(self) -> Iterator[bytes]:
        """Yield MJPEG multipart chunks for a FastAPI StreamingResponse."""
        raise NotImplementedError(
            "TODO(P2): loop self.frame(); cv2.imencode('.jpg', frame); yield "
            f"b'--{MJPEG_BOUNDARY}\\r\\nContent-Type: image/jpeg\\r\\n\\r\\n' + jpg + b'\\r\\n'. "
            "Sleep 1/self.framerate between iterations."
        )
