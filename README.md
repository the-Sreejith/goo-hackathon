# DummE

A small robotic arm on a rotating chassis. Sees its surroundings, understands a natural-language command **in any of 147 languages**, and executes it — all running on-device on a Raspberry Pi 5 using **Gemma 3n E2B**.

> User: *"pick up the red block and put it in the blue cup"* · *"लाल ब्लॉक उठाओ"* · *"أحضر المكعب الأحمر"*
> DummE: sweeps with the camera, finds red, picks it, rotates to blue, drops it in, goes home.

Zero cloud, zero latency, zero privacy compromise — with first-language access built in.

We prototyped the frame in cardboard (it was fragile; see `docs/submission.md` §6). Printable SG90-arm parts now live under `3d-models/` for a sturdier rebuild on the same electronics + software stack.

## Quickstart (MacBook dev)

```bash
git clone https://github.com/the-Sreejith/goo-hackathon
cd goo-hackathon
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"        # ruff, black, pytest, pytest-cov, httpx
cp .env.example .env

# Smoke test — canonical "pick red, put blue" end-to-end with mocks
python -m scripts.demo_run

# Run the web UI
DUMME_MOCK_HARDWARE=true uvicorn dumme.app:app --reload
# Open http://127.0.0.1:8000
```

Pi-only deps (`picamera2`, `adafruit-circuitpython-pca9685`, `piper-tts`, `vosk`) skip on macOS/x86_64 via platform markers. `DUMME_MOCK_HARDWARE=auto` detects the platform; force with `true`/`false`.

## Pi deployment

Follow [`docs/pi_setup.md`](./docs/pi_setup.md) top-to-bottom for OS flash, WiFi, I2C/SPI, llama.cpp build, and Gemma download. Then from the Mac:

```bash
# Sync code to the Pi (faster than git-on-Pi setup for a hackathon).
rsync -az --exclude '.venv' --exclude '.git' --exclude 'models/*.gguf' \
      --exclude '__pycache__' --exclude '.env' --exclude 'pi-passwords.txt' \
      ./ dumme@dumme.local:/home/dumme/dumme/
```

Install + start the systemd services once:

```bash
ssh dumme@dumme.local '
  sudo cp ~/dumme/systemd/dumme-llama.service /etc/systemd/system/
  sudo cp ~/dumme/systemd/dumme-app.service   /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable --now dumme-llama.service dumme-app.service
'
```

UI lands on `http://dumme.local:8000`, LLM on `http://dumme.local:8080`.

## Tests

```bash
make test            # unit + integration (default — hermetic, ~1 s)
make eval            # live LLM utterance eval (needs llama-server)
make smoke           # scripts/preflight.sh — run on the Pi before demo
make coverage        # pytest --cov with 80% floor
pytest -m hardware   # on the Pi only
```

See [`docs/testing.md`](./docs/testing.md) for the full tier breakdown and eval-report artifact format.

## Docs

| Topic | File |
|---|---|
| Hackathon brief + inventory | [`docs/starting_point.md`](./docs/starting_point.md) |
| Day-of build plan | [`docs/plan.md`](./docs/plan.md) |
| Pi setup (OS, WiFi, llama.cpp, Gemma) | [`docs/pi_setup.md`](./docs/pi_setup.md) |
| Module map + request trace | [`docs/architecture.md`](./docs/architecture.md) |
| GPIO / power / servo wiring | [`docs/wiring.md`](./docs/wiring.md) |
| Test tiers + eval report + CI | [`docs/testing.md`](./docs/testing.md) |
| Demo runbook (pre-flight + 90 s pitch) | [`docs/demo_script.md`](./docs/demo_script.md) |

Index: [`docs/README.md`](./docs/README.md).

## Project layout

```
dumme/          FastAPI app + modules (motion, vision, llm, calibration, io, utils)
config/         YAML configs + Gemma prompt template
static/         Browser UI (HTML + JS + CSS)
scripts/        Hardware smoke tests + preflight.sh + calibration + demo run
tests/          unit + integration + eval + hardware tiers
systemd/        dumme-llama.service + dumme-app.service
docs/           All setup / architecture / testing / demo / submission docs
models/         Gitignored .gguf files (Gemma weights, ~2.8 GB)
3d-models/      Printable SG90 arm + gripper parts (STL / 3MF / Fusion360)
.github/        CI workflow (ruff + black + pytest + coverage upload)
```
