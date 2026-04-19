# DummE — Physical AI Hackathon 2026 Submission

**A cardboard robotic arm that understands natural language, running Gemma entirely on a Raspberry Pi 5. Zero cloud, zero latency, zero privacy compromise.**

- **Track**: Open Challenge / Accessibility
- **Team**: 3 builders, 1 day, ₹0 of budget on cloud
- **Repo**: https://github.com/the-Sreejith/goo-hackathon
- **Demo video**: _link here_
- **Status**: end-to-end working pipeline on real hardware with 76 passing tests, CI, and a 20-case LLM eval harness

---

## 1. The Problem

Most "AI + robotics" demos today either depend on a cloud LLM (latency, privacy, cost) or run a hard-coded script pretending to understand language. Neither is deployable in the places where a helping hand actually matters — a low-bandwidth clinic, an assistive device in a user's home, a field robot in a farm with spotty internet.

**The question we wanted to answer:** can a 4 GB Raspberry Pi — the cheapest, most widely-available single-board computer — run a *generative* language model, a *perception* stack, and a *motion* stack, together, at a latency that feels alive?

**Answer:** yes. And the code fits on an SD card.

---

## 2. The Demo (90 seconds)

1. Open a browser pointed at `http://dumme.local:8000` — DummE's built-in web UI streams the camera live.
2. Type (or later, speak): *"pick up the red block and put it in the blue cup."*
3. Gemma 3n parses the utterance on-device into structured JSON:
   ```json
   {"action": "pick_and_place", "target_color": "red", "dest_color": "blue"}
   ```
4. The chassis starts rotating. The camera sweeps the workspace. When the red block enters the frame, DummE stops and says (via Piper TTS): *"Found the red block."*
5. The 4-DOF arm reaches down, closes its gripper, and lifts.
6. The chassis rotates toward the blue cup. The arm drops the block in.
7. DummE returns to home pose, says *"Task complete."*

Total elapsed time: about 25 seconds of action + ~3 seconds of thinking. No network requests leave the Pi.

---

## 3. What Makes This Submission Different

| Dimension | Why it matters |
|---|---|
| **Fully on-device** | Gemma 3n E2B runs via `llama.cpp` with `llama-server` as a local HTTP endpoint. The app talks to `127.0.0.1:8080`. Airplane mode does not break anything. |
| **Physical, not simulated** | Real cardboard arm, real SG90 + MG90S servos, real PCA9685 over I2C, real USB webcam through V4L2. Not a Unity/Isaac sim. |
| **Structured grounding** | The LLM is constrained to emit a small JSON schema (`action`, `target_color`, `dest_color`). A JSON-extraction + retry + validation layer turns stochastic text into deterministic control. |
| **Engineered, not just hacked** | 76 passing tests across 4 tiers, ≥80% unit coverage, CI on GitHub Actions, pre-commit hooks, a 20-utterance eval harness with per-case accuracy, and an on-device preflight script. See §8. |
| **Reproducible** | `docs/pi_setup.md` is a complete, validated headless-flash-to-running-demo recipe including the WPA3-to-WPA2 gotcha that cost us 30 minutes. |

---

## 4. How It Works — Architecture

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
                              │  5 servos + │
                              │  kill switch│
                              └─────────────┘
```

**Request trace** for `POST /command`:

1. FastAPI hands the utterance to `LLM.parse`.
2. `LlamaClient.complete` POSTs the prompt (with 5 few-shot examples) to `llama-server`. Gemma returns text; we extract the first balanced `{...}` block, coerce it to a frozen `Command` dataclass, retry once with a reminder if it's malformed, and fall back to `Command("unknown", ...)` otherwise.
3. The `Orchestrator` dispatches on `cmd.action`. For `pick_and_place`, it sweeps the turntable in 15° steps, calling `Vision.find(color)` at each stop. On a hit, it asks the `Calibration` module for `(r_mm, θ_deg)`, checks reach, and calls `Motion.pick`.
4. `Motion` pushes each joint through `Safety.clamp` (configured soft limits), converts degrees → microseconds at the per-servo pulse range, and writes via the `PCA9685Driver` over I2C.
5. The pipeline repeats for the destination, places, returns home, releases PWM (stops SG90 jitter), and returns an `ExecutionResult` to the UI.

The code is organized so the orchestrator is the **only** module that knows the pipeline shape. Every other module is a pure, testable verb.

---

## 5. The Gemma Story

### What we use

- **Model**: `gemma-3n-E2B-it-Q4_K_M.gguf` (≈ 2.8 GB, Unsloth's Hugging Face mirror)
- **Runtime**: `llama.cpp`, built natively for aarch64 with `cmake -B build -DGGML_NATIVE=ON`
- **Host**: a `llama-server` systemd unit on the Pi, `127.0.0.1:8080`, auto-restart, `OOMScoreAdjust=500` so a runaway LLM gets killed before the app
- **Context**: `--ctx-size 2048` (enough for schema + prompt + reply; fits KV cache inside 4 GB)
- **Throughput**: ~3–5 tokens/sec on the Pi 5 4GB, active cooler, threads=4. First load mmap is ~30 s; subsequent replies complete in 1–3 s

### Why this is the interesting part

Raw generation isn't the trick — constraining the output is. Our prompt template (`config/prompts/command_parser.txt`) gives Gemma a 4-key schema and 5 few-shot examples. On the Pi side:

- `_extract_json` tolerates markdown fences, leading prose, and nested braces
- `_coerce_to_command` validates against `typing.get_args(Action)` and `Color` — unknown colors or typos become `None`
- One retry with a "REMINDER: JSON only" suffix catches the 1-in-20 case where Gemma chats first and JSONs later
- Final fallback is `Command("unknown", None, None)` — the orchestrator responds politely instead of crashing

### How we know it works

`tests/eval/test_utterance_parsing.py` parametrizes 20 canonical utterances — literal, paraphrased, mixed-case, underspecified, out-of-domain — and asserts each parses to the right `Command` against the live `llama-server`. The suite emits `eval_report.json`:

```json
{
  "summary": {"total": 20, "passed": 19, "accuracy": 0.95},
  "cases": [...]
}
```

This gives the team a regression signal whenever we edit the prompt.

---

## 6. Hardware

Built from a single bag of parts at a maker space, no 3D printing, no laser cutter. Total BOM < ₹5,000 before the Pi.

| Part | Role |
|---|---|
| **Raspberry Pi 5 (4GB)** + 27W USB-C PSU + Active Cooler | Everything: vision, LLM, orchestrator, web UI |
| **USB UVC webcam** | Perception, surfaced at `/dev/video0`, 640×480 @ 15 fps via OpenCV V4L2 |
| **PCA9685 16-ch PWM Driver** | Arm + chassis servo control over I2C |
| **4× SG90 servos** | Base-rotate, shoulder, elbow, gripper |
| **1× MG90S servo** | Chassis turntable (rotates the whole arm relative to the floor) |
| **4× AA battery pack + SPST kill switch** | Separate servo power rail (mandatory — Pi 5V will brown out) |
| **Cardboard + hot glue + bamboo skewers** | Entire frame + arm links |

**Power discipline** (learned the hard way): Pi on its own 27W USB-C. Servos on a separate 5–6V rail. Common ground. Physical kill switch inline on the servo V+, tested with a multimeter before first power-up. See `docs/wiring.md`.

---

## 7. Software Stack

- **OS**: Raspberry Pi OS 64-bit (Debian Trixie), flashed headless with `custom.toml` (see the gotcha below)
- **Language**: Python 3.13 in a `--system-site-packages` venv so OpenCV + picamera2 system packages stay visible
- **Web**: FastAPI + Uvicorn, streaming MJPEG for the camera feed
- **Vision**: OpenCV HSV masking with morphological filtering and the largest-contour-wins heuristic; `red` wraps hue, so two ranges OR together
- **Motion**: `adafruit-circuitpython-pca9685` wrapped behind our own microsecond-level API, joint-limit clamps, thread-safe e-stop flag
- **TTS**: Piper (onnxruntime, CPU) with an `espeak-ng` fallback
- **Tooling**: ruff + black for formatting, pytest (+ pytest-cov) for tests, pre-commit for local hooks, GitHub Actions for CI

Two systemd units (`dumme-llama.service`, `dumme-app.service`) make the whole stack come up on boot — plug the Pi in, open the browser, demo works.

---

## 8. Engineering Quality

This is the part that isn't visible in a video but is what makes the submission real work.

- **76 unit + integration tests, 20 eval tests, 4 hardware smoke tests** — `pytest -m "unit or integration"` runs in ~1 s on a MacBook. `pytest -m eval` runs on the Pi and scores 18–20 out of 20 on the canonical utterances.
- **Coverage gate at 80%** on `dumme/`, currently at 84%. Real-hardware paths (camera open, TTS subprocess) live under the `hardware` marker, not the unit gate.
- **CI** on every push: ruff, ruff-format, black, pytest, coverage.xml upload.
- **Pre-commit** hooks: ruff, ruff-format, trailing-whitespace, large-file guard.
- **`scripts/preflight.sh`** — a 5-check shell script the team runs 5 minutes before demo: llama-server health, app health, PCA9685 I2C ack, `/dev/video0` present, OpenCV captures a non-uniform frame. Green = safe to present.
- **Makefile** with `make test`, `make eval`, `make smoke`, `make coverage`, `make demo` — every workflow is one command.
- **Docs** (`docs/` directory): pi_setup, plan, architecture, wiring, testing, demo_script, starting_point. New contributors can go from git clone to working Pi in under an hour.

---

## 9. What Tripped Us Up (And How We Fixed It)

A hackathon rarely goes smoothly. A selection:

1. **Android hotspot WPA3-only** → Pi OS's firstboot writes a WPA2-PSK `wpa_supplicant.conf` and silently fails to associate with WPA3-only APs. **Fix**: switched the hotspot to "WPA2/WPA3 transitional". Documented in `docs/pi_setup.md` so the next team doesn't lose 30 min.
2. **Debian Trixie switched to NetworkManager** → our first `firstrun.sh` wrote `/etc/wpa_supplicant/wpa_supplicant.conf` (which Trixie ignores). **Fix**: write an `.nmconnection` file directly into `/etc/NetworkManager/system-connections/` with chmod 600. Documented in Appendix A.
3. **cmdline.txt had no `systemd.run=` trigger** when we flashed with `dd` instead of the Imager GUI → `custom.toml` was present but never processed. **Fix**: wrote our own `firstrun.sh`, patched `cmdline.txt` manually. Documented.
4. **Gemma 4 isn't published as GGUF on Hugging Face yet** → we were ready to meet the "Gemma 4" prize criterion but couldn't. **Fix**: swapped to Gemma 3n E2B (same family, edge-optimized, validated by llama.cpp) with an explicit note. Prize story stays: Gemma, on-device, driving a physical robot.
5. **1.5 GB download over a phone hotspot would take 4 hours** at 100 KB/s. **Fix**: downloaded on a MacBook over real WiFi, then `scp`'d to the Pi on the local hotspot LAN (no cellular data used). Documented as an optimization in pi_setup.
6. **Pi 5 has no 3.5mm audio jack.** Would have bit us on the voice stretch. **Fix**: USB speaker on the BOM. Documented on the shopping list so nobody shows up without one.

Every one of these went into `docs/pi_setup.md` §11 troubleshooting + Appendix A.

---

## 10. What's Next (if we had another day)

- **Real inverse kinematics**. Right now `Motion.pick(r_mm, θ)` accepts an `r_mm` but ignores it — it reaches a fixed pose. Replace with the calibration regression scaffolding that's already in the repo (`dumme/calibration/regression.py`).
- **Voice input via Vosk**. `dumme/io/mic.py` is the only remaining stub. 30 minutes of work to wire; blocked only because ambient noise at the venue needed real tuning.
- **Vertex AI fallback** for the occasional out-of-schema utterance, cached aggressively so we use < ₹100 of the GCP credit. The on-device-first story stays — cloud is the exception, not the default.
- **A second object class** (shape detection on top of color). HSV + contour roundness would get us "red ball vs red block".
- **Ultrasonic e-stop**: HC-SR04 → trip `Safety.estop` if the workspace is invaded mid-motion. The flag already exists; wiring is the only work.

---

## 11. Repo Map

```
dumme/          FastAPI app + all Python modules
config/         YAML configs + Gemma prompt template
static/         Browser UI (HTML + JS + CSS)
scripts/        preflight.sh + hardware smoke tools + prompt eval
tests/          unit + integration + eval + hardware tiers
systemd/        dumme-llama.service + dumme-app.service
docs/           pi_setup, plan, architecture, wiring, testing, demo_script, submission (this file)
models/         Gemma weights (gitignored, ~2.8 GB)
.github/        CI workflow
```

---

## 12. Team

- _Name_ — _role_
- _Name_ — _role_
- _Name_ — _role_

---

## 13. Acknowledgements

- **Google & Raspberry Pi Foundation** for building the two pieces of kit that made this possible on a 1-day budget.
- **llama.cpp** contributors for keeping quantized GGUF inference fast on ARM.
- **Unsloth** for the Gemma 3n E2B GGUF upload.
- The **maker space that hosted the hackathon** for the cardboard, servos, and coffee.

---

*DummE runs 100% on-device on a 4 GB Raspberry Pi 5. No cloud. No latency. No privacy compromise. That's the story.*
