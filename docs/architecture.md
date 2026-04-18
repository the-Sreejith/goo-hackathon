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
│ Gemma +   │  │ picamera │   │  Sweep → detect │
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
- `camera.Camera` — picamera2 wrapper, one-shot + MJPEG generator.
- `detector.Vision` — HSV masking + contour selection. Returns `Detection(color, pixel_xy, area_px)` or `None`.

### `dumme.llm/` — Utterance → Command
- `client.LlamaClient` — HTTP client for local llama.cpp server on port 8080.
- `parser.LLM` — fills the prompt template, extracts JSON, validates, retries once. Falls back to `Command("unknown", ...)`.
- `schema` — `Command`, `ExecutionResult` dataclasses + `ok()`/`fail()` helpers.

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
| Gemma backend | `http://127.0.0.1:8080/completion` — override via `LLAMA_URL` env |
| Camera device | First CSI camera via `picamera2` defaults |

## Testing Strategy

- **Unit (`tests/`)**: pure logic — JSON extraction, regression math, safety clamps. Zero hardware deps. Runs on MacBook.
- **Integration (none yet)**: live LLM tests are `scripts/prompt_test.py` — skipped if llama-server isn't up.
- **Hardware smoke (`scripts/`)**: `servo_sweep.py`, `i2c_probe.py`, `camera_preview.py` — run on the Pi.
- **End-to-end (`scripts/demo_run.py`)**: the canonical "pick red, put blue" trace. Passes with mocks today; matches real hardware once P2/P3 fill in `NotImplementedError` bodies.
