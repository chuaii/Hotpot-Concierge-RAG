#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试推荐与购物车解析业务逻辑。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from web.recommendation import (
    GUESTS_TO_PORTIONS,
    recommend_items,
    ingredient_has_allergen,
    parse_add_remove_item,
    ALLERGY_SEAFOOD,
    ALLERGY_GLUTEN,
    ALLERGY_PEANUT,
)


class TestRecommendation(unittest.TestCase):
    def setUp(self) -> None:
        menu_path = Path(__file__).resolve().parent.parent / "data" / "hotpot_menu.json"
        if not menu_path.exists():
            self.skipTest("菜单文件不存在: data/hotpot_menu.json")

    def test_guests_to_portions_mapping(self) -> None:
        """人数与推荐份数规定正确。"""
        self.assertEqual(GUESTS_TO_PORTIONS[1], 8)
        self.assertEqual(GUESTS_TO_PORTIONS[2], 10)
        self.assertEqual(GUESTS_TO_PORTIONS[3], 12)
        self.assertEqual(GUESTS_TO_PORTIONS[4], 14)
        self.assertEqual(GUESTS_TO_PORTIONS[5], 16)
        self.assertEqual(GUESTS_TO_PORTIONS[6], 17)

    def test_recommend_items_count_by_guests(self) -> None:
        """推荐数量应按规定人数截取。"""
        items1, count1 = recommend_items(1, [])
        self.assertEqual(count1, 8)
        self.assertEqual(len(items1), 8)

        items2, count2 = recommend_items(2, [])
        self.assertEqual(count2, 10)
        self.assertEqual(len(items2), 10)

        items3, count3 = recommend_items(4, [])
        self.assertEqual(count3, 14)
        self.assertEqual(len(items3), 14)

    def test_recommend_items_seafood_allergy_replacement(self) -> None:
        """海鲜过敏时虾丸、蟹柳、龙虾丸被替换（需 6 人以上才能包含这些项）。"""
        items_allergy, count_allergy = recommend_items(6, [ALLERGY_SEAFOOD])
        ids_allergy = {it["id"] for it in items_allergy}
        self.assertNotIn("shrimp_ball", ids_allergy)
        self.assertNotIn("lobster_ball", ids_allergy)
        self.assertNotIn("crab_sticks", ids_allergy)
        self.assertIn("chinese_cabbage", ids_allergy)  # 替换 shrimp_ball
        self.assertEqual(count_allergy, 17)

    def test_recommend_items_gluten_allergy_replacement(self) -> None:
        """麸质过敏时手工面、乌冬面被替换（需 6 人以上才能包含这些主食）。"""
        items, _ = recommend_items(6, [ALLERGY_GLUTEN])
        ids = {it["id"] for it in items}
        self.assertNotIn("homemade_noodle", ids)
        self.assertNotIn("udon_noodle", ids)
        self.assertIn("konjac_noodles", ids)  # 替换 homemade_noodle

    def test_recommend_items_filters_allergen_ingredients(self) -> None:
        """过敏列表中有的食材不应出现在推荐中。"""
        items, _ = recommend_items(2, [ALLERGY_SEAFOOD])
        for it in items:
            self.assertFalse(
                ingredient_has_allergen(it, ALLERGY_SEAFOOD),
                f"{it.get('name_cn')} 含海鲜，不应在海鲜过敏推荐中",
            )

    def test_ingredient_has_allergen_seafood(self) -> None:
        """海鲜过敏原检测。"""
        self.assertTrue(
            ingredient_has_allergen(
                {"id": "shrimp_ball", "name_cn": "虾丸", "name_en": "Shrimp Ball", "category": "seafood"},
                ALLERGY_SEAFOOD,
            )
        )
        self.assertTrue(
            ingredient_has_allergen(
                {"id": "crab_sticks", "name_cn": "蟹柳", "name_en": "Crab Sticks", "category": "seafood"},
                ALLERGY_SEAFOOD,
            )
        )
        self.assertFalse(
            ingredient_has_allergen(
                {"id": "potato_slices", "name_cn": "土豆片", "name_en": "Potato", "category": "vegetable"},
                ALLERGY_SEAFOOD,
            )
        )

    def test_ingredient_has_allergen_gluten(self) -> None:
        """麸质过敏原检测。"""
        self.assertTrue(
            ingredient_has_allergen(
                {"id": "fried_round_gluten", "name_cn": "油面筋", "name_en": "Fried Round Gluten"},
                ALLERGY_GLUTEN,
            )
        )
        self.assertTrue(
            ingredient_has_allergen(
                {"id": "udon_noodle", "name_cn": "乌冬面", "name_en": "Udon Noodle", "notes_en": "gluten"},
                ALLERGY_GLUTEN,
            )
        )
        self.assertFalse(
            ingredient_has_allergen(
                {"id": "bean_vermicelli", "name_cn": "龙口粉丝", "category": "staple"},
                ALLERGY_GLUTEN,
            )
        )

    def test_parse_add_remove_item_add_keywords(self) -> None:
        """添加关键词解析。"""
        item_id, is_add = parse_add_remove_item("添加牛肉片")
        self.assertEqual(item_id, "beef_sliced")
        self.assertTrue(is_add)

        item_id, is_add = parse_add_remove_item("再来一份土豆片")
        self.assertEqual(item_id, "potato_slices")
        self.assertTrue(is_add)

        item_id, is_add = parse_add_remove_item("加上金针菇")
        self.assertEqual(item_id, "enoki_mushroom")
        self.assertTrue(is_add)

    def test_parse_add_remove_item_remove_keywords(self) -> None:
        """移除关键词解析。"""
        item_id, is_add = parse_add_remove_item("去掉牛肉片")
        self.assertEqual(item_id, "beef_sliced")
        self.assertFalse(is_add)

        item_id, is_add = parse_add_remove_item("不要虾丸")
        self.assertEqual(item_id, "shrimp_ball")
        self.assertFalse(is_add)

        item_id, is_add = parse_add_remove_item("取消豆芽")
        self.assertEqual(item_id, "bean_sprouts")
        self.assertFalse(is_add)

    def test_parse_add_remove_item_synonyms(self) -> None:
        """同义词解析（肥牛->牛肉片等）。"""
        item_id, _ = parse_add_remove_item("添加肥牛")
        self.assertEqual(item_id, "beef_sliced")
        item_id, _ = parse_add_remove_item("加羊肉")
        self.assertEqual(item_id, "lamb_sliced")
        item_id, _ = parse_add_remove_item("来一份米饭")
        self.assertEqual(item_id, "steam_rice")

    def test_parse_add_remove_item_unknown_returns_none(self) -> None:
        """未知食材返回 None。"""
        item_id, is_add = parse_add_remove_item("添加火星菜")
        self.assertIsNone(item_id)
        self.assertTrue(is_add)

    def test_parse_add_remove_item_no_keyword_returns_none(self) -> None:
        """无添加/移除关键词时返回 None。"""
        item_id, _ = parse_add_remove_item("牛肉片好吃吗")
        self.assertIsNone(item_id)

    def test_recommend_items_guests_over_6(self) -> None:
        """人数超过 6 时使用 17 作为上限。"""
        items, count = recommend_items(10, [])
        self.assertEqual(count, 17)
        self.assertEqual(len(items), 17)


if __name__ == "__main__":
    unittest.main()
