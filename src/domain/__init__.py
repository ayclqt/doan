"""
Domain module containing business models and entities using msgspec.
"""

from .models import (
    Product,
    TextChunk,
    SearchResult,
    VectorSearchResult,
    QueryContext,
    QAResponse,
    EmbeddingConfig,
    VectorStoreConfig,
    LLMConfig,
    WebSearchConfig,
)

__all__ = [
    # Core domain entities
    "Product",
    "TextChunk",
    "SearchResult",
    "VectorSearchResult",
    "QueryContext",
    "QAResponse",
    # Configuration models
    "EmbeddingConfig",
    "VectorStoreConfig",
    "LLMConfig",
    "WebSearchConfig",
]
