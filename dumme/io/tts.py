"""Text-to-speech via Piper (preferred) with espeak-ng fallback.

Piper gives natural voices if a .onnx model is present under `voice_path`.
Otherwise we fall back to `espeak-ng` (pre-installed on Pi OS Bookworm) so
TTS still works without any asset downloads. Both paths are fire-and-forget —
TTS is cosmetic and must never crash the pipeline.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from dumme.utils.logging import get_logger

_log = get_logger(__name__)


class TTS:
    """Simple facade: `tts.say('Found the red block.')`."""

    def __init__(self, voice_path: Path | str | None = None, enabled: bool = True) -> None:
        self.voice_path = Path(voice_path) if voice_path else None
        self.enabled = enabled
        self._backend = self._choose_backend()
        _log.info("TTS backend=%s voice=%s", self._backend, self.voice_path)

    def _choose_backend(self) -> str:
        if self.voice_path and self.voice_path.is_file() and shutil.which("piper"):
            return "piper"
        if shutil.which("espeak-ng"):
            return "espeak-ng"
        if shutil.which("espeak"):
            return "espeak"
        return "none"

    def say(self, text: str) -> None:
        """Synthesize `text` and play through the default audio sink."""
        if not self.enabled or not text:
            _log.debug("[tts-off] %s", text)
            return
        try:
            if self._backend == "piper":
                self._say_piper(text)
            elif self._backend in ("espeak-ng", "espeak"):
                self._say_espeak(text)
            else:
                _log.info("[tts-nobackend] %s", text)
        except Exception as exc:  # TTS is cosmetic — never propagate
            _log.warning("TTS failed (backend=%s): %s", self._backend, exc)

    def _say_piper(self, text: str) -> None:
        # piper --model voice.onnx --output_raw | aplay -r 22050 -f S16_LE -t raw -
        piper = subprocess.Popen(
            ["piper", "--model", str(self.voice_path), "--output_raw"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        aplay = subprocess.Popen(
            ["aplay", "-q", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-"],
            stdin=piper.stdout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        assert piper.stdin is not None
        piper.stdin.write(text.encode("utf-8"))
        piper.stdin.close()
        aplay.wait(timeout=10)
        piper.wait(timeout=10)

    def _say_espeak(self, text: str) -> None:
        subprocess.run(
            [self._backend, "--", text],
            check=False,
            timeout=10,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
