#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试订单生成业务逻辑。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from concierge.menu_generator import generate_order_struct
from concierge.schemas import HotpotOrder


class TestMenuGenerator(unittest.TestCase):
    def setUp(self) -> None:
        menu_path = Path(__file__).resolve().parent.parent / "data" / "hotpot_menu.json"
        if not menu_path.exists():
            self.skipTest("菜单文件不存在: data/hotpot_menu.json")

    def test_generate_order_struct_returns_hotpot_order(self) -> None:
        profile = {"num_guests": 2, "broth_id": "tomato_herbs"}
        cart = ["beef_sliced", "potato_slices", "bean_sprouts"]
        order = generate_order_struct(profile, cart)
        self.assertIsInstance(order, HotpotOrder)
        self.assertEqual(order.num_guests, 2)
        self.assertEqual(order.broth_id, "tomato_herbs")

    def test_order_items_filter_invalid_ids(self) -> None:
        """无效的 cart id 应被过滤，不加入订单。"""
        profile = {"num_guests": 1, "broth_id": "ginger_green_onion"}
        cart = ["beef_sliced", "invalid_id_xyz", "potato_slices"]
        order = generate_order_struct(profile, cart)
        ids = [it.menu_item_id for it in order.items]
        self.assertIn("beef_sliced", ids)
        self.assertIn("potato_slices", ids)
        self.assertNotIn("invalid_id_xyz", ids)

    def test_portion_calculation_per_guest(self) -> None:
        """份数应按每人推荐份数 × 人数计算。"""
        profile = {"num_guests": 2, "broth_id": "tomato_herbs"}
        # beef_sliced: portion_per_person=1.5
        cart = ["beef_sliced"]
        order = generate_order_struct(profile, cart)
        self.assertEqual(len(order.items), 1)
        # 1.5 * 2 = 3.0
        self.assertAlmostEqual(order.items[0].quantity, 3.0, places=1)

    def test_portion_minimum_half(self) -> None:
        """份数至少 0.5（避免 round 到 0）。"""
        profile = {"num_guests": 1, "broth_id": "ginger_green_onion"}
        # 选一个 portion_per_person 很小的
        cart = ["konjac_noodles"]  # 0.3 per person
        order = generate_order_struct(profile, cart)
        self.assertGreaterEqual(order.items[0].quantity, 0.5)

    def test_multi_broth_from_profile(self) -> None:
        """多锅底时从 profile.broths 解析。"""
        profile = {
            "num_guests": 2,
            "broths": [
                {"broth_id": "tomato_herbs", "name_cn": "番茄火锅汤底", "quantity": 1},
                {"broth_id": "szechwan_spicy", "name_cn": "川味香辣汤底", "quantity": 1},
            ],
        }
        cart = ["beef_sliced"]
        order = generate_order_struct(profile, cart)
        self.assertEqual(order.broth_id, "tomato_herbs")
        self.assertEqual(len(order.broths), 2)
        self.assertEqual(order.broths[0].broth_id, "tomato_herbs")
        self.assertEqual(order.broths[1].broth_id, "szechwan_spicy")

    def test_dipping_sauce_from_sauce_pairing(self) -> None:
        """蘸料应由风味图谱推荐。"""
        profile = {"num_guests": 1, "broth_id": "szechwan_spicy"}
        cart = ["beef_tripe", "beef_sliced"]
        order = generate_order_struct(profile, cart)
        self.assertTrue(order.dipping_sauce_recipe)
        self.assertIsInstance(order.dipping_sauce_recipe, list)

    def test_default_broth_when_missing(self) -> None:
        """无 broth_id 时默认 tomato。"""
        profile = {"num_guests": 1}
        cart = ["beef_sliced"]
        order = generate_order_struct(profile, cart)
        self.assertEqual(order.broth_id, "tomato")
        # tomato 可能映射到 tomato_herbs，取决于菜单
        self.assertTrue(order.broth_name_cn)

    def test_num_guests_default_one(self) -> None:
        """无 num_guests 时默认 1。"""
        profile = {"broth_id": "ginger_green_onion"}
        cart = ["beef_sliced"]
        order = generate_order_struct(profile, cart)
        self.assertEqual(order.num_guests, 1)

    def test_empty_cart_produces_valid_order(self) -> None:
        """空购物车仍生成有效订单（仅锅底）。"""
        profile = {"num_guests": 2, "broth_id": "tomato_herbs"}
        cart: list[str] = []
        order = generate_order_struct(profile, cart)
        self.assertIsInstance(order, HotpotOrder)
        self.assertEqual(len(order.items), 0)
        self.assertEqual(order.num_guests, 2)


if __name__ == "__main__":
    unittest.main()
