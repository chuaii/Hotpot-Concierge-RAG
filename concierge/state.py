# -*- coding: utf-8 -*-
"""
智能火锅点餐顾问 - 对话状态定义（LangGraph State）。
"""
from __future__ import annotations

from typing import Annotated, Any, Optional

from typing_extensions import TypedDict

from langgraph.graph.message import add_messages


# 与 LangGraph 兼容：messages 使用 add_messages 归并，避免覆盖历史
class OrderState(TypedDict, total=False):
    """点餐对话状态。"""
    messages: Annotated[list[Any], add_messages]
    customer_profile: dict          # spice_tolerance, allergies, preferences, budget_max, num_guests, broth_id
    current_step: str               # preference_gathering | menu_generation | sauce_recommendation
    cart: list[str]                 # 暂存的菜品 ID（menu_item_id）
    confirmed: bool                 # 用户是否已确认方案
    last_order_json: Optional[dict] # 最近一次生成的结构化订单（HotpotOrder），供展示与重试
