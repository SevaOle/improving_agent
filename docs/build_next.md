# PulsePal Next Build Tasks (Speed-first)

## Backend (today)
- [x] Auth + demo login
- [x] Chat pipeline scaffold
- [x] Daily report generation
- [x] Health endpoint to verify integration wiring
- [ ] Replace daily report generator with Airia `DailyReviewAgent`
- [ ] Save pipeline run logs (`provider`, latency, fallback flag)

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
- [ ] Confirm `/chat/send` returns `pipeline.extractor_provider=airia`

## Voice + Modulate (after text demo works)
- [ ] Expo voice capture
- [ ] Upload to backend
- [ ] Run Modulate moderation before transcript storage
- [ ] Store moderation flags in `messages.modulate_flags_json`
