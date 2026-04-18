"""Text-to-speech via Piper. Offline, runs fine on the Pi 5.

Needs a Piper voice model. A small English voice (~20 MB) lives under
models/piper/ (gitignored, downloaded during Pi setup).
"""

from __future__ import annotations

from pathlib import Path

from dumme.utils.logging import get_logger

_log = get_logger(__name__)


class TTS:
    """Simple facade: `tts.say('Found the red block.')`."""

    def __init__(self, voice_path: Path | str | None = None, enabled: bool = True) -> None:
        self.voice_path = Path(voice_path) if voice_path else None
        self.enabled = enabled

    def say(self, text: str) -> None:
        """Synthesize `text` and play it through the default audio sink."""
        if not self.enabled:
            _log.info("[tts-disabled] %s", text)
            return
        raise NotImplementedError(
            "TODO(P2): run piper CLI or bindings with self.voice_path; "
            "pipe wav to aplay (ALSA) on the Pi. Swallow errors — TTS is cosmetic."
        )
