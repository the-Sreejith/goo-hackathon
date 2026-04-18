"""Thin wrapper over adafruit_pca9685 that exposes a per-channel microsecond API.

On non-Pi platforms (MacBook dev), the adafruit + busio imports will fail.
We defer them to __init__ so `import dumme.motion.driver` still works for
signature introspection, tests, and linting.
"""

from __future__ import annotations

from dumme.utils.logging import get_logger

_log = get_logger(__name__)


class PCA9685Driver:
    """Translate `(channel, pulse_us)` into 12-bit duty cycle writes on the PCA9685."""

    def __init__(
        self,
        pwm_frequency_hz: int = 50,
        i2c_address: int = 0x40,
        mock: bool = False,
    ) -> None:
        """If `mock=True`, stores writes in a dict for introspection — no I2C I/O."""
        self.pwm_frequency_hz = pwm_frequency_hz
        self.i2c_address = i2c_address
        self.mock = mock
        self._last_us: dict[int, float] = {}
        self._pca = None  # filled in by _connect() on real hardware

        if not mock:
            self._connect()

    def _connect(self) -> None:
        """Lazy-import adafruit so this module loads on non-Pi dev boxes."""
        raise NotImplementedError(
            "TODO(P3): import board, busio, adafruit_pca9685; "
            "instantiate PCA9685 at self.i2c_address; "
            "set self._pca.frequency = self.pwm_frequency_hz."
        )

    def set_pulse_us(self, channel: int, pulse_us: float) -> None:
        """Write a pulse width in microseconds to `channel` (0-15)."""
        self._last_us[channel] = pulse_us
        if self.mock:
            _log.debug("mock PCA9685 ch=%d pulse_us=%.1f", channel, pulse_us)
            return
        raise NotImplementedError(
            "TODO(P3): convert pulse_us → 12-bit duty at self.pwm_frequency_hz, "
            "write to self._pca.channels[channel].duty_cycle."
        )

    def release(self, channel: int) -> None:
        """Zero PWM on `channel` — stops SG90 jitter at rest."""
        self.set_pulse_us(channel, 0.0)

    def release_all(self) -> None:
        for ch in range(16):
            self.release(ch)

    def last_written_us(self, channel: int) -> float | None:
        return self._last_us.get(channel)
