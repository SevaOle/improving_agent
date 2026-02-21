# PulsePal API Keys / Secrets Checklist

## Required for demo

1. **Gemini API key**
   - Env: `GEMINI_API_KEY`
   - Used by: extractor + responder + daily pattern prompts

2. **Airia credentials**
   - Env examples: `AIRIA_BASE_URL`, `AIRIA_AGENT_ID_MESSAGE`, `AIRIA_AGENT_ID_DAILY`, `AIRIA_API_KEY`
   - Used by: orchestrated agent calls from backend

## Optional (Phase 2)

3. **Modulate API key**
   - Env: `MODULATE_API_KEY`
   - Used by: voice moderation flags before transcript persistence

4. **Speech-to-Text provider key** (if needed)
   - Env example: `GOOGLE_STT_API_KEY`
   - Used by: voice check-in transcription pipeline

## Backend runtime keys

5. **JWT/app secret**
   - Env: `APP_SECRET`
   - Used by: token signing (replace current hackathon token table)

6. **Database URL**
   - Env: `DATABASE_URL`
   - Default now: local sqlite file for speed

## Fast env file template

```bash
GEMINI_API_KEY=
AIRIA_BASE_URL=
AIRIA_API_KEY=
AIRIA_AGENT_ID_MESSAGE=
AIRIA_AGENT_ID_DAILY=
MODULATE_API_KEY=
GOOGLE_STT_API_KEY=
APP_SECRET=change-me
DATABASE_URL=sqlite:///backend/pulsepal.db
```

## Security shortcut notes

- For the hackathon, `.env` local + one shared demo account is acceptable.
- Before production: rotate keys, add vault, and remove plain token table auth.
