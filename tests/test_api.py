from fastapi.testclient import TestClient

from backend.app import app


def test_signup_chat_daily_flow():
    client = TestClient(app)

    signup = client.post(
        "/auth/signup",
        json={"email": "demo@pulsepal.dev", "password": "secret12", "timezone": "UTC"},
    )
    assert signup.status_code == 200
    token = signup.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    send = client.post(
        "/chat/send",
        json={"content": "I feel dizzy and tired after poor sleep", "source": "text"},
        headers=headers,
    )
    assert send.status_code == 200
    assert "reply" in send.json()
    assert "pipeline" in send.json()

    run_daily = client.post("/daily/run", json={}, headers=headers)
    assert run_daily.status_code == 200

    insight = client.get("/insights/latest", headers=headers)
    assert insight.status_code == 200
    assert insight.json()["report"] is not None

    timeline = client.get("/timeline?days=7", headers=headers)
    assert timeline.status_code == 200
    assert len(timeline.json()["events"]) >= 1


def test_demo_login_and_health():
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True

    demo = client.post("/auth/demo")
    assert demo.status_code == 200
    assert demo.json()["demo"] is True
