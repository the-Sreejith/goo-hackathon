"""Capture a single frame to /tmp/preview.jpg for quick visual confirmation.

Run on the Pi:
    python -m scripts.camera_preview
    scp dumme@dumme.local:/tmp/preview.jpg .   # from MacBook
"""

from __future__ import annotations

from pathlib import Path

import cv2

from dumme.utils.config import load_yaml
from dumme.utils.logging import get_logger
from dumme.vision.camera import Camera

_log = get_logger("scripts.camera_preview")

OUT_PATH = Path("/tmp/preview.jpg")


def main() -> None:
    vision_cfg = load_yaml("vision")["camera"]
    cam = Camera(
        width=vision_cfg["width"],
        height=vision_cfg["height"],
        framerate=vision_cfg["framerate"],
        exposure_us=vision_cfg.get("exposure_us"),
    )
    try:
        frame = cam.frame()
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(OUT_PATH), frame)
        _log.info("Wrote %s (%dx%d)", OUT_PATH, frame.shape[1], frame.shape[0])
    finally:
        cam.close()


if __name__ == "__main__":
    main()
