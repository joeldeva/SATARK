from fastapi.testclient import TestClient

import main


def test_health_ready_reports_dependency_failures(monkeypatch):
    monkeypatch.setattr(
        "main.readiness",
        lambda: {
            "ready": False,
            "checks": {
                "database": {"ok": True},
                "redis": {"ok": False, "error": "Redis is unreachable"},
            },
        },
    )

    response = TestClient(main.app).get("/health/ready")

    assert response.status_code == 503
    assert response.json()["ready"] is False
    assert response.json()["checks"]["redis"]["ok"] is False


def test_health_ready_reports_success(monkeypatch):
    monkeypatch.setattr(
        "main.readiness",
        lambda: {
            "ready": True,
            "checks": {
                "database": {"ok": True},
                "redis": {"ok": True},
                "chroma": {"ok": True},
                "ollama": {"ok": True},
            },
        },
    )

    response = TestClient(main.app).get("/health/ready")

    assert response.status_code == 200
    assert response.json()["ready"] is True
