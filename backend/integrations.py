from __future__ import annotations

import json
import os
from typing import Any

import httpx


class IntegrationConfig:
    def __init__(self) -> None:
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.airia_base_url = os.getenv("AIRIA_BASE_URL", "")
        self.airia_api_key = os.getenv("AIRIA_API_KEY", "")
        self.airia_agent_id_message = os.getenv("AIRIA_AGENT_ID_MESSAGE", "")
        self.airia_agent_id_daily = os.getenv("AIRIA_AGENT_ID_DAILY", "")


CONFIG = IntegrationConfig()


class IntegrationError(Exception):
    pass


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout_s: int = 8) -> dict[str, Any]:
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=timeout_s)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        raise IntegrationError(str(exc)) from exc


def call_gemini_structured(system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
    if not CONFIG.gemini_api_key:
        raise IntegrationError("Missing GEMINI_API_KEY")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{CONFIG.gemini_model}:generateContent?key={CONFIG.gemini_api_key}"
    )
    prompt = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            f"{system_prompt}\n\n"
                            "Return valid JSON only.\n"
                            f"INPUT:\n{json.dumps(user_payload)}"
                        )
                    }
                ],
            }
        ]
    }

    data = _post_json(url, prompt, headers={"Content-Type": "application/json"})
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
    except Exception as exc:
        raise IntegrationError(f"Gemini parse failure: {exc}") from exc


def call_airia_agent(agent_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not (CONFIG.airia_base_url and CONFIG.airia_api_key and agent_id):
        raise IntegrationError("Missing Airia configuration")
    url = f"{CONFIG.airia_base_url.rstrip('/')}/agents/{agent_id}/invoke"
    headers = {
        "Authorization": f"Bearer {CONFIG.airia_api_key}",
        "Content-Type": "application/json",
    }
    return _post_json(url, payload, headers=headers)
