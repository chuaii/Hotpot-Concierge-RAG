# -*- coding: utf-8 -*-
"""
示例：在代码中读取文本、存入数据库并问答。
运行：python run_example.py
"""
from rag import RAG

# 1. 创建 RAG，并准备一段文本
rag = RAG()

text = """
Python 是一种广泛使用的高级编程语言，以简洁易读著称。
它支持多种编程范式，包括面向对象、命令式和函数式编程。
Python 拥有丰富的标准库和第三方库，常用于 Web 开发、数据分析、人工智能等领域。
"""

# 2. 把文本存入向量数据库
n = rag.ingest_text(text)
print(f"已录入 {n} 个文本块。\n")

# 3. 提问并得到答案
questions = [
    "Python 是什么？",
    "Python 常用于哪些领域？",
]

for q in questions:
    answer = rag.query(q, use_llm=False)  # 不调用 API，只返回检索内容
    print(f"问: {q}")
    print(f"答: {answer}\n")
