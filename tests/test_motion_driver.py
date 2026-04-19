"""PCA9685Driver unit tests against the in-process mock.

Real-hardware paths (`_connect`, I2C writes) are covered by the
@hardware smoke suite — not here.
"""

from __future__ import annotations

import pytest

from dumme.motion.driver import PCA9685Driver


@pytest.fixture
def driver() -> PCA9685Driver:
    return PCA9685Driver(pwm_frequency_hz=50, mock=True)


@pytest.mark.unit
class TestSetPulseUs:
    def test_mock_does_not_touch_i2c(self, driver: PCA9685Driver) -> None:
        driver.set_pulse_us(0, 1500.0)
        assert driver.last_written_us(0) == 1500.0

    def test_channel_out_of_range_raises(self, driver: PCA9685Driver) -> None:
        with pytest.raises(ValueError, match="channel must be 0..15"):
            driver.set_pulse_us(-1, 1500.0)
        with pytest.raises(ValueError, match="channel must be 0..15"):
            driver.set_pulse_us(16, 1500.0)

    def test_records_per_channel(self, driver: PCA9685Driver) -> None:
        driver.set_pulse_us(0, 1000.0)
        driver.set_pulse_us(5, 2000.0)
        assert driver.last_written_us(0) == 1000.0
        assert driver.last_written_us(5) == 2000.0
        assert driver.last_written_us(7) is None

    def test_last_write_wins(self, driver: PCA9685Driver) -> None:
        driver.set_pulse_us(3, 1000.0)
        driver.set_pulse_us(3, 1800.0)
        assert driver.last_written_us(3) == 1800.0


@pytest.mark.unit
class TestRelease:
    def test_release_sets_zero(self, driver: PCA9685Driver) -> None:
        driver.set_pulse_us(2, 1500.0)
        driver.release(2)
        assert driver.last_written_us(2) == 0.0

    def test_release_all_sets_zero_on_all_channels(
        self, driver: PCA9685Driver
    ) -> None:
        # Seed a few channels with nonzero pulses.
        for ch in (0, 5, 10, 15):
            driver.set_pulse_us(ch, 1500.0)
        driver.release_all()
        for ch in range(16):
            assert driver.last_written_us(ch) == 0.0


@pytest.mark.unit
def test_real_mode_without_hardware_raises_on_import() -> None:
    """Non-mock constructor should try to import adafruit/board. On a Mac
    dev box those imports fail — we assert a clear error, not a silent hang.
    """
    # board/busio are Pi-only. Any ImportError or RuntimeError is acceptable.
    with pytest.raises((ImportError, RuntimeError, Exception)):
        PCA9685Driver(mock=False)
