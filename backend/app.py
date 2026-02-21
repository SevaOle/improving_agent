from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, EmailStr, Field

from backend.integrations import CONFIG, IntegrationError, call_airia_agent, call_gemini_structured

DB_PATH = Path(__file__).resolve().parent / "pulsepal.db"

app = FastAPI(title="PulsePal API", version="0.3.0")

RESPONDER_SYSTEM_PROMPT = """
You are PulsePal, a wellness pattern tracker and supportive guide.
Never diagnose and never suggest prescription changes.
Give concise practical advice, ask follow-up questions, and escalate only when risk flags suggest urgency.
Output JSON with keys: reply, follow_up_questions, suggested_actions, risk_level, safety_footer.
""".strip()

EXTRACTOR_SYSTEM_PROMPT = """
Extract structured wellness events and a memory patch from user check-in text.
Output JSON with keys: events, risk_flags, memory_patch, needs_clarification.
""".strip()

DAILY_SYSTEM_PROMPT = """
Analyze the user's recent wellness history and return conservative, non-diagnostic daily guidance.
Output JSON with keys: pattern_summary, what_changed, possible_explanations_non_diagnostic,
suggested_next_steps, check_in_message, tomorrow_questions, risk_level, memory_patch.
""".strip()


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    timezone: str = "UTC"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChatSendRequest(BaseModel):
    content: str
    source: str = "text"


class DailyRunRequest(BaseModel):
    user_id: int | None = None


class FeedbackRequest(BaseModel):
    message_id: int | None = None
    daily_report_id: int | None = None
    helpful: bool
    notes: str = ""


class InternalUserRequest(BaseModel):
    user_id: int


class InternalSaveMessageRequest(BaseModel):
    user_id: int
    role: str
    content: str
    source: str = "text"
    modulate_flags_json: dict[str, Any] | list[Any] | None = None


class InternalSaveEventsRequest(BaseModel):
    user_id: int
    source_message_id: int | None = None
    events: list[dict[str, Any]]


class InternalMergeMemoryRequest(BaseModel):
    user_id: int
    patch: dict[str, Any]


class InternalSaveDailyReportRequest(BaseModel):
    user_id: int
    report_json: dict[str, Any]


class InternalSeedDemoRequest(BaseModel):
    user_id: int


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def merge_dict(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_dict(merged[key], value)
        elif isinstance(value, list) and isinstance(merged.get(key), list):
            merged[key] = list(dict.fromkeys([*merged[key], *value]))
        else:
            merged[key] = value
    return merged


def get_user_id_from_token(authorization: str | None = Header(default=None)) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.removeprefix("Bearer ").strip()
    conn = get_conn()
    row = conn.execute("SELECT user_id FROM auth_tokens WHERE token = ?", (token,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid token")
    return int(row["user_id"])


def require_internal_key(x_internal_key: str | None = Header(default=None)) -> None:
    configured = CONFIG.internal_api_key
    if not configured:
        raise HTTPException(status_code=503, detail="INTERNAL_API_KEY not configured")
    if x_internal_key != configured:
        raise HTTPException(status_code=401, detail="Invalid internal key")


def init_db() -> None:
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            timezone TEXT DEFAULT 'UTC',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS auth_tokens (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            source TEXT DEFAULT 'text',
            modulate_flags_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            source_message_id INTEGER,
            event_type TEXT NOT NULL,
            title TEXT NOT NULL,
            details TEXT,
            severity TEXT DEFAULT 'low',
            time_ref TEXT DEFAULT 'unknown',
            tags_json TEXT DEFAULT '[]',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(source_message_id) REFERENCES messages(id)
        );

        CREATE TABLE IF NOT EXISTS user_memory (
            user_id INTEGER PRIMARY KEY,
            memory_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS daily_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            report_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message_id INTEGER,
            daily_report_id INTEGER,
            helpful INTEGER,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """
    )
    conn.commit()
    conn.close()


@app.on_event("startup")
def startup() -> None:
    init_db()


def build_user_context(conn: sqlite3.Connection, user_id: int) -> dict[str, Any]:
    memory_row = conn.execute("SELECT memory_json FROM user_memory WHERE user_id = ?", (user_id,)).fetchone()
    messages = conn.execute(
        "SELECT id, role, content, created_at FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT 10", (user_id,)
    ).fetchall()
    events = conn.execute(
        "SELECT event_type, title, severity, time_ref, tags_json, created_at FROM events WHERE user_id = ? ORDER BY id DESC LIMIT 40",
        (user_id,),
    ).fetchall()
    latest_report = conn.execute(
        "SELECT report_json FROM daily_reports WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
    ).fetchone()

    return {
        "memory": json.loads(memory_row["memory_json"]) if memory_row else {},
        "messages": [dict(row) for row in reversed(messages)],
        "events": [
            {
                **dict(row),
                "tags": json.loads(row["tags_json"] or "[]"),
            }
            for row in reversed(events)
        ],
        "latest_report": json.loads(latest_report["report_json"]) if latest_report else None,
    }


def save_assistant_message(
    conn: sqlite3.Connection,
    user_id: int,
    content: str,
    source: str = "text",
    modulate_flags_json: dict[str, Any] | list[Any] | None = None,
) -> int:
    cur = conn.execute(
        "INSERT INTO messages (user_id, role, content, source, modulate_flags_json, created_at) VALUES (?, 'assistant', ?, ?, ?, ?)",
        (user_id, content, source, json.dumps(modulate_flags_json) if modulate_flags_json is not None else None, now_iso()),
    )
    return int(cur.lastrowid)


def persist_events(conn: sqlite3.Connection, user_id: int, source_message_id: int | None, events: list[dict[str, Any]]) -> None:
    for event in events:
        conn.execute(
            """
            INSERT INTO events (user_id, source_message_id, event_type, title, details, severity, time_ref, tags_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                source_message_id,
                event.get("event_type", "incident"),
                event.get("title", "Event"),
                event.get("details", ""),
                event.get("severity", "low"),
                event.get("time_ref", "unknown"),
                json.dumps(event.get("tags", [])),
                now_iso(),
            ),
        )


def ensure_memory_row(conn: sqlite3.Connection, user_id: int) -> dict[str, Any]:
    row = conn.execute("SELECT memory_json FROM user_memory WHERE user_id = ?", (user_id,)).fetchone()
    if row:
        return json.loads(row["memory_json"])
    memory = {"preferences": {}, "recurring_patterns": {}}
    conn.execute(
        "INSERT INTO user_memory (user_id, memory_json, updated_at) VALUES (?, ?, ?)",
        (user_id, json.dumps(memory), now_iso()),
    )
    return memory


def deterministic_daily_report(rows: list[sqlite3.Row]) -> dict[str, Any]:
    tag_count: dict[str, int] = {}
    type_count: dict[str, int] = {}
    for row in rows:
        type_count[row["event_type"]] = type_count.get(row["event_type"], 0) + 1
        for tag in json.loads(row["tags_json"] or "[]"):
            tag_count[tag] = tag_count.get(tag, 0) + 1

    top_tags = sorted(tag_count.items(), key=lambda x: x[1], reverse=True)[:3]
    top_types = sorted(type_count.items(), key=lambda x: x[1], reverse=True)[:3]
    return {
        "pattern_summary": [f"{tag} showed up {count} times recently" for tag, count in top_tags] or ["Not enough data yet."],
        "what_changed": [f"Most frequent event types: {', '.join([f'{t} ({c})' for t, c in top_types])}"]
        if top_types
        else ["Still collecting baseline data over your first week."],
        "possible_explanations_non_diagnostic": ["Sleep, hydration, and stress swings often move together."],
        "suggested_next_steps": ["Keep daily check-ins brief but consistent.", "Track one behavior change tomorrow."],
        "check_in_message": "Quick check-in: what felt better or worse today vs yesterday?",
        "tomorrow_questions": ["How was your sleep quality?", "What was your stress peak today?"],
        "risk_level": "low",
        "memory_patch": {"recurring_patterns": {"daily_top_tags": [t[0] for t in top_tags]}},
        "stats": {"event_types": type_count, "tag_frequency": tag_count},
    }


def fake_extractor(message: str) -> dict[str, Any]:
    lower = message.lower()
    events: list[dict[str, Any]] = []
    risk_flags: list[dict[str, Any]] = []
    tags: list[str] = []

    if any(word in lower for word in ["tired", "fatigue", "exhausted"]):
        tags.append("fatigue")
        events.append(
            {
                "event_type": "symptom",
                "title": "Low energy",
                "details": "User mentioned tiredness or fatigue.",
                "severity": "medium",
                "time_ref": "today",
                "tags": ["fatigue"],
            }
        )
    if any(word in lower for word in ["dizzy", "dizziness"]):
        tags.append("dizziness")
        events.append(
            {
                "event_type": "symptom",
                "title": "Dizziness",
                "details": "User reported dizziness.",
                "severity": "medium",
                "time_ref": "today",
                "tags": ["dizziness"],
            }
        )
    if any(word in lower for word in ["anxious", "stress", "stressed"]):
        events.append(
            {
                "event_type": "stress",
                "title": "Stress spike",
                "details": "User mentioned stress or anxiety.",
                "severity": "medium",
                "time_ref": "today",
                "tags": ["stress"],
            }
        )
    if "chest pain" in lower or "can't breathe" in lower:
        risk_flags.append(
            {
                "flag": "chest_pain",
                "confidence": "high",
                "note": "Potentially urgent symptom phrase detected.",
            }
        )

    return {
        "events": events,
        "risk_flags": risk_flags,
        "memory_patch": {
            "recurring_patterns": {"top_tags": tags},
            "preferences": {},
            "known_triggers": [],
            "helpful_actions": [],
        },
        "needs_clarification": [],
    }


def fake_responder(extracted: dict[str, Any]) -> dict[str, Any]:
    risk_level = "high" if extracted.get("risk_flags") else "low"
    return {
        "reply": "Thanks for sharing this. I can't diagnose, but I can help you track patterns and pick a practical next step.",
        "follow_up_questions": [
            "When did this start today?",
            "Anything different with sleep, hydration, or stress this week?",
        ],
        "suggested_actions": [
            "Drink water and have a light snack if you have not eaten recently.",
            "Do a 2-minute breathing reset and note if symptoms shift.",
        ],
        "risk_level": risk_level,
        "safety_footer": "If symptoms become severe, sudden, or scary, seek urgent in-person care right away." if risk_level == "high" else "",
    }


def llm_extract(user_text: str, context: dict[str, Any]) -> tuple[dict[str, Any], str]:
    payload = {
        "user_message": user_text,
        "user_memory_json": context["memory"],
        "recent_events": context["events"],
        "recent_messages": context["messages"],
    }
    try:
        if CONFIG.airia_agent_id_message:
            return call_airia_agent(CONFIG.airia_agent_id_message, {"mode": "extract", **payload}), "airia"
        return call_gemini_structured(EXTRACTOR_SYSTEM_PROMPT, payload), "gemini"
    except IntegrationError:
        return fake_extractor(user_text), "fallback"


def llm_respond(user_text: str, extracted: dict[str, Any], context: dict[str, Any]) -> tuple[dict[str, Any], str]:
    payload = {
        "user_message": user_text,
        "extracted": extracted,
        "user_memory_json": context["memory"],
        "recent_messages": context["messages"],
        "daily_report": context["latest_report"],
    }
    try:
        if CONFIG.airia_agent_id_message:
            return call_airia_agent(CONFIG.airia_agent_id_message, {"mode": "respond", **payload}), "airia"
        return call_gemini_structured(RESPONDER_SYSTEM_PROMPT, payload), "gemini"
    except IntegrationError:
        return fake_responder(extracted), "fallback"


def llm_daily(user_id: int, context: dict[str, Any]) -> tuple[dict[str, Any], str]:
    payload = {
        "user_id": user_id,
        "last_30_days_events": context["events"],
        "recent_messages": context["messages"],
        "user_memory_json": context["memory"],
        "latest_report": context["latest_report"],
    }
    try:
        if CONFIG.airia_agent_id_daily:
            return call_airia_agent(CONFIG.airia_agent_id_daily, payload), "airia"
        return call_gemini_structured(DAILY_SYSTEM_PROMPT, payload), "gemini"
    except IntegrationError:
        return {}, "fallback"


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "db_path": str(DB_PATH),
        "integrations": {
            "gemini_configured": bool(CONFIG.gemini_api_key),
            "airia_configured": bool(CONFIG.airia_base_url and CONFIG.airia_api_key),
            "message_agent_configured": bool(CONFIG.airia_agent_id_message),
            "daily_agent_configured": bool(CONFIG.airia_agent_id_daily),
            "internal_api_key_configured": bool(CONFIG.internal_api_key),
        },
    }


@app.post("/auth/signup")
def signup(body: SignupRequest):
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, timezone, created_at) VALUES (?, ?, ?, ?)",
            (body.email, hash_password(body.password), body.timezone, now_iso()),
        )
        user_id = int(cur.lastrowid)
        ensure_memory_row(conn, user_id)
        token = secrets.token_urlsafe(24)
        conn.execute("INSERT INTO auth_tokens (token, user_id, created_at) VALUES (?, ?, ?)", (token, user_id, now_iso()))
        conn.commit()
        return {"user_id": user_id, "token": token}
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail="Email already exists") from exc
    finally:
        conn.close()


@app.post("/auth/login")
def login(body: LoginRequest):
    conn = get_conn()
    user = conn.execute("SELECT id, password_hash FROM users WHERE email = ?", (body.email,)).fetchone()
    if not user or user["password_hash"] != hash_password(body.password):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = secrets.token_urlsafe(24)
    conn.execute("INSERT INTO auth_tokens (token, user_id, created_at) VALUES (?, ?, ?)", (token, user["id"], now_iso()))
    conn.commit()
    conn.close()
    return {"token": token, "user_id": int(user["id"])}


@app.post("/auth/demo")
def demo_login():
    conn = get_conn()
    email = "demo@pulsepal.app"
    user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if not user:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, timezone, created_at) VALUES (?, ?, ?, ?)",
            (email, hash_password("demo-pass"), "UTC", now_iso()),
        )
        user_id = int(cur.lastrowid)
        ensure_memory_row(conn, user_id)
    else:
        user_id = int(user["id"])

    token = secrets.token_urlsafe(24)
    conn.execute("INSERT INTO auth_tokens (token, user_id, created_at) VALUES (?, ?, ?)", (token, user_id, now_iso()))
    conn.commit()
    conn.close()
    return {"user_id": user_id, "token": token, "demo": True}


@app.post("/chat/send")
def chat_send(body: ChatSendRequest, user_id: int = Depends(get_user_id_from_token)):
    conn = get_conn()
    user_message_cur = conn.execute(
        "INSERT INTO messages (user_id, role, content, source, created_at) VALUES (?, 'user', ?, ?, ?)",
        (user_id, body.content, body.source, now_iso()),
    )
    user_message_id = int(user_message_cur.lastrowid)

    context = build_user_context(conn, user_id)
    extracted, extractor_provider = llm_extract(body.content, context)
    persist_events(conn, user_id, user_message_id, extracted.get("events", []))

    merged_memory = merge_dict(context["memory"], extracted.get("memory_patch", {}))
    conn.execute("UPDATE user_memory SET memory_json = ?, updated_at = ? WHERE user_id = ?", (json.dumps(merged_memory), now_iso(), user_id))

    response_json, responder_provider = llm_respond(body.content, extracted, context)
    reply_text = response_json.get("reply", "I am here for you. Want to do a short check-in?")
    save_assistant_message(conn, user_id, reply_text, modulate_flags_json=extracted.get("risk_flags", []))

    conn.commit()
    conn.close()

    return {
        **response_json,
        "reply": reply_text,
        "pipeline": {"extractor_provider": extractor_provider, "responder_provider": responder_provider},
        "extracted": extracted,
    }


@app.post("/daily/run")
def daily_run(body: DailyRunRequest, user_id: int = Depends(get_user_id_from_token)):
    target_user = body.user_id or user_id
    conn = get_conn()
    context = build_user_context(conn, target_user)

    llm_report, report_provider = llm_daily(target_user, context)
    if llm_report and isinstance(llm_report, dict) and llm_report.get("pattern_summary"):
        report = llm_report
    else:
        rows = conn.execute(
            "SELECT event_type, title, tags_json FROM events WHERE user_id = ? ORDER BY created_at DESC LIMIT 200",
            (target_user,),
        ).fetchall()
        report = deterministic_daily_report(rows)
        report_provider = "fallback"

    merged_memory = merge_dict(context["memory"], report.get("memory_patch", {}))
    conn.execute("UPDATE user_memory SET memory_json = ?, updated_at = ? WHERE user_id = ?", (json.dumps(merged_memory), now_iso(), target_user))
    conn.execute(
        "INSERT INTO daily_reports (user_id, date, report_json, created_at) VALUES (?, DATE('now'), ?, ?)",
        (target_user, json.dumps(report), now_iso()),
    )
    save_assistant_message(conn, target_user, report.get("check_in_message", "Quick check-in: how are you feeling today?"))
    conn.commit()
    conn.close()
    return {**report, "pipeline": {"provider": report_provider}}


@app.get("/chat/thread")
def chat_thread(user_id: int = Depends(get_user_id_from_token)):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, role, content, source, created_at FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT 100",
        (user_id,),
    ).fetchall()
    conn.close()
    return {"messages": [dict(row) for row in reversed(rows)]}


@app.get("/insights/latest")
def latest_insight(user_id: int = Depends(get_user_id_from_token)):
    conn = get_conn()
    row = conn.execute(
        "SELECT id, date, report_json, created_at FROM daily_reports WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    if not row:
        return {"report": None}
    return {"report": {"id": row["id"], "date": row["date"], "created_at": row["created_at"], "data": json.loads(row["report_json"])}}


@app.get("/timeline")
def timeline(days: int = 30, user_id: int = Depends(get_user_id_from_token)):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT id, event_type, title, details, severity, time_ref, tags_json, created_at
        FROM events WHERE user_id = ?
        ORDER BY id DESC LIMIT ?
        """,
        (user_id, max(1, min(days * 10, 500))),
    ).fetchall()
    conn.close()
    payload = []
    for row in rows:
        item = dict(row)
        item["tags"] = json.loads(item.pop("tags_json"))
        payload.append(item)
    return {"events": list(reversed(payload))}


@app.post("/feedback")
def add_feedback(body: FeedbackRequest, user_id: int = Depends(get_user_id_from_token)):
    conn = get_conn()
    conn.execute(
        "INSERT INTO feedback (user_id, message_id, daily_report_id, helpful, notes, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, body.message_id, body.daily_report_id, 1 if body.helpful else 0, body.notes, now_iso()),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


# --- Internal endpoints for Airia tools (secured by INTERNAL_API_KEY) ---


@app.post("/internal/user/context")
def internal_user_context(body: InternalUserRequest, _: None = Depends(require_internal_key)):
    conn = get_conn()
    context = build_user_context(conn, body.user_id)
    conn.close()
    return context


@app.post("/internal/message/save")
def internal_save_message(body: InternalSaveMessageRequest, _: None = Depends(require_internal_key)):
    if body.role not in {"user", "assistant"}:
        raise HTTPException(status_code=400, detail="role must be user or assistant")
    conn = get_conn()
    if body.role == "assistant":
        message_id = save_assistant_message(conn, body.user_id, body.content, body.source, body.modulate_flags_json)
    else:
        cur = conn.execute(
            "INSERT INTO messages (user_id, role, content, source, modulate_flags_json, created_at) VALUES (?, 'user', ?, ?, ?, ?)",
            (body.user_id, body.content, body.source, json.dumps(body.modulate_flags_json) if body.modulate_flags_json is not None else None, now_iso()),
        )
        message_id = int(cur.lastrowid)
    conn.commit()
    conn.close()
    return {"message_id": message_id}


@app.post("/internal/events/save")
def internal_save_events(body: InternalSaveEventsRequest, _: None = Depends(require_internal_key)):
    conn = get_conn()
    persist_events(conn, body.user_id, body.source_message_id, body.events)
    conn.commit()
    conn.close()
    return {"ok": True, "count": len(body.events)}


@app.post("/internal/memory/merge")
def internal_merge_memory(body: InternalMergeMemoryRequest, _: None = Depends(require_internal_key)):
    conn = get_conn()
    current = ensure_memory_row(conn, body.user_id)
    merged = merge_dict(current, body.patch)
    conn.execute("UPDATE user_memory SET memory_json = ?, updated_at = ? WHERE user_id = ?", (json.dumps(merged), now_iso(), body.user_id))
    conn.commit()
    conn.close()
    return {"ok": True, "memory": merged}


@app.post("/internal/daily/save")
def internal_save_daily(body: InternalSaveDailyReportRequest, _: None = Depends(require_internal_key)):
    conn = get_conn()
    conn.execute(
        "INSERT INTO daily_reports (user_id, date, report_json, created_at) VALUES (?, DATE('now'), ?, ?)",
        (body.user_id, json.dumps(body.report_json), now_iso()),
    )
    if body.report_json.get("check_in_message"):
        save_assistant_message(conn, body.user_id, body.report_json["check_in_message"])
    conn.commit()
    conn.close()
    return {"ok": True}


@app.post("/internal/demo/seed")
def internal_seed_demo(body: InternalSeedDemoRequest, _: None = Depends(require_internal_key)):
    conn = get_conn()
    samples = [
        "I was dizzy after skipping lunch and sleeping 5 hours.",
        "Stress was high and I had low energy in the afternoon.",
        "Felt better after hydration and a short walk.",
    ]
    for text in samples:
        msg_cur = conn.execute(
            "INSERT INTO messages (user_id, role, content, source, created_at) VALUES (?, 'user', ?, 'text', ?)",
            (body.user_id, text, now_iso()),
        )
        extracted = fake_extractor(text)
        persist_events(conn, body.user_id, int(msg_cur.lastrowid), extracted.get("events", []))
    conn.commit()
    conn.close()
    return {"ok": True, "seeded_messages": len(samples)}
