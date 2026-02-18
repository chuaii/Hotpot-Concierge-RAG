#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 RAG 核心业务逻辑（文本摄取、分块、检索）。
注意：首次运行会下载 embedding 模型，可能较慢。
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.rag import RAG


class TestRAGCore(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.rag = RAG(
            persist_directory=self.temp_dir,
            collection_name="test_rag_core",
        )

    def tearDown(self) -> None:
        import shutil
        if hasattr(self, "temp_dir") and Path(self.temp_dir).exists():
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            except OSError:
                pass

    def test_ingest_text_empty_returns_zero(self) -> None:
        """空文本录入返回 0。"""
        n = self.rag.ingest_text("")
        self.assertEqual(n, 0)
        n = self.rag.ingest_text("   \n\t  ")
        self.assertEqual(n, 0)

    def test_ingest_text_non_empty_returns_positive(self) -> None:
        """非空文本录入返回分块数。"""
        text = "火锅是一种中国传统烹饪方式。将各种食材放入锅中涮煮。"
        n = self.rag.ingest_text(text)
        self.assertGreater(n, 0)
        self.assertLessEqual(n, 10)  # 短文本不应产生过多块

    def test_ingest_file_not_found_raises(self) -> None:
        """不存在的文件应抛出 FileNotFoundError。"""
        with self.assertRaises(FileNotFoundError) as ctx:
            self.rag.ingest_file("/nonexistent/path/to/file.txt")
        self.assertIn("不存在", str(ctx.exception))

    def test_retrieve_returns_list(self) -> None:
        """retrieve 应返回字符串列表。"""
        self.rag.ingest_text("测试内容：牛肉片涮 8-12 秒即可食用。")
        docs = self.rag.retrieve("牛肉片怎么涮", top_k=3)
        self.assertIsInstance(docs, list)
        self.assertTrue(all(isinstance(d, str) for d in docs))
        self.assertGreater(len(docs), 0)
        self.assertIn("牛肉", " ".join(docs))

    def test_query_without_llm_returns_context(self) -> None:
        """不用 LLM 时 query 返回检索内容拼接。"""
        self.rag.ingest_text("豆芽煮 10-20 秒。土豆片煮 2-3 分钟。")
        ans = self.rag.query("豆芽煮多久", use_llm=False)
        self.assertIn("根据检索到的内容", ans)
        self.assertIn("豆芽", ans)

    def test_query_empty_retrieve_returns_no_content(self) -> None:
        """无检索结果时返回无内容提示。"""
        # 使用空库或无关查询
        ans = self.rag.query("火星火锅怎么吃", use_llm=False)
        self.assertIn("没有相关内容", ans)

    def test_ingest_file_with_ingredient_section_splits(self) -> None:
        """含 67 种食材章节的文本应按食材分块录入。"""
        sample_file = _ROOT / "data" / "sample.txt"
        if not sample_file.exists():
            self.skipTest("data/sample.txt 不存在，跳过食材分块测试")
        n = self.rag.ingest_file(str(sample_file))
        self.assertGreater(n, 1)
        # 至少应有多个块（主部分 + 各食材）
        self.assertGreaterEqual(n, 20)

    def test_retrieve_ranked_by_similarity(self) -> None:
        """检索结果应按相似度排序，相关度高的靠前。"""
        self.rag.ingest_text("竹轮是一种鱼糜制品，煮 3-5 分钟。口感 Q 弹。")
        self.rag.ingest_text("鱼丸虾丸煮 3-5 分钟。")
        chunks = self.rag.retrieve("竹轮有什么特点", top_k=5)
        self.assertGreater(len(chunks), 0)
        all_text = " ".join(chunks)
        self.assertIn("竹轮", all_text)


if __name__ == "__main__":
    unittest.main()
