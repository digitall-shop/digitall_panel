SERVICE=node-agent
PYTHON?=python

run:
	$(PYTHON) apps/node-agent/main.py

fmt:
	pre-commit run black --files apps/node-agent/main.py || true
	pre-commit run ruff-format --files apps/node-agent/main.py || true

lint:
	pre-commit run ruff --files apps/node-agent/main.py || true

test:
	pytest -q -k node_agent_heartbeat

proto:
	make generate-proto

