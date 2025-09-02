SERVICE=collector
PYTHON?=python

run:
	uvicorn apps.collector.main:app --host 0.0.0.0 --port 8010

fmt:
	pre-commit run black --files apps/collector/main.py || true
	pre-commit run ruff-format --files apps/collector/main.py || true

lint:
	pre-commit run ruff --files apps/collector/main.py || true

test:
	pytest -q -k collector_health

proto:
	make generate-proto

