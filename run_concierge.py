# -*- coding: utf-8 -*-
"""
智能火锅点餐顾问 - 本地对话入口（LangGraph 多轮 + 结构化订单生成）。
不依赖 Google ADK，直接运行：python run_concierge.py
"""
import sys

from langchain_core.messages import AIMessage, HumanMessage

from concierge import generate_order_struct, run_concierge_once


CONFIRM_KEYWORDS = {"确认", "可以", "就这些", "好的", "行", "ok", "yes", "confirm", "sure"}


def _is_confirm(text: str) -> bool:
    t = text.strip().lower()
    return t in CONFIRM_KEYWORDS or any(k in t for k in ("确认", "可以", "就这些"))


def _last_ai_message(state: dict) -> str | None:
    for m in reversed(state.get("messages") or []):
        if isinstance(m, AIMessage) and m.content:
            return m.content
    return None


def main():
    print("=" * 50)
    print(" Agentic Hotpot Concierge（智能火锅点餐顾问）")
    print("=" * 50)
    print("请描述您的需求，例如：")
    print("  「微辣、不吃羊肉、预算200元、4个人」")
    print("确认方案后将生成标准化订单。输入 q 退出。\n")

    state: dict | None = None

    while True:
        try:
            line = input("您: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line or line.lower() == "q":
            break

        # 已有方案 + 用户确认 → 生成结构化订单
        if state and _is_confirm(line):
            cart = state.get("cart") or []
            profile = state.get("customer_profile") or {}
            if cart and profile:
                try:
                    order = generate_order_struct(profile, cart)
                    print("\n顾问: 已按您的要求生成订单，如下可交厨房执行。\n")
                    print("【结构化订单】")
                    print(order.model_dump_json(indent=2, ensure_ascii=False))
                    print()
                except Exception as e:
                    print(f"\n生成订单时出错: {e}\n")
                continue

        # 正常对话轮次：跑 LangGraph
        try:
            state = run_concierge_once(line, state)
        except Exception as e:
            print(f"\n顾问: 抱歉出了点问题 ({e})，请再说一次。\n")
            continue

        if state is None:
            print("\n顾问: 抱歉，未能处理您的请求，请再试一次。\n")
            state = {}
            continue

        # 输出最后一条 AI 回复
        reply = _last_ai_message(state)
        if reply:
            print(f"\n顾问: {reply}\n")

    print("再见！欢迎下次光临。")


if __name__ == "__main__":
    main()
