"""Canonical end-to-end demo: 'pick up the red block and put it in the blue cup'.

Runs the full pipeline once and prints the ExecutionResult. Used as the Phase A
exit gate — if this prints a result (even if it's `NotImplementedError`'d
for real hardware steps), the wiring is sound.

    python -m scripts.demo_run
"""

from __future__ import annotations

import sys

from dumme.calibration.regression import Calibration
from dumme.llm.client import LlamaClient
from dumme.llm.parser import LLM
from dumme.motion.driver import PCA9685Driver
from dumme.motion.primitives import Motion
from dumme.motion.safety import Safety
from dumme.orchestrator import Orchestrator
from dumme.utils.config import load_yaml
from dumme.utils.logging import get_logger
from dumme.vision.camera import Camera
from dumme.vision.detector import Vision

_log = get_logger("scripts.demo_run")

UTTERANCE = "pick up the red block and put it in the blue cup"


def main() -> int:
    servo_cfg = load_yaml("servos")
    vision_cfg = load_yaml("vision")
    calibration_cfg = load_yaml("calibration")

    # Force mock mode for this scripted demo — no real hardware assumption.
    driver = PCA9685Driver(pwm_frequency_hz=int(servo_cfg.get("pwm_frequency_hz", 50)), mock=True)
    safety = Safety(joint_limits=servo_cfg.get("joint_limits", {}))
    motion = Motion(driver=driver, servo_cfg=servo_cfg["servos"], safety=safety)

    camera = Camera(
        width=vision_cfg["camera"]["width"],
        height=vision_cfg["camera"]["height"],
        framerate=vision_cfg["camera"]["framerate"],
        mock=True,
    )
    vision = Vision(camera=camera, vision_cfg=vision_cfg)
    calibration = Calibration(raw=calibration_cfg)

    llm = LLM(client=LlamaClient())
    orchestrator = Orchestrator(motion=motion, vision=vision, calibration=calibration)

    _log.info("Utterance: %s", UTTERANCE)
    try:
        cmd = llm.parse(UTTERANCE)
    except NotImplementedError as exc:
        _log.warning("LLM.parse not implemented yet (%s). Using canned Command.", exc)
        from dumme.llm.schema import Command

        cmd = Command(action="pick_and_place", target_color="red", dest_color="blue")
    _log.info("Command: %s", cmd)
    result = orchestrator.execute(cmd)
    print(f"ok={result.ok}  message={result.message}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
