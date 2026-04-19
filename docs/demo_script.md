# DummE — Demo Day Runbook

## 30 min before

- [ ] Power up Pi + servo rail, open SSH from all 3 MacBooks.
- [ ] `bash scripts/preflight.sh` — green on all 5 checks. If not, fix now.
- [ ] `python -m scripts.servo_sweep` — each joint rotates through full range, no binding.
- [ ] `python -m scripts.prompt_test` — ≥ 18/20 pass. (Or `pytest -m eval` for the report artifact.)
- [ ] Recalibrate HSV: `python -m scripts.camera_preview` under the demo lighting, tweak `config/vision.yaml`.
- [ ] Confirm systemd services are running: `systemctl status dumme-llama.service dumme-app.service --no-pager`.
- [ ] Run `python -m scripts.demo_run` — result `ok=True`.

## 10 min before

- [ ] Motion to home pose; call `release_all()` so servos aren't jittering on stage.
- [ ] Close unused apps on the Pi (`pgrep -af python` — kill strays).
- [ ] White workspace backdrop laid out, desk lamp on.
- [ ] Target blocks + cups placed within reach envelope.
- [ ] Phone/laptop has `http://dumme.local:8000` open.
- [ ] **Backup video cued up** in case live run fails.

## The Demo (90 seconds)

1. **Introduce the arm** (10s) — "This is DummE. 100% cardboard. 4-DOF arm on a rotating chassis. The Pi 5 you see on the base runs Gemma 3n E2B locally — zero cloud."
2. **Open the UI** (5s) — show the camera feed, say what we're about to ask for.
3. **Type the command** (10s) — "pick up the red block and put it in the blue cup". (Optional wow beat: repeat it in a second language — *"लाल ब्लॉक उठाओ"* or the judge's first language — to show Gemma 3n's 147-language coverage in one device.)
4. **Gemma parses** (5s) — briefly show the returned JSON on screen. Mention: on-device, ~1–3 seconds at ~5 tok/s on CPU.
5. **Arm acts** (45s) — chassis sweeps, finds red, picks, rotates, drops in blue, returns home.
6. **Close the pitch** (15s) — "Everything you saw ran on the Pi. No cloud, no API calls, no network round-trip. That's the Gemma story at the edge."

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
