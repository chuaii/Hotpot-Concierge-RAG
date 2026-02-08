# -*- coding: utf-8 -*-
"""
风味图谱：锅底 + 主料 -> 蘸料推荐（calc_sauce_pairing 工具，可供 LangGraph/ADK 调用）。
"""
import json
from pathlib import Path

RULES_PATH = Path(__file__).parent.parent / "data" / "sauce_pairing_rules.json"


def _load_rules() -> dict:
    if not RULES_PATH.exists():
        return {"rules": [], "default_sauce": {"sauce_recipe": ["蒜泥+香油+蚝油+香菜"], "reason_cn": "万能蘸料", "reason_en": "All-purpose"}}
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def calc_sauce_pairing(
    broth_id: str,
    ingredient_ids: list[str],
    menu_path: Path | str | None = None,
) -> dict:
    """
    根据锅底与已选食材推荐蘸料配方。
    可供 ADK 工具定义：Tool(sauce_pairing, "Recommend dipping sauce for broth and ingredients")
    """
    from .menu_loader import load_menu, get_all_broths_with_prices, get_all_items_with_prices

    menu = load_menu(menu_path)
    broths = {b["id"]: b for b in get_all_broths_with_prices(menu)}
    items = {it["id"]: it for it in get_all_items_with_prices(menu)}

    broth = broths.get(broth_id, {})
    spicy = broth.get("spicy") is True or broth.get("spicy") == "half"
    broth_tags = []
    if spicy:
        broth_tags.append("spicy")
    if "sichuan" in (broth.get("name_en") or "").lower() or "川" in (broth.get("name_cn") or ""):
        broth_tags.append("sichuan")
    if "tomato" in broth_id or "番茄" in (broth.get("name_cn") or ""):
        broth_tags.append("tomato")
    if broth.get("spicy") is False:
        broth_tags.append("mild")
    if "bone" in broth_id or "骨" in (broth.get("name_cn") or ""):
        broth_tags.append("bone")
    if broth.get("spicy") == "half":
        broth_tags.append("half")

    ingredient_tags = []
    for iid in ingredient_ids:
        it = items.get(iid, {})
        cat = (it.get("category") or "").lower()
        name_en = (it.get("name_en") or "").lower()
        name_cn = (it.get("name_cn") or "")
        if cat == "meat":
            ingredient_tags.append("meat")
        if "lamb" in name_en or "羊肉" in name_cn:
            ingredient_tags.append("lamb")
        if "beef" in name_en or "牛" in name_cn:
            ingredient_tags.append("beef")
        if cat == "seafood" or "shrimp" in name_en or "虾" in name_cn:
            ingredient_tags.append("seafood")
        if "tripe" in name_en or "毛肚" in name_cn or "黄喉" in name_cn:
            ingredient_tags.append("tripe")
        if "offal" in name_en or "内脏" in name_cn:
            ingredient_tags.append("offal")
        if cat == "vegetable":
            ingredient_tags.append("vegetable")
    ingredient_tags = list(set(ingredient_tags))

    data = _load_rules()
    for rule in data.get("rules", []):
        bt = set(rule.get("broth_tags", []))
        it = set(rule.get("ingredient_tags", []))
        if bt and not (bt & set(broth_tags)):
            continue
        if it and not (it & set(ingredient_tags)):
            continue
        return {
            "status": "success",
            "sauce_recipe": rule.get("sauce_recipe", []),
            "reason_cn": rule.get("reason_cn", ""),
            "reason_en": rule.get("reason_en", ""),
        }

    default = data.get("default_sauce", {})
    return {
        "status": "success",
        "sauce_recipe": default.get("sauce_recipe", ["蒜泥+香油+蚝油+香菜"]),
        "reason_cn": default.get("reason_cn", "万能蘸料"),
        "reason_en": default.get("reason_en", "All-purpose"),
    }
