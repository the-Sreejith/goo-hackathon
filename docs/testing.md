# DummE — Testing, Verification, Evaluation

The test suite is sliced into **four tiers**, each with a pytest marker. The
default `pytest` run hits **unit + integration** only; `eval` and `hardware`
tiers are opt-in so a MacBook dev box stays green without a Gemma server
or a Pi attached.

| Marker | Runs by default? | What it needs |
|---|---|---|
| `unit` | yes | Nothing. Fully hermetic. |
| `integration` | yes | Nothing — FastAPI `TestClient` with a stubbed LLM. |
| `eval` | no | A reachable `llama-server` (defaults to `http://127.0.0.1:8080`). |
| `hardware` | no | A Pi with `/dev/i2c-1`, `/dev/video0`, and a live `llama-server`. |

Config lives in `pyproject.toml` under `[tool.pytest.ini_options]`:

```toml
markers = [
    "unit: fast isolated tests",
    "integration: require external services",
    "eval: hits the live llama-server; slow",
    "hardware: requires Pi + I2C + camera",
]
addopts = "-ra --strict-markers -m 'not eval and not hardware'"
```

## Running the suite

```bash
# Default: unit + integration.
pytest
make test

# Opt-in tiers.
pytest -m eval                       # LLM utterance parsing eval
pytest -m hardware                   # on the Pi only
pytest -m "unit or integration or eval or hardware"   # everything
make test-all

# Coverage (80% floor on `dumme/`, configured in pyproject).
pytest --cov=dumme --cov-report=term-missing
make coverage
```

## Tier 1 — unit tests

| File | Covers |
|---|---|
| `tests/test_calibration_fit.py` | Affine least-squares fit, pixel→polar, reach envelope |
| `tests/test_safety_limits.py` | Joint-limit clamp, `EstopFlag` thread-safety, `Safety.allowed` |
| `tests/test_llm_parser.py` | JSON extraction, `Command` coercion, `LLM.parse` retry/fallback |
| `tests/test_llm_client.py` | `LlamaClient.complete` POST shape, `healthy()` 200/500/refused |
| `tests/test_vision_detector.py` | Synthetic BGR frames, HSV hue-wrap (red), area threshold, largest-contour selection |
| `tests/test_motion_driver.py` | PCA9685 mock mode, channel bounds, release semantics |
| `tests/test_motion_primitives.py` | `home`, `rotate`, `pick`, `place`, `_us_for_angle`, e-stop refusal |
| `tests/test_orchestrator.py` | Command dispatch, sweep sequencing, target-not-found, crash-safety `release_all` |

## Tier 2 — integration

| File | Covers |
|---|---|
| `tests/test_app_endpoints.py` | FastAPI `TestClient` against the lifespan-built `Services` — `/status`, `/command`, `/estop`, `/estop/clear`, `/`. LLM is replaced post-startup with a canned `FakeLLM` so the path is deterministic without a live server. |

`DUMME_MOCK_HARDWARE=true` is set at import time to route all hardware
modules through mock implementations.

## Tier 3 — evaluation (`@pytest.mark.eval`)

**`tests/eval/test_utterance_parsing.py`** parametrizes the 20 canonical
utterances defined once in `scripts/prompt_test.py::CASES` and asserts each
parses to its expected `Command`. The module `pytest.skip`s cleanly when
the server isn't reachable.

**Eval report artifact** — `tests/eval/conftest.py` installs a
`pytest_sessionfinish` hook that writes `eval_report.json` at repo root:

```json
{
  "summary": {"total": 20, "passed": 19, "failed": 1, "accuracy": 0.95},
  "cases": [
    {"id": "test_utterance_parses_to_expected[00:'pick up the red block']", "outcome": "passed", "duration_s": 1.1},
    ...
  ]
}
```

Use this to diff accuracy across prompt edits. A drop is the signal that
`config/prompts/command_parser.txt` or the stop-tokens need tuning.

## Tier 4 — hardware smoke (`@pytest.mark.hardware`)

**`tests/hardware/test_hardware_smoke.py`** — skips cleanly if a
prerequisite is missing, fails loudly if it's present but misbehaving:

| Test | Prerequisite | Asserts |
|---|---|---|
| `test_pca9685_on_i2c_bus_1` | `/dev/i2c-1` + `smbus2` | MODE1 read at `0x40` doesn't `OSError` |
| `test_camera_captures_a_frame` | `/dev/video0` + `cv2` | `cv2.VideoCapture(0)` returns a non-uniform frame |
| `test_llama_server_health` | `LlamaClient().healthy()` | `/health` → 200 |
| `test_llama_server_roundtrip` | same | `complete()` returns non-empty string |

Run on the Pi: `pytest -m hardware`.

## `scripts/preflight.sh` — the 5-minute checklist

Run 5 minutes before demo. Self-contained bash; exits nonzero on first
failure. Checks (in order):

1. `curl /health` on `http://127.0.0.1:8080` (llama-server)
2. `curl /status` on `http://127.0.0.1:8000` (app)
3. `i2cdetect -y 1` shows `40` (PCA9685)
4. `/dev/video0` present (USB camera)
5. `cv2.VideoCapture(0).read()` returns a frame

```bash
make smoke            # equivalent to: bash scripts/preflight.sh
```

## CI (`.github/workflows/ci.yml`)

Triggered on pushes to `main` and every PR. Two jobs:

- **lint** — `ruff check`, `ruff format --check`, `black --check`
- **test** — `pip install -e ".[dev]"`, `pytest -v`, upload `coverage.xml`

`eval` and `hardware` tiers don't run in CI — default addopts skip them.

## Pre-commit

Install once per clone:

```bash
pip install pre-commit
pre-commit install
```

Hooks run on staged files: `ruff --fix`, `ruff format`, trailing-whitespace,
EOF fixer, YAML check, large-file guard (500 KB), merge-conflict marker.

## Coverage gate

`[tool.coverage.run]` sources `dumme/`, branch coverage on. `dumme/io/mic.py`
is omitted while Vosk STT is still a stretch.

`[tool.coverage.report]` has `fail_under = 80` — PRs that drop below 80%
fail the test job. Current floor is comfortable (≈ 84%); the uncovered
paths are real-hardware branches in `camera.py` and `tts.py` that land
under the `@hardware` tier, not the unit gate.

## What's NOT tested (and why)

| Gap | Why | Mitigation |
|---|---|---|
| Full kinematics of `Motion.pick` / `place` | `r_mm` is currently ignored (calibration regression placeholder). Only the pulse-width math is real. | Tests assert that the driver receives *some* write per joint — exact angles land when the real IK does. |
| MJPEG `/stream` endpoint | `TestClient` + sync-generator StreamingResponse deadlocks cleanup. | Covered by `Camera.mjpeg_frames` yield-one-frame behavior in the hardware tier. |
| `Mic.listen` (Vosk STT) | Still `NotImplementedError`; omitted from coverage. | `tests/test_mic.py` covers the mock-mode path only. |
| Real servo motion | Can't replicate a cardboard arm in CI. | `scripts/servo_sweep.py` is the manual smoke; `preflight.sh` is the sanity check. |
