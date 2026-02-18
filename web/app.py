# -*- coding: utf-8 -*-
"""
FastAPI 后端：智能火锅点餐顾问 + RAG 知识问答。
前置路由：知识类问题 → RAG 检索回答；点餐类问题 → LangGraph Concierge。
"""
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import AIMessage

from core import RAG
from concierge import generate_order_struct, run_concierge_once
from concierge.menu_loader import get_all_items_with_prices, load_menu

from .recommendation import (
    ALLERGY_GLUTEN,
    ALLERGY_SEAFOOD,
    DEFAULT_RECOMMEND_IDS,
    GLUTEN_IDS,
    GLUTEN_REPLACEMENTS,
    SEAFOOD_IDS,
    SEAFOOD_REPLACEMENTS,
    ingredient_has_allergen,
    parse_add_remove_item,
    recommend_items,
)
from .schemas import (
    BrothSelectionBody,
    CartUpdateRequest,
    ChatRequest,
    ChatResponse,
    RecommendRequest,
    RecommendResponse,
)

load_dotenv()

# 项目根目录（web 上一级），数据目录与静态目录
_ROOT = Path(__file__).resolve().parent.parent
_KNOWLEDGE_DIR = _ROOT / "data"
STATIC_DIR = Path(__file__).resolve().parent / "static"

# ---------- RAG 单例 ----------
_rag: RAG | None = None


def _get_rag() -> RAG:
    global _rag
    if _rag is None:
        _rag = RAG()
    return _rag


def _auto_ingest():
    """启动时自动将 data/*.txt 灌入向量数据库（幂等：ChromaDB 会去重）。"""
    rag = _get_rag()
    if not _KNOWLEDGE_DIR.exists():
        return
    total = 0
    for f in _KNOWLEDGE_DIR.glob("*.txt"):
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

    # 合并前端传来的上下文（人数、过敏、锅底）到 session
    if req.num_guests is not None or req.allergies is not None or req.broths is not None:
        profile = dict(state.get("customer_profile") or {})
        if req.num_guests is not None:
            profile["num_guests"] = max(1, min(6, req.num_guests))
        if req.allergies is not None:
            profile["allergies"] = [a.strip() for a in req.allergies if a and str(a).strip()]
        if req.broths is not None:
            profile["broths"] = []
            if len(req.broths) > 0:
                menu = load_menu()
                soup_bases = menu.get("soup_bases", [])
                name_to_broth = {b.get("name_cn"): b for b in soup_bases if b.get("name_cn")}
                for sel in req.broths:
                    if (sel.quantity or 0) <= 0:
                        continue
                    b = name_to_broth.get(sel.name_cn or "")
                    if b:
                        profile["broths"].append({
                            "broth_id": b.get("id"),
                            "name_cn": b.get("name_cn"),
                            "name_en": b.get("name_en", ""),
                            "quantity": max(1, int(sel.quantity)),
                        })
        state = {**state, "customer_profile": profile}
        _sessions[session_id] = state

    if not user_msg:
        return ChatResponse(session_id=session_id, reply="请输入您的需求。", source="system")

    # ① 已有方案 + 用户确认 → 生成结构化订单
    if state and _is_confirm(user_msg):
        cart = state.get("cart") or []
        profile = state.get("customer_profile") or {}
        if cart and profile:
            try:
                order = generate_order_struct(profile, cart)
                order_dict = order.model_dump()
                if order_dict.get("broths"):
                    order_dict.pop("broth_id", None)
                    order_dict.pop("broth_name_cn", None)
                    order_dict.pop("broth_name_en", None)
                return ChatResponse(
                    session_id=session_id,
                    reply="已按您的要求生成订单，如下可交厨房执行 ✅",
                    source="concierge",
                    order_json=order_dict,
                )
            except Exception as e:
                return ChatResponse(
                    session_id=session_id, reply=f"生成订单时出错：{e}", source="concierge"
                )

    # ② 已有购物车 + 增减食材 → 直接修改 cart，不跑 Concierge
    cart = state.get("cart") or []
    profile = state.get("customer_profile") or {}
    if cart and profile:
        item_id, is_add = parse_add_remove_item(user_msg)
        if item_id:
            menu = load_menu()
            valid_ids = {it.get("id") for it in menu.get("ingredients", [])}
            if item_id in valid_ids:
                if is_add:
                    cart = list(cart) + [item_id]
                    items = get_all_items_with_prices(menu)
                    by_id = {it.get("id"): it for it in items}
                    it = by_id.get(item_id, {})
                    name = it.get("name_cn") or it.get("name_en") or item_id
                    reply = f"已添加「{name}」。当前共 {len(cart)} 样食材。满意可回复「确认」下单。"
                else:
                    try:
                        cart = list(cart)
                        cart.remove(item_id)
                        items = get_all_items_with_prices(menu)
                        by_id = {it.get("id"): it for it in items}
                        it = by_id.get(item_id, {})
                        name = it.get("name_cn") or it.get("name_en") or item_id
                        reply = f"已去掉「{name}」。当前共 {len(cart)} 样食材。"
                    except ValueError:
                        reply = "当前列表中没有该食材。"
                _sessions[session_id] = {**state, "cart": cart}
                return ChatResponse(session_id=session_id, reply=reply, source="concierge")

    # ③ 知识类问题 → RAG 检索回答
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

    # ④ 点餐流程 → LangGraph Concierge
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


@app.post("/api/recommend", response_model=RecommendResponse)
async def recommend(req: RecommendRequest):
    """根据人数与过敏项生成预选食材，并存入 session。"""
    session_id = req.session_id or str(uuid.uuid4())
    num_guests = max(1, min(6, req.num_guests))
    allergies = [a.strip() for a in (req.allergies or []) if a and a.strip()]
    items, total = recommend_items(num_guests, allergies)
    cart_ids = [it.get("id") for it in items if it.get("id")]
    profile = {
        "spice_tolerance": "medium",
        "allergies": allergies,
        "dislikes": [],
        "preferences": [],
        "num_guests": num_guests,
        "language": "zh",
        "broth_id": "szechwan_spicy",
    }
    _sessions[session_id] = {
        "cart": cart_ids,
        "customer_profile": profile,
        "messages": [],
    }
    cart_ids_set = set(cart_ids)
    out = [
        {"id": it.get("id"), "name_cn": it.get("name_cn"), "name_en": it.get("name_en"), "category": it.get("category")}
        for it in items
    ]
    menu = load_menu()
    all_ingredients = menu.get("ingredients", [])
    filtered_all = []
    for it in all_ingredients:
        skip = any(a and ingredient_has_allergen(it, a.strip()) for a in allergies)
        if skip:
            continue
        filtered_all.append(it)
    ordered_ids = list(DEFAULT_RECOMMEND_IDS)
    if any(a.strip() == ALLERGY_SEAFOOD for a in allergies if a):
        repl_iter = iter(SEAFOOD_REPLACEMENTS)
        ordered_ids = [next(repl_iter) if x in SEAFOOD_IDS else x for x in ordered_ids]
    if any(a.strip() == ALLERGY_GLUTEN for a in allergies if a):
        repl_iter = iter(GLUTEN_REPLACEMENTS)
        ordered_ids = [next(repl_iter) if x in GLUTEN_IDS else x for x in ordered_ids]
    display_order = []
    valid_ids = {it.get("id") for it in filtered_all}
    for iid in ordered_ids:
        if iid in valid_ids:
            display_order.append(iid)
    for it in filtered_all:
        iid = it.get("id")
        if iid and iid not in display_order:
            display_order.append(iid)
    all_items = []
    for iid in display_order:
        it = next((x for x in filtered_all if x.get("id") == iid), None)
        if it:
            all_items.append({
                "id": it.get("id"),
                "name_cn": it.get("name_cn"),
                "name_en": it.get("name_en"),
                "checked": it.get("id") in cart_ids_set,
            })
    msg = f"已为 {num_guests} 人推荐 {total} 样食材，勾选/取消勾选即可调整，满意后回复「确认」下单。"
    if allergies:
        msg = f"已排除 {', '.join(allergies)}。" + msg
    return RecommendResponse(
        items=out,
        all_items=all_items,
        total=total,
        num_guests=num_guests,
        message=msg,
        session_id=session_id,
    )


@app.post("/api/cart/update")
async def cart_update(req: CartUpdateRequest):
    """根据勾选状态更新购物车。"""
    session_id = req.session_id
    if session_id not in _sessions:
        return {"ok": False, "error": "session_not_found"}
    state = _sessions[session_id]
    menu = load_menu()
    valid_ids = {it.get("id") for it in menu.get("ingredients", [])}
    cart = [iid for iid in req.cart if iid in valid_ids]
    _sessions[session_id] = {**state, "cart": cart}
    return {"ok": True, "cart": cart, "total": len(cart)}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# ---------- 静态文件（前后端一体：web/static） ----------
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Hotpot Concierge + RAG API is running. Visit /docs for API docs."}
