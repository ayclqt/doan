"""
Module khởi tạo cho package core
"""

from .chatbot import ProductChatbot
from .ingest import DataIngestor
from .vector_store import VectorStore

__all__ = ["ProductChatbot", "DataIngestor", "VectorStore"]
__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__license__ = "MIT"
__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"
