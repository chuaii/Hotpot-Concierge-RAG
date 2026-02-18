# -*- coding: utf-8 -*-
"""
智能火锅点餐顾问 - 工具定义（可供 LangGraph / Google ADK 调用）。
"""
from pathlib import Path
from typing import Any

from .menu_loader import load_menu, get_all_items_with_prices, get_all_broths_with_prices
from .sauce_pairing import calc_sauce_pairing


def get_menu_by_preference(
    spice_tolerance: str = "medium",
    allergies: str = "",
    num_guests: int = 1,
    menu_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    根据口味与忌口从菜单中筛选推荐菜品。
    ADK 工具描述：Get recommended menu items by spice tolerance, allergies, and guest count.
    """
    menu = load_menu(menu_path)
    profile = {
        "spice_tolerance": spice_tolerance,
        "allergies": [a.strip() for a in allergies.split(",") if a.strip()],
        "num_guests": num_guests,
    }
    broths = get_all_broths_with_prices(menu)
    items = get_all_items_with_prices(menu)
    allergies_set = set(profile.get("allergies") or [])
    rec_broth_id = "tomato"
    if spice_tolerance in ("high", "medium"):
        rec_broth_id = "spicy_sichuan" if spice_tolerance == "high" else "yinyang"
    rec_items = []
    for it in items:
        name_en = (it.get("name_en") or "").lower()
        name_cn = it.get("name_cn") or ""
        if any(a in name_en or a in name_cn for a in allergies_set):
            continue
        rec_items.append({
            "id": it["id"],
            "name_cn": it.get("name_cn"),
            "name_en": it.get("name_en"),
            "category": it.get("category"),
            "price_per_portion": it.get("price_per_portion"),
        })
    broth = next((b for b in broths if b["id"] == rec_broth_id), broths[0] if broths else {})
    return {
        "status": "success",
        "broth_id": rec_broth_id,
        "broth_name_cn": broth.get("name_cn"),
        "broth_name_en": broth.get("name_en"),
        "items": rec_items[:15],
        "num_guests": num_guests,
    }


def sauce_pairing(
    broth_id: str,
    ingredient_ids: str,
    menu_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    根据锅底与食材 ID 推荐蘸料配方（风味图谱）。
    ADK 工具描述：Recommend dipping sauce recipe for given broth and ingredient IDs (comma-separated).
    """
    ids = [x.strip() for x in ingredient_ids.split(",") if x.strip()]
    return calc_sauce_pairing(broth_id, ids, menu_path)


# 供 Google ADK 使用的工具列表（adk run 时注入 root_agent）
ADK_TOOLS = [get_menu_by_preference, sauce_pairing]
