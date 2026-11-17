# BRUCE API

Secure OpenAI-compatible chat gateway and SQLite conversation/memory store.

## Setup

```powershell
cd services/api
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set:
- `BRUCE_API_KEY`: long random secret used by BRUCE clients.
- `BRUCE_MODEL_BASE_URL`: provider-compatible API base URL.
- `BRUCE_MODEL_API_KEY`: provider credential (server only).
- `BRUCE_MODEL_NAME`: exact model identifier supported by your provider.

Start:
```powershell
uvicorn main:app --host 127.0.0.1 --port 8787
```

The API refuses chat until a real model credential and model ID are configured. Do not expose this service publicly without HTTPS, authentication, rate limiting, and a production database.

## Context and memory

The gateway retains conversation messages in SQLite and includes the latest configured message window plus saved memory records in each request. Context limits are still constrained by the selected model's context window. This service does not create a new neural network or increase the underlying model's intelligence; it securely connects BRUCE to a model provider.

## Routes

- `GET /health` — non-secret status.
- `POST /v1/chat` — authenticated model request.
- `GET /v1/conversations` and `GET /v1/conversations/{id}`.
- `POST /v1/memories`, `GET /v1/memories`.

All authenticated routes require `Authorization: Bearer <BRUCE_API_KEY>`.
