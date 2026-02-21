from fastapi.testclient import TestClient

from backend import integrations
from backend.app import app


def test_signup_chat_daily_flow():
    client = TestClient(app)

    signup = client.post(
        "/auth/signup",
        json={"email": "demo@pulsepal.dev", "password": "secret12", "timezone": "UTC"},
    )
    assert signup.status_code == 200
    token = signup.json()["token"]
    user_id = signup.json()["user_id"]
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
    assert "pipeline" in run_daily.json()

    insight = client.get("/insights/latest", headers=headers)
    assert insight.status_code == 200
    assert insight.json()["report"] is not None

    timeline = client.get("/timeline?days=7", headers=headers)
    assert timeline.status_code == 200
    assert len(timeline.json()["events"]) >= 1

    assert isinstance(user_id, int)


def test_demo_login_health_and_internal_endpoints():
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True

    demo = client.post("/auth/demo")
    assert demo.status_code == 200
    assert demo.json()["demo"] is True

    integrations.CONFIG.internal_api_key = "internal-test-key"
    internal_headers = {"x-internal-key": "internal-test-key"}

    ctx = client.post("/internal/user/context", json={"user_id": demo.json()["user_id"]}, headers=internal_headers)
    assert ctx.status_code == 200

    seed = client.post("/internal/demo/seed", json={"user_id": demo.json()["user_id"]}, headers=internal_headers)
    assert seed.status_code == 200
    assert seed.json()["seeded_messages"] == 3

    save_msg = client.post(
        "/internal/message/save",
        json={"user_id": demo.json()["user_id"], "role": "assistant", "content": "hello from tool", "source": "text"},
        headers=internal_headers,
    )
    assert save_msg.status_code == 200

    merge = client.post(
        "/internal/memory/merge",
        json={"user_id": demo.json()["user_id"], "patch": {"preferences": {"style": "concise"}}},
        headers=internal_headers,
    )
    assert merge.status_code == 200
