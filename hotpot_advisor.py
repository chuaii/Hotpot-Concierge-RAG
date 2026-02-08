# -*- coding: utf-8 -*-
"""
火锅店顾问（基于 LangChain + Gemini）：本店食材/锅底数据回答「该点多少」「哪个更受欢迎」。
"""
import json
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate
from llm import get_llm

DEFAULT_MENU_PATH = Path(__file__).parent / "data" / "hotpot_menu.json"


def load_menu(path: str | Path | None = None) -> dict:
    path = path or DEFAULT_MENU_PATH
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"菜单文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_menu_for_llm(menu: dict) -> str:
    lines = []
    lines.append(f"店铺: {menu.get('shop_name', '')} / {menu.get('shop_name_en', '')}")
    lines.append("")
    bases = menu.get("soup_bases", [])
    if bases:
        lines.append("【锅底 Soup bases】")
        for b in bases:
            rank = b.get("popularity_rank", "?")
            spicy = "spicy" if b.get("spicy") is True else ("half" if b.get("spicy") == "half" else "not spicy")
            lines.append(
                f"- {b.get('name_cn')} / {b.get('name_en')}: "
                f"popularity_rank={rank}, {spicy}. "
                f"{b.get('description_en', b.get('description_cn', ''))} "
                f"Recommended for: {', '.join(b.get('recommended_for', []))}"
            )
        lines.append("")
    items = menu.get("ingredients", [])
    if items:
        lines.append("【食材 Ingredients】")
        lines.append("(portion_per_person = recommended portions per person; total = guests × portion_per_person)")
        for it in items:
            p = it.get("portion_per_person", "?")
            u = it.get("unit_en", it.get("unit_cn", "portion"))
            rank = it.get("popularity_rank", "?")
            lines.append(
                f"- {it.get('name_cn')} / {it.get('name_en')} ({it.get('category', '')}): "
                f"portion_per_person={p} {u}, popularity_rank={rank}. "
                f"{it.get('notes_en', '')}"
            )
        lines.append("")
    notes = menu.get("portion_notes", {})
    if notes.get("en"):
        lines.append("Note: " + notes["en"])
    return "\n".join(lines)


HOTPOT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "You are a helpful hot pot restaurant advisor. You have ONLY the following menu data from our restaurant. "
        "Answer questions about: (1) how much of each food to order (portions per person or total for the table), "
        "(2) which soup bases or ingredients are most popular. "
        "Use ONLY the given data; do not invent items or numbers. "
        "If the customer asks in English, answer in English; if in Chinese, answer in Chinese. "
        "Keep answers concise and practical for staff to use when serving foreign or local guests."
    )),
    ("human", "【Our menu data】\n{context}\n\n【Question】\n{question}"),
])


def ask(
    question: str,
    menu: dict | None = None,
    num_guests: int | None = None,
    menu_path: str | Path | None = None,
) -> str:
    if menu is None:
        menu = load_menu(menu_path)
    context = format_menu_for_llm(menu)
    if num_guests is not None:
        context += f"\n\nCurrent table: {num_guests} guests. Use this to compute total portions (portions = portion_per_person × {num_guests})."

    llm = get_llm(temperature=0, max_output_tokens=600)
    chain = HOTPOT_PROMPT | llm

    try:
        msg = chain.invoke({"context": context, "question": question})
        return msg.content if hasattr(msg, "content") else str(msg)
    except Exception as e:
        return f"调用 Gemini 失败: {e}"
