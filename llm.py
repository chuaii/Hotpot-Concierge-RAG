# -*- coding: utf-8 -*-
"""
统一的 LLM 工厂：全局使用 Google Gemini（通过 LangChain ChatGoogleGenerativeAI）。
需要设置环境变量 GOOGLE_API_KEY。
"""
import os
from langchain_google_genai import ChatGoogleGenerativeAI

DEFAULT_MODEL = "gemini-2.0-flash"


def get_llm(
    model: str | None = None,
    temperature: float = 0.3,
    max_output_tokens: int = 512,
):
    """获取 Gemini LLM 实例。"""
    model = model or os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "请设置环境变量 GOOGLE_API_KEY。\n"
            "获取方式：https://aistudio.google.com/app/apikey"
        )
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )
