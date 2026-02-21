# Airia To-Do (Fast Hackathon Version)

## 1) Create two Airia agents

- `MessagePipelineAgent`
- `DailyReviewAgent`

## 2) Wire tool endpoints (backend)

Use these backend operations as tool calls from Airia:

- `db.get_user_context(user_id)`
- `db.save_message(user_id, role, content, source)`
- `db.save_events(user_id, source_message_id, events)`
- `db.merge_user_memory(user_id, patch)`
- `db.save_daily_report(user_id, report_json)`
- `db.post_assistant_message(user_id, content)`

> Hackathon shortcut: keep these as internal backend functions at first, then expose as Airia tools only for final demo.

## 3) MessagePipelineAgent flow

1. Receive `user_id + text`
2. Pull context (last 10 messages, last daily report, memory)
3. Call Gemini Extractor prompt
4. Validate strict JSON schema
5. Persist events + memory patch
6. Call Gemini Responder prompt
7. Persist assistant message
8. Return `{reply, follow_up_questions, suggested_actions, risk_level}`

## 4) DailyReviewAgent flow

1. Trigger daily at 9PM user local time (or manual button)
2. Load last 30 days events/messages/feedback
3. Calculate deterministic metrics first (frequency, co-occurrence)
4. Ask Gemini for pattern narrative + tomorrow questions
5. Save daily report and memory patch
6. Post a short check-in message for next day

## 5) Airia demo checklist

- [ ] Endpoint from app routes to Airia agent URL
- [ ] Agent logs visible for judges
- [ ] One-user demo account pre-seeded with event history
- [ ] Manual button in app calls `/daily/run` for instant wow moment
- [ ] Keep failure fallback: if Airia fails, return local mock responder

## 6) Fallback strategy for hackathon reliability

- Timeout Airia/Gemini at 8s.
- If timeout/failure:
  - save user message anyway
  - run local fallback extraction and response
  - mark run as `fallback=true` in logs

This guarantees the demo never freezes.
