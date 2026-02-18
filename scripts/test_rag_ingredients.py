#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
本地测试：检查 67 种食材在 RAG 中是否都能被检索命中。

用法（在项目根目录执行）：
  python scripts/test_rag_ingredients.py
  python scripts/test_rag_ingredients.py --with-llm   # 用 LLM 生成答案并检查是否「未提及」

依赖：先确保已录入知识库（启动过 web 或运行过 ingest），且 data/chroma_data 存在。
Windows 下若中文乱码，可先执行 chcp 65001 或 set PYTHONIOENCODING=utf-8 再运行。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 保证项目根在 path 中
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from concierge.menu_loader import load_menu
from core import RAG


def _expand_query(name_cn: str, name_en: str) -> str:
    """与 web/app 中扩展逻辑一致，便于向量检索命中。"""
    extra = " ".join(
        filter(
            None,
            [name_en, name_cn, "介绍", "涮煮", "时间", "特点", "丸子", "煮法", "分钟", "口感"],
        )
    )
    return f"{name_cn}有什么特点和涮煮建议？ {extra}"


def _retrieve_with_boost(rag: RAG, question: str, boost_name: str, top_k: int = 8) -> list[str]:
    """检索时对包含 boost_name 的 chunk 优先排序（与 app 中逻辑一致）。"""
    fetch_k = 120
    docs = list(rag._vectorstore.similarity_search(question, k=fetch_k))
    key = boost_name.strip()
    # 若主检索不含该名，用纯食材名做备用检索
    if not any(key in d.page_content for d in docs):
        fallback = rag._vectorstore.similarity_search(key, k=10)
        seen = {d.page_content for d in docs}
        for d in fallback:
            if d.page_content not in seen:
                docs.append(d)
                seen.add(d.page_content)
    sorted_docs = sorted(
        docs,
        key=lambda d: (0 if key in d.page_content else 1),
    )
    return [d.page_content for d in sorted_docs[:top_k]]


def run_tests(use_llm: bool = False) -> tuple[int, int, list[dict]]:
    """
    遍历菜单中 67 种食材，逐个测试 RAG 是否命中。
    命中规则：
      - 不用 LLM：检索到的 top 块中至少有一块包含该食材中文名或英文名。
      - 用 LLM：调用 query() 得到的答案里不包含「参考内容中未提及」且包含食材名。
    返回 (总数, 命中数, 未命中列表 [{name_cn, name_en}, ...])。
    """
    menu = load_menu()
    ingredients = menu.get("ingredients", [])
    if not ingredients:
        print("未找到食材列表，请检查 data/hotpot_menu.json")
        return 0, 0, []

    rag = RAG()
    total = len(ingredients)
    hit = 0
    missed = []

    for i, it in enumerate(ingredients, 1):
        name_cn = (it.get("name_cn") or "").strip()
        name_en = (it.get("name_en") or "").strip()
        if not name_cn and not name_en:
            missed.append({"name_cn": "", "name_en": it.get("id", "")})
            continue

        question = f"{name_cn}有什么特点和涮煮建议？"
        expanded = _expand_query(name_cn, name_en)
        boost_name = name_cn or name_en

        if use_llm:
            answer = rag.query(expanded, top_k=8, boost_contains=boost_name, use_llm=True)
            # 命中：答案里没有「未提及」且出现了该食材名
            not_mentioned = "参考内容中未提及" in answer or "未提及" in answer
            has_name = name_cn in answer or (name_en and name_en in answer)
            is_hit = has_name and not not_mentioned
        else:
            chunks = _retrieve_with_boost(rag, expanded, boost_name, top_k=8)
            is_hit = any(
                name_cn in c or (name_en and name_en in c) for c in chunks
            )

        if is_hit:
            hit += 1
            status = "OK"
        else:
            missed.append({"name_cn": name_cn, "name_en": name_en})
            status = "MISS"

        print(f"  [{i:2d}/{total}] {status}  {name_cn} / {name_en or '-'}")

    return total, hit, missed


def main():
    parser = argparse.ArgumentParser(description="测试每种食材是否被 RAG 命中")
    parser.add_argument(
        "--with-llm",
        action="store_true",
        help="使用 LLM 生成答案并据此判断是否命中（需配置 Gemini API）",
    )
    args = parser.parse_args()

    print("RAG 食材命中测试（67 种食材）")
    print("=" * 50)
    total, hit, missed = run_tests(use_llm=args.with_llm)
    print("=" * 50)
    print(f"合计: {total} 种食材，命中 {hit} 种，未命中 {len(missed)} 种")

    if missed:
        print("\n未命中列表：")
        for m in missed:
            print(f"  - {m['name_cn']} / {m['name_en']}")

    sys.exit(0 if len(missed) == 0 else 1)


if __name__ == "__main__":
    main()
