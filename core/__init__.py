# -*- coding: utf-8 -*-
"""核心：LLM 工厂 + RAG 知识库。"""
from .llm import get_llm
from .rag import RAG

__all__ = ["get_llm", "RAG"]
