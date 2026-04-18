"""Offline speech-to-text via Vosk. STRETCH GOAL — only used if Phase D happens.

Requires a small Vosk model (vosk-model-small-en-us, ~40 MB) and a USB mic
(Pi 5 has no onboard audio-in).
"""

from __future__ import annotations

from pathlib import Path

from dumme.utils.logging import get_logger

_log = get_logger(__name__)


class Mic:
    """Push-to-talk style: `utterance = mic.listen(max_seconds=5)`."""

    def __init__(self, model_path: Path | str | None = None, sample_rate: int = 16000) -> None:
        self.model_path = Path(model_path) if model_path else None
        self.sample_rate = sample_rate

    def listen(self, max_seconds: float = 5.0) -> str:
        """Block up to max_seconds, return the best-guess transcript."""
        raise NotImplementedError(
            "TODO(stretch): vosk.Model(self.model_path); open pyaudio stream at "
            "self.sample_rate mono; feed recognizer chunks until silence or timeout; "
            "return recognizer.FinalResult()['text']."
        )
