# DummE — Wiring Reference

Quick reference for every physical connection. **Read [`pi_setup.md`](./pi_setup.md) §9 (Power Wiring) before plugging anything in.**

## Power Rails

```
┌─────────────────┐        ┌──────────────────────────────┐
│ 27W USB-C PSU   │──── 5V ┤ Pi 5 (USB-C input)           │
│ (Pi only)       │        │ Logic, camera, llama-server  │
└─────────────────┘        └──────────────────────────────┘

┌─────────────────┐        ┌──────────────────────────────┐
│ 4×AA (6V) OR    │── 5–6V ┤ PCA9685 V+ (servo rail)      │
│ 5V/3A UBEC      │        │ — kill-switch inline on V+   │
└─────────────────┘        └──────────────────────────────┘

GND — tied together between both rails (mandatory common ground).
```

**Never** feed servos from the Pi 5V pin. Brown-out = CPU reboot mid-LLM-inference.

## I2C Bus (Pi ↔ PCA9685)

| PCA9685 pin | Pi GPIO pin | Pi BCM | Notes |
|---|---|---|---|
| VCC (logic)  | Pin 1   | 3V3   | Powers the PCA9685 logic side |
| GND          | Pin 6   | —     | Common ground |
| SDA          | Pin 3   | GPIO2 | I2C data |
| SCL          | Pin 5   | GPIO3 | I2C clock |
| V+ (servo)   | (external 5–6V rail) | — | DO NOT connect to Pi |

Verify with `i2cdetect -y 1` — should show `40` in the grid.

## Servo Channel Map (PCA9685)

| Channel | Joint | Servo | Physical role |
|---|---|---|---|
| 0 | J1 — base_rotate | SG90 | Arm shoulder pivot relative to chassis |
| 1 | J2 — shoulder    | SG90 | Lifts the upper arm |
| 2 | J3 — elbow       | SG90 | Flexes the forearm |
| 3 | J4 — gripper     | SG90 | Opens/closes gripper jaw |
| 4 | turntable        | MG90S | Rotates the whole chassis |

Each servo has three wires: brown/black (GND), red (V+ from battery rail), orange/yellow (signal to PCA9685 channel).

## Kill Switch

SPST toggle wired inline on the **servo V+ line** (between battery + and PCA9685 V+). Cuts ALL servo power instantly without affecting the Pi. Test with a multimeter before first power-up.

## Camera

Pick one path; `dumme/vision/camera.py` supports both.

### USB UVC webcam (current build)

Plug into any Pi 5 USB-A port. The kernel exposes it as `/dev/video0`. No
`raspi-config` step needed. Verify:

```bash
lsusb                        # "UVC Camera" or "PC Camera" line appears
v4l2-ctl --list-devices      # shows /dev/video0
```

OpenCV opens it via `cv2.VideoCapture(0, cv2.CAP_V4L2)` — see `Camera._open`.

### CSI Pi Camera Module (alternative)

Ribbon → CSI port on Pi 5. **Blue tab faces the Ethernet port.** If reversed,
`picamera2` init fails. Swap `Camera._open` for a `picamera2.Picamera2()`
instance if you go this route; the rest of the vision stack is unchanged.

## Chassis Turntable

- MG90S mounted to the lower cardboard disc.
- Servo horn glued + screwed to the upper disc.
- Skewer/dowel through both disc centers as rotation axis.
- Low-friction washer between discs (plastic lid works).
- Cable loop through the center pin — leaves slack for rotation.

## Optional (stretch)

### Ultrasonic E-stop
HC-SR04 → Pi 5V + GND + GPIO trigger/echo. If reading <20 cm, app trips `EstopFlag`.

### USB Mic / Speaker
- Pi 5 has **no** 3.5mm audio jack. Use a USB sound card or USB speaker.
- Mic: any cheap USB mic works with Vosk.
