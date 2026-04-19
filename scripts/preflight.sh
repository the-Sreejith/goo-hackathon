#!/usr/bin/env bash
# DummE pre-demo smoke checks. Run on the Pi ~5 min before showtime.
# Exits nonzero on the first failure so the team notices immediately.

set -u
status=0

pass() { printf '  \033[32mOK\033[0m   %s\n' "$1"; }
fail() { printf '  \033[31mFAIL\033[0m %s\n' "$1"; status=1; }

printf '== DummE preflight ==\n'

# 1. llama-server
if curl -sf http://127.0.0.1:8080/health >/dev/null; then
    pass "llama-server /health"
else
    fail "llama-server not reachable at http://127.0.0.1:8080/health"
fi

# 2. FastAPI app
if status_json=$(curl -sf http://127.0.0.1:8000/status); then
    pass "FastAPI /status ($status_json)"
else
    fail "FastAPI app not reachable at http://127.0.0.1:8000/status"
fi

# 3. PCA9685 on I2C
if i2cdetect -y 1 2>/dev/null | awk 'NR>1' | grep -qw 40; then
    pass "PCA9685 detected at 0x40 on I2C bus 1"
else
    fail "PCA9685 not detected on I2C bus 1 (expected addr 0x40)"
fi

# 4. USB camera
if [ -e /dev/video0 ]; then
    pass "/dev/video0 present"
else
    fail "No /dev/video0 — USB camera not connected?"
fi

# 5. Camera actually captures
python3 - <<'PY' 2>/dev/null && pass "cv2.VideoCapture(0) reads a frame" || fail "cv2.VideoCapture(0) could not read a frame"
import sys
try:
    import cv2
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    ok, frame = cap.read()
    cap.release()
    sys.exit(0 if ok and frame is not None else 1)
except Exception:
    sys.exit(1)
PY

printf '\n'
if [ $status -eq 0 ]; then
    printf '\033[32mAll preflight checks passed.\033[0m\n'
else
    printf '\033[31mPreflight FAILED — fix above before demo.\033[0m\n'
fi
exit $status
