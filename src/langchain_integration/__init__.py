"""
LangChain integration with Qdrant for vector search capabilities.
"""

from .pipeline import LangchainPipeline
from .vectorstore import VectorStore
from .text_processor import TextProcessor

__all__ = ["LangchainPipeline", "VectorStore", "TextProcessor"]
__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"
