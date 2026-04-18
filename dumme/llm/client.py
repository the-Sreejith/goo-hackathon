"""HTTP client for a locally-running llama.cpp server.

Default launch (see PI_SETUP.md §6.4):
    llama-server -m models/gemma-4-e2b-it-Q4_K_M.gguf \\
        --ctx-size 2048 --n-predict 128 --threads 4 \\
        --host 127.0.0.1 --port 8080
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import requests

from dumme.utils.logging import get_logger

_log = get_logger(__name__)


@dataclass(frozen=True)
class CompletionRequest:
    prompt: str
    n_predict: int = 128
    temperature: float = 0.1
    stop: tuple[str, ...] = ()


class LlamaClient:
    """POSTs to the /completion endpoint of llama.cpp server. No streaming."""

    def __init__(self, base_url: str | None = None, timeout_s: float = 30.0) -> None:
        self.base_url = (base_url or os.environ.get("LLAMA_URL", "http://127.0.0.1:8080")).rstrip(
            "/"
        )
        self.timeout_s = timeout_s

    def complete(self, req: CompletionRequest) -> str:
        """Return the raw `content` string from the server. Caller parses it."""
        raise NotImplementedError(
            "TODO(P2): POST to f'{self.base_url}/completion' with "
            "{prompt, n_predict, temperature, stop}, return json['content']. "
            "Use requests.post(..., timeout=self.timeout_s)."
        )

    def healthy(self) -> bool:
        """Quick ping — used by /status to report LLM availability."""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=2.0)
            return resp.status_code == 200
        except requests.RequestException as exc:
            _log.debug("llama-server health check failed: %s", exc)
            return False
