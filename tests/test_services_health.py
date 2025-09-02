import pytest
from fastapi.testclient import TestClient

# Import service apps
from apps.control_api.main import app as control_app
from apps.collector.main import app as collector_app
from apps.scheduler.main import app as scheduler_app

@pytest.mark.parametrize(
    "app,endpoint", [
        (control_app, "/health"),
        (collector_app, "/health"),
        (scheduler_app, "/health"),
    ]
)
def test_health_endpoints(app, endpoint):
    client = TestClient(app)
    r = client.get(endpoint)
    assert r.status_code == 200
    assert r.json().get("status") == "ok"
