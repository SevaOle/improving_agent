# PulsePal (Hackathon Build)

Mobile-first wellness companion with a fast backend scaffold optimized for speed.

## What is included right now

- FastAPI backend with:
  - auth (signup/login, no email verify)
  - demo user login endpoint for judges (`POST /auth/demo`)
  - chat endpoint with a **2-step pipeline shape** (extract -> respond)
  - provider routing: Airia -> Gemini -> fallback mock logic
  - event + memory persistence
  - daily analysis endpoint
  - timeline and insights read endpoints
- SQLite database auto-created on startup.
- Hackathon docs for:
  - Airia setup to-dos
  - API keys checklist

> Important: Airia/Gemini run only when keys are set. Otherwise pipeline falls back to local mocks to keep demo reliability.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app:app --reload --port 8000
```

Open docs at `http://localhost:8000/docs`.

## API flow

1. `POST /auth/signup` -> get token
2. `POST /chat/send` with `Authorization: Bearer <token>`
3. `POST /daily/run` to generate daily report
4. `GET /insights/latest` and `GET /timeline`

For judge demo:

1. `POST /auth/demo`
2. Use returned bearer token
3. Hit `/chat/send` and `/daily/run`

## Integration status endpoint

- `GET /health` returns which integrations are configured (Gemini/Airia IDs/keys).


## Internal tool endpoints (for Airia tools)

Set `INTERNAL_API_KEY` in backend env, then Airia tools can call:

- `POST /internal/user/context`
- `POST /internal/message/save`
- `POST /internal/events/save`
- `POST /internal/memory/merge`
- `POST /internal/daily/save`
- `POST /internal/demo/seed`

Send header: `x-internal-key: <INTERNAL_API_KEY>`.

## Repo layout

- `backend/app.py` – routes, db schema, and pipeline orchestration
- `backend/integrations.py` – Airia/Gemini HTTP integrations
- `docs/airia_todo.md` – exactly what to configure in Airia
- `docs/api_keys.md` – exactly what keys/secrets you need
- `tests/test_api.py` – smoke tests for critical endpoints
