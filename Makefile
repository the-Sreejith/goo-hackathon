# DummE dev targets. Run `make` or `make help` for the list.

.DEFAULT_GOAL := help
.PHONY: help install test test-all eval smoke lint format coverage demo clean

help:
	@echo "DummE — developer targets"
	@echo "  make install      Install package + dev deps (editable)"
	@echo "  make test         Run unit + integration tests (default)"
	@echo "  make test-all     Run every marker (unit+integration+eval+hardware)"
	@echo "  make eval         Run the LLM eval suite (needs llama-server)"
	@echo "  make smoke        scripts/preflight.sh (run on the Pi)"
	@echo "  make coverage     pytest --cov with 80% floor"
	@echo "  make lint         ruff + black check"
	@echo "  make format       ruff format + black write"
	@echo "  make demo         Start llama-server + FastAPI app (mock hardware)"
	@echo "  make clean        Remove caches + build artifacts"

install:
	pip install -e ".[dev]"

test:
	pytest

test-all:
	pytest -m "unit or integration or eval or hardware"

eval:
	pytest -m eval

smoke:
	bash scripts/preflight.sh

coverage:
	pytest --cov=dumme --cov-report=term-missing

lint:
	ruff check .
	ruff format --check .
	black --check .

format:
	ruff check --fix .
	ruff format .
	black .

demo:
	DUMME_MOCK_HARDWARE=true \
	    uvicorn dumme.app:app --host 0.0.0.0 --port 8000

clean:
	rm -rf .pytest_cache .ruff_cache .coverage coverage.xml htmlcov \
	       dumme.egg-info build dist
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
