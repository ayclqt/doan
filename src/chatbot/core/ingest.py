"""
Module xử lý việc nhập dữ liệu vào vector store
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
    CSVLoader,
    UnstructuredExcelLoader,
)

from ..config import logger
from .vector_store import VectorStore

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__license__ = "MIT"
__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class DataIngestor:
    """
    Lớp xử lý việc nhập dữ liệu vào vector store
    """

    def __init__(self, vector_store: Optional[VectorStore] = None):
        """
        Khởi tạo DataIngestor

        Args:
            vector_store: Đối tượng VectorStore để lưu trữ dữ liệu
        """
        self.vector_store = vector_store or VectorStore()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        logger.info("Khởi tạo DataIngestor")

    def ingest_documents(self, documents: List[Document]) -> None:
        """
        Xử lý và nhập danh sách tài liệu vào vector store

        Args:
            documents: Danh sách tài liệu cần xử lý
        """
        if not documents:
            logger.warning("Không có tài liệu nào để xử lý")
            return

        # Chia nhỏ tài liệu
        split_docs = self.text_splitter.split_documents(documents)
        logger.info(f"Đã chia {len(documents)} tài liệu thành {len(split_docs)} đoạn")

        # Thêm vào vector store
        self.vector_store.add_documents(split_docs)
        logger.info(f"Đã nhập {len(split_docs)} đoạn vào vector store")

    def ingest_texts(
        self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        Xử lý và nhập danh sách văn bản vào vector store

        Args:
            texts: Danh sách văn bản cần xử lý
            metadatas: Danh sách metadata tương ứng với từng văn bản
        """
        if not texts:
            logger.warning("Không có văn bản nào để xử lý")
            return

        # Chia nhỏ văn bản
        split_texts = []
        split_metadatas = []

        for i, text in enumerate(texts):
            chunks = self.text_splitter.split_text(text)
            split_texts.extend(chunks)

            # Xử lý metadata nếu có
            metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
            split_metadatas.extend([metadata] * len(chunks))

        logger.info(f"Đã chia {len(texts)} văn bản thành {len(split_texts)} đoạn")

        # Thêm vào vector store
        self.vector_store.add_texts(split_texts, split_metadatas)
        logger.info(f"Đã nhập {len(split_texts)} đoạn vào vector store")

    def ingest_from_file(self, file_path: str) -> None:
        """
        Nhập dữ liệu từ file vào vector store

        Args:
            file_path: Đường dẫn đến file cần xử lý
        """
        if not os.path.exists(file_path):
            logger.error(f"File không tồn tại: {file_path}")
            return

        logger.info(f"Bắt đầu xử lý file: {file_path}")
        path = Path(file_path)

        # Chọn loader phù hợp dựa vào phần mở rộng của file
        loader = None

        if path.suffix.lower() == ".txt":
            loader = TextLoader(file_path, encoding="utf-8")
        elif path.suffix.lower() == ".pdf":
            loader = PyPDFLoader(file_path)
        elif path.suffix.lower() in [".doc", ".docx"]:
            loader = Docx2txtLoader(file_path)
        elif path.suffix.lower() == ".csv":
            loader = CSVLoader(file_path)
        elif path.suffix.lower() in [".xls", ".xlsx"]:
            loader = UnstructuredExcelLoader(file_path)
        else:
            logger.error(f"Không hỗ trợ định dạng file: {path.suffix}")
            return

        # Tải tài liệu
        try:
            documents = loader.load()
            logger.info(f"Đã tải {len(documents)} tài liệu từ file {path.name}")

            # Xử lý và nhập tài liệu
            self.ingest_documents(documents)

        except Exception as e:
            logger.error(f"Lỗi khi xử lý file {path.name}: {str(e)}")

    def ingest_from_directory(
        self, directory_path: str, recursive: bool = True
    ) -> None:
        """
        Nhập dữ liệu từ thư mục vào vector store

        Args:
            directory_path: Đường dẫn đến thư mục cần xử lý
            recursive: Có xử lý đệ quy các thư mục con hay không
        """
        if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
            logger.error(f"Thư mục không tồn tại: {directory_path}")
            return

        logger.info(f"Bắt đầu xử lý thư mục: {directory_path}")

        # Lấy danh sách file trong thư mục
        path = Path(directory_path)

        # Xác định pattern dựa vào tham số recursive
        pattern = "**/*" if recursive else "*"

        # Các định dạng file được hỗ trợ
        supported_extensions = [
            ".txt",
            ".pdf",
            ".doc",
            ".docx",
            ".csv",
            ".xls",
            ".xlsx",
        ]

        # Xử lý từng file
        for file_path in path.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                self.ingest_from_file(str(file_path))

        logger.info(f"Đã hoàn thành xử lý thư mục: {directory_path}")

    def get_store_stats(self) -> Dict[str, Any]:
        """
        Lấy thông tin thống kê về vector store

        Returns:
            Dictionary chứa thông tin thống kê
        """
        return self.vector_store.get_collection_stats()

    def reset_store(self) -> None:
        """Xóa toàn bộ dữ liệu trong vector store"""
        self.vector_store.delete_collection()
        logger.info("Đã xóa toàn bộ dữ liệu trong vector store")
