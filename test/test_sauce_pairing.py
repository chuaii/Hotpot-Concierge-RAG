#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试蘸料搭配风味图谱业务逻辑。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from concierge.sauce_pairing import calc_sauce_pairing


class TestSaucePairing(unittest.TestCase):
    def setUp(self) -> None:
        menu_path = Path(__file__).resolve().parent.parent / "data" / "hotpot_menu.json"
        if not menu_path.exists():
            self.skipTest("菜单文件不存在: data/hotpot_menu.json")

    def test_calc_sauce_pairing_returns_success(self) -> None:
        result = calc_sauce_pairing("szechwan_spicy", ["beef_tripe", "beef_sliced"])
        self.assertEqual(result["status"], "success")
        self.assertIn("sauce_recipe", result)
        self.assertIn("reason_cn", result)
        self.assertIn("reason_en", result)

    def test_spicy_sichuan_tripe_beef_matches_rule(self) -> None:
        """川味辣锅 + 牛肚牛百叶应命中「蒜泥+香油+香菜」规则。"""
        result = calc_sauce_pairing(
            "szechwan_spicy",
            ["beef_tripe", "beef_omasum", "beef_sliced"],
        )
        self.assertEqual(result["status"], "success")
        recipe = result.get("sauce_recipe") or []
        recipe_str = " ".join(recipe) if isinstance(recipe, list) else str(recipe)
        self.assertIn("蒜泥", recipe_str)
        self.assertIn("香油", recipe_str)

    def test_tomato_beef_lamb_matches_rule(self) -> None:
        """番茄锅 + 牛肉羊肉应命中「海鲜汁+牛肉粒+香菜」规则。"""
        result = calc_sauce_pairing(
            "tomato_herbs",
            ["beef_sliced", "lamb_sliced"],
        )
        self.assertEqual(result["status"], "success")
        recipe = result.get("sauce_recipe") or []
        recipe_str = " ".join(recipe) if isinstance(recipe, list) else str(recipe)
        self.assertIn("海鲜汁", recipe_str)
        self.assertIn("牛肉粒", recipe_str)

    def test_default_sauce_when_no_rule_match(self) -> None:
        """无匹配规则时返回默认蘸料（未知锅底 + 无标签食材）。"""
        result = calc_sauce_pairing(
            "unknown_broth_no_tags",
            ["potato_slices"],
        )
        self.assertEqual(result["status"], "success")
        self.assertTrue(
            result.get("sauce_recipe"),
            "应有默认蘸料配方",
        )
        # 默认配方含蒜泥、香油、蚝油
        recipe = result.get("sauce_recipe") or []
        recipe_str = " ".join(recipe) if isinstance(recipe, list) else str(recipe)
        self.assertTrue(
            "蒜泥" in recipe_str or "香油" in recipe_str or "蚝油" in recipe_str,
            "默认蘸料应含常用调料",
        )

    def test_seafood_spicy_broth(self) -> None:
        """海鲜冬阴功 + 虾丸应命中海鲜辣锅蘸料规则。"""
        result = calc_sauce_pairing(
            "seafood_tom_yum",
            ["shrimp_ball", "crab_sticks"],
        )
        self.assertEqual(result["status"], "success")
        recipe = result.get("sauce_recipe") or []
        recipe_str = " ".join(recipe) if isinstance(recipe, list) else str(recipe)
        self.assertIn("海鲜汁", recipe_str)

    def test_empty_ingredients_returns_default(self) -> None:
        """空食材列表应返回默认蘸料。"""
        result = calc_sauce_pairing("tomato_herbs", [])
        self.assertEqual(result["status"], "success")
        self.assertTrue(result.get("sauce_recipe"))

    def test_unknown_broth_id_uses_default(self) -> None:
        """未知锅底 ID 仍可返回默认蘸料。"""
        result = calc_sauce_pairing("unknown_broth_xyz", ["beef_sliced"])
        self.assertEqual(result["status"], "success")
        self.assertTrue(result.get("sauce_recipe"))

    def test_unknown_ingredient_ids_ignored(self) -> None:
        """未知食材 ID 不报错，按已知规则或默认返回。"""
        result = calc_sauce_pairing(
            "szechwan_spicy",
            ["unknown_ingredient_xyz", "beef_tripe"],
        )
        self.assertEqual(result["status"], "success")


if __name__ == "__main__":
    unittest.main()
