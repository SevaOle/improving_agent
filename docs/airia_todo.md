# Airia Setup Guide (Step-by-step, Hackathon Friendly)

This is the practical setup path for **PulsePal + Airia + Gemini**.

## TL;DR architecture decision

**Use your backend DB (SQLite/Postgres), not Airia as your primary database.**

Why:
- You already have tables and API routes in FastAPI.
- You control timeline/insights queries directly.
- If Airia is down, app can still run on fallback logic.

So Airia is the **orchestrator layer**, not your source-of-truth storage.

---

## 1) What you need ready before Airia config

- Running backend URL (local tunnel or deployed), e.g.:
  - `https://<your-backend-host>`
- At least one user in DB (or use `POST /auth/demo`).
- Gemini key in backend env (`GEMINI_API_KEY`) or Gemini configured inside Airia.

---

## 2) Create exactly 2 agents in Airia

## Agent A: `MessagePipelineAgent`

### Input contract

```json
{
  "user_id": 123,
  "content": "I feel dizzy today and slept poorly",
  "source": "text"
}
```

### Job it should do

1. Load user context from backend:
   - memory
   - last 10 messages
   - recent events
   - latest daily report
2. Run **Extractor** prompt (Gemini):
   - return structured `events`, `risk_flags`, `memory_patch`.
3. Persist extraction:
   - save events
   - merge memory patch
4. Run **Responder** prompt (Gemini):
   - return `reply`, follow-up questions, suggested actions, risk level.
5. Persist assistant reply message.
6. Return response payload to backend/app.

### Output contract

```json
{
  "reply": "string",
  "follow_up_questions": ["..."],
  "suggested_actions": ["..."],
  "risk_level": "low|medium|high",
  "safety_footer": "string",
  "extracted": {
    "events": [],
    "risk_flags": [],
    "memory_patch": {}
  }
}
```

---

## Agent B: `DailyReviewAgent`

### Input contract

```json
{
  "user_id": 123,
  "days": 30
}
```

### Job it should do

1. Load last 30 days of events/messages/feedback.
2. Compute simple deterministic metrics first (frequency/co-occurrence).
3. Run daily pattern analysis prompt (Gemini).
4. Return:
   - pattern summary
   - non-diagnostic suggestions
   - tomorrow check-in questions
   - check-in message text
   - memory patch
5. Persist report + post check-in assistant message.

### Output contract

```json
{
  "pattern_summary": ["..."],
  "what_changed": ["..."],
  "suggested_next_steps": ["..."],
  "tomorrow_questions": ["..."],
  "check_in_message": "...",
  "risk_level": "low|medium|high",
  "memory_patch": {}
}
```

---

## 3) Tool/API boundaries (who does what)

## Backend responsibilities (source of truth)
- Users/auth/tokens
- Message storage
- Events storage
- User memory merge + storage
- Daily report storage
- Timeline/insights query APIs

## Airia responsibilities
- Agent sequencing/workflows
- Calling Gemini with your prompts
- Returning validated JSON payloads

---

## 4) How backend sends data through Airia

Your backend should call Airia agent invoke endpoint with:

- `AIRIA_BASE_URL`
- `AIRIA_API_KEY`
- `AIRIA_AGENT_ID_MESSAGE`
- `AIRIA_AGENT_ID_DAILY`

Current code path already does this in `backend/integrations.py` and `backend/app.py`.

Example call shape used by backend:

```json
{
  "mode": "extract",
  "user_message": "...",
  "user_memory_json": {},
  "recent_events": [],
  "recent_messages": []
}
```

and later:

```json
{
  "mode": "respond",
  "user_message": "...",
  "extracted": {},
  "user_memory_json": {},
  "recent_messages": [],
  "daily_report": {}
}
```

---

## 5) Step-by-step to configure in Airia UI

1. Create `MessagePipelineAgent`.
2. Set model provider to Gemini.
3. Add prompt instructions for extractor + responder (or two subflows if supported).
4. Ensure strict JSON output per contract.
5. Save and copy agent ID -> put in `.env` as `AIRIA_AGENT_ID_MESSAGE`.
6. Create `DailyReviewAgent`.
7. Add daily-analysis prompt + output schema.
8. Save and copy agent ID -> `.env` as `AIRIA_AGENT_ID_DAILY`.
9. In backend `.env`, set:
   - `AIRIA_BASE_URL`
   - `AIRIA_API_KEY`
   - both agent IDs
10. Restart backend and verify:
    - `GET /health` shows Airia configured flags true.
    - `POST /chat/send` returns `pipeline.extractor_provider = "airia"`.

---

## 6) Which URLs/links you need to provide

You should have these ready:

1. **Backend public URL** (for Airia tools/webhooks if needed)
2. **Airia workspace/base URL**
3. **Airia Agent IDs** (`message`, `daily`)
4. (Optional) **Frontend app URL** for demo
5. (Optional) **Modulate endpoint URL** when voice is added

If your backend runs locally, use a tunnel (e.g., ngrok/cloudflared) and keep URL stable during judging.

---

## 7) Reliability rules for hackathon demo

- Set 8s timeout on Airia/Gemini calls.
- On failure:
  - still store user message
  - run local fallback extraction/responder
  - return response with `pipeline.*_provider = "fallback"`
- Keep one seeded demo user for predictable results.

This guarantees your demo remains responsive even if sponsor APIs wobble.
