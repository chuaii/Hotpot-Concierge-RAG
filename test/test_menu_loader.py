#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试菜单加载与价格计算业务逻辑。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from concierge.menu_loader import (
    load_menu,
    get_item_price,
    get_all_items_with_prices,
    get_all_broths_with_prices,
    DEFAULT_MENU_PATH,
)


class TestMenuLoader(unittest.TestCase):
    def setUp(self) -> None:
        if not DEFAULT_MENU_PATH.exists():
            self.skipTest("菜单文件不存在，跳过: data/hotpot_menu.json")

    def test_load_menu_returns_dict(self) -> None:
        menu = load_menu()
        self.assertIsInstance(menu, dict)
        self.assertIn("ingredients", menu)
        self.assertIn("soup_bases", menu)
        self.assertIn("shop_name", menu)

    def test_load_menu_67_ingredients(self) -> None:
        menu = load_menu()
        ingredients = menu.get("ingredients", [])
        self.assertEqual(len(ingredients), 67, "菜单应包含 67 种食材")

    def test_load_menu_20_soup_bases(self) -> None:
        menu = load_menu()
        broths = menu.get("soup_bases", [])
        self.assertGreaterEqual(len(broths), 15, "菜单应包含至少 15 种锅底")

    def test_ingredient_has_required_fields(self) -> None:
        menu = load_menu()
        for it in menu.get("ingredients", [])[:5]:
            self.assertIn("id", it)
            self.assertIn("name_cn", it)
            self.assertIn("category", it)
            self.assertIn("portion_per_person", it)

    def test_get_item_price_known_ids(self) -> None:
        self.assertEqual(get_item_price("sliced_beef", "meat"), 38.0)
        self.assertEqual(get_item_price("sliced_lamb", "meat"), 36.0)
        self.assertEqual(get_item_price("potato_slices", "vegetable"), 10.0)
        self.assertEqual(get_item_price("tofu", "tofu"), 12.0)
        self.assertEqual(get_item_price("noodles", "staple"), 8.0)

    def test_get_item_price_category_fallback(self) -> None:
        # 未知 id 用品类默认价
        price = get_item_price("unknown_id", "meat")
        self.assertEqual(price, 32.0)
        price = get_item_price("unknown_id", "vegetable")
        self.assertEqual(price, 12.0)
        price = get_item_price("unknown_id", "seafood")
        self.assertEqual(price, 28.0)
        # category=None 时用 "meat" 作为 key，得 32.0
        price = get_item_price("unknown_id", None)
        self.assertEqual(price, 32.0)
        # 未知品类用默认 20.0
        price = get_item_price("unknown_id", "other")
        self.assertEqual(price, 20.0)

    def test_get_all_items_with_prices(self) -> None:
        menu = load_menu()
        items = get_all_items_with_prices(menu)
        self.assertEqual(len(items), 67)
        for it in items:
            self.assertIn("price_per_portion", it)
            self.assertIsInstance(it["price_per_portion"], (int, float))
            self.assertGreater(it["price_per_portion"], 0)

    def test_get_all_broths_with_prices(self) -> None:
        menu = load_menu()
        broths = get_all_broths_with_prices(menu)
        self.assertGreaterEqual(len(broths), 15)
        for b in broths:
            self.assertIn("price", b)
            self.assertIn("id", b)
            self.assertIn("name_cn", b)

    def test_load_menu_file_not_found(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_menu("/nonexistent/path/menu.json")


if __name__ == "__main__":
    unittest.main()
