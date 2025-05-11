"""
Module quản lý vector store sử dụng ChromaDB
"""

import os
from typing import List, Optional, Dict, Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document

from ..config import settings, logger

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__license__ = "MIT"
__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class VectorStore:
    """
    Lớp quản lý kho dữ liệu vector sử dụng ChromaDB
    """

    def __init__(
        self,
        collection_name: Optional[str] = None,
        persist_directory: Optional[str] = None,
        embedding: Optional[Embeddings] = None,
    ):
        """
        Khởi tạo VectorStore

        Args:
            collection_name: Tên của collection trong ChromaDB
            persist_directory: Thư mục lưu trữ dữ liệu của ChromaDB
            embedding: Model embedding sử dụng
        """
        self.collection_name = collection_name or settings.collection_name
        self.persist_directory = persist_directory or settings.chroma_db_directory

        # Đảm bảo thư mục lưu trữ tồn tại
        os.makedirs(self.persist_directory, exist_ok=True)

        # Khởi tạo embedding
        self.embedding = embedding or OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key.get_secret_value(),
        )

        # Khởi tạo client ChromaDB
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

        # Khởi tạo vector store
        self._initialize_vector_store()

        logger.info(
            "Khởi tạo VectorStore",
            collection_name=self.collection_name,
            persist_directory=self.persist_directory,
        )

    def _initialize_vector_store(self) -> None:
        """Khởi tạo vector store với LangChain"""
        self.vector_store = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embedding,
            persist_directory=self.persist_directory,
            client=self.client,
        )

    def add_documents(self, documents: List[Document]) -> None:
        """
        Thêm tài liệu vào vector store

        Args:
            documents: Danh sách tài liệu cần thêm
        """
        if not documents:
            logger.warning("Không có tài liệu nào để thêm vào vector store")
            return

        logger.info(f"Thêm {len(documents)} tài liệu vào vector store")
        self.vector_store.add_documents(documents)

    def add_texts(
        self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        Thêm danh sách văn bản vào vector store

        Args:
            texts: Danh sách văn bản cần thêm
            metadatas: Danh sách metadata tương ứng với từng văn bản
        """
        if not texts:
            logger.warning("Không có văn bản nào để thêm vào vector store")
            return

        logger.info(f"Thêm {len(texts)} văn bản vào vector store")
        self.vector_store.add_texts(texts=texts, metadatas=metadatas)

    def similarity_search(self, query: str, k: int = 4, **kwargs) -> List[Document]:
        """
        Tìm kiếm tài liệu tương tự với truy vấn

        Args:
            query: Truy vấn cần tìm kiếm
            k: Số lượng kết quả trả về
            **kwargs: Các tham số bổ sung

        Returns:
            Danh sách tài liệu tương tự
        """
        logger.info("Tìm kiếm tài liệu tương tự", query=query, k=k)
        return self.vector_store.similarity_search(query=query, k=k, **kwargs)

    def similarity_search_with_score(
        self, query: str, k: int = 4, **kwargs
    ) -> List[tuple[Document, float]]:
        """
        Tìm kiếm tài liệu tương tự với truy vấn và trả về điểm tương đồng

        Args:
            query: Truy vấn cần tìm kiếm
            k: Số lượng kết quả trả về
            **kwargs: Các tham số bổ sung

        Returns:
            Danh sách tuple gồm tài liệu và điểm tương đồng
        """
        logger.info("Tìm kiếm tài liệu tương tự với điểm", query=query, k=k)
        return self.vector_store.similarity_search_with_score(
            query=query, k=k, **kwargs
        )

    def get_collections(self) -> List[str]:
        """
        Lấy danh sách tên các collection trong ChromaDB

        Returns:
            Danh sách tên các collection
        """
        return [c.name for c in self.client.list_collections()]

    def delete_collection(self) -> None:
        """Xóa collection hiện tại"""
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Đã xóa collection {self.collection_name}")
        except ValueError as e:
            logger.error(f"Lỗi khi xóa collection: {e}")

        # Khởi tạo lại vector store
        self._initialize_vector_store()

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Lấy thông tin thống kê về collection hiện tại

        Returns:
            Dictionary chứa thông tin thống kê
        """
        try:
            collection = self.client.get_collection(self.collection_name)
            count = collection.count()
            return {
                "collection_name": self.collection_name,
                "count": count,
            }
        except ValueError:
            return {
                "collection_name": self.collection_name,
                "count": 0,
            }
