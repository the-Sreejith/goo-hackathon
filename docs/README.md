# DummE Docs

One entry per topic. Read `plan.md` and `pi_setup.md` first — every other
doc assumes you've done those.

## Start here

- [starting_point.md](./starting_point.md) — hackathon brief, inventory, prize criteria, final project pitch
- [plan.md](./plan.md) — day-of build plan: MVP slice, roles, schedule, cut list
- [pi_setup.md](./pi_setup.md) — shopping list, headless Pi flash, WiFi, llama.cpp build, Gemma download, systemd services

## Reference (during the build)

- [architecture.md](./architecture.md) — module map, request trace, hardware–software contract
- [wiring.md](./wiring.md) — GPIO pinout, power rails, kill switch, camera, servo channel map
- [testing.md](./testing.md) — test tiers, markers, eval harness, preflight script, coverage gate
- [demo_script.md](./demo_script.md) — pre-demo checklist, 90-second pitch, on-stage recovery
- [submission.md](./submission.md) — hackathon submission write-up (copy-paste into Google Docs)

## Hardware / code map

| Where | What |
|---|---|
| `dumme/app.py` | FastAPI entrypoint, `Services` container, lifespan |
| `dumme/orchestrator.py` | Command → action pipeline (the only module that knows the shape) |
| `dumme/llm/` | Gemma client + JSON-schema-constrained parser |
| `dumme/vision/` | OpenCV USB-camera capture + HSV blob detector |
| `dumme/motion/` | PCA9685 driver + Motion primitives + Safety clamps |
| `dumme/calibration/` | Pixel → (r, θ) affine regression |
| `dumme/io/` | Piper TTS + Vosk STT |
| `config/` | YAML configs + Gemma prompt template |
| `scripts/` | Hardware smoke utilities + `preflight.sh` + prompt eval |
| `tests/` | Unit + integration + eval + hardware tiers |
| `systemd/` | `dumme-llama.service`, `dumme-app.service` |
