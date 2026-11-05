import pytest
from fastapi.testclient import TestClient


def test_demo_portal_routes_are_registered():
    from main import app
    paths = {route.path for route in app.routes}
    assert "/app" in paths
    assert "/app/login" in paths
    assert "/app/api/status" in paths
    assert "/app/api/process" in paths


def test_demo_session_signature_and_expiry(monkeypatch):
    from docintel.webapp import _make_session, _valid_session
    monkeypatch.setenv("DOCINTEL_DEMO_SESSION_SECRET", "test-session-secret")
    token = _make_session()
    assert _valid_session(token)
    assert not _valid_session(token + "tampered")


def test_demo_portal_rejects_unauthenticated_api_calls():
    from main import app
    client = TestClient(app)
    response = client.get("/app/api/status")
    assert response.status_code == 401


def test_demo_login_requires_configured_credentials(monkeypatch):
    from main import app
    monkeypatch.delenv("DOCINTEL_DEMO_PASSWORD", raising=False)
    monkeypatch.delenv("DOCINTEL_DEMO_SESSION_SECRET", raising=False)
    client = TestClient(app)
    response = client.post("/app/login", data={"password": "anything"})
    assert response.status_code == 503
