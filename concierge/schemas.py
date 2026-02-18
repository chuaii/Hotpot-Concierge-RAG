# -*- coding: utf-8 -*-
"""
智能火锅点餐顾问 - 结构化输出 Schema（Pydantic）。
用于 Pydantic AI 强制约束菜单/订单格式，便于厨房执行与防幻觉。
"""
from typing import Literal

from pydantic import BaseModel, Field


# ---------- 与厨房/前台一致的标准化字段 ----------
class MenuItem(BaseModel):
    """单条菜品（标准化，可供厨房出餐）。"""
    menu_item_id: str = Field(description="店内菜品ID，与库存一致，如 sliced_beef, tomato")
    name_cn: str = Field(description="中文名")
    name_en: str = Field(default="", description="英文名")
    category: Literal["meat", "vegetable", "seafood", "tofu", "staple", "soup_base"] = Field(
        description="品类"
    )
    quantity: float = Field(ge=0.1, description="数量（份数）")
    unit: str = Field(default="portion", description="单位，如 portion")
    reason: str = Field(default="", description="推荐理由，为何符合客人口味/需求")


class BrothSelection(BaseModel):
    """订单中的单种锅底及份数。"""
    broth_id: str = Field(description="锅底ID")
    broth_name_cn: str = Field(description="锅底中文名")
    broth_name_en: str = Field(default="", description="锅底英文名")
    quantity: int = Field(ge=1, description="份数")


class HotpotOrder(BaseModel):
    """火锅订单（结构化输出，机器可读）。"""
    broth_id: str = Field(description="主锅底ID（兼容单锅底或多锅底时第一个）")
    broth_name_cn: str = Field(description="主锅底中文名")
    broth_name_en: str = Field(default="", description="主锅底英文名")
    broths: list[BrothSelection] = Field(
        default_factory=list,
        description="所选锅底列表（含份数），为空时用 broth_id 表示单锅底",
    )
    items: list[MenuItem] = Field(description="菜品明细，仅包含店内有的 menu_item_id")
    num_guests: int = Field(ge=1, description="用餐人数")
    dipping_sauce_recipe: list[str] = Field(
        default_factory=list,
        description="蘸料调配步骤，如：蒜泥+香油+香菜；或按风味图谱推荐",
    )


# ---------- 对话中使用的客户画像（LangGraph state 的一部分） ----------
class CustomerProfile(BaseModel):
    """从多轮对话中抽取的客户偏好（用于菜单推荐与订单生成）。自助餐固定每人价格，无需预算。"""
    spice_tolerance: Literal["none", "mild", "medium", "high"] = "medium"
    allergies: list[str] = Field(default_factory=list, description="忌口/过敏，如 peanuts, lamb")
    dislikes: list[str] = Field(default_factory=list, description="不喜欢的食材或口感，如 offal")
    preferences: list[str] = Field(default_factory=list, description="偏好，如 crunchy, tender, seafood")
    num_guests: int = Field(default=1, ge=1, description="用餐人数")
    language: Literal["zh", "en"] = "zh"
