# -*- coding: utf-8 -*-
"""FastAPI 请求/响应模型（点餐顾问 Web API）。"""
from typing import Optional

from pydantic import BaseModel


class BrothSelectionBody(BaseModel):
    """前端提交的锅底选项（中文名 + 份数）。"""
    name_cn: str
    quantity: int = 1


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    num_guests: Optional[int] = None
    allergies: Optional[list[str]] = None
    broths: Optional[list[BrothSelectionBody]] = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    source: str = "concierge"
    order_json: Optional[dict] = None


class RecommendRequest(BaseModel):
    num_guests: int = 2
    allergies: list[str] = []
    session_id: Optional[str] = None


class RecommendResponse(BaseModel):
    items: list[dict]
    all_items: list[dict]
    total: int
    num_guests: int
    message: str
    session_id: str


class CartUpdateRequest(BaseModel):
    session_id: str
    cart: list[str]
