# -*- coding: utf-8 -*-
"""
加载火锅菜单与价格，为 RAG/库存检索与结构化订单提供数据。
"""
import json
from pathlib import Path

DEFAULT_MENU_PATH = Path(__file__).parent.parent / "data" / "hotpot_menu.json"
# 默认单价（元/份），与 menu_item_id 对应；若菜单无 price 则用此表或按品类默认
DEFAULT_PRICES: dict[str, float] = {
    "sliced_beef": 38.0,
    "sliced_lamb": 36.0,
    "pork_belly": 32.0,
    "shrimp": 42.0,
    "fish_balls": 22.0,
    "tofu": 12.0,
    "lettuce": 10.0,
    "potato_slices": 10.0,
    "noodles": 8.0,
}
CATEGORY_DEFAULT_PRICE: dict[str, float] = {
    "meat": 32.0,
    "seafood": 28.0,
    "vegetable": 12.0,
    "tofu": 12.0,
    "staple": 8.0,
}
SOUP_BASE_PRICE: dict[str, float] = {
    "tomato": 28.0,
    "spicy_sichuan": 32.0,
    "bone": 26.0,
    "yinyang": 38.0,
}


def load_menu(path: Path | str | None = None) -> dict:
    path = path or DEFAULT_MENU_PATH
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"菜单文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_item_price(item_id: str, category: str | None = None) -> float:
    if item_id in DEFAULT_PRICES:
        return DEFAULT_PRICES[item_id]
    if item_id in SOUP_BASE_PRICE:
        return SOUP_BASE_PRICE[item_id]
    return CATEGORY_DEFAULT_PRICE.get(category or "meat", 20.0)


def get_all_items_with_prices(menu: dict) -> list[dict]:
    """返回带 price 的食材列表，供检索与结构化输出校验。"""
    result = []
    for it in menu.get("ingredients", []):
        item_id = it.get("id", "")
        cat = it.get("category", "")
        result.append({
            **it,
            "price_per_portion": it.get("price_per_portion") or get_item_price(item_id, cat),
        })
    return result


def get_all_broths_with_prices(menu: dict) -> list[dict]:
    result = []
    for b in menu.get("soup_bases", []):
        bid = b.get("id", "")
        result.append({
            **b,
            "price": b.get("price") or SOUP_BASE_PRICE.get(bid, 28.0),
        })
    return result
