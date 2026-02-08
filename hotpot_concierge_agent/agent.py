# -*- coding: utf-8 -*-
"""
Google ADK 封装：智能火锅点餐顾问 Agent。
使用方式：在项目根目录执行 adk run hotpot_concierge_agent（需先 pip install google-adk）。
将 LangGraph 逻辑与蘸料/菜单工具封装为 ADK Agent，便于 Tracing 与部署 Cloud Run。
"""
try:
    from google.adk.agents import Agent
except ImportError:
    Agent = None

from concierge.tools import get_menu_by_preference, sauce_pairing


if Agent is not None:
    root_agent = Agent(
        model="gemini-2.5-flash",  # find_model.py，需 GOOGLE_API_KEY
        name="hotpot_concierge",
        description="智能火锅点餐顾问：根据口味、忌口、预算与人数推荐锅底与菜品，并推荐蘸料配方。",
        instruction=(
            "你是火锅店点餐顾问。根据客人需求（辣度、忌口、预算、人数）推荐锅底与食材，并调用工具推荐蘸料。"
            "可先调用 get_menu_by_preference 获取推荐列表，再按需调用 sauce_pairing 给出蘸料配方。"
            "回复简洁实用，中英文按客人语言来。"
        ),
        tools=[get_menu_by_preference, sauce_pairing],
    )
else:
    root_agent = None
