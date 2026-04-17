import os
import time
import signal
import logging
import json
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Security, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from app.config import settings
from app.auth import verify_api_key
from app.rate_limiter import check_rate_limit
from app.cost_guard import check_and_record_cost

# Mock LLM
from utils.mock_llm import ask as llm_ask

# ── Logging ──
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False

# ── Redis Client ──
redis_client = settings.get_redis_client()

# ── Session Management (Stateless) ──
def load_session(session_id: str) -> dict:
    if redis_client:
        data = redis_client.get(f"session:{session_id}")
        return json.loads(data) if data else {}
    return {}

def save_session(session_id: str, data: dict, ttl: int = 3600):
    if redis_client:
        redis_client.setex(f"session:{session_id}", ttl, json.dumps(data))

def append_to_history(session_id: str, role: str, content: str):
    session = load_session(session_id)
    history = session.get("history", [])
    history.append({
        "role": role,
        "content": content,
        "ts": datetime.now(timezone.utc).isoformat()
    })
    # Keep last 10 turns
    if len(history) > 20:
        history = history[-20:]
    session["history"] = history
    save_session(session_id, session)
    return history

# ── Lifespan ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(json.dumps({"event": "startup", "app": settings.app_name}))
    _is_ready = True
    yield
    _is_ready = False
    logger.info(json.dumps({"event": "shutdown"}))

# ── App Init ──
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

# ── Models ──
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None

class AskResponse(BaseModel):
    session_id: str
    question: str
    answer: str
    turn: int
    model: str
    timestamp: str

# ── Endpoints ──

@app.get("/", tags=["Ops"])
def root():
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "platform": "Railway",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/health", tags=["Ops"])
def health():
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "platform": "Railway",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/ready", tags=["Ops"])
def ready():
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    if redis_client:
        try:
            redis_client.ping()
        except:
            raise HTTPException(503, "Redis down")
    return {"ready": True}

@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    request: Request,
    _key: str = Depends(verify_api_key),
):
    # 1. Rate Limiting (Redis-backed)
    check_rate_limit(_key[:8])

    # 2. Session & History
    session_id = body.session_id or str(uuid.uuid4())
    history = append_to_history(session_id, "user", body.question)

    # 3. Cost Guard (Pre-check)
    check_and_record_cost(_key[:8], len(body.question.split()), 0)

    # 4. LLM Call
    # In production, you'd pass the full history to the model
    answer = llm_ask(body.question)

    # 5. Cost Guard (Post-record)
    check_and_record_cost(_key[:8], 0, len(answer.split()))
    
    # 6. Save Answer
    append_to_history(session_id, "assistant", answer)

    return AskResponse(
        session_id=session_id,
        question=body.question,
        answer=answer,
        turn=len([m for m in history if m["role"] == "user"]),
        model=settings.llm_model,
        timestamp=datetime.now(timezone.utc).isoformat()
    )

@app.get("/history/{session_id}", tags=["Agent"])
def get_history(session_id: str, _key: str = Depends(verify_api_key)):
    session = load_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session

def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum}))

signal.signal(signal.SIGTERM, _handle_signal)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
