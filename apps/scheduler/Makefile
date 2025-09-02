SERVICE=scheduler
PYTHON?=python

run:
	uvicorn apps.scheduler.main:app --host 0.0.0.0 --port 8020

fmt:
	pre-commit run black --files apps/scheduler/main.py || true
	pre-commit run ruff-format --files apps/scheduler/main.py || true

lint:
	pre-commit run ruff --files apps/scheduler/main.py || true

test:
	pytest -q -k scheduler_health

proto:
	make generate-proto

