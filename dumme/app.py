"""FastAPI entrypoint for DummE.

Routes:
    POST /command   {"utterance": str} → ExecutionResult JSON
    GET  /stream    MJPEG multipart of the camera feed
    GET  /status    {"estop": bool, "base_angle_deg": float, "last_result": str|null}
    POST /estop     Trips the e-stop flag. Returns {"estop": true}.
    GET  /          Serves static/index.html
    GET  /static/*  Serves static assets

Run locally (dev):
    uvicorn dumme.app:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from dumme.calibration.regression import Calibration
from dumme.io.mic import Mic
from dumme.io.tts import TTS
from dumme.llm.client import LlamaClient
from dumme.llm.parser import LLM
from dumme.motion.driver import PCA9685Driver
from dumme.motion.primitives import Motion
from dumme.motion.safety import Safety
from dumme.orchestrator import Orchestrator
from dumme.utils.config import REPO_ROOT, load_yaml
from dumme.utils.logging import get_logger
from dumme.vision.camera import MJPEG_BOUNDARY, Camera
from dumme.vision.detector import Vision

_log = get_logger(__name__)
STATIC_DIR: Path = Path(os.environ.get("DUMME_STATIC_DIR", REPO_ROOT / "static"))


# ── DI container ──────────────────────────────────────────────────────────
class Services:
    """Constructed at startup — one instance lives on app.state."""

    def __init__(self) -> None:
        servo_cfg = load_yaml("servos")
        vision_cfg = load_yaml("vision")
        calibration_cfg = load_yaml("calibration")

        mock_hardware = os.environ.get("DUMME_MOCK_HARDWARE", "auto")
        use_mock = self._decide_mock(mock_hardware)

        driver = PCA9685Driver(
            pwm_frequency_hz=int(servo_cfg.get("pwm_frequency_hz", 50)),
            mock=use_mock,
        )
        safety = Safety(
            joint_limits=servo_cfg.get("joint_limits", {}),
            rate_limit_deg_per_sec=float(servo_cfg.get("rate_limit_deg_per_sec", 90.0)),
        )
        if os.environ.get("ESTOP_ON_START", "false").lower() == "true":
            safety.estop.set()

        self.motion = Motion(driver=driver, servo_cfg=servo_cfg["servos"], safety=safety)
        self.camera = Camera(
            width=vision_cfg["camera"]["width"],
            height=vision_cfg["camera"]["height"],
            framerate=vision_cfg["camera"]["framerate"],
            exposure_us=vision_cfg["camera"].get("exposure_us"),
            mock=use_mock,
        )
        self.vision = Vision(camera=self.camera, vision_cfg=vision_cfg)
        self.calibration = Calibration(raw=calibration_cfg)
        self.llm = LLM(client=LlamaClient())
        voice_path = os.environ.get("DUMME_PIPER_VOICE")
        self.tts = TTS(
            voice_path=voice_path,
            enabled=os.environ.get("DUMME_TTS", "true").lower() != "false",
        )
        vosk_model_path = os.environ.get(
            "DUMME_VOSK_MODEL", str(REPO_ROOT / "models" / "vosk-model-small-en-us")
        )
        self.mic = Mic(model_path=vosk_model_path, mock=use_mock)
        self.orchestrator = Orchestrator(
            motion=self.motion,
            vision=self.vision,
            calibration=self.calibration,
            on_status=self.tts.say,
        )
        _log.info("Services initialized (mock_hardware=%s)", use_mock)

    @staticmethod
    def _decide_mock(flag: str) -> bool:
        if flag == "true":
            return True
        if flag == "false":
            return False
        # auto — detect via platform
        import platform

        return platform.machine() != "aarch64"

    def shutdown(self) -> None:
        try:
            self.motion.release_all()
        except Exception as exc:  # noqa: BLE001
            _log.warning("motion release_all failed: %s", exc)
        try:
            self.camera.close()
        except Exception as exc:  # noqa: BLE001
            _log.warning("camera close failed: %s", exc)


# ── lifespan + app ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001 — FastAPI requires this signature
    services = Services()
    app.state.services = services
    try:
        yield
    finally:
        services.shutdown()


app = FastAPI(title="DummE", version="0.1.0", lifespan=lifespan)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.exception_handler(NotImplementedError)
async def _not_implemented_handler(request: Request, exc: NotImplementedError) -> JSONResponse:
    """Unimplemented TODOs return 200 with ok=False instead of 500.

    Makes the scaffold usable end-to-end: the browser UI shows which piece
    each teammate still needs to fill in, instead of a crash.
    """
    _log.warning("%s %s: NotImplementedError: %s", request.method, request.url.path, exc)
    return JSONResponse({"ok": False, "message": f"Not yet implemented: {exc}"})


# ── schemas ───────────────────────────────────────────────────────────────
class CommandRequest(BaseModel):
    utterance: str


class CommandResponse(BaseModel):
    ok: bool
    message: str


class ListenRequest(BaseModel):
    max_seconds: float = 5.0


class ListenResponse(BaseModel):
    ok: bool
    message: str
    transcript: str


class StatusResponse(BaseModel):
    estop: bool
    base_angle_deg: float
    turntable_angle_deg: float
    llm_healthy: bool
    last_result: str | None


# ── routes ────────────────────────────────────────────────────────────────
@app.get("/")
def index() -> FileResponse:
    index_path = STATIC_DIR / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)


@app.post("/command", response_model=CommandResponse)
def post_command(req: CommandRequest, request: Request) -> CommandResponse:
    services: Services = request.app.state.services
    cmd = services.llm.parse(req.utterance)
    result = services.orchestrator.execute(cmd)
    return CommandResponse(ok=result.ok, message=result.message)


@app.post("/listen", response_model=ListenResponse)
def post_listen(req: ListenRequest, request: Request) -> ListenResponse:
    """Record from the mic, transcribe, parse, and execute — one-shot push-to-talk."""
    services: Services = request.app.state.services
    try:
        transcript = services.mic.listen(max_seconds=req.max_seconds)
    except RuntimeError as exc:
        _log.warning("/listen: mic unavailable: %s", exc)
        return ListenResponse(ok=False, message=str(exc), transcript="")
    if not transcript:
        return ListenResponse(ok=False, message="No speech detected.", transcript="")
    cmd = services.llm.parse(transcript)
    result = services.orchestrator.execute(cmd)
    return ListenResponse(ok=result.ok, message=result.message, transcript=transcript)


@app.get("/stream")
def get_stream(request: Request) -> StreamingResponse:
    services: Services = request.app.state.services
    return StreamingResponse(
        services.camera.mjpeg_frames(),
        media_type=f"multipart/x-mixed-replace; boundary={MJPEG_BOUNDARY}",
    )


@app.get("/status", response_model=StatusResponse)
def get_status(request: Request) -> StatusResponse:
    services: Services = request.app.state.services
    snap = services.motion.snapshot()
    last = services.orchestrator.last_result
    return StatusResponse(
        estop=bool(snap["estop"]),
        base_angle_deg=float(snap["base_angle_deg"]),
        turntable_angle_deg=float(snap["turntable_angle_deg"]),
        llm_healthy=services.llm.client.healthy(),
        last_result=last.message if last else None,
    )


@app.post("/estop")
def post_estop(request: Request) -> JSONResponse:
    services: Services = request.app.state.services
    services.motion.estop()
    return JSONResponse({"estop": True})


@app.post("/estop/clear")
def post_estop_clear(request: Request) -> JSONResponse:
    """Explicit recovery — the UI must not auto-clear to prevent footguns."""
    services: Services = request.app.state.services
    services.motion.safety.estop.clear()
    return JSONResponse({"estop": False})
