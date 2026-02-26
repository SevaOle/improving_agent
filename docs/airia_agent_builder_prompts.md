# PulsePal: Full AI Prompts to Build Airia Tables + Agent Flowcharts

Use these prompts directly with an AI assistant (or inside Airia prompt builder) to generate complete, implementation-ready specs.

---

## Prompt 1 — System Architect Prompt (Master)

```text
You are a senior AI systems architect for a hackathon project called PulsePal.

Goal:
Design complete Airia agent architecture, backend data contracts, and flowcharts for a wellness app.

Non-negotiable constraints:
1) Airia is orchestration, not source-of-truth DB.
2) Backend DB stores all canonical data.
3) No medical diagnosis. Conservative recommendations only.
4) If AI fails, return deterministic fallback plan.
5) Every flow must specify input -> processing -> output.

Project summary:
- PulsePal is a mobile-first wellness companion.
- User does text check-ins (voice later).
- Message pipeline has 2 AI steps:
  A) Extractor: convert message to structured events + memory patch + risk flags.
  B) Responder: generate supportive reply + follow-up + suggested actions + risk level.
- Daily loop analyzes recent history and generates check-in for tomorrow.
- Sponsors: Airia (orchestration), Gemini (LLM), Modulate (voice moderation, optional).

Required output sections (return ALL):
1) Architecture diagram narrative.
2) Airia agents list with responsibilities.
3) Tool endpoint map (backend internal endpoints).
4) Data model tables with field-level definitions.
5) Message pipeline flowchart (step-by-step).
6) Daily review flowchart (step-by-step).
7) Failure/fallback paths.
8) Security model and required keys.
9) API payload contracts (strict JSON examples).
10) Build order for 48-hour hackathon.

Output format requirements:
- Use Markdown.
- Use explicit headings.
- For each flow step, include:
  - Input
  - Processing
  - Output
  - Failure handling
- Include at least one Mermaid flowchart for each major flow.
```

---

## Prompt 2 — Airia Tables + Contracts Prompt

```text
Create implementation-ready table specs for PulsePal.

Context:
- Backend DB is canonical.
- Airia agents read/write through internal backend APIs.
- Need robust schemas for analytics and timeline rendering.

Generate tables:
1) users
2) messages
3) events
4) user_memory
5) daily_reports
6) feedback
7) pipeline_runs (new)
8) tool_call_logs (new)

For each table provide:
- Purpose
- Columns (name, type, nullability)
- Indexes
- Example row JSON
- Data lifecycle notes (retention / archival)

Special requirements:
- messages must support text and voice transcript source.
- events must store source_message_id and tag arrays.
- daily_reports must include risk_level and tomorrow_questions.
- pipeline_runs must track provider used (airia/gemini/fallback), latency, status.
- tool_call_logs must track tool_name, request_id, duration_ms, error field.

Also output:
- SQL CREATE TABLE statements (SQLite-compatible)
- Suggested migration order
- Minimal seed data for demo
```

---

## Prompt 3 — MessagePipelineAgent Prompt (Detailed)

```text
Design MessagePipelineAgent in extreme detail for PulsePal.

Goal:
Given {user_id, content, source}, process check-in end-to-end.

Input contract:
{
  "user_id": 123,
  "content": "I feel dizzy and tired today",
  "source": "text"
}

Required processing stages:
1) Validate input.
2) Save user message.
3) Load context (memory + recent events + recent messages + latest daily report).
4) Extractor stage (Gemini): produce structured events + risk_flags + memory_patch.
5) Persist events.
6) Merge memory patch.
7) Responder stage (Gemini): produce reply + follow-up + suggestions + risk level.
8) Save assistant reply.
9) Return unified response.
10) Emit run log to pipeline_runs.

For each stage provide:
- Inputs
- Processing logic
- Outputs
- Expected latency target
- Failure behavior and fallback

Output artifacts required:
- Mermaid flowchart
- Strict JSON schemas for extractor output and responder output
- Pseudocode for orchestration
- Retry policy (timeouts, max retries)
- Red-flag escalation policy (without diagnosing)
```

---

## Prompt 4 — DailyReviewAgent Prompt (Detailed)

```text
Design DailyReviewAgent in extreme detail for PulsePal.

Trigger:
- Scheduled once daily (9 PM local user time)
- Manual trigger endpoint allowed

Input contract:
{
  "user_id": 123,
  "days": 30
}

Required processing stages:
1) Load last 30 days events/messages/feedback.
2) Compute deterministic stats first (frequencies, co-occurrence, trend deltas).
3) Generate daily analysis with Gemini.
4) Validate output schema.
5) Merge returned memory_patch into user_memory.
6) Save report into daily_reports.
7) Post assistant check-in message for tomorrow.
8) Write pipeline run log.

Return format must include:
- pattern_summary
- what_changed
- possible_explanations_non_diagnostic
- suggested_next_steps
- check_in_message
- tomorrow_questions
- risk_level
- memory_patch

Also include:
- Mermaid flowchart
- fallback behavior if Gemini fails
- risk-based escalation text templates (low/medium/high)
```

---

## Prompt 5 — Airia Tool Mapping Prompt

```text
Map Airia tools to backend internal endpoints for PulsePal.

Existing internal endpoints:
- POST /internal/user/context
- POST /internal/message/save
- POST /internal/events/save
- POST /internal/memory/merge
- POST /internal/daily/save
- POST /internal/demo/seed

Security:
- Header required: x-internal-key
- Secret source: INTERNAL_API_KEY

Output required:
1) Tool catalog table:
   - tool_name
   - endpoint
   - input schema
   - output schema
   - when to call
2) Example Airia tool invocation payloads.
3) Error handling matrix for status codes 400/401/503/500.
4) Recommended idempotency strategy.
5) Observability fields to log per tool call.
```

---

## Prompt 6 — Flowchart Generator Prompt (Visual)

```text
Generate Mermaid flowcharts for PulsePal that are presentation-ready for judges.

Need these diagrams:
1) End-to-end chat request path
2) Extract + respond internals
3) Daily review batch path
4) Fallback/error path
5) Voice moderation (future Modulate path)

For each flowchart include:
- Entry point
- Decision nodes
- Data storage points
- Provider branch (Airia vs Gemini vs fallback)
- Output to mobile UI

Also provide one short plain-English explanation under each chart.
```

---

## Prompt 7 — “Generate Ready-to-Implement Airia Spec” (Single-shot)

```text
Produce a final implementation spec for PulsePal Airia integration.

You must output only these sections in order:
1) Assumptions
2) Environment variables required
3) Agent definitions (MessagePipelineAgent, DailyReviewAgent)
4) Tool definitions mapped to backend endpoints
5) Data contracts (all request/response JSON)
6) SQL schema (all required tables)
7) Mermaid flowcharts (chat + daily + fallback)
8) Error handling and retries
9) Security controls
10) 2-day build plan with priorities
11) Demo script for judges (3 minutes)

Constraints:
- No diagnosis language.
- Keep recommendations conservative.
- Include fallback behavior for every AI step.
- Include one “common failure and fix” table.
```

---

## Copy/Paste Add-on: Required JSON Schemas

Use these when asking AI to enforce strict outputs.

### Extractor schema target

```json
{
  "events": [
    {
      "event_type": "symptom|mood|sleep|medication|lifestyle|stress|diet|incident",
      "title": "short label",
      "details": "1-2 sentences",
      "severity": "low|medium|high",
      "time_ref": "today|yesterday|this week|explicit date|unknown",
      "tags": ["tag1", "tag2"]
    }
  ],
  "risk_flags": [
    {
      "flag": "fainting|chest_pain|breathing|self_harm|severe_allergic|other",
      "confidence": "low|medium|high",
      "note": "brief explanation"
    }
  ],
  "memory_patch": {
    "preferences": {},
    "recurring_patterns": {},
    "known_triggers": [],
    "helpful_actions": []
  },
  "needs_clarification": ["question1", "question2"]
}
```

### Responder schema target

```json
{
  "reply": "string",
  "follow_up_questions": ["...", "..."],
  "suggested_actions": ["...", "..."],
  "risk_level": "low|medium|high",
  "safety_footer": "string or empty"
}
```

### Daily schema target

```json
{
  "pattern_summary": ["..."],
  "what_changed": ["..."],
  "possible_explanations_non_diagnostic": ["..."],
  "suggested_next_steps": ["..."],
  "check_in_message": "short message",
  "tomorrow_questions": ["..."],
  "risk_level": "low|medium|high",
  "memory_patch": {}
}
```
