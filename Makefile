PYTHON?=python
PIP?=pip
SERVICES=control-api collector scheduler node-agent

.PHONY: install fmt lint test generate-proto pre-commit

install:
	$(PIP) install -r requirements.txt

fmt:
	pre-commit run black --all-files || true
	pre-commit run ruff-format --all-files || true

lint:
	pre-commit run ruff --all-files || true

pre-commit:
	pre-commit install

test:
	pytest -q

generate-proto:
	python -m grpc_tools.protoc -I proto --python_out=packages/common/vpnpanel_common/proto --grpc_python_out=packages/common/vpnpanel_common/proto proto/node_control.proto

