# DummE

A cardboard robotic arm on a rotating chassis. Sees its surroundings, understands a natural-language command, and executes it — all running on-device on a Raspberry Pi 5 using **Gemma 4 E2B**.

> User: *"pick up the red block and put it in the blue cup"*
> DummE: sweeps with the camera, finds red, picks it, rotates to blue, drops it in, goes home.

Zero cloud, zero latency, zero privacy compromise.

## Quickstart (MacBook dev)

```bash
git clone <this-repo>
cd goo-hackathon
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"        # ruff, black, pytest
cp .env.example .env

# Smoke test — canonical "pick red, put blue" end-to-end with mocks
python -m scripts.demo_run

# Run the web UI
uvicorn dumme.app:app --reload
# Open http://127.0.0.1:8000
```

Pi hardware deps (`picamera2`, `adafruit-circuitpython-pca9685`, `piper-tts`) skip on macOS/x86_64 via platform markers. The app detects the missing hardware via `DUMME_MOCK_HARDWARE=auto` and runs in mock mode.

## Pi deployment

Follow [`PI_SETUP.md`](./PI_SETUP.md) top-to-bottom for OS flash, I2C enable, llama.cpp build, and Gemma 4 download. Then:

```bash
# On the Pi
cd ~/goo-hackathon
source .venv/bin/activate
pip install -r requirements.txt

# llama-server (one tmux pane)
~/llama.cpp/build/bin/llama-server \
    -m models/gemma-4-e2b-it-Q4_K_M.gguf \
    --ctx-size 2048 --threads 4 --host 127.0.0.1 --port 8080

# App (another pane)
uvicorn dumme.app:app --host 0.0.0.0 --port 8000
```

Or enable the systemd units (`systemd/dumme-llama.service`, `systemd/dumme-app.service`) for autostart.

## What's wired up, what's TODO

The scaffold gives every module a typed interface and wires the FastAPI routes end-to-end. Bodies that touch hardware or an LLM raise `NotImplementedError` with a `TODO(Pn)` tag indicating which track owns the fill-in:

| Track | Owner | Files with TODOs |
|---|---|---|
| P1 (Hardware) | — | No code — cardboard + wiring |
| P2 (Perception + LLM) | — | `dumme/vision/*`, `dumme/llm/*`, `dumme/io/tts.py` |
| P3 (Motion + Integration) | — | `dumme/motion/*`, `scripts/calibrate.py` |

Everything else (orchestrator, config loading, FastAPI routes, dataclasses, safety clamps, regression math, browser UI) is implemented and tested.

## Docs

- [`PLAN.md`](./PLAN.md) — the day-of build plan
- [`PI_SETUP.md`](./PI_SETUP.md) — shopping list + OS/llama.cpp setup
- [`docs/architecture.md`](./docs/architecture.md) — module map + request trace
- [`docs/wiring.md`](./docs/wiring.md) — pinout reference
- [`docs/demo_script.md`](./docs/demo_script.md) — pitch runbook

## Tests

```bash
pytest -v                                  # 3 test files, pure logic, no hardware
pytest --cov=dumme --cov-report=term-missing
ruff check .
black --check .
```

## Project layout

```
dumme/          FastAPI app + all Python modules (motion, vision, llm, calibration, io, utils)
config/         YAML configs + Gemma prompt template
static/         Browser UI (HTML + JS + CSS)
scripts/        Hardware smoke tests + calibration + demo run
tests/          Pure-logic pytest suite
systemd/        Optional autostart units
docs/           Architecture, wiring, demo runbook
models/         Gitignored .gguf files (Gemma weights, 1.6 GB)
```
