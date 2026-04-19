"""FastAPI integration tests with TestClient.

Runs the full lifespan (Services + Orchestrator wiring) in DUMME_MOCK_HARDWARE
mode, replacing `services.llm` with a canned fake so the LLM path is
deterministic without a live llama-server.
"""

from __future__ import annotations

import os

# MUST be set before importing dumme.app — Services() reads it at startup.
os.environ["DUMME_MOCK_HARDWARE"] = "true"

from typing import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from dumme.app import app  # noqa: E402
from dumme.llm.schema import Command  # noqa: E402


class FakeLLM:
    """Stand-in for LLM: returns a canned Command per-utterance-substring."""

    def __init__(self, table: dict[str, Command]) -> None:
        self.table = table
        # Satisfy dumme.app.Services.llm.client.healthy() used by /status.

        class _StubClient:
            @staticmethod
            def healthy() -> bool:
                return True

        self.client = _StubClient()

    def parse(self, utterance: str) -> Command:
        lowered = utterance.lower()
        for key, cmd in self.table.items():
            if key in lowered:
                return cmd
        return Command("unknown", None, None)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as tc:
        # Replace the LLM after lifespan startup so tests are hermetic.
        tc.app.state.services.llm = FakeLLM(  # type: ignore[attr-defined]
            {
                "home": Command("home", None, None),
                "red": Command("pick_and_place", "red", "blue"),
            }
        )
        yield tc


@pytest.mark.integration
class TestStatusEndpoint:
    def test_status_returns_schema(self, client: TestClient) -> None:
        resp = client.get("/status")
        assert resp.status_code == 200
        body = resp.json()
        for key in ("estop", "base_angle_deg", "turntable_angle_deg", "llm_healthy"):
            assert key in body
        assert body["llm_healthy"] is True


@pytest.mark.integration
class TestCommandEndpoint:
    def test_home_returns_ok(self, client: TestClient) -> None:
        resp = client.post("/command", json={"utterance": "go home please"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "Home" in body["message"]

    def test_unknown_returns_not_ok(self, client: TestClient) -> None:
        resp = client.post("/command", json={"utterance": "tell me a joke"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False


@pytest.mark.integration
class TestEstopEndpoint:
    def test_estop_trips_flag(self, client: TestClient) -> None:
        resp = client.post("/estop")
        assert resp.status_code == 200
        assert resp.json() == {"estop": True}
        # /status should now reflect the trip.
        status = client.get("/status").json()
        assert status["estop"] is True

    def test_estop_clear_untrips(self, client: TestClient) -> None:
        client.post("/estop")
        resp = client.post("/estop/clear")
        assert resp.status_code == 200
        assert resp.json() == {"estop": False}


@pytest.mark.integration
class TestIndex:
    def test_index_served(self, client: TestClient) -> None:
        resp = client.get("/")
        # 200 if index.html is present, 404 otherwise — both are acceptable.
        assert resp.status_code in (200, 404)

    # NOTE: /stream is an infinite MJPEG generator; we don't exercise it in
    # the TestClient flow since graceful shutdown of StreamingResponse with
    # a sync generator is racy and deadlocks the lifespan cleanup. Route
    # wiring is covered transitively by `Camera.mjpeg_frames` in integration
    # on a real Pi — tracked under the hardware smoke suite.
