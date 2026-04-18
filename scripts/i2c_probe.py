"""Verify the PCA9685 is visible on I2C bus 1 at address 0x40.

Runs `i2cdetect -y 1` and checks for '40' in the output. Pi-only.
"""

from __future__ import annotations

import subprocess
import sys

from dumme.utils.logging import get_logger

_log = get_logger("scripts.i2c_probe")


def main() -> int:
    try:
        out = subprocess.check_output(["i2cdetect", "-y", "1"], text=True, timeout=5)
    except FileNotFoundError:
        _log.error("i2cdetect not installed. Run: sudo apt install -y i2c-tools")
        return 2
    except subprocess.CalledProcessError as exc:
        _log.error("i2cdetect failed: %s", exc)
        return exc.returncode
    except subprocess.TimeoutExpired:
        _log.error("i2cdetect timed out")
        return 3

    print(out)
    if " 40" in out:
        _log.info("PCA9685 detected at 0x40")
        return 0
    _log.error(
        "PCA9685 NOT detected. Check SDA=GPIO2, SCL=GPIO3, 3.3V VCC, common GND, "
        "and `sudo raspi-config nonint do_i2c 0` was run."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
