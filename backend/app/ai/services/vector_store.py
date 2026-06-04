"""
VectorStoreService — FAISS 向量库管理。

功能:
    1. 文档导入与向量化
    2. 相似度检索
    3. 向量库持久化（磁盘）
"""

import os
import json
import logging
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# ---- 向量库存储路径 ----
# 优先使用环境变量，避免中文路径问题

_default_path = Path(os.environ.get("TEMP", "C:/Temp")) / "smartdesk_vector_store"
VECTOR_STORE_DIR = Path(os.environ.get("VECTOR_STORE_DIR", str(_default_path)))
VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)


class SimpleEmbeddings(Embeddings):
    """
    Embedding 封装 — 使用 BAAI/bge-small-zh-v1.5 本地模型。

    模型: BAAI/bge-small-zh-v1.5（中文优化，512维）
    """

    _model = None
    _dimension = 512

    def __init__(self):
        if SimpleEmbeddings._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("[Embedding] 加载本地模型: BAAI/bge-small-zh-v1.5")
                SimpleEmbeddings._model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
                SimpleEmbeddings._dimension = SimpleEmbeddings._model.get_embedding_dimension()
                logger.info("[Embedding] 模型加载完成，维度: %d", SimpleEmbeddings._dimension)
            except Exception as e:
                logger.error("[Embedding] 模型加载失败: %s", e)
                raise

    def _embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = SimpleEmbeddings._model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]


class VectorStoreService:
    """
    FAISS 向量库服务。

    管理文档的存储、索引和检索。
    """

    def __init__(self):
        self._embedding = SimpleEmbeddings()
        self._dimension = SimpleEmbeddings._dimension
        self._index: faiss.IndexFlatIP | None = None
        self._documents: list[Document] = []
        self._doc_id_counter = 0

        # 尝试加载已有索引
        self._load_index()

    # ---- 文档导入 ----

    def add_documents(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> int:
        """
        导入文档到向量库。

        Args:
            texts: 原始文本列表
            metadatas: 元数据列表
            chunk_size: 分块大小
            chunk_overlap: 分块重叠

        Returns:
            新增文档块数量
        """
        # 1. 文本分块
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " "],
        )

        all_chunks: list[Document] = []
        for i, text in enumerate(texts):
            meta = metadatas[i] if metadatas else {}
            chunks = splitter.create_documents([text], metadatas=[meta])
            for chunk in chunks:
                chunk.metadata["doc_id"] = self._doc_id_counter
                self._doc_id_counter += 1
            all_chunks.extend(chunks)

        if not all_chunks:
            return 0

        # 2. 向量化
        contents = [c.page_content for c in all_chunks]
        try:
            embeddings = self._embedding.embed_documents(contents)
            embeddings_np = np.array(embeddings, dtype=np.float32)
        except Exception as e:
            logger.error("[VectorStore] Embedding 失败: %s", e)
            raise

        # 3. 归一化（用于内积相似度）
        faiss.normalize_L2(embeddings_np)

        # 4. 写入 FAISS 索引
        if self._index is None:
            self._index = faiss.IndexFlatIP(self._dimension)

        self._index.add(embeddings_np)
        self._documents.extend(all_chunks)

        # 5. 持久化
        self._save_index()

        logger.info("[VectorStore] 导入 %d 个文档块", len(all_chunks))
        return len(all_chunks)

    # ---- 检索 ----

    def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """
        相似度检索。

        Args:
            query: 查询文本
            top_k: 返回前 K 个结果

        Returns:
            检索结果列表，包含 content, score, metadata
        """
        if self._index is None or self._index.ntotal == 0:
            return []

        # 向量化查询
        query_vec = self._embedding.embed_query(query)
        query_np = np.array([query_vec], dtype=np.float32)
        faiss.normalize_L2(query_np)

        # 检索
        k = min(top_k, self._index.ntotal)
        scores, indices = self._index.search(query_np, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._documents):
                continue
            doc = self._documents[idx]
            results.append({
                "content": doc.page_content,
                "score": float(score),
                "metadata": doc.metadata,
            })

        return results

    # ---- 持久化 ----

    def _save_index(self) -> None:
        """保存索引和文档到磁盘"""
        if self._index is None:
            return

        index_path = VECTOR_STORE_DIR / "faiss.index"
        docs_path = VECTOR_STORE_DIR / "documents.json"

        faiss.write_index(self._index, str(index_path))

        docs_data = [
            {
                "page_content": d.page_content,
                "metadata": d.metadata,
            }
            for d in self._documents
        ]
        with open(docs_path, "w", encoding="utf-8") as f:
            json.dump(docs_data, f, ensure_ascii=False)

        logger.info("[VectorStore] 索引已保存: %d 条文档", len(self._documents))

    def _load_index(self) -> None:
        """从磁盘加载索引和文档"""
        index_path = VECTOR_STORE_DIR / "faiss.index"
        docs_path = VECTOR_STORE_DIR / "documents.json"

        if not index_path.exists() or not docs_path.exists():
            logger.info("[VectorStore] 未找到已有索引，将创建新索引")
            return

        try:
            self._index = faiss.read_index(str(index_path))

            with open(docs_path, "r", encoding="utf-8") as f:
                docs_data = json.load(f)

            self._documents = [
                Document(page_content=d["page_content"], metadata=d["metadata"])
                for d in docs_data
            ]

            if self._documents:
                self._doc_id_counter = max(
                    d.metadata.get("doc_id", 0) for d in self._documents
                ) + 1

            logger.info("[VectorStore] 加载已有索引: %d 条文档", len(self._documents))
        except Exception as e:
            logger.error("[VectorStore] 加载索引失败: %s", e)
            self._index = None
            self._documents = []

    # ---- 状态 ----

    @property
    def doc_count(self) -> int:
        """当前文档数量"""
        return len(self._documents)

    def clear(self) -> None:
        """清空向量库"""
        self._index = None
        self._documents = []
        self._doc_id_counter = 0

        index_path = VECTOR_STORE_DIR / "faiss.index"
        docs_path = VECTOR_STORE_DIR / "documents.json"
        if index_path.exists():
            index_path.unlink()
        if docs_path.exists():
            docs_path.unlink()

        logger.info("[VectorStore] 已清空")


# ---- 全局单例 ----

vector_store = VectorStoreService()
