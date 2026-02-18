# -*- coding: utf-8 -*-
"""
FastAPI 后端：智能火锅点餐顾问 + RAG 知识问答。
前置路由：知识类问题 → RAG 检索回答；点餐类问题 → LangGraph Concierge。
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

load_dotenv()

from langchain_core.messages import AIMessage

from concierge import generate_order_struct, run_concierge_once
from rag import RAG

# ---------- RAG 单例 ----------
_rag: RAG | None = None
_KNOWLEDGE_DIR = Path(__file__).parent / "data"
_KNOWLEDGE_FILE = Path(__file__).parent / "sample.txt"


def _get_rag() -> RAG:
    global _rag
    if _rag is None:
        _rag = RAG()
    return _rag


def _auto_ingest():
    """启动时自动将知识文档灌入向量数据库（幂等：ChromaDB 会去重）。"""
    rag = _get_rag()
    files_to_ingest = []
    if _KNOWLEDGE_FILE.exists():
        files_to_ingest.append(_KNOWLEDGE_FILE)
    for f in _KNOWLEDGE_DIR.glob("*.txt"):
        if f not in files_to_ingest:
            files_to_ingest.append(f)
    total = 0
    for f in files_to_ingest:
        n = rag.ingest_file(str(f))
        total += n
    if total > 0:
        print(f"[RAG] 已自动录入 {total} 个文本块到知识库。")


# ---------- 知识类问题路由 ----------
KNOWLEDGE_KEYWORDS = [
    "是什么", "什么是", "怎么", "如何", "为什么", "适合", "区别",
    "技巧", "注意", "热量", "健康", "营养", "过敏", "禁忌",
    "多久", "几分钟", "礼仪", "知识", "介绍", "推荐理由",
    "蘸料", "dipping", "how", "what", "why", "recommend",
    "allergy", "healthy", "calorie", "tip",
]


def _is_knowledge_query(text: str) -> bool:
    """判断用户消息是否为知识类问题（而非点餐流程）。"""
    t = text.strip().lower()
    if len(t) < 4:
        return False
    return any(kw in t for kw in KNOWLEDGE_KEYWORDS)


# ---------- 内存 Session Store ----------
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
    source: str = "concierge"
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
    _auto_ingest()
    yield
    _sessions.clear()


app = FastAPI(
    title="Hotpot Concierge + RAG API",
    description="智能火锅点餐顾问 + RAG 知识问答 Web 服务",
    version="2.0.0",
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
    统一对话接口（前置路由）：
    - 知识类问题 → RAG 检索 + Gemini 生成答案
    - 点餐流程   → LangGraph Concierge 多轮对话
    - 确认下单   → 生成结构化订单 JSON
    """
    session_id = req.session_id or str(uuid.uuid4())
    state = _get_session(session_id)
    user_msg = req.message.strip()

    if not user_msg:
        return ChatResponse(session_id=session_id, reply="请输入您的需求。", source="system")

    # ① 已有方案 + 用户确认 → 生成结构化订单
    if state and _is_confirm(user_msg):
        cart = state.get("cart") or []
        profile = state.get("customer_profile") or {}
        if cart and profile:
            try:
                order = generate_order_struct(profile, cart)
                return ChatResponse(
                    session_id=session_id,
                    reply="已按您的要求生成订单，如下可交厨房执行 ✅",
                    source="concierge",
                    order_json=order.model_dump(),
                )
            except Exception as e:
                return ChatResponse(
                    session_id=session_id, reply=f"生成订单时出错：{e}", source="concierge"
                )

    # ② 知识类问题 → RAG 检索回答
    if _is_knowledge_query(user_msg):
        try:
            rag = _get_rag()
            answer = rag.query(user_msg, top_k=3)
            return ChatResponse(session_id=session_id, reply=answer, source="rag")
        except Exception as e:
            return ChatResponse(
                session_id=session_id,
                reply=f"知识检索出错：{e}，请换个问法试试。",
                source="rag",
            )

    # ③ 点餐流程 → LangGraph Concierge
    try:
        new_state = run_concierge_once(user_msg, state if state else None)
    except Exception as e:
        return ChatResponse(
            session_id=session_id,
            reply=f"抱歉出了点问题：{e}，请再说一次。",
            source="concierge",
        )

    if new_state is None:
        return ChatResponse(
            session_id=session_id,
            reply="抱歉，未能处理您的请求，请再试一次。",
            source="concierge",
        )

    _sessions[session_id] = new_state
    reply = _last_ai_message(new_state) or "正在为您准备方案…"
    return ChatResponse(session_id=session_id, reply=reply, source="concierge")


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
    return {"message": "Hotpot Concierge + RAG API is running. Visit /docs for API docs."}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
