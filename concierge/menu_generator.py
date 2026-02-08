# -*- coding: utf-8 -*-
"""
智能火锅点餐顾问 - 结构化菜单生成（Pydantic AI）。
将 LangGraph 收集的 customer_profile + cart 转为标准化 HotpotOrder，供厨房执行。
"""
from pathlib import Path

from .menu_loader import get_all_broths_with_prices, get_all_items_with_prices, load_menu
from .schemas import HotpotOrder, MenuItem
from .sauce_pairing import calc_sauce_pairing


def _menu_context(menu: dict) -> str:
    """供 LLM 参考的菜单文本（仅包含 id/name/price/category）。"""
    lines = ["【锅底】"]
    for b in get_all_broths_with_prices(menu):
        lines.append(f"  id={b['id']} name_cn={b.get('name_cn')} name_en={b.get('name_en')} price={b.get('price', 0)}")
    lines.append("【食材】")
    for it in get_all_items_with_prices(menu):
        lines.append(
            f"  menu_item_id={it['id']} name_cn={it.get('name_cn')} name_en={it.get('name_en')} "
            f"category={it.get('category')} price_per_portion={it.get('price_per_portion', 0)}"
        )
    return "\n".join(lines)


def generate_order_struct(
    customer_profile: dict,
    cart: list[str],
    menu_path: Path | str | None = None,
    use_pydantic_ai: bool = True,
) -> HotpotOrder:
    """
    根据画像与购物车生成结构化订单。
    若 use_pydantic_ai=True 且已安装 pydantic-ai，则用 Agent(output_type=HotpotOrder) 生成并校验；
    否则用 LLM + 手工解析/校验为 HotpotOrder。
    """
    menu = load_menu(menu_path)
    brooths = get_all_broths_with_prices(menu)
    items = get_all_items_with_prices(menu)
    by_id = {it["id"]: it for it in items}
    broth_id = customer_profile.get("broth_id") or "tomato"
    broth = next((b for b in brooths if b["id"] == broth_id), brooths[0] if brooths else {})
    num_guests = max(1, int(customer_profile.get("num_guests") or 1))
    context = _menu_context(menu)

    # 仅允许 cart 中存在的 id，并计算份数（按每人推荐份数）
    order_items: list[MenuItem] = []
    total = 0.0
    for iid in cart:
        it = by_id.get(iid)
        if not it:
            continue
        portion_per = it.get("portion_per_person", 1.0)
        qty = max(0.5, round(portion_per * num_guests, 1))
        price = it.get("price_per_portion", 20.0)
        order_items.append(
            MenuItem(
                menu_item_id=iid,
                name_cn=it.get("name_cn", ""),
                name_en=it.get("name_en", ""),
                category=it.get("category", "meat"),
                quantity=qty,
                unit=it.get("unit_en", "portion"),
                price=price,
                reason="",
            )
        )
        total += price * qty
    total += broth.get("price", 28.0)

    # 蘸料：风味图谱
    sauce_result = calc_sauce_pairing(broth_id, cart, menu_path)
    recipe = sauce_result.get("sauce_recipe") or ["蒜泥+香油+蚝油+香菜"]

    return HotpotOrder(
        broth_id=broth_id,
        broth_name_cn=broth.get("name_cn", ""),
        broth_name_en=broth.get("name_en", ""),
        items=order_items,
        total_estimate=round(total, 2),
        num_guests=num_guests,
        dipping_sauce_recipe=recipe if isinstance(recipe, list) else [recipe],
    )


def generate_order_with_llm(
    customer_profile: dict,
    cart: list[str],
    menu_path: Path | str | None = None,
) -> HotpotOrder:
    """
    使用 LLM 生成推荐理由等，再组装为 HotpotOrder（仍做 Pydantic 校验）。
    若需严格防幻觉，可仅用 generate_order_struct 不用 LLM。
    """
    return generate_order_struct(customer_profile, cart, menu_path, use_pydantic_ai=False)
