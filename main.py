# -*- coding: utf-8 -*-
"""
入口：手动录入文本到 RAG 知识库，或启动 Web 服务。

用法：
  python main.py ingest <文件路径>      将文本文件录入知识库
  python main.py serve                  启动 Web 服务（等同 python api.py）
"""
import argparse
import os
import sys

from core import RAG


def main():
    parser = argparse.ArgumentParser(description="火锅顾问 + RAG 系统")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest_p = sub.add_parser("ingest", help="将文本文件录入 RAG 知识库")
    ingest_p.add_argument("file", type=str, help="文本文件路径（UTF-8）")
    ingest_p.add_argument("--encoding", type=str, default="utf-8")
    ingest_p.add_argument("--collection", type=str, default="rag_docs")
    ingest_p.add_argument("--persist", type=str, default="data/chroma_data")

    sub.add_parser("serve", help="启动 Web 服务（FastAPI + Uvicorn）")

    args = parser.parse_args()

    if args.command == "ingest":
        rag = RAG(collection_name=args.collection, persist_directory=args.persist)
        try:
            n = rag.ingest_file(args.file, encoding=args.encoding)
            print(f"已录入 {n} 个文本块到知识库。")
        except FileNotFoundError as e:
            print(e, file=sys.stderr)
            sys.exit(1)

    elif args.command == "serve":
        import uvicorn
        port = int(os.environ.get("PORT", 8080))
        uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
