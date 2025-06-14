"""
LangChain integration with Qdrant for vector search capabilities.
"""

# Clean facade system exports
from .facade import get_facade, ProductAssistantFacade
from .product_introduction_agent import get_product_introduction_agent
from .product_deduplication import deduplicate_search_results
from .enhanced_search import search_diverse_products

# Core utilities (still needed)
from .text_processor import TextProcessor
from .vectorstore import VectorStore

__all__ = [
    # Clean system
    "get_facade",
    "ProductAssistantFacade",
    "get_product_introduction_agent",
    "deduplicate_search_results",
    "search_diverse_products",
    # Core utilities
    "TextProcessor",
    "VectorStore",
]

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"
