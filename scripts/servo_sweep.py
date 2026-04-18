"""Sweep each servo from min → max → home to confirm wiring and travel range.

Run on the Pi, with servo power connected:
    python -m scripts.servo_sweep
"""

from __future__ import annotations

import time

from dumme.motion.driver import PCA9685Driver
from dumme.motion.safety import Safety
from dumme.utils.config import load_yaml
from dumme.utils.logging import get_logger

_log = get_logger("scripts.servo_sweep")


def main() -> None:
    cfg = load_yaml("servos")
    driver = PCA9685Driver(pwm_frequency_hz=int(cfg.get("pwm_frequency_hz", 50)))
    Safety(joint_limits=cfg.get("joint_limits", {}))

    for name, spec in cfg["servos"].items():
        _log.info("Sweeping %s on channel %d", name, spec["channel"])
        for us in (spec["min_us"], spec["max_us"], spec["min_us"]):
            driver.set_pulse_us(spec["channel"], us)
            time.sleep(0.8)
        # Home and release.
        home_us = spec["min_us"] + (spec["max_us"] - spec["min_us"]) * (spec["home_deg"] / 180.0)
        driver.set_pulse_us(spec["channel"], home_us)
        time.sleep(0.4)
        driver.release(spec["channel"])
        _log.info("  %s home+release", name)

    _log.info("Sweep done.")


if __name__ == "__main__":
    main()
