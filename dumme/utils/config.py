"""YAML config loader and path helpers.

Resolution order for CONFIG_DIR:
    1. Env var DUMME_CONFIG_DIR
    2. <repo_root>/config
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT: Path = Path(__file__).resolve().parents[2]


def _resolve_config_dir() -> Path:
    env = os.environ.get("DUMME_CONFIG_DIR")
    if env:
        return Path(env).resolve()
    return REPO_ROOT / "config"


CONFIG_DIR: Path = _resolve_config_dir()


def load_yaml(name: str) -> dict[str, Any]:
    """Load a YAML file from CONFIG_DIR. `name` may include .yaml or not."""
    if not name.endswith((".yaml", ".yml")):
        name = f"{name}.yaml"
    path = CONFIG_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Config at {path} must be a mapping, got {type(data).__name__}")
    return data


def load_prompt(name: str) -> str:
    """Load a prompt template from CONFIG_DIR/prompts/<name>.txt."""
    if not name.endswith(".txt"):
        name = f"{name}.txt"
    path = CONFIG_DIR / "prompts" / name
    if not path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")
