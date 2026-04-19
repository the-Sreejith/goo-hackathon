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
| **Hot glue gun + 10 sticks** | Cardboard joinery (prototype only — see note) | ~₹400 |
| **Bamboo skewers or chopsticks** | Internal bracing for arm segments (prototype only) | ~₹50 |
| **5-ply corrugated cardboard** (~1 sqm) | Prototype frame material | scrap |

> **Prototype note** — The cardboard frame is fine for electronics bring-up but flexes under the arm's own weight (~5–10° of joint slop at the elbow). For a sturdy build, print the parts in [`3d-models/sg90-robot-arm-model_files/`](../3d-models/sg90-robot-arm-model_files/) instead: STL + 3MF for any slicer, Fusion 360 sources (`*.f3d`, `*.f3z`) if you want to edit, plus a printable assembly PDF. The servo channel map and `config/servos.yaml` don't change.
| **SPST toggle switch** (5A rated) | Inline kill switch on servo V+ — you WILL need it | ~₹50 |
| **M2 / M3 screws + washers** | Servo mounting (most SG90s ship with these — check first) | — |

### 1.2 Demo-Day Props

| Item | Why |
|---|---|
| Ping-pong ball + small foam cubes in **red, blue, green** | Target objects for pick-and-place |
| 3–4 small coloured cups/bowls | Destinations |
| Desk lamp | Even lighting kills HSV flakiness |
| White A3 paper or foam board | Workspace backdrop — huge win for colour detection |

### 1.3 Camera (pick one)

| Item | Why | Notes |
|---|---|---|
| **Raspberry Pi Camera Module** | CSI ribbon, lowest latency, native `picamera2` path | Default per BOM. Ribbon blue-tab faces ethernet. |
| **USB UVC webcam** | Works out of the box via OpenCV V4L2, appears as `/dev/video0` | Current build uses this. No CSI wiring needed. |

### 1.4 Voice Stretch (skip unless P2 is green by hour 7)

| Item | Why |
|---|---|
| Cheap USB microphone | Pi 5 has no onboard mic input |
| USB speaker (or 3.5mm powered speaker + USB audio dongle) | ⚠️ **Pi 5 removed the 3.5mm audio jack** — you cannot just plug headphones in |

### 1.5 Nice-to-Have (debugging lifesavers)

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
4. **Choose OS** → `Raspberry Pi OS (64-bit)` — Trixie (Debian 13) as of writing. Use the full-with-desktop variant; enables VNC later if you need it.
5. **Choose Storage** → the 64GB card.
6. Click **Next** → when prompted "Would you like to apply OS customisation settings?" → **EDIT SETTINGS**. This step is the entire game.

   **General tab**:
   - ✅ Set hostname: `dumme` (reachable as `dumme.local`)
   - ✅ Set username: `dumme` + a strong password (save it to `pi-passwords.txt` — gitignored)
   - ✅ Configure wireless LAN: your WiFi SSID + password + **country code** (`IN`, `AE`, etc.)
   - ✅ Set locale: `Asia/Kolkata` (or `Asia/Dubai`), keyboard `us`

   > ⚠️ If your WiFi is WPA3-only (common on recent Android hotspots), switch it to **WPA2-Personal** or **WPA2/WPA3 transitional** — Pi OS firstboot writes a WPA2-PSK config and silently fails to join WPA3-only APs.
   > ⚠️ If you flash with `dd` instead of the Imager GUI, see Appendix A (at the bottom of this doc) for how to wire up `firstrun.sh` + `cmdline.txt` manually.

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
# CSI camera: no-op on Bookworm/Trixie — libcamera + picamera2 just work.
# USB UVC camera: also no-op — kernel exposes it as /dev/video0 automatically.

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

Easiest: rsync the repo from your Mac (avoids setting up a GitHub deploy key on the Pi).

```bash
# On Mac — from the repo root
rsync -az --exclude '.venv' --exclude '.git' --exclude 'models/*.gguf' \
      --exclude '__pycache__' --exclude '.env' --exclude 'pi-passwords.txt' \
      ./ dumme@dumme.local:/home/dumme/dumme/
```

Then on the Pi:

```bash
cd ~/dumme
# --system-site-packages lets the venv see apt-installed picamera2.
python3 -m venv --system-site-packages .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt    # fastapi, opencv, adafruit-*, piper-tts, ...
```

Add the venv auto-activate to `.bashrc` so SSH sessions land inside it:

```bash
grep -q 'source ~/dumme/.venv/bin/activate' ~/.bashrc \
  || echo 'source ~/dumme/.venv/bin/activate' >> ~/.bashrc
```

### 5.3 Passwordless sudo for the `dumme` user

Raspberry Pi OS (post-Bookworm) no longer ships a default passwordless-sudo file for non-`pi` users. Add one so the rest of setup doesn't prompt:

```bash
echo "dumme ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/010_dumme-nopasswd
sudo chmod 440 /etc/sudoers.d/010_dumme-nopasswd
```

---

## 6. Build llama.cpp + Download Gemma

### 6.1 Build llama.cpp

```bash
cd ~
git clone --depth=1 https://github.com/ggml-org/llama.cpp
cd llama.cpp
cmake -B build -DGGML_NATIVE=ON
cmake --build build -j4
# ~5–8 minutes on Pi 5
```

```bash
./build/bin/llama-cli --version
```

### 6.2 Download Gemma 3n E2B Q4_K_M (~2.8 GB)

Gemma 3n is the current edge-friendly variant supported by llama.cpp; it's the model we've validated on Pi 5.

```bash
mkdir -p ~/dumme/models && cd ~/dumme/models
wget -O gemma-3n-E2B-it-Q4_K_M.gguf \
  'https://huggingface.co/unsloth/gemma-3n-E2B-it-GGUF/resolve/main/gemma-3n-E2B-it-Q4_K_M.gguf'
```

> ⚠️ **On a phone hotspot this download is punishing** (several hours at ~400 KB/s). Two faster options:
> 1. Download on the Mac over real WiFi, then `scp` to the Pi over Hephaestus — the hotspot hop is LAN-only and much quicker than an internet-bridged one.
> 2. Use a USB stick — Mac to stick to Pi is ~1 min each way.

### 6.3 Smoke-test Gemma

```bash
~/llama.cpp/build/bin/llama-cli \
  -m ~/dumme/models/gemma-3n-E2B-it-Q4_K_M.gguf \
  --ctx-size 1024 \
  --threads 4 \
  -p "Return ONLY valid JSON: {\"status\": \"ok\"}" \
  --n-predict 20 --no-conversation
```

First load mmaps ~3 GB and can take 30–60 s; subsequent prompts are faster.

### 6.4 Run llama-server (what the app actually hits)

Production path: enable the systemd service (see §8).

Ad-hoc path:

```bash
~/llama.cpp/build/bin/llama-server \
  -m ~/dumme/models/gemma-3n-E2B-it-Q4_K_M.gguf \
  --ctx-size 2048 \
  --threads 4 \
  --host 127.0.0.1 \
  --port 8080
```

From another SSH session:

```bash
curl -sf http://127.0.0.1:8080/health
# → {"status":"ok"}

curl -s http://127.0.0.1:8080/v1/chat/completions \
     -H 'Content-Type: application/json' \
     -d '{"messages":[{"role":"user","content":"Say only OK."}],"max_tokens":10}' \
     | python3 -m json.tool
```

If `/health` is `ok` and the chat endpoint returns text, the LLM stack is done.

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

## 8. systemd services (autostart on boot)

Install the two unit files that ship in the repo and enable them:

```bash
sudo cp ~/dumme/systemd/dumme-llama.service /etc/systemd/system/
sudo cp ~/dumme/systemd/dumme-app.service   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now dumme-llama.service
sudo systemctl enable --now dumme-app.service

systemctl status dumme-llama.service dumme-app.service --no-pager
```

Logs:

```bash
journalctl -u dumme-llama.service -n 50 --no-pager
journalctl -u dumme-app.service   -n 50 --no-pager
```

Both services expect the code at `/home/dumme/dumme/` and the venv at
`/home/dumme/dumme/.venv`. Update the unit files if you deployed elsewhere.

---

## 9. Power Wiring (read before plugging anything in)

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

## 10. Pre-Flight Verification (run 24 hrs before hack day)

Run the automated check:

```bash
bash scripts/preflight.sh
```

It covers the machine-verifiable items below. Tick the manual ones by hand.

**Automated** (by `preflight.sh`):
- [ ] `llama-server` `/health` responds on `http://127.0.0.1:8080`.
- [ ] FastAPI app `/status` responds on `http://127.0.0.1:8000`.
- [ ] `i2cdetect -y 1` shows `0x40` (PCA9685).
- [ ] `/dev/video0` is present.
- [ ] `cv2.VideoCapture(0).read()` returns a frame.

**Manual:**
- [ ] `ssh dumme@dumme.local` works from every teammate's Mac.
- [ ] VS Code Remote-SSH opens the Pi.
- [ ] `models/gemma-3n-E2B-it-Q4_K_M.gguf` exists and is ~2.8 GB.
- [ ] Gemma completion latency is ≤ 5 s for a 20-token reply.
- [ ] Piper TTS plays a test phrase through the USB speaker (stretch).
- [ ] Kill switch physically cuts servo power (test with multimeter).
- [ ] Pi stays under 80 °C after a 10-minute LLM load test (`vcgencmd measure_temp`).
- [ ] `pytest` is green; `pytest -m eval` scores ≥ 18/20.

---

## 11. Troubleshooting Cheatsheet

| Symptom | Likely cause | Fix |
|---|---|---|
| `ping dumme.local` times out | mDNS blocked, wrong country code, or WPA3-only AP | SSH by IP; switch hotspot to WPA2; re-flash with correct WiFi country |
| SSH permission denied | Key not copied, or password from Imager wrong | Re-copy key (`ssh-copy-id dumme@dumme.local`); check `pi-passwords.txt` |
| Pi never joins WiFi | `cmdline.txt` missing `systemd.run=firstrun.sh` (dd-flash only) | See Appendix A for the manual wiring |
| Pi reboots mid-inference | Under-powered PSU | Use the **27W** official PSU, not a Pi 4 charger |
| Pi hits 85 °C and throttles | No active cooler | Install the Active Cooler, rerun |
| PCA9685 not found on I2C | I2C not enabled, or SDA/SCL swapped | `sudo raspi-config nonint do_i2c 0`, check wiring |
| USB camera not at `/dev/video0` | Hub/cable issue | `lsusb` should show a UVC-class device; `v4l2-ctl --list-devices` confirms the node |
| `picamera2` import error | Pi Camera ribbon backwards | If using CSI: flip ribbon, blue tab faces ethernet |
| Servos twitch at rest | No PWM release after motion | `Motion.release_all()` (sets PWM=0) |
| Gemma returns garbage | Context too long, prompt missing few-shots | Keep `--ctx-size 2048`; check `config/prompts/command_parser.txt` |
| `llama-server` OOM killed | 4 GB Pi + wrong quant | Use `Q4_K_M`; check `free -h`; `OOMScoreAdjust=500` in the unit file |
| Hotspot isolates the Pi | Venue WiFi blocks client↔client | Use a phone hotspot, not venue WiFi, for Mac↔Pi traffic |

---

## Appendix A — dd-based flash (no Imager GUI)

Sometimes the GUI is blocked (no admin on the Mac, CI, automated setup). You can still flash headlessly:

```bash
# On Mac
curl -L -o /tmp/pi-os.img.xz \
  'https://downloads.raspberrypi.com/raspios_arm64_latest'
diskutil list external physical            # find the SD card → /dev/diskN
diskutil unmountDisk /dev/diskN
xz -dc /tmp/pi-os.img.xz | sudo dd of=/dev/rdiskN bs=4m status=progress
```

Then write `firstrun.sh` + patch `cmdline.txt` on the boot partition — an example `firstrun.sh` that configures hostname, user, SSH, and a NetworkManager WiFi profile lives at [scripts/preflight.sh](../scripts/preflight.sh) neighbourhood (check git history of `boot-partition-firstrun.sh` if you need a template). Essence:

```
systemd.run=/boot/firmware/firstrun.sh systemd.run_success_action=reboot systemd.unit=kernel-command-line.target
```

appended to `cmdline.txt`. `firstrun.sh` writes `/etc/NetworkManager/system-connections/<SSID>.nmconnection` (chmod 600), sets the hostname, enables SSH, and `rm`s itself at the end. See the troubleshooting note above for why plain `wpa_supplicant.conf` no longer works on Trixie.

---

**Once the preflight script is green and every manual box ticked, you're ready to start the hack.** From that point, follow `plan.md` for the build itself.
