# DummE — Architecture

```
┌────────────────────────────────────────────────────────────┐
│                      Browser (any device)                   │
│              Text input + live camera MJPEG                 │
└────────────────────────────┬───────────────────────────────┘
                             │ HTTP
┌────────────────────────────▼───────────────────────────────┐
│                   FastAPI app (dumme/app.py)                │
│  POST /command   GET /stream   GET /status   POST /estop    │
└──┬────────────────┬────────────────┬───────────────────────┘
   │                │                │
┌──▼────────┐  ┌────▼─────┐   ┌──────▼──────────┐
│  llm/     │  │ vision/  │   │  orchestrator   │
│ Gemma 3n  │  │ cv2 UVC  │   │  Sweep → detect │
│ JSON-only │  │ + HSV    │   │  → pick → place │
└───────────┘  └──────────┘   └──────┬──────────┘
                                     │
                              ┌──────▼──────┐
                              │  motion/    │
                              │  PCA9685 +  │
                              │  primitives │
                              └──────┬──────┘
                                     │ I2C
                              ┌──────▼──────┐
                              │  PCA9685    │
                              │  → 5 servos │
                              └─────────────┘
```

## Module Responsibilities

### `dumme.app` — FastAPI entrypoint
Builds the `Services` container at startup (reads `config/*.yaml`), wires routes, serves `static/`. Every request handler delegates into `Orchestrator`, `LLM`, `Motion`, or `Camera` — no business logic lives in route handlers.

### `dumme.orchestrator` — The Command → Action loop
The only module that knows the pipeline shape. `execute(cmd)` dispatches `home` / `pick_and_place` / `unknown`. `sweep_and_detect(color)` iterates the turntable in 15° steps, calling `vision.find(color)` at each stop until a hit (or the full sweep completes).

### `dumme.motion/` — Hardware actuation
- `driver.PCA9685Driver` — microsecond-level PWM writes, lazy-imports `adafruit_pca9685` so this module loads on a MacBook.
- `primitives.Motion` — verbs the orchestrator calls (`home`, `pick`, `place`, `release_all`, `estop`). Every write goes through `Safety.clamp` and honours `Safety.estop`.
- `safety.Safety` — joint-limit clamping + thread-safe `EstopFlag`.

### `dumme.vision/` — Perception
- `camera.Camera` — `cv2.VideoCapture(0, cv2.CAP_V4L2)` wrapper for USB UVC webcams. One-shot + MJPEG generator. Falls back to solid-colour frames in mock mode.
- `detector.Vision` — HSV masking + morphology + contour selection. Returns `Detection(color, pixel_xy, area_px)` or `None`. Red hue wraps, so the config OR's two ranges together.

### `dumme.llm/` — Utterance → Command
- `client.LlamaClient` — HTTP client for local llama.cpp server on port 8080.
- `parser.LLM` — fills the prompt template, extracts JSON, validates, retries once. Falls back to `Command("unknown", ...)`.
- `schema` — `Command`, `ExecutionResult` dataclasses + `ok()`/`fail()` helpers.
- **Multilingual**: Gemma 3n covers 147 languages. The prompt template + JSON schema are language-agnostic — the same `Command("pick_and_place", "red", "blue")` comes out whether the user said "pick the red one" or "लाल ब्लॉक उठाओ". No per-locale build.

### `dumme.calibration/` — Pixel → polar (r, θ)
Affine regression fit from 5+ hand-captured samples. Used by the orchestrator to turn a detected pixel into a motion target.

### `dumme.io/` — Speech I/O
- `tts.TTS` — Piper wrapper for spoken replies.
- `mic.Mic` — Vosk STT, stretch only.

### `dumme.utils/` — Shared infrastructure
- `config.load_yaml` — reads `config/*.yaml`, resolves `DUMME_CONFIG_DIR` override.
- `logging.get_logger` — structured logging, respects `LOG_LEVEL`.

## Request Trace: `POST /command`

```
POST /command {"utterance": "pick red, drop blue"}
  → app.post_command
  → services.llm.parse(utterance)                 # HTTP → llama-server → JSON → Command
  → services.orchestrator.execute(cmd)
    → motion.base_rotate / turntable_rotate       # sweep
    → vision.find(target_color) ... (repeat)
    → calibration.pixel_to_polar(...)
    → motion.pick(r, θ)
    → (same for destination)
    → motion.place(r, θ); motion.home()
  → return ExecutionResult → JSON
```

## Hardware-Software Contract

| Concern | Boundary |
|---|---|
| PCA9685 I2C address | `0x40` (default) — `config/servos.yaml` is source of truth for channels |
| Servo pulse range | `min_us` / `max_us` per joint in `config/servos.yaml` |
| Joint soft limits | `joint_limits` in `config/servos.yaml` — enforced by `Safety.clamp` |
| Gemma backend | `http://127.0.0.1:8080/completion` — override via `LLAMA_URL` env. Current weights: `gemma-3n-E2B-it-Q4_K_M.gguf` (~2.8 GB). |
| Camera device | `/dev/video0` via OpenCV V4L2 (USB UVC). `picamera2` is supported if you wire a CSI ribbon and swap `Camera._open`. |

## Testing Strategy

See [testing.md](./testing.md) for the full breakdown. In short:

- **Unit** (`@pytest.mark.unit`, default) — hermetic logic: JSON extraction, regression math, safety clamps, motion pulse math, vision HSV, orchestrator dispatch with fakes, LLM client with mocked `requests`.
- **Integration** (`@pytest.mark.integration`, default) — FastAPI `TestClient` with a stubbed LLM.
- **Eval** (`@pytest.mark.eval`, opt-in) — live-LLM accuracy suite parametrized over 20 canonical utterances in `scripts/prompt_test.py::CASES`.
- **Hardware** (`@pytest.mark.hardware`, opt-in) — Pi-only: I2C ack at 0x40, camera frame variance, llama-server roundtrip.
- **Preflight** (`scripts/preflight.sh`) — 5-minute shell sanity check before demo.

The default `pytest` / `make test` run covers unit+integration; `make eval`, `pytest -m hardware`, and `make smoke` are the opt-in tiers.
