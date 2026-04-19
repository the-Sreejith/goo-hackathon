"""Offline speech-to-text via Vosk + sounddevice.

Usage:
    mic = Mic(model_path="models/vosk-model-small-en-us")
    transcript = mic.listen(max_seconds=5.0)  # blocks, returns best-guess text

Behaviour:
    * Mock mode (no mic / dev box) returns `DUMME_MOCK_UTTERANCE` (env) or "".
    * Real mode opens a 16 kHz mono int16 stream and feeds Vosk's
      KaldiRecognizer. We early-exit when Vosk reports a full utterance
      (silence-bounded), else stop at `max_seconds`.
    * Missing model or missing audio device is a non-fatal RuntimeError —
      the /listen route surfaces it as ok=False so the UI can recover.

Assets:
    Download `vosk-model-small-en-us-0.15` (~40 MB) from
    https://alphacephei.com/vosk/models and unpack into `models/`.
"""

from __future__ import annotations

import json
import os
import queue
import time
from pathlib import Path

from dumme.utils.logging import get_logger

_log = get_logger(__name__)

_VOSK_SAMPLE_RATE = 16000
_VOSK_BLOCK_SIZE = 4000  # ~0.25s at 16 kHz — smooth recogniser feed
_MODEL_MISSING_MSG = (
    "Vosk model not found at {path}. Download vosk-model-small-en-us-0.15 "
    "from https://alphacephei.com/vosk/models and unpack it there."
)


class Mic:
    """Push-to-talk style speech-to-text. `transcript = mic.listen()`."""

    def __init__(
        self,
        model_path: Path | str | None = None,
        sample_rate: int = _VOSK_SAMPLE_RATE,
        mock: bool = False,
    ) -> None:
        self.model_path = Path(model_path) if model_path else None
        self.sample_rate = sample_rate
        self.mock = mock
        self._model = None  # lazy-load on first listen() — startup stays fast

        if self.mock:
            _log.info("Mic: mock mode (no audio capture)")
        elif self.model_path is None or not self.model_path.is_dir():
            _log.warning(
                "Mic: vosk model path %s not found — /listen will return ok=False",
                self.model_path,
            )

    @property
    def available(self) -> bool:
        """True iff a real listen() call would have a chance of succeeding."""
        if self.mock:
            return True
        return self.model_path is not None and self.model_path.is_dir()

    def listen(self, max_seconds: float = 5.0) -> str:
        """Block up to `max_seconds`, return the best-guess transcript.

        Raises RuntimeError if the model or audio device is unavailable.
        """
        if self.mock:
            utterance = os.environ.get("DUMME_MOCK_UTTERANCE", "").strip()
            _log.info("Mic(mock).listen -> %r", utterance)
            return utterance

        if self.model_path is None or not self.model_path.is_dir():
            raise RuntimeError(_MODEL_MISSING_MSG.format(path=self.model_path))

        self._ensure_model_loaded()
        return self._record_and_recognize(max_seconds=max_seconds)

    def _ensure_model_loaded(self) -> None:
        if self._model is not None:
            return
        try:
            import vosk  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("vosk package not installed — `pip install vosk`") from exc

        vosk.SetLogLevel(-1)  # silence Kaldi's stderr firehose
        _log.info("Mic: loading vosk model from %s", self.model_path)
        self._model = vosk.Model(str(self.model_path))

    def _record_and_recognize(self, max_seconds: float) -> str:
        import vosk  # type: ignore[import-not-found]

        try:
            import sounddevice as sd  # type: ignore[import-not-found]
        except (ImportError, OSError) as exc:
            raise RuntimeError(
                "sounddevice unavailable — `pip install sounddevice` and "
                "ensure PortAudio (libportaudio2) is installed"
            ) from exc

        recognizer = vosk.KaldiRecognizer(self._model, self.sample_rate)
        recognizer.SetWords(False)

        audio_q: queue.Queue[bytes] = queue.Queue()

        def _callback(indata, frames, time_info, status) -> None:  # noqa: ANN001 — sounddevice API
            if status:
                _log.debug("sounddevice status: %s", status)
            audio_q.put(bytes(indata))

        deadline = time.monotonic() + max_seconds
        final_text: str | None = None

        try:
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=_VOSK_BLOCK_SIZE,
                dtype="int16",
                channels=1,
                callback=_callback,
            ):
                _log.info("Mic: listening (max %.1fs)", max_seconds)
                while time.monotonic() < deadline:
                    try:
                        chunk = audio_q.get(timeout=0.2)
                    except queue.Empty:
                        continue
                    if recognizer.AcceptWaveform(chunk):
                        phrase = _extract_text(recognizer.Result())
                        if phrase:
                            final_text = phrase
                            break  # silence-bounded utterance — done
        except Exception as exc:
            raise RuntimeError(f"audio capture failed: {exc}") from exc

        if final_text is None:
            final_text = _extract_text(recognizer.FinalResult())

        transcript = final_text.strip()
        _log.info("Mic: transcript=%r", transcript)
        return transcript


def _extract_text(result_json: str) -> str:
    """Pull the 'text' field out of a Vosk result JSON blob; tolerate garbage."""
    try:
        data = json.loads(result_json)
    except (ValueError, TypeError):
        return ""
    text = data.get("text")
    return text if isinstance(text, str) else ""
