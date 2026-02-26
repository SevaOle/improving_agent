from __future__ import annotations

"""
Step-by-step test guide for PulsePal integration.

Run these incrementally:
1) pytest -q tests/test_api.py::test_step_01_backend_import_and_health
2) pytest -q tests/test_api.py::test_step_02_required_env_keys_for_live_llm
3) pytest -q tests/test_api.py::test_step_03_internal_api_key_for_airia_tools
4) pytest -q tests/test_api.py::test_step_04_demo_auth_and_basic_chat_flow
5) pytest -q tests/test_api.py::test_step_05_internal_tool_endpoints_roundtrip
"""

import uuid

from fastapi.testclient import TestClient

from backend import integrations
from backend.app import app


def test_step_01_backend_import_and_health() -> None:
    """Sanity: app imports, starts, and health endpoint works."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload.get("ok") is True, f"Expected health.ok=true, got: {payload}"


def test_step_02_required_env_keys_for_live_llm() -> None:
    """
    Fails with actionable messages if live LLM/Airia keys are not configured.

    If this fails, set values in your local .env and restart test process.
    """
    missing = []
    if not integrations.CONFIG.gemini_api_key:
        missing.append("GEMINI_API_KEY")
    if not integrations.CONFIG.airia_api_key:
        missing.append("AIRIA_API_KEY")
    if not integrations.CONFIG.airia_base_url:
        missing.append("AIRIA_BASE_URL")
    if not integrations.CONFIG.airia_agent_id_message:
        missing.append("AIRIA_AGENT_ID_MESSAGE")
    if not integrations.CONFIG.airia_agent_id_daily:
        missing.append("AIRIA_AGENT_ID_DAILY")

    assert not missing, (
        "Missing required env vars for LIVE integration test: "
        + ", ".join(missing)
        + ".\nSet them in .env, then re-run this test."
    )


def test_step_03_internal_api_key_for_airia_tools() -> None:
    """
    Fails if INTERNAL_API_KEY is not set.

    This key secures /internal/* endpoints used by Airia tools.
    """
    assert integrations.CONFIG.internal_api_key, (
        "INTERNAL_API_KEY is missing. Set it in .env so Airia tool endpoints are protected and usable."
    )


def test_step_04_demo_auth_and_basic_chat_flow() -> None:
    """Checks auth, chat, daily report, insights, timeline."""
    client = TestClient(app)

    email = f"demo-{uuid.uuid4().hex[:8]}@pulsepal.dev"
    signup = client.post("/auth/signup", json={"email": email, "password": "secret12", "timezone": "UTC"})
    assert signup.status_code == 200, signup.text

    token = signup.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    send = client.post(
        "/chat/send",
        json={"content": "I feel dizzy and tired after poor sleep", "source": "text"},
        headers=headers,
    )
    assert send.status_code == 200, send.text
    send_json = send.json()
    assert "reply" in send_json, f"Missing reply in /chat/send response: {send_json}"
    assert "pipeline" in send_json, f"Missing pipeline metadata in /chat/send response: {send_json}"

    run_daily = client.post("/daily/run", json={}, headers=headers)
    assert run_daily.status_code == 200, run_daily.text

    insight = client.get("/insights/latest", headers=headers)
    assert insight.status_code == 200, insight.text
    assert insight.json().get("report") is not None, "Expected a latest daily report after /daily/run"

    timeline = client.get("/timeline?days=7", headers=headers)
    assert timeline.status_code == 200, timeline.text
    assert len(timeline.json().get("events", [])) >= 1, "Expected at least one extracted event"


def test_step_05_internal_tool_endpoints_roundtrip() -> None:
    """Checks /internal/* tool endpoints with x-internal-key."""
    client = TestClient(app)

    demo = client.post("/auth/demo")
    assert demo.status_code == 200, demo.text
    user_id = demo.json()["user_id"]

    headers = {"x-internal-key": integrations.CONFIG.internal_api_key or ""}

    context = client.post("/internal/user/context", json={"user_id": user_id}, headers=headers)
    assert context.status_code == 200, (
        "Internal context endpoint failed. If 401/503, verify INTERNAL_API_KEY in .env and x-internal-key header. "
        f"Response: {context.status_code} {context.text}"
    )

    seed = client.post("/internal/demo/seed", json={"user_id": user_id}, headers=headers)
    assert seed.status_code == 200, seed.text

    save_msg = client.post(
        "/internal/message/save",
        json={"user_id": user_id, "role": "assistant", "content": "tool test message", "source": "text"},
        headers=headers,
    )
    assert save_msg.status_code == 200, save_msg.text

    save_events = client.post(
        "/internal/events/save",
        json={
            "user_id": user_id,
            "source_message_id": None,
            "events": [
                {
                    "event_type": "mood",
                    "title": "Calmer evening",
                    "details": "User reported feeling calmer",
                    "severity": "low",
                    "time_ref": "today",
                    "tags": ["calm"],
                }
            ],
        },
        headers=headers,
    )
    assert save_events.status_code == 200, save_events.text

    merge_memory = client.post(
        "/internal/memory/merge",
        json={"user_id": user_id, "patch": {"preferences": {"style": "concise"}}},
        headers=headers,
    )
    assert merge_memory.status_code == 200, merge_memory.text

    save_daily = client.post(
        "/internal/daily/save",
        json={
            "user_id": user_id,
            "report_json": {
                "pattern_summary": ["Stress lower than yesterday"],
                "what_changed": ["Better hydration"],
                "suggested_next_steps": ["Keep hydration target"],
                "tomorrow_questions": ["How was sleep latency?"],
                "check_in_message": "How did today compare to yesterday?",
            },
        },
        headers=headers,
    )
    assert save_daily.status_code == 200, save_daily.text
