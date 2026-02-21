# PulsePal Next Build Tasks (Speed-first)

## Backend (today)
- [x] Auth + demo login
- [x] Chat pipeline scaffold
- [x] Daily report generation
- [x] Health endpoint to verify integration wiring
- [x] Internal Airia-tool endpoints (`/internal/*`) protected by `INTERNAL_API_KEY`
- [ ] Add structured run logs (provider, latency, fallback flag)
- [ ] Add JWT auth replacement for token table

## Expo frontend (fast)
- [ ] Auth screen: sign in / sign up / demo login button
- [ ] Chat screen with thread + text input + send
- [ ] Insights screen consuming `/insights/latest`
- [ ] Timeline screen consuming `/timeline`
- [ ] Settings screen with disclaimer + delete button (can be stub)

## Airia wiring (must-do)
- [ ] Deploy `MessagePipelineAgent`
- [ ] Deploy `DailyReviewAgent`
- [ ] Point backend env vars to Airia IDs
- [ ] Add Airia tools mapping to backend internal endpoints:
  - [ ] `POST /internal/user/context`
  - [ ] `POST /internal/message/save`
  - [ ] `POST /internal/events/save`
  - [ ] `POST /internal/memory/merge`
  - [ ] `POST /internal/daily/save`
- [ ] Confirm `/chat/send` returns `pipeline.extractor_provider=airia`
- [ ] Confirm `/daily/run` returns `pipeline.provider=airia`

## Voice + Modulate (after text demo works)
- [ ] Expo voice capture
- [ ] Upload to backend
- [ ] Run Modulate moderation before transcript storage
- [ ] Store moderation flags in `messages.modulate_flags_json`
