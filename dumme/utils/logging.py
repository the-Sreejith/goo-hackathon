"""Structured logger. Thin wrapper over stdlib logging — respects LOG_LEVEL env."""

from __future__ import annotations

import logging
import os
import sys

_CONFIGURED = False


def _configure_root() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-5s %(name)s :: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger. Safe to call repeatedly."""
    _configure_root()
    return logging.getLogger(name)
