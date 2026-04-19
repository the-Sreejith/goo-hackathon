# DummE — Pi Setup & Shopping Guide

> Everything to buy, flash, and configure **before hack day**. Works headless from a MacBook — no monitor or keyboard needed. Follow top to bottom.

---

## 1. Shopping List

### 1.1 Essentials (must-have before hack day)

| Item | Why | Approx ₹ |
|---|---|---|
| **Samsung EVO Plus 64GB microSD** (A2/V30) | Storage — chosen for random-IOPS speed | ~₹700 |
| **Pi 5 Official 27W USB-C PSU** (5V/5A) | Pi 5 brown-outs on weaker supplies; Pi 4 chargers **do not** work | ~₹1,500 |
| **Pi 5 Active Cooler** (official fan + heatsink) | Pi 5 throttles hard under LLM load — non-optional for Gemma | ~₹500 |
| **USB-C microSD card reader** | For flashing the card from MacBook (skip if your Mac has an SD slot + microSD adapter) | ~₹300 |
| **4×AA battery holder + 4 AA batteries** *(or 5V 3A UBEC)* | **Separate servo power rail** — mandatory, never share Pi's 5V | ~₹200 |
| **Jumper wires**: 40× M-F, 40× M-M, 20× F-F | Every connection on the build | ~₹300 |
| **Mini breadboard** (400-point) | Consolidating grounds + power rails | ~₹150 |
| **Hot glue gun + 10 sticks** | Cardboard joinery | ~₹400 |
| **Bamboo skewers or chopsticks** | Internal bracing for arm segments | ~₹50 |
| **5-ply corrugated cardboard** (~1 sqm) | Frame material | scrap |
| **SPST toggle switch** (5A rated) | Inline kill switch on servo V+ — you WILL need it | ~₹50 |
| **M2 / M3 screws + washers** | Servo mounting (most SG90s ship with these — check first) | — |

### 1.2 Demo-Day Props

| Item | Why |
|---|---|
| Ping-pong ball + small foam cubes in **red, blue, green** | Target objects for pick-and-place |
| 3–4 small coloured cups/bowls | Destinations |
| Desk lamp | Even lighting kills HSV flakiness |
| White A3 paper or foam board | Workspace backdrop — huge win for colour detection |

### 1.3 Voice Stretch (skip unless P2 is green by hour 7)

| Item | Why |
|---|---|
| Cheap USB microphone | Pi 5 has no onboard mic input |
| USB speaker (or 3.5mm powered speaker + USB audio dongle) | ⚠️ **Pi 5 removed the 3.5mm audio jack** — you cannot just plug headphones in |

### 1.4 Nice-to-Have (debugging lifesavers)

| Item | Why |
|---|---|
| Ethernet cable | Fallback if WiFi is flaky on demo day |
| Multimeter | Debugs power issues in 30 seconds instead of 30 minutes |
| 1–2 extra SG90 servos | Burnouts happen during calibration |

---

## 2. Flash the SD Card from MacBook (Headless)

### 2.1 Install Raspberry Pi Imager

```bash
brew install --cask raspberry-pi-imager
```

Or download the `.dmg` from [raspberrypi.com/software](https://www.raspberrypi.com/software/).

### 2.2 Flash Pi OS with headless config baked in

1. Insert the 64GB microSD (via reader) into your MacBook.
2. Open **Raspberry Pi Imager**.
3. **Choose Device** → `Raspberry Pi 5`.
4. **Choose OS** → `Raspberry Pi OS (64-bit)` (the full-with-desktop version — enables VNC later if you need it).
5. **Choose Storage** → the 64GB card.
6. Click **Next** → when prompted "Would you like to apply OS customisation settings?" → **EDIT SETTINGS**. This step is the entire game.

   **General tab**:
   - ✅ Set hostname: `dumme` (reachable as `dumme.local`)
   - ✅ Set username: `dumme` + a strong password
   - ✅ Configure wireless LAN: your WiFi SSID + password + **country code `AE`** (or wherever you are)
   - ✅ Set locale: `Asia/Dubai`, keyboard `us` (or your layout)

   **Services tab**:
   - ✅ Enable SSH → **Use password authentication** (simplest for hackathon)

   **Options tab**:
   - ✅ Eject media when finished

7. **Save** → **Yes** to apply → your Mac password → wait ~5 min for flash + verify.

### 2.3 Boot the Pi

1. Eject the card, slot it into the Pi 5 (underside).
2. Plug in the **27W USB-C PSU**.
3. Green LED blinks steadily → booting. First boot takes **~2–3 minutes** while the filesystem expands.

---

## 3. Find and SSH into the Pi

From your MacBook Terminal:

```bash
ping dumme.local
```

If it resolves → you're in business. If not:

```bash
brew install nmap
sudo nmap -sn 192.168.1.0/24        # adjust subnet to your LAN
# Look for the Pi by vendor name "Raspberry Pi"
```

Once you have the hostname or IP:

```bash
ssh dumme@dumme.local
# or
ssh dumme@<ip-address>
```

Type `yes` at the fingerprint prompt, then your password.

### 3.1 Passwordless SSH (recommended, 30 seconds)

```bash
# On MacBook:
ssh-keygen -t ed25519        # skip if you already have a key
ssh-copy-id dumme@dumme.local
```

Never type the password again. Do this from every teammate's laptop so all three can log in.

---

## 4. First-Run System Config

Once SSHed in:

```bash
# Update everything
sudo apt update && sudo apt full-upgrade -y

# Install baseline tooling
sudo apt install -y git python3-pip python3-venv i2c-tools \
                    build-essential cmake wget curl

# Enable hardware interfaces non-interactively
sudo raspi-config nonint do_i2c 0       # I2C on (for PCA9685)
sudo raspi-config nonint do_spi 0       # SPI on
# Camera: no-op on Bookworm — libcamera is default, picamera2 just works

# Reboot so changes apply cleanly
sudo reboot
```

Wait ~30 sec, SSH back in.

Verify I2C (once PCA9685 is wired later):

```bash
i2cdetect -y 1
# Should show "40" in the grid when PCA9685 is connected
```

---

## 5. Dev Environment from MacBook (no monitor, forever)

### 5.1 VS Code Remote-SSH

1. Install **VS Code** on MacBook.
2. Install the **Remote - SSH** extension.
3. `Cmd+Shift+P` → `Remote-SSH: Connect to Host...` → enter `dumme@dumme.local`.
4. VS Code now runs against the Pi. Edit files, open terminals, debug Python — all as if local.

All three teammates can connect to the same Pi simultaneously. No monitor, no keyboard, no VNC.

### 5.2 Project Directory + Python venv

Inside the SSH session:

```bash
mkdir -p ~/dumme && cd ~/dumme
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install picamera2 adafruit-circuitpython-pca9685 \
            fastapi uvicorn opencv-python-headless \
            numpy pyyaml piper-tts requests
```

Add the venv auto-activate to `.bashrc` so SSH sessions land inside it:

```bash
echo 'source ~/dumme/.venv/bin/activate' >> ~/.bashrc
```

---

## 6. Build llama.cpp + Download Gemma 4

### 6.1 Build llama.cpp

```bash
cd ~
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
cmake -B build -DGGML_NATIVE=ON
cmake --build build -j4
# ~5–8 minutes on Pi 5
```

Confirm Gemma 4 is supported (build date should be ≥ April 2026):

```bash
./build/bin/llama-cli --version
```

### 6.2 Download Gemma 4 E2B (primary) + Gemma 3n E2B (fallback)

```bash
mkdir -p ~/dumme/models && cd ~/dumme/models

# Primary: Gemma 4 E2B Q4_K_M (~1.6 GB)
wget -O gemma-4-e2b-it-Q4_K_M.gguf \
  'https://huggingface.co/google/gemma-4-e2b-it-GGUF/resolve/main/gemma-4-e2b-it-Q4_K_M.gguf'

# Fallback: Gemma 3n E2B Q4 (~1.5 GB)
wget -O gemma-3n-E2B-Q4.gguf \
  'https://huggingface.co/google/gemma-3n-E2B-it-GGUF/resolve/main/gemma-3n-E2B-it-Q4_K_M.gguf'
```

> ⚠️ **Confirm the exact Hugging Face paths at download time** — Google's GGUF repo structure may differ from the URLs above. Search `gemma-4-e2b-it-GGUF` on Hugging Face if wget 404s.

### 6.3 Smoke-test Gemma

```bash
~/llama.cpp/build/bin/llama-cli \
  -m ~/dumme/models/gemma-4-e2b-it-Q4_K_M.gguf \
  --ctx-size 2048 \
  --threads 4 \
  -p "Return ONLY valid JSON: {\"status\": \"ok\"}" \
  --n-predict 20
```

Expect a sensible JSON-ish response in ~3–6 seconds.

### 6.4 Run llama-server (what the app will actually hit)

```bash
~/llama.cpp/build/bin/llama-server \
  -m ~/dumme/models/gemma-4-e2b-it-Q4_K_M.gguf \
  --ctx-size 2048 \
  --n-predict 128 \
  --threads 4 \
  --host 127.0.0.1 \
  --port 8080
```

From another SSH session:

```bash
curl -s http://127.0.0.1:8080/completion \
  -d '{"prompt": "Return JSON only: {\"ok\": true}", "n_predict": 20}' \
  | python3 -m json.tool
```

If you see a valid completion, the LLM stack is done.

---

## 7. GitHub Setup (so all 3 devs can push)

```bash
# On the Pi
git config --global user.name  "DummE Team"
git config --global user.email "dumme@hackathon.local"

ssh-keygen -t ed25519 -C "dumme-pi"
cat ~/.ssh/id_ed25519.pub
# Paste this into GitHub → Settings → SSH and GPG keys → New SSH key
```

Each teammate also adds their own Mac's SSH key to GitHub and clones directly onto the Pi via VS Code Remote.

---

## 8. Power Wiring (read before plugging anything in)

```
              ┌──────────────┐
              │  Pi 5 brain  │
              └──────┬───────┘
                     │ I2C (SDA/SCL)
              ┌──────▼───────┐      ┌──────────────┐
              │   PCA9685    │◄──── │  4×AA pack   │  5–6V
              │   16-ch PWM  │      │  (servo V+)  │
              └──┬───────────┘      └──────┬───────┘
                 │ 5 PWM lines             │
         ┌───────┴────────┐                │
         │                │                │
     5 servos          GND ──────────┬─────┘
                                     │
                              ┌──────┴──────┐
                              │   KILL      │  ← SPST toggle on V+
                              │   SWITCH    │     between battery + PCA9685
                              └─────────────┘
```

**Rules, in order of how badly they'll burn you:**

1. **Never** power servos from the Pi's 5V pin. They will brown out the CPU mid-LLM-inference.
2. **Always** share ground between the Pi and the servo rail. Floating grounds = erratic PWM = dancing arm.
3. **Always** wire the kill switch inline on V+. During calibration, an SG90 going full-range into a stuck joint will burn out in seconds.
4. **Always** feed PCA9685's `V+` from the battery, and its `VCC` from the Pi's 3.3V (logic). Two separate supplies, two separate jobs.

---

## 9. Pre-Flight Verification (run 24 hrs before hack day)

Tick every box. If any fails, fix it before the hack starts — not during.

- [ ] `ssh dumme@dumme.local` works from all 3 MacBooks.
- [ ] VS Code Remote-SSH opens the Pi from all 3 MacBooks.
- [ ] `python -c "from picamera2 import Picamera2; Picamera2()"` runs without error.
- [ ] `i2cdetect -y 1` shows `0x40` when PCA9685 is wired.
- [ ] `~/llama.cpp/build/bin/llama-cli --version` is from April 2026 or later.
- [ ] `models/gemma-4-e2b-it-Q4_K_M.gguf` exists and is ~1.6 GB.
- [ ] `models/gemma-3n-E2B-Q4.gguf` exists and is ~1.5 GB (fallback).
- [ ] `llama-server` smoke test via `curl` returns a completion.
- [ ] `piper` TTS plays a test phrase through USB speaker (stretch only).
- [ ] GitHub push/pull works from the Pi.
- [ ] Kill switch physically cuts servo power when flipped (test with multimeter).
- [ ] Pi stays under 80°C after a 10-minute `llama-cli` load test (`vcgencmd measure_temp`).

---

## 10. Troubleshooting Cheatsheet

| Symptom | Likely cause | Fix |
|---|---|---|
| `ping dumme.local` times out | mDNS blocked or wrong country code | SSH by IP; re-flash with correct WiFi country |
| SSH connection refused | SSH not enabled in Imager settings | Re-flash, tick the SSH box |
| Pi reboots mid-inference | Under-powered PSU | Use the **27W** official PSU, not a Pi 4 charger |
| Pi hits 85°C and throttles | No active cooler | Install the Active Cooler, rerun |
| PCA9685 not found on I2C | I2C not enabled, or SDA/SCL swapped | `sudo raspi-config nonint do_i2c 0`, check wiring |
| `picamera2` import error | Ribbon cable backwards | Flip ribbon, blue tab facing ethernet port |
| Servos twitch at rest | No PWM release after motion | Call `Motion.release_all()` (sets PWM=0) |
| Gemma returns garbage | Context too long, or wrong model | `--ctx-size 2048`, confirm model file |
| `llama-server` OOM killed | E4B loaded by mistake on 4GB Pi | Use E2B Q4_K_M; check `free -h` |

---

**Once every box in §9 is ticked, you're ready to start the hack.** From that point, follow `PLAN.md` for the build itself.
