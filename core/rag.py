# -*- coding: utf-8 -*-
"""
RAG 系统核心（基于 LangChain + Gemini）：文本摄取、向量存储、检索与问答。
"""
import re
from pathlib import Path

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain

from .llm import get_llm

# 默认配置
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50
DEFAULT_COLLECTION_NAME = "rag_docs"
DEFAULT_EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_PERSIST_DIR = "data/chroma_data"


def _get_embeddings(model_name: str = DEFAULT_EMBED_MODEL) -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=model_name)


def _get_vectorstore(
    collection_name: str,
    persist_directory: str,
    embedding_function: HuggingFaceEmbeddings,
):
    Path(persist_directory).mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=collection_name,
        embedding_function=embedding_function,
        persist_directory=persist_directory,
    )


class RAG:
    """RAG：基于 LangChain 的文本录入、向量存储与检索问答（Gemini）。"""

    def __init__(
        self,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        persist_directory: str = DEFAULT_PERSIST_DIR,
        embed_model_name: str = DEFAULT_EMBED_MODEL,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._embeddings = _get_embeddings(embed_model_name)
        self._vectorstore = _get_vectorstore(
            collection_name, persist_directory, self._embeddings
        )
        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""],
        )

    def _get_rag_chain(self, top_k: int = 5):
        retriever = self._vectorstore.as_retriever(search_kwargs={"k": top_k})
        llm = get_llm(temperature=0, max_output_tokens=500)
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个助手。请仅根据下面提供的【参考内容】回答问题。若参考内容中没有相关信息，请明确说「参考内容中未提及」。不要编造内容。"),
            ("human", "【参考内容】\n{context}\n\n【问题】\n{input}"),
        ])
        combine_docs_chain = create_stuff_documents_chain(llm, prompt)
        return create_retrieval_chain(retriever, combine_docs_chain)

    def _get_combine_chain(self):
        """返回仅组合文档的 chain（不包含 retriever），用于传入已重排的 docs。"""
        llm = get_llm(temperature=0, max_output_tokens=500)
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个助手。请仅根据下面提供的【参考内容】回答问题。若参考内容中没有相关信息，请明确说「参考内容中未提及」。不要编造内容。"),
            ("human", "【参考内容】\n{context}\n\n【问题】\n{input}"),
        ])
        return create_stuff_documents_chain(llm, prompt)

    def ingest_text(self, text: str) -> int:
        if not text or not text.strip():
            return 0
        docs = [Document(page_content=text.strip())]
        splits = self._text_splitter.split_documents(docs)
        if not splits:
            return 0
        self._vectorstore.add_documents(splits)
        return len(splits)

    def ingest_file(self, file_path: str, encoding: str = "utf-8") -> int:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        text = path.read_text(encoding=encoding)
        # 若包含 67 种食材章节，则将该章节按「一种食材一块」打散，避免鱼丸/虾丸/墨鱼丸等易混食材挤在同一块里
        if "【67 种食材详细介绍】" in text or "■ 蔬菜类" in text:
            return self._ingest_file_with_ingredient_splitting(text)
        return self.ingest_text(text)

    def _ingest_file_with_ingredient_splitting(self, text: str) -> int:
        """前半部分按原分块录入；67 种食材段按「一条食材一个 chunk」打散录入，便于单种食材检索。"""
        marker = "【67 种食材详细介绍】"
        idx = text.find(marker)
        if idx == -1:
            idx = text.find("■ 蔬菜类")
        if idx == -1:
            return self.ingest_text(text)
        main_part = text[:idx].strip()
        ingredients_section = text[idx:].strip()
        n_main = 0
        if main_part:
            n_main = self.ingest_text(main_part)
        # 按行首「数字. 」拆成一条条食材，每种食材单独成块
        chunks = re.split(r"\n(?=\d+\. )", ingredients_section)
        n_ing = 0
        for c in chunks:
            c = c.strip()
            if not c or not re.match(r"^\d+\. ", c):
                continue
            self._vectorstore.add_documents([Document(page_content=c)])
            n_ing += 1
        return n_main + n_ing

    def retrieve(self, query: str, top_k: int = 5) -> list[str]:
        docs = self._vectorstore.similarity_search(query, k=top_k)
        return [d.page_content for d in docs]

    def query(
        self,
        question: str,
        top_k: int = 5,
        use_llm: bool = True,
        boost_contains: str | None = None,
    ) -> str:
        """若提供 boost_contains（如食材名「竹轮」「海带」），先多取 2 倍候选再按「是否含该名」重排，优先命中对应块。"""
        if use_llm:
            try:
                if boost_contains:
                    # 主检索：扩大候选池以覆盖全部 67 种食材独立 chunk
                    fetch_k = 120
                    docs = self._vectorstore.similarity_search(question, k=fetch_k)
                    key = boost_contains.strip()
                    # 若主检索结果中不含该名，用纯食材名做备用检索（应对鱿鱼花、火锅云吞等向量相似度偏低的）
                    if not any(key in d.page_content for d in docs):
                        fallback = self._vectorstore.similarity_search(key, k=10)
                        seen = {d.page_content for d in docs}
                        for d in fallback:
                            if d.page_content not in seen:
                                docs.append(d)
                                seen.add(d.page_content)
                    docs_sorted = sorted(
                        docs,
                        key=lambda d: (0 if key in d.page_content else 1),
                    )
                    docs_top = docs_sorted[:top_k]
                    combine_chain = self._get_combine_chain()
                    result = combine_chain.invoke({"context": docs_top, "input": question})
                    return result.get("answer", "") or "当前知识库中没有相关内容，无法回答。"
                chain = self._get_rag_chain(top_k)
                result = chain.invoke({"input": question})
                return result.get("answer", "") or "当前知识库中没有相关内容，无法回答。"
            except Exception as e:
                chunks = self.retrieve(question, top_k=top_k)
                context = "\n\n".join(chunks) if chunks else ""
                return f"调用 Gemini 失败: {e}\n\n检索到的内容：\n{context}"
        chunks = self.retrieve(question, top_k=top_k)
        if not chunks:
            return "当前知识库中没有相关内容，无法回答。"
        return "根据检索到的内容：\n\n" + "\n\n".join(chunks)
