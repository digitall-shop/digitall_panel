SERVICE=control-api
PYTHON?=python

run:
	$(PYTHON) apps/control-api/main.py

fmt:
	pre-commit run black --files apps/control-api/main.py || true
	pre-commit run ruff-format --files apps/control-api/main.py || true

lint:
	pre-commit run ruff --files apps/control-api/main.py || true

test:
	pytest -q -k control_api_health

proto:
	make generate-proto

