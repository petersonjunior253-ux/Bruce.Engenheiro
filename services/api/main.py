from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Literal

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BRUCE_", env_file=".env", extra="ignore")
    api_key: str = "development-only-change-me"
    model_base_url: str = "http://127.0.0.1:11434/v1"
    model_api_key: str = ""
    model_name: str = "llama3.2"
    system_prompt: str = (
        "You are BRUCE, the user's personal assistant. Be capable, direct, thoughtful, "
        "proactive, and transparent. Use the conversation context. Never claim an action "
        "was completed unless a connected tool confirms it. Ask approval before sensitive, "
        "external, financial, or irreversible actions."
    )
    max_context_messages: int = 80
    max_output_tokens: int = 4096
    database_path: str = "./data/bruce.sqlite3"


settings = Settings()
db_path = Path(settings.database_path)
db_path.parent.mkdir(parents=True, exist_ok=True)
app = FastAPI(title="BRUCE Personal Intelligence API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("BRUCE_ALLOWED_ORIGINS", "https://bruce-preview-six.vercel.app,https://bruce-preview-petersonjunior253-8756s-projects.vercel.app,http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


def connect_db():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect_db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY, title TEXT NOT NULL DEFAULT 'Nova conversa',
            created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT NOT NULL,
            role TEXT NOT NULL, content TEXT NOT NULL, created_at INTEGER NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL,
            content TEXT NOT NULL, created_at INTEGER NOT NULL
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, id)")
        conn.commit()


@app.on_event("startup")
def startup():
    init_db()


def require_auth(authorization: str | None = Header(default=None)):
    if not settings.api_key or settings.api_key == "development-only-change-me":
        raise HTTPException(503, "Configure BRUCE_API_KEY antes de expor a API.")
    expected = "Bearer " + settings.api_key
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(401, "Credencial inválida.")


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=100000)


class ChatRequest(BaseModel):
    conversation_id: str | None = Field(default=None, max_length=80)
    messages: list[ChatMessage] = Field(min_length=1, max_length=200)


class MemoryRequest(BaseModel):
    category: str = Field(default="general", max_length=60)
    content: str = Field(min_length=1, max_length=12000)


def get_memory_context() -> str:
    with connect_db() as conn:
        rows = conn.execute("SELECT category, content FROM memories ORDER BY id DESC LIMIT 30").fetchall()
    return "\n".join(f"- [{row['category']}] {row['content']}" for row in rows)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "BRUCE Personal Intelligence API",
        "model_configured": bool(settings.model_name),
        "model_name": settings.model_name,
        "model_provider": "OpenAI-compatible endpoint",
        "voice": "client-or-device",
        "database": "sqlite",
        "time": int(time.time()),
    }


@app.post("/v1/chat", dependencies=[Depends(require_auth)])
async def chat(payload: ChatRequest):
    if not settings.model_name:
        raise HTTPException(503, "Modelo não configurado. Defina BRUCE_MODEL_API_KEY e BRUCE_MODEL_NAME no servidor.")
    conversation_id = payload.conversation_id or hashlib.sha256(
        f"{time.time_ns()}".encode()
    ).hexdigest()[:24]
    now = int(time.time())
    with connect_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO conversations(id, created_at, updated_at) VALUES(?,?,?)",
            (conversation_id, now, now),
        )
        history = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?",
            (conversation_id, settings.max_context_messages),
        ).fetchall()
        history = list(reversed(history))
        for item in payload.messages:
            conn.execute(
                "INSERT INTO messages(conversation_id, role, content, created_at) VALUES(?,?,?,?)",
                (conversation_id, item.role, item.content, now),
            )
        conn.execute(
            "UPDATE conversations SET updated_at=?, title=CASE WHEN title=? THEN ? ELSE title END WHERE id=?",
            (now, "Nova conversa", payload.messages[0].content.strip()[:72] or "Nova conversa", conversation_id),
        )
        conn.commit()

    memory = get_memory_context()
    system = settings.system_prompt
    if memory:
        system += "\n\nMemórias fornecidas pelo usuário:\n" + memory
    context_messages = [{"role": row["role"], "content": row["content"]} for row in history]
    context_messages.extend({"role": item.role, "content": item.content} for item in payload.messages)
    messages = [{"role": "system", "content": system}]
    messages.extend(context_messages[-settings.max_context_messages:])
    url = settings.model_base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if settings.model_api_key:
        headers["Authorization"] = f"Bearer {settings.model_api_key}"
    body = {
        "model": settings.model_name,
        "messages": messages,
        "max_tokens": settings.max_output_tokens,
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=15.0)) as client:
            response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()
            result = response.json()
        answer = result["choices"][0]["message"]["content"]
        if isinstance(answer, list):
            answer = "".join(part.get("text", "") for part in answer if isinstance(part, dict))
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Resposta vazia do provedor")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"Provedor de IA retornou HTTP {exc.response.status_code}.") from exc
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise HTTPException(502, "Não foi possível obter uma resposta do modelo configurado.") from exc

    with connect_db() as conn:
        conn.execute(
            "INSERT INTO messages(conversation_id, role, content, created_at) VALUES(?,?,?,?)",
            (conversation_id, "assistant", answer, int(time.time())),
        )
        conn.commit()
    return {"conversation_id": conversation_id, "message": answer, "model": settings.model_name}


@app.get("/v1/conversations", dependencies=[Depends(require_auth)])
def conversations():
    with connect_db() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC LIMIT 100"
        ).fetchall()
    return [dict(row) for row in rows]


@app.get("/v1/conversations/{conversation_id}", dependencies=[Depends(require_auth)])
def conversation(conversation_id: str):
    with connect_db() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at FROM messages WHERE conversation_id=? ORDER BY id",
            (conversation_id,),
        ).fetchall()
    return {"conversation_id": conversation_id, "messages": [dict(row) for row in rows]}


@app.post("/v1/memories", dependencies=[Depends(require_auth)])
def add_memory(payload: MemoryRequest):
    with connect_db() as conn:
        cursor = conn.execute(
            "INSERT INTO memories(category, content, created_at) VALUES(?,?,?)",
            (payload.category, payload.content, int(time.time())),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "saved": True}


@app.get("/v1/memories", dependencies=[Depends(require_auth)])
def memories():
    with connect_db() as conn:
        rows = conn.execute("SELECT id, category, content, created_at FROM memories ORDER BY id DESC LIMIT 100").fetchall()
    return [dict(row) for row in rows]


class ConversationTitleRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)


@app.patch("/v1/conversations/{conversation_id}", dependencies=[Depends(require_auth)])
def rename_conversation(conversation_id: str, payload: ConversationTitleRequest):
    with connect_db() as conn:
        cursor = conn.execute(
            "UPDATE conversations SET title=?, updated_at=? WHERE id=?",
            (payload.title.strip(), int(time.time()), conversation_id),
        )
        conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(404, "Conversa não encontrada.")
    return {"updated": True, "conversation_id": conversation_id}


@app.delete("/v1/conversations/{conversation_id}", dependencies=[Depends(require_auth)])
def delete_conversation(conversation_id: str):
    with connect_db() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id=?", (conversation_id,))
        cursor = conn.execute("DELETE FROM conversations WHERE id=?", (conversation_id,))
        conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(404, "Conversa não encontrada.")
    return {"deleted": True, "conversation_id": conversation_id}


@app.delete("/v1/memories/{memory_id}", dependencies=[Depends(require_auth)])
def delete_memory(memory_id: int):
    with connect_db() as conn:
        cursor = conn.execute("DELETE FROM memories WHERE id=?", (memory_id,))
        conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(404, "Memória não encontrada.")
    return {"deleted": True, "id": memory_id}


@app.get("/v1/capabilities", dependencies=[Depends(require_auth)])
def capabilities():
    return {
        "assistant": "BRUCE",
        "chat": True,
        "persistent_conversations": True,
        "persistent_memory": True,
        "model": {"name": settings.model_name, "base_url": settings.model_base_url, "provider_auth_configured": bool(settings.model_api_key)},
        "tools": {"android_actions": False, "web_search": False, "calendar": False, "notifications": False},
        "note": "Capacidades só são anunciadas como ativas quando há uma integração real conectada.",
    }
