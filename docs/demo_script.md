# DummE — Demo Day Runbook

## 30 min before

- [ ] Power up Pi + servo rail, open SSH from all 3 MacBooks.
- [ ] `python -m scripts.i2c_probe` — PCA9685 seen at `0x40`.
- [ ] `python -m scripts.camera_preview` — scp the JPG, inspect framing.
- [ ] `python -m scripts.servo_sweep` — each joint rotates through full range, no binding.
- [ ] Launch llama-server: `~/llama.cpp/build/bin/llama-server -m models/gemma-4-e2b-it-Q4_K_M.gguf --ctx-size 2048 --threads 4 --host 127.0.0.1 --port 8080`.
- [ ] `python -m scripts.prompt_test` — ≥ 18/20 pass.
- [ ] Recalibrate HSV: `python -m scripts.camera_preview` under the demo lighting, tweak `config/vision.yaml`.
- [ ] Start the FastAPI app: `uvicorn dumme.app:app --host 0.0.0.0 --port 8000`.
- [ ] Run `python -m scripts.demo_run` — result `ok=True`.

## 10 min before

- [ ] Motion to home pose; call `release_all()` so servos aren't jittering on stage.
- [ ] Close unused apps on the Pi (`pgrep -af python` — kill strays).
- [ ] White workspace backdrop laid out, desk lamp on.
- [ ] Target blocks + cups placed within reach envelope.
- [ ] Phone/laptop has `http://dumme.local:8000` open.
- [ ] **Backup video cued up** in case live run fails.

## The Demo (90 seconds)

1. **Introduce the arm** (10s) — "This is DummE. 100% cardboard. 4-DOF arm on a rotating chassis. The Pi 5 you see on the base runs Gemma 4 E2B locally — zero cloud."
2. **Open the UI** (5s) — show the camera feed, say what we're about to ask for.
3. **Type the command** (10s) — "pick up the red block and put it in the blue cup".
4. **Gemma parses** (5s) — briefly show the returned JSON on screen. Mention: on-device, ~3 seconds.
5. **Arm acts** (45s) — chassis sweeps, finds red, picks, rotates, drops in blue, returns home.
6. **Close the pitch** (15s) — "Everything you saw ran on the Pi. No cloud, no API calls, no network round-trip. That's the Gemma 4 story at the edge."

## If the live run fails

Do not freeze. Say: *"Let me show you the run we recorded this morning — same code, same hardware."* Hit play on the backup video. The pitch continues.

## Common on-stage recovery

| Symptom | Quick fix |
|---|---|
| Arm doesn't move | Check kill switch; POST `/estop/clear`. |
| "I can't see the X object" | Move the block; adjust lamp; re-send. |
| Gripper drops the ball | Add a foam pad (cue in pocket); reduce lift speed in `config/servos.yaml`. |
| Servo jitter when idle | `release_all()` wasn't called — POST `/command {"utterance":"go home"}` then stop. |
| Camera feed black | Ribbon cable reversed. Flip it. (Pre-flight should catch this.) |
