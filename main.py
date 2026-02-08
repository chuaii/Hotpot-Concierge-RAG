# -*- coding: utf-8 -*-
"""
RAG 系统入口：读取文本存入数据库，然后进行问答。
用法：
  python main.py ingest <文本文件路径>
  python main.py ask "你的问题"
  python main.py chat
  python main.py hotpot "问题" [--guests N]
"""
import argparse
import sys

from rag import RAG
from hotpot_advisor import ask as hotpot_ask


def main():
    parser = argparse.ArgumentParser(description="RAG：录入文本并问答（Gemini）")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest_parser = sub.add_parser("ingest", help="将文本文件内容录入知识库")
    ingest_parser.add_argument("file", type=str, help="文本文件路径（UTF-8）")
    ingest_parser.add_argument("--encoding", type=str, default="utf-8")
    ingest_parser.add_argument("--collection", type=str, default="rag_docs")
    ingest_parser.add_argument("--persist", type=str, default="./chroma_data")

    ask_parser = sub.add_parser("ask", help="问一个问题并得到答案")
    ask_parser.add_argument("question", type=str, help="你的问题")
    ask_parser.add_argument("--top-k", type=int, default=5)
    ask_parser.add_argument("--no-llm", action="store_true")
    ask_parser.add_argument("--collection", type=str, default="rag_docs")
    ask_parser.add_argument("--persist", type=str, default="./chroma_data")

    chat_parser = sub.add_parser("chat", help="连续问答模式")
    chat_parser.add_argument("--top-k", type=int, default=5)
    chat_parser.add_argument("--no-llm", action="store_true")
    chat_parser.add_argument("--collection", type=str, default="rag_docs")
    chat_parser.add_argument("--persist", type=str, default="./chroma_data")

    hotpot_parser = sub.add_parser("hotpot", help="火锅店顾问")
    hotpot_parser.add_argument("question", type=str)
    hotpot_parser.add_argument("--guests", type=int, default=None, metavar="N")
    hotpot_parser.add_argument("--menu", type=str, default=None)

    args = parser.parse_args()

    if args.command == "ingest":
        rag = RAG(collection_name=args.collection, persist_directory=args.persist)
        try:
            n = rag.ingest_file(args.file, encoding=args.encoding)
            print(f"已录入 {n} 个文本块到知识库。")
        except FileNotFoundError as e:
            print(e, file=sys.stderr)
            sys.exit(1)

    elif args.command == "ask":
        rag = RAG(collection_name=args.collection, persist_directory=args.persist)
        answer = rag.query(args.question, top_k=args.top_k, use_llm=not args.no_llm)
        print(answer)

    elif args.command == "chat":
        rag = RAG(collection_name=args.collection, persist_directory=args.persist)
        print("进入问答模式。输入问题后回车；输入 q 或空行退出。\n")
        while True:
            try:
                q = input("你: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not q or q.lower() == "q":
                break
            answer = rag.query(q, top_k=args.top_k, use_llm=not args.no_llm)
            print(f"\nRAG: {answer}\n")

    elif args.command == "hotpot":
        try:
            answer = hotpot_ask(args.question, num_guests=args.guests, menu_path=args.menu)
            print(answer)
        except FileNotFoundError as e:
            print(e, file=sys.stderr)
            sys.exit(1)

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
