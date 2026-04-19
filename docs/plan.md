# DummE — Physical AI Hackathon 2026 Build Plan

> **Goal**: A cardboard robotic arm on a rotating chassis that sees its surroundings, understands a natural-language command, and executes it — all running on-device on a Raspberry Pi 5 using Gemma.
>
> **Team**: 3 people. **Time**: 1 day. **Track**: Open Challenge / Accessibility (indoor assistance aide).

---

## 1. The MVP Demo

**Storyboard (90 seconds, the whole pitch):**

1. User opens the web UI and types or speaks: *"Pick up the red block and put it in the blue cup."*
2. DummE's chassis **rotates slowly**, sweeping the workspace with the camera.
3. When the red block enters the frame, DummE **stops** and says (TTS): *"Found the red block."*
4. The arm **picks** the block, the chassis **rotates** toward the blue cup, and the arm **drops** it in.
5. DummE returns to home pose and says: *"Task complete."*

That is the entire demo. Every feature not on this list is cut.

---

## 2. Hardware

### 2.1 BOM (from provided inventory)

| Part | Role | Qty |
|---|---|---|
| Raspberry Pi 5 (4GB) | Brain — vision, LLM, orchestration | 1 |
| Pi Camera Module | Perception | 1 |
| PCA9685 16-ch PWM Driver | Drives all servos over I2C | 1 |
| SG90 Micro Servo | Arm joints: base-rotate, shoulder, elbow, gripper | 4 |
| **MG90S Micro Servo** | **Chassis turntable** (holds the whole arm) | 1 |
| HC-SR04 Ultrasonic | Workspace safety stop (optional) | 1 |
| 5V/5A USB-C PSU | Pi power | 1 |
| 5–6V/3A battery or PSU | Servo power (separate rail) | 1 |

**Not used** (stay on the table for the hero photo): ESP32, Arduino Uno, remaining MG995s, GPS, DHT, BME, HX711, MPU6050, IR sensor.

### 2.2 Power Rules (critical)

- **Pi on its own USB-C 5V/5A.**
- **Servos on a separate 5–6V/3A rail.** Never power servos from the Pi's 5V pin — they'll brown out the CPU.
- **Common ground only** between the two rails.
- **Physical kill switch** (toggle or inline button) on the servo V+ line. You will need it.

### 2.3 Mechanical

**Arm (4-DOF, SG90s):**

| Joint | Servo | Range |
|---|---|---|
| J1 — base rotate | SG90 #1 | 0–180° |
| J2 — shoulder | SG90 #2 | 30–150° |
| J3 — elbow | SG90 #3 | 20–160° |
| J4 — gripper | SG90 #4 | open/close |

**Chassis turntable:** MG90S mounted below two cardboard discs. A skewer or dowel pin runs through the center of both discs as the rotation axis. A plastic lid or 3D-printed washer sits between them for low friction. The arm's base plate is glued to the top disc.

### 2.4 Cardboard Assembly Rules

SG90s are forgiving on cardboard (low torque), but these rules still matter:

- **Double-layer corrugated**, grain directions crossed, hot-glued.
- **Bamboo skewers or chopsticks** as internal bracing along every arm segment.
- **Servo horns**: sandwich the horn between the cardboard and a second small cardboard plate + washer. Screws pull through a single layer.
- **Keep arm segments short** (<15 cm each). Long segments amplify torque and cause sag.
- **Heavy base**: tape the chassis base to a book, a hardcover, or a box weighted with anything dense. A top-heavy arm will tip during a swing.
- **Cable routing**: run servo wires through the turntable's center pin area, leave slack so rotation doesn't yank them.

### 2.5 Payload Budget

SG90 torque ≈ 1.8 kg·cm. With a 10 cm forearm, payload at the gripper tip is roughly **100–150 g max**. Safe target objects:

- Ping-pong ball
- Foam cube (3 cm)
- Bottle cap
- Small plastic block

Avoid anything heavier than a matchbox.

---

## 3. Software Architecture

```
┌────────────────────────────────────────────────────────────┐
│                      Browser (any device)                   │
│              Text input + live camera MJPEG                 │
└────────────────────────────┬───────────────────────────────┘
                             │ HTTP
┌────────────────────────────▼───────────────────────────────┐
│                   FastAPI app (app.py)                      │
│  POST /command   GET /stream   GET /status   POST /estop   │
└──┬────────────────┬────────────────┬───────────────────────┘
   │                │                │
┌──▼────────┐  ┌────▼─────┐   ┌──────▼──────────┐
│  llm.py   │  │ vision.py│   │  orchestrator.py│
│ Gemma 3n  │  │ cv2 UVC  │   │  Sweep → detect │
│ JSON-only │  │ + HSV    │   │  → pick → place │
└───────────┘  └──────────┘   └──────┬──────────┘
                                     │
                              ┌──────▼──────┐
                              │  motion.py  │
                              │  PCA9685 +  │
                              │  primitives │
                              └──────┬──────┘
                                     │ I2C
                              ┌──────▼──────┐
                              │  PCA9685    │
                              │  → 5 servos │
                              └─────────────┘
```

### 3.1 Repo Layout

```
dumme/
├── app.py                  # FastAPI entrypoint, serves UI
├── config.yaml             # servo limits, HSV ranges, calibration
├── dumme/
│   ├── __init__.py
│   ├── motion.py           # PCA9685 driver, motion primitives
│   ├── vision.py           # OpenCV UVC + HSV detection
│   ├── llm.py              # Gemma wrapper, JSON-strict prompt
│   ├── calibration.py      # pixel → (r, θ) map
│   └── orchestrator.py     # main command loop
├── static/
│   └── index.html          # single-file browser UI
├── models/
│   └── gemma-3n-E2B-it-Q4_K_M.gguf  # active model (~2.8 GB)
├── scripts/
│   ├── servo_sweep.py      # sanity-check each servo
│   ├── calibrate.py        # interactive calibration ritual
│   └── test_pipeline.py    # scripted end-to-end demo
├── requirements.txt
└── README.md
```

### 3.2 Key Interfaces

**`motion.py`**
```python
class Motion:
    def home(self) -> None: ...
    def base_rotate(self, angle_deg: float) -> None: ...
    def pick(self, r_mm: float, theta_deg: float) -> None: ...
    def place(self, r_mm: float, theta_deg: float) -> None: ...
    def release_all(self) -> None: ...    # zero PWM, stops jitter
    def estop(self) -> None: ...          # freeze + cut power flag
```

**`vision.py`**
```python
@dataclass(frozen=True)
class Detection:
    color: str
    pixel_xy: tuple[int, int]
    area_px: int

class Vision:
    def frame(self) -> np.ndarray: ...
    def find(self, color: str) -> Detection | None: ...
```

**`llm.py`**
```python
@dataclass(frozen=True)
class Command:
    action: str                  # "pick_and_place" | "home" | "unknown"
    target_color: str | None
    dest_color: str | None

class LLM:
    def parse(self, utterance: str) -> Command: ...
```

**`orchestrator.py`**
```python
class Orchestrator:
    def execute(self, cmd: Command) -> ExecutionResult: ...
```

### 3.3 Gemma Model Choice

**Active: Gemma 3n E2B (Q4_K_M GGUF)** — edge-optimised, supported by llama.cpp, validated on Pi 5.

| Aspect | Value |
|---|---|
| Model file | `gemma-3n-E2B-it-Q4_K_M.gguf` (~2.8 GB; `unsloth` mirror) |
| Effective params | ~2 B |
| Multimodal | Text-only on our path |
| Throughput on 4GB Pi 5 | ~3–5 tokens/sec (plenty for a ~20-token JSON reply) |
| Context cap | `--ctx-size 2048` (native 128K is too much KV cache for 4GB) |

> The original plan targeted **Gemma 4 E2B** for first-party prize alignment, but that variant isn't available as a published GGUF on Hugging Face at build time. Gemma 3n E2B is the functionally equivalent replacement — same on-device Gemma story, shippable.

**Do NOT use on this Pi**: Gemma 3n E4B (~4 GB, no RAM headroom for app + OS), 26B MoE, 31B Dense.

**llama.cpp launch command** (or use `systemctl start dumme-llama.service`):
```bash
llama-server \
  -m models/gemma-3n-E2B-it-Q4_K_M.gguf \
  --ctx-size 2048 \
  --threads 4 \
  --host 127.0.0.1 --port 8080
```

### 3.4 Gemma Prompt (JSON-strict)

System prompt enforces the schema. Few-shot examples cover common phrasings. Retry once if output isn't valid JSON.

```
You are DummE's command parser. Convert the user's request to JSON ONLY.
Do not add commentary. Do not use markdown fences.

Schema:
{
  "action": "pick_and_place" | "home" | "unknown",
  "target_color": "red" | "blue" | "green" | null,
  "dest_color":   "red" | "blue" | "green" | null
}

Examples:
User: "pick up the red block and put it in the blue cup"
{"action":"pick_and_place","target_color":"red","dest_color":"blue"}

User: "grab the green one and drop it in red"
{"action":"pick_and_place","target_color":"green","dest_color":"red"}

User: "go home"
{"action":"home","target_color":null,"dest_color":null}

User: "dance for me"
{"action":"unknown","target_color":null,"dest_color":null}
```

### 3.5 Main Loop (pseudocode)

```python
def execute(cmd: Command) -> ExecutionResult:
    if cmd.action == "home":
        motion.home(); return ok()
    if cmd.action == "unknown":
        return fail("I didn't understand that.")

    # Sweep to find target
    target_hit = sweep_and_detect(cmd.target_color)
    if not target_hit:
        return fail(f"I can't see the {cmd.target_color} object.")

    # Pick
    r, theta = calibration.pixel_to_polar(target_hit.pixel_xy, motion.base_angle)
    motion.pick(r, theta)

    # Find destination
    dest_hit = sweep_and_detect(cmd.dest_color)
    if not dest_hit:
        motion.home(); return fail(f"I can't see the {cmd.dest_color} destination.")

    # Place
    r2, theta2 = calibration.pixel_to_polar(dest_hit.pixel_xy, motion.base_angle)
    motion.place(r2, theta2)
    motion.home()
    return ok()
```

---

## 4. Team Split

| Person | Track | Owns |
|---|---|---|
| **P1** | Hardware | Cardboard cut + assembly, servo mounting, PCA9685 wiring, power rails, kill switch |
| **P2** | Perception + LLM | `vision.py`, `llm.py`, Gemma setup, browser UI, live camera feed |
| **P3** | Motion + Integration | `motion.py`, `calibration.py`, `orchestrator.py`, `app.py`, demo script |

**Golden rule**: everyone commits a working stub to `main` in the first hour. No one waits on anyone.

---

## 5. Phased Execution

### Phase A — End-to-end skeleton (parallel, ~1 hour)

All three people land code on `main` **before any real hardware works**.

**P1 (Hardware)**
- Cut cardboard from the blueprint.
- Dry-fit arm + turntable (no glue yet).
- Label every servo wire (J1/J2/J3/J4/TURN).
- Solder power rail.

**P2 (Perception + LLM)**
- `vision.find()` returns a hardcoded fake `Detection` for any color.
- `llm.parse()` returns a hardcoded `Command` for one test string.
- Minimal HTML page: text box + Submit button + `<img src="/stream">`.

**P3 (Motion + Integration)**
- `motion.*` methods `print()` what they would do, no hardware calls.
- FastAPI app with `/command`, `/stream`, `/status`, `/estop`.
- `orchestrator.execute()` glues the three stubs.

**Exit gate**: typing "pick red, put blue" in the browser prints the full pipeline trace to the console. Nothing real works yet — that's fine.

### Phase B — Swap stubs for reality (parallel, ~3 hours)

**P1 (Hardware)**
- Final glue-up of arm and turntable.
- Mount Pi, camera, and PCA9685 on the chassis.
- Weight the base. Confirm turntable holds the arm without creep.
- Join P3 during calibration (hour ~4).

**P2 (Perception + LLM)**
1. `cv2.VideoCapture(0)` USB UVC capture → FastAPI MJPEG stream at `/stream` (swap in `picamera2` if using a CSI ribbon).
2. HSV color masks for red, blue, green. Tune under the actual demo lighting.
3. `Vision.find(color)` returns the largest contour's centroid + area. Reject detections with area < threshold.
4. Install `llama.cpp` on Pi. Download **Gemma 3n E2B Q4_K_M GGUF** (~2.8 GB, via `unsloth` on Hugging Face) to `models/`.
5. Launch `llama-server` with `--ctx-size 2048 --threads 4`. Wire `LLM.parse()` to hit it over HTTP with the JSON-strict prompt.
6. Test **20+ phrasings**. Add few-shot examples until ≥95% parse correctly.
7. Add `piper` TTS for spoken replies.

**P3 (Motion + Integration)**
1. `Motion` class wraps `adafruit_pca9685`. Every servo has `min_us`, `max_us`, `home_deg` in `config.yaml`.
2. `scripts/servo_sweep.py` — sanity-check each servo individually.
3. **Calibration ritual** (run WITH the real arm, not simulated):
   - Place a block at 5 known `(x, y)` positions on the workspace.
   - For each: manually jog the arm to a good pick pose, record `(base_angle, shoulder, elbow)` and the pixel location of the block in the camera frame at turntable angle 0.
   - Fit a regression: `(pixel_x, pixel_y) → (shoulder, elbow)`. Linear or affine is fine.
   - Turntable rotation adds a constant offset: `absolute_theta = pixel_theta + turntable_angle`.
4. Primitives: `home()`, `base_rotate()`, `pick(r, theta)`, `place(r, theta)`, `release_all()`, `estop()`.
5. `sweep_and_detect(color)` — rotate turntable in 15° steps from -60° to +60°, capture frame at each stop, return first hit.

### Phase C — Integration + demo hardening (~2 hours)

- Run the full loop **10 times**. Each failure → a guard rail or a demo-script workaround.
- Common fixes you'll add:
  - Servo jitter at rest → `release_all()` after every primitive.
  - Block outside reach → polite TTS error + return to home.
  - Gripper slips the ball → slow down the lift; add a foam pad on the gripper tips.
  - Turntable slips → bigger servo horn contact area, more glue.
- **Record the demo video now.** Do not leave it for the last 15 minutes.
- Write the README with architecture diagram, Gemma callout, wiring photos.

### Phase D — Stretch goals (only if green by hour 7)

- Voice input via Vosk tiny (offline STT).
- A third color / object class.
- OLED status display over I2C.
- Ultrasonic e-stop: if HC-SR04 reads <20cm (human hand in workspace), freeze the arm.
- `sweep_and_detect` early-stop animation (rotate toward the target smoothly).

---

## 6. Hard Cuts (confirmed)

- ❌ 6-DOF arm — 4 is enough.
- ❌ Real inverse kinematics — regression from calibration points suffices.
- ❌ Wrist pitch/roll — gripper approaches vertically.
- ❌ Wheeled mobility — the chassis rotates but doesn't drive.
- ❌ Depth camera / stereo — workspace is a flat table at a known height.
- ❌ ESP32 / Arduino — Pi drives PCA9685 directly over I2C.
- ❌ Cloud LLM — Gemma on-device is the prize story.
- ❌ GPS, DHT, BME, HX711, MPU, IR — out of scope for the MVP.

---

## 7. Risk Register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Arm tips forward when reaching | High | Heavy base (tape book/board under chassis) |
| SG90 jitter at rest | High | `release_all()` (PWM=0) after each motion |
| SG90s overheat during calibration | Medium | Short bursts; arm rests on cardboard support in home pose |
| Gemma returns malformed JSON | Medium | Strict schema prompt + 1-retry with reminder; regex extract `{...}` |
| Gemma 3n E2B hits RAM limit on 4GB Pi | Medium | Drop `--ctx-size` to 1024; close unused services; check `free -h` |
| Gemma token throughput too slow | Medium | Show "Thinking…" in UI; keep prompt short; cap `--n-predict 128` |
| HSV mask misses block under shadow | High | White sheet as workspace + desk lamp for even lighting |
| Cable pulled during base rotation | Medium | Route through turntable center; leave slack loop |
| Turntable slips under load | Medium | MG90S horn glued AND screwed; short arm segments |
| Pi CPU overload (vision + LLM) | Medium | Detect and LLM don't run concurrently; Gemma Q4 quantization |
| Gripper drops the ball | High | Foam pads on gripper tips; slow lift speed |
| Demo ambient light changes | Medium | Recalibrate HSV just before demo; add a lamp |

---

## 8. Prize Criteria Fit

- **Gemma**: we run **Gemma 3n E2B** **on-device** via `llama.cpp` on a 4GB Pi 5. On-device Gemma, structured JSON output driving real-world actuation — no cloud, no API calls.
- **Accessibility / multilingual**: Gemma 3n supports **147 languages**, so the same device serves users across ages and first languages without a cloud translation hop. This is the headline accessibility story for the submission.
- **GCP ($5 budget)**: use Vertex AI only as an optional fallback for commands Gemma can't parse locally, and cache aggressively. An on-device-only story is simpler and probably more compelling — lean on "zero cloud, zero latency, zero privacy compromise" as the narrative.
- **Physical AI**: camera + servos + cardboard form factor + real-world pick-and-place.
- **Track fit** (Accessibility or Open): voice/text command → physical action maps directly to "empowering people with disabilities" or "open-ended AI + hardware".

---

## 9. Pre-flight Checklist

**Hardware, OS, and model setup are documented in [`pi_setup.md`](./pi_setup.md).** Complete every step (including the verification checklist in §10 of that doc) **before** hack day starts.

**Project-specific readiness** (additional to `pi_setup.md`):
- [ ] Repo scaffold (`app.py`, `motion.py`, `vision.py`, `llm.py`, `config.yaml`, `scripts/`) pushed to GitHub.
- [ ] Cardboard blueprints printed.
- [ ] Props on hand: cardboard sheets, hot glue, skewers, foam cubes, ping-pong ball, coloured cups, desk lamp, white workspace backdrop.
- [ ] 1–2 extra SG90 servos (burnout insurance).
- [ ] Kill switch wired inline on servo V+ and physically tested (multimeter-verified).

---

## 10. One-Page Demo Day Runbook

1. **30 min before**: power up, run `scripts/test_pipeline.py`, recalibrate HSV under demo lighting.
2. **10 min before**: home pose, release servos, close unused apps on the Pi.
3. **Demo**:
   - Show the cardboard arm (authenticity wins hearts).
   - Open the browser UI on a phone or laptop.
   - Type the command. Let Gemma parse (show the JSON on screen).
   - Watch the sweep, pick, place, return home.
   - Final line: *"Everything you saw ran on the Pi. No cloud."*
4. **Backup**: if live run fails, play the pre-recorded video immediately. Do not freeze.

---

**Ready to scaffold the repo?** Once the plan is approved, create the directory tree in §3.1 and commit working stubs so P1/P2/P3 can start in parallel.
