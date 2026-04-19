"""Hardware smoke — requires a Pi with camera, PCA9685, and llama-server.

Each test skips cleanly if its prerequisite is missing, so `pytest -m
hardware` on a dev box reports useful skips instead of errors.

Run:
    pytest -m hardware
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _has_i2c_bus() -> bool:
    return Path("/dev/i2c-1").exists()


def _has_v4l_camera() -> bool:
    return Path("/dev/video0").exists()


@pytest.mark.hardware
def test_pca9685_on_i2c_bus_1() -> None:
    """0x40 should ACK on the primary I2C bus."""
    if not _has_i2c_bus():
        pytest.skip("/dev/i2c-1 not present — not running on a Pi")
    try:
        import smbus2
    except ImportError:
        pytest.skip("smbus2 not installed")

    bus = smbus2.SMBus(1)
    try:
        # Read the MODE1 register (0x00). Any non-exception response = present.
        bus.read_byte_data(0x40, 0x00)
    except OSError as exc:
        pytest.fail(f"PCA9685 at 0x40 did not ACK: {exc}")
    finally:
        bus.close()


@pytest.mark.hardware
def test_camera_captures_a_frame() -> None:
    """VideoCapture(0) should return a non-uniform frame (variance > 0)."""
    if not _has_v4l_camera():
        pytest.skip("/dev/video0 not present — USB camera not connected")

    import cv2
    import numpy as np

    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    try:
        assert cap.isOpened(), "cv2.VideoCapture(0) failed to open"
        # Discard warm-up frames (common UVC behavior).
        for _ in range(3):
            cap.read()
        ok, frame = cap.read()
        assert ok and frame is not None, "no frame returned"
        assert float(np.var(frame)) > 0.0, "frame is uniform — sensor covered?"
    finally:
        cap.release()


@pytest.mark.hardware
def test_llama_server_health() -> None:
    """Health endpoint on the Pi-local llama-server."""
    from dumme.llm.client import LlamaClient

    client = LlamaClient()
    if not client.healthy():
        pytest.skip(f"llama-server not reachable at {client.base_url}")


@pytest.mark.hardware
def test_llama_server_roundtrip() -> None:
    """End-to-end: utterance → non-empty completion."""
    from dumme.llm.client import CompletionRequest, LlamaClient

    client = LlamaClient()
    if not client.healthy():
        pytest.skip(f"llama-server not reachable at {client.base_url}")
    out = client.complete(
        CompletionRequest(prompt="Return the single word OK.", n_predict=10)
    )
    assert isinstance(out, str)
    assert len(out) > 0
