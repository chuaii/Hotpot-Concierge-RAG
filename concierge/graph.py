# -*- coding: utf-8 -*-
"""
智能火锅点餐顾问 - LangGraph 状态图（Gemini）。
流程：Profiler（收集画像） -> Inventory（筛选菜品） -> Reviewer（展示方案）。
"""
import json
import re
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from .menu_loader import get_all_broths_with_prices, get_all_items_with_prices, load_menu
from .state import OrderState

# llm.py 位于项目根目录，由入口脚本保证 sys.path 包含项目根
from llm import get_llm


def _ensure_profile(state: OrderState) -> dict:
    return state.get("customer_profile") or {
        "spice_tolerance": "medium",
        "allergies": [],
        "dislikes": [],
        "preferences": [],
        "budget_max": None,
        "num_guests": 1,
        "language": "zh",
    }


def _extract_json(text: str) -> dict | None:
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    else:
        m2 = re.search(r"\{.*\}", text, re.DOTALL)
        if m2:
            text = m2.group(0)
    try:
        return json.loads(text)
    except Exception:
        return None


def profiler_node(state: OrderState) -> dict:
    messages = state.get("messages") or []
    profile = _ensure_profile(state)
    llm = get_llm(temperature=0.2, max_output_tokens=400)

    system_prompt = (
        "你是火锅店点餐顾问。根据用户至今的发言，更新并输出客户画像（JSON），并判断是否还需要追问。\n"
        "画像字段：\n"
        "  spice_tolerance: none / mild / medium / high（注意：用户说'变态辣'应映射为 high）\n"
        "  allergies: 忌口/过敏列表\n"
        "  dislikes: 不喜欢的食材或口感列表\n"
        "  preferences: 偏好列表（如 crunchy, tender, seafood）\n"
        "  budget_max: 数字或 null（如用户说'预算150'，则为 150）\n"
        "  num_guests: 用餐人数（整数）\n"
        "  language: zh / en\n\n"
        "判断规则：若用户已给出辣度、人数、忌口（哪怕没有忌口也算明确），则 need_more=false。\n"
        "只输出一个 JSON 对象，包含 key：profile、need_more、next_question。"
    )

    conv_lines = ["对话历史："]
    for m in messages[-10:]:
        role = "user" if isinstance(m, HumanMessage) else "assistant"
        content = m.content if hasattr(m, "content") else str(m)
        conv_lines.append(f"{role}: {content}")
    conv_lines.append(f"\n当前画像：{json.dumps(profile, ensure_ascii=False)}")
    conv_lines.append("\n请输出 JSON（profile, need_more, next_question）：")

    try:
        resp = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content="\n".join(conv_lines)),
        ])
        text = resp.content if hasattr(resp, "content") else str(resp)
    except Exception as e:
        return {
            "customer_profile": profile,
            "current_step": "menu_generation",
            "messages": [AIMessage(content=f"（模型调用异常：{e}，将用默认画像继续）")],
        }

    out = _extract_json(text)
    if out:
        new_profile = out.get("profile", profile)
        need_more = out.get("need_more", False)
        next_q = out.get("next_question", "")
    else:
        new_profile = profile
        need_more = False
        next_q = ""

    updates: dict = {
        "customer_profile": new_profile,
        "current_step": "preference_gathering" if need_more else "menu_generation",
    }
    if need_more and next_q:
        updates["messages"] = [AIMessage(content=next_q)]
    return updates


def _route_after_profiler(state: OrderState) -> Literal["need_more", "done"]:
    step = state.get("current_step", "")
    return "done" if step == "menu_generation" else "need_more"


def inventory_node(state: OrderState) -> dict:
    menu = load_menu()
    profile = _ensure_profile(state)
    items = get_all_items_with_prices(menu)
    allergies = set((profile.get("allergies") or []) + (profile.get("dislikes") or []))
    spice = profile.get("spice_tolerance", "medium")

    if spice in ("none", "mild"):
        broth_id = "tomato"
    elif spice == "high":
        broth_id = "spicy_sichuan"
    else:
        broth_id = "yinyang"

    cart_ids = []
    for it in items:
        iid = it.get("id", "")
        name_en = (it.get("name_en") or "").lower()
        name_cn = (it.get("name_cn") or "")
        if any(a.lower() in name_en or a in name_cn for a in allergies):
            continue
        cart_ids.append(iid)

    by_cat: dict[str, list] = {}
    for it in items:
        if it["id"] not in cart_ids:
            continue
        by_cat.setdefault(it.get("category", "other"), []).append(it)
    recommended = []
    for cat in ["meat", "seafood", "vegetable", "tofu", "staple"]:
        for it in (by_cat.get(cat) or [])[:3]:
            recommended.append(it["id"])
    cart = recommended[:10] if recommended else cart_ids[:10]

    return {
        "cart": cart,
        "customer_profile": {**profile, "broth_id": broth_id},
        "current_step": "sauce_recommendation",
    }


def reviewer_node(state: OrderState) -> dict:
    menu = load_menu()
    profile = _ensure_profile(state)
    cart = state.get("cart") or []
    broths = get_all_broths_with_prices(menu)
    items = get_all_items_with_prices(menu)
    by_id = {it["id"]: it for it in items}
    broth_id = profile.get("broth_id", "tomato")
    broth = next((b for b in broths if b["id"] == broth_id), broths[0] if broths else {})
    num_guests = max(1, int(profile.get("num_guests") or 1))
    lang = profile.get("language", "zh")

    lines = []
    total = broth.get("price", 28.0)
    if lang == "en":
        lines.append(f"Broth: {broth.get('name_en', broth.get('name_cn'))} (¥{broth.get('price', 28)})")
        for iid in cart:
            it = by_id.get(iid, {})
            ppp = it.get("portion_per_person", 1.0)
            qty = max(0.5, round(ppp * num_guests, 1))
            price = it.get("price_per_portion", 20.0)
            sub = round(price * qty, 1)
            total += sub
            lines.append(f"  - {it.get('name_en', it.get('name_cn'))} × {qty} portions (¥{sub})")
        lines.append(f"\nEstimated total: ¥{round(total)}")
        lines.append("Does this look good? Reply 'confirm' to place the order, or tell me what to change.")
    else:
        lines.append(f"锅底：{broth.get('name_cn', broth.get('name_en'))}（¥{broth.get('price', 28)}）")
        for iid in cart:
            it = by_id.get(iid, {})
            ppp = it.get("portion_per_person", 1.0)
            qty = max(0.5, round(ppp * num_guests, 1))
            price = it.get("price_per_portion", 20.0)
            sub = round(price * qty, 1)
            total += sub
            lines.append(f"  - {it.get('name_cn', it.get('name_en'))} × {qty}份（¥{sub}）")
        lines.append(f"\n预估总价：¥{round(total)}")
        budget = profile.get("budget_max")
        if budget and total > budget:
            lines.append(f"⚠ 超出预算（¥{budget}），可以告诉我去掉哪些或减少份数。")
        lines.append("满意的话回复「确认」生成订单，或告诉我要调整的地方。")

    return {
        "messages": [AIMessage(content="\n".join(lines))],
        "current_step": "sauce_recommendation",
    }


def build_order_graph():
    workflow = StateGraph(OrderState)
    workflow.add_node("profiler", profiler_node)
    workflow.add_node("inventory", inventory_node)
    workflow.add_node("reviewer", reviewer_node)

    workflow.add_edge(START, "profiler")
    workflow.add_conditional_edges(
        "profiler",
        _route_after_profiler,
        {"need_more": END, "done": "inventory"},
    )
    workflow.add_edge("inventory", "reviewer")
    workflow.add_edge("reviewer", END)
    return workflow.compile()


def run_concierge_once(user_message: str, initial_state: OrderState | None = None) -> dict:
    graph = build_order_graph()
    state: OrderState = initial_state.copy() if initial_state else {}
    msgs = list(state.get("messages") or [])
    msgs.append(HumanMessage(content=user_message))
    state["messages"] = msgs
    result = graph.invoke(state)
    return result
