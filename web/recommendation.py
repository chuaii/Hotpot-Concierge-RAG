# -*- coding: utf-8 -*-
"""
食材推荐与购物车解析逻辑。
规定：1人8份、2人10份、3人12份、4人14份、5人16份、6人17份（总种类数）。
"""
from concierge.menu_loader import get_all_items_with_prices, load_menu

# ---------- 人数 → 总份数规定 ----------
GUESTS_TO_PORTIONS = {1: 8, 2: 10, 3: 12, 4: 14, 5: 16, 6: 17}

DEFAULT_RECOMMEND_IDS = [
    "bean_sprouts",
    "potato_slices",
    "baby_bok_choy",
    "enoki_mushroom",
    "broccoli",
    "regular_tofu",
    "beef_sliced",
    "pork_sliced",
    "lamb_sliced",
    "beef_meat_ball",
    "shrimp_ball",
    "lobster_ball",
    "beef_tendon",
    "crab_sticks",
    "bean_vermicelli",
    "homemade_noodle",
    "udon_noodle",
]
SEAFOOD_IDS = {"shrimp_ball", "lobster_ball", "crab_sticks"}
SEAFOOD_REPLACEMENTS = ["chinese_cabbage", "frozen_tofu", "pork_meat_ball"]
GLUTEN_IDS = {"homemade_noodle", "udon_noodle"}
GLUTEN_REPLACEMENTS = ["konjac_noodles", "yam_noodle"]

ALLERGY_PEANUT = "花生"
ALLERGY_SEAFOOD = "海鲜"
ALLERGY_GLUTEN = "面筋"

ADD_CART_KEYWORDS = ("添加", "加", "再来", "来一份", "加上", "要", "多要", "再来一份")
REMOVE_CART_KEYWORDS = ("去掉", "不要", "删掉", "取消", "移除", "减去")

_INGREDIENT_KEYWORDS: list[tuple[str, str]] = []


def ingredient_has_allergen(item: dict, allergen: str) -> bool:
    """判断某食材是否含有指定过敏原。"""
    name_cn = (item.get("name_cn") or "").strip()
    name_en = (item.get("name_en") or "").lower()
    notes = (item.get("notes_en") or "").lower()
    cat = (item.get("category") or "").lower()
    iid = (item.get("id") or "").lower()
    if allergen == ALLERGY_PEANUT:
        return "花生" in name_cn or "peanut" in name_en or "peanut" in notes
    if allergen == ALLERGY_SEAFOOD:
        if cat == "seafood":
            return True
        cn_seafood = ("虾", "蟹", "鱼", "海鲜", "墨鱼", "鱿鱼", "青口", "蚬", "鲍鱼", "海参", "鱼丸", "虾丸", "蟹柳", "龙利鱼", "海带")
        if any(x in name_cn for x in cn_seafood):
            return True
        en_seafood = ("shrimp", "crab", "fish", "seafood", "cuttlefish", "squid", "mussel", "clam", "abalone", "lobster", "basa")
        return any(x in name_en for x in en_seafood)
    if allergen == ALLERGY_GLUTEN:
        if iid == "fried_round_gluten":
            return True
        return "面筋" in name_cn or "gluten" in name_en or "gluten" in notes
    return False


def recommend_items(num_guests: int, allergies: list[str]) -> tuple[list[dict], int]:
    """根据人数与过敏列表，按固定顺序返回人气菜品；按人数规定截取份数。"""
    menu = load_menu()
    items = get_all_items_with_prices(menu)
    by_id = {it.get("id"): it for it in items}
    has_seafood_allergy = any(a.strip() == ALLERGY_SEAFOOD for a in allergies if a)
    has_gluten_allergy = any(a.strip() == ALLERGY_GLUTEN for a in allergies if a)

    ordered_ids = list(DEFAULT_RECOMMEND_IDS)
    if has_seafood_allergy:
        repl_iter = iter(SEAFOOD_REPLACEMENTS)
        ordered_ids = [next(repl_iter) if x in SEAFOOD_IDS else x for x in ordered_ids]
    if has_gluten_allergy:
        repl_iter = iter(GLUTEN_REPLACEMENTS)
        ordered_ids = [next(repl_iter) if x in GLUTEN_IDS else x for x in ordered_ids]

    seen = set()
    result: list[dict] = []
    for iid in ordered_ids:
        if iid in seen:
            continue
        it = by_id.get(iid)
        if not it:
            continue
        skip = False
        for a in allergies:
            if a and ingredient_has_allergen(it, a.strip()):
                skip = True
                break
        if skip:
            continue
        seen.add(iid)
        result.append(it)

    target = GUESTS_TO_PORTIONS.get(num_guests, 17)
    result = result[:target]
    return result, len(result)


def _build_ingredient_keywords() -> list[tuple[str, str]]:
    """构建 关键词->id 映射，用于解析「添加米饭」等。"""
    menu = load_menu()
    items = menu.get("ingredients", [])
    pairs: list[tuple[str, str]] = []
    synonyms = {
        "米饭": "steam_rice", "白米饭": "steam_rice",
        "肥牛": "beef_sliced", "牛肉": "beef_sliced",
        "羊肉": "lamb_sliced", "猪肉": "pork_sliced", "鸡肉": "chicken_sliced",
        "豆皮": "bean_curd_wrapper", "宽粉": "mung_clear_sheets",
    }
    for kw, iid in synonyms.items():
        pairs.append((kw, iid))
    for it in items:
        name_cn = (it.get("name_cn") or "").strip()
        iid = it.get("id", "")
        if name_cn and iid:
            pairs.append((name_cn, iid))
    pairs.sort(key=lambda x: -len(x[0]))
    return pairs


def parse_add_remove_item(msg: str) -> tuple[str | None, bool]:
    """
    解析用户消息中的增减意图。返回 (item_id, is_add)。
    若无法解析返回 (None, True)。
    """
    global _INGREDIENT_KEYWORDS
    if not _INGREDIENT_KEYWORDS:
        _INGREDIENT_KEYWORDS = _build_ingredient_keywords()
    t = msg.strip()
    is_add = any(k in t for k in ADD_CART_KEYWORDS)
    is_remove = any(k in t for k in REMOVE_CART_KEYWORDS)
    if not is_add and not is_remove:
        return None, True
    for kw, iid in _INGREDIENT_KEYWORDS:
        if kw in t:
            return iid, not is_remove
    return None, True
