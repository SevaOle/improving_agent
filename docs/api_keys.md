# PulsePal Keys, URLs, and Access You Must Have

This is the exact checklist for what you need to collect before final integration.

## 1) Required secrets (must have)

1. `GEMINI_API_KEY`
   - Needed for extractor/responder/daily pattern prompts.
   - If Gemini is configured inside Airia only, you may still keep this as backend fallback.

2. `AIRIA_API_KEY`
   - Used by backend to invoke Airia agents.

3. `AIRIA_AGENT_ID_MESSAGE`
   - Agent ID for `MessagePipelineAgent`.

4. `AIRIA_AGENT_ID_DAILY`
   - Agent ID for `DailyReviewAgent`.

---

## 2) Required URLs/links (must have)

1. `AIRIA_BASE_URL`
   - Example format: `https://<your-airia-domain>`

2. `BACKEND_PUBLIC_URL`
   - Needed if Airia tools call your backend endpoints directly.
   - If not exposing backend as tools yet, still useful for debugging and demo.

3. (Optional but recommended) `FRONTEND_DEMO_URL`
   - For judge handoff and demo reliability.

---

## 3) Runtime/app secrets

1. `APP_SECRET`
   - For stronger auth/session signing (future hardening).

2. `DATABASE_URL`
   - For SQLite/Postgres selection.

---

## 4) Optional sponsor integrations (Phase 2)

1. `MODULATE_API_KEY`
   - Voice moderation/safety.

2. `GOOGLE_STT_API_KEY` (or equivalent)
   - Voice-to-text transcription.

---

## 5) Minimal .env template

```bash
# Core
GEMINI_API_KEY=
AIRIA_BASE_URL=
AIRIA_API_KEY=
AIRIA_AGENT_ID_MESSAGE=
AIRIA_AGENT_ID_DAILY=

# Runtime
APP_SECRET=change-me
DATABASE_URL=sqlite:///backend/pulsepal.db

# Optional
BACKEND_PUBLIC_URL=
FRONTEND_DEMO_URL=
MODULATE_API_KEY=
GOOGLE_STT_API_KEY=
```

---

## 6) What to share with me (or any integrator) to finish quickly

Provide these values/links and integration can be finished fast:

- Airia base URL
- Airia message agent ID
- Airia daily agent ID
- Confirmation whether Gemini is called from Airia only or also backend fallback
- Backend public URL (if using Airia tools hitting backend)
- Modulate key + endpoint docs (only if voice is in scope now)

Do **not** paste actual secret values in chat logs; use `.env` locally.
