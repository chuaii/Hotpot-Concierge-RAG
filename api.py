# -*- coding: utf-8 -*-
"""
FastAPI 后端：火锅点餐顾问 Web API + RAG 问答。
支持基于 session_id 的多轮对话。
"""
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# 加载 .env 中的 GOOGLE_API_KEY 等
load_dotenv()

from langchain_core.messages import AIMessage

from concierge import generate_order_struct, run_concierge_once


# ---------- 内存 Session Store ----------
# 生产环境可替换为 Redis / Firestore
_sessions: dict[str, dict] = {}


def _get_session(session_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = {}
    return _sessions[session_id]


# ---------- 请求/响应 Schema ----------

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    order_json: Optional[dict] = None


# ---------- 确认关键词 ----------
CONFIRM_KEYWORDS = {"确认", "可以", "就这些", "好的", "行", "ok", "yes", "confirm", "sure"}


def _is_confirm(text: str) -> bool:
    t = text.strip().lower()
    return t in CONFIRM_KEYWORDS or any(k in t for k in ("确认", "可以", "就这些"))


def _last_ai_message(state: dict) -> str | None:
    for m in reversed(state.get("messages") or []):
        if isinstance(m, AIMessage) and m.content:
            return m.content
    return None


# ---------- FastAPI App ----------

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    _sessions.clear()


app = FastAPI(
    title="Hotpot Concierge API",
    description="智能火锅点餐顾问 Web 服务",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    多轮对话接口。
    - 首次请求可不传 session_id（自动生成）。
    - 后续请求需带 session_id 以维持上下文。
    - 用户发送"确认"等关键词 → 生成结构化订单。
    """
    session_id = req.session_id or str(uuid.uuid4())
    state = _get_session(session_id)

    user_msg = req.message.strip()
    if not user_msg:
        return ChatResponse(session_id=session_id, reply="请输入您的需求。")

    # 已有方案 + 用户确认 → 生成结构化订单
    if state and _is_confirm(user_msg):
        cart = state.get("cart") or []
        profile = state.get("customer_profile") or {}
        if cart and profile:
            try:
                order = generate_order_struct(profile, cart)
                order_dict = order.model_dump()
                _sessions[session_id] = state  # keep state
                return ChatResponse(
                    session_id=session_id,
                    reply="已按您的要求生成订单，如下可交厨房执行 ✅",
                    order_json=order_dict,
                )
            except Exception as e:
                return ChatResponse(session_id=session_id, reply=f"生成订单时出错：{e}")

    # 正常对话轮次
    try:
        new_state = run_concierge_once(user_msg, state if state else None)
    except Exception as e:
        return ChatResponse(session_id=session_id, reply=f"抱歉出了点问题：{e}，请再说一次。")

    if new_state is None:
        return ChatResponse(session_id=session_id, reply="抱歉，未能处理您的请求，请再试一次。")

    _sessions[session_id] = new_state

    reply = _last_ai_message(new_state) or "正在为您准备方案…"
    return ChatResponse(session_id=session_id, reply=reply)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# ---------- 静态文件 ----------
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Hotpot Concierge API is running. Visit /docs for API docs."}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
