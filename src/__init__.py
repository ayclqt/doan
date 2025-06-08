"""
Modern Q&A system for electronic products using functional programming.

This package provides a complete Q&A system with:
- Functional programming patterns
- Immutable data structures using msgspec
- Vector search with Qdrant
- Web search integration
- Streaming responses
- High performance and maintainability
"""

from .main import Application, create_application, create_simple_qa_function
from .infrastructure.config import ConfigurationManager, get_config, get_logger
from .services.qa_pipeline import QAPipelineService, create_qa_service
from .services.vector_store import (
    initialize_vector_store,
    search_vector_store,
    index_chunks_to_vector_store,
)
from .services.web_search import search_product_info, is_search_available
from .utils.text_processing import (
    load_and_process_data,
    create_embedding_config,
    process_products_to_chunks,
)
from .domain.models import (
    Product,
    TextChunk,
    SearchResult,
    VectorSearchResult,
    QueryContext,
    QAResponse,
    LLMConfig,
    VectorStoreConfig,
    EmbeddingConfig,
    WebSearchConfig,
)
from .core.types import Result, Maybe, safe_call, pipe, compose

# Legacy imports for backward compatibility
from .services.qa_pipeline import QAPipelineService as LangchainPipeline
from .services.vector_store import initialize_vector_store as VectorStore
from .utils.text_processing import load_and_process_data as TextProcessor

__version__ = "2.0.0"
__author__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"

__all__ = [
    # Main application
    "Application",
    "create_application",
    "create_simple_qa_function",
    # Configuration
    "ConfigurationManager",
    "get_config",
    "get_logger",
    # Services
    "QAPipelineService",
    "create_qa_service",
    "initialize_vector_store",
    "search_vector_store",
    "index_chunks_to_vector_store",
    "search_product_info",
    "is_search_available",
    # Utilities
    "load_and_process_data",
    "create_embedding_config",
    "process_products_to_chunks",
    # Domain models
    "Product",
    "TextChunk",
    "SearchResult",
    "VectorSearchResult",
    "QueryContext",
    "QAResponse",
    "LLMConfig",
    "VectorStoreConfig",
    "EmbeddingConfig",
    "WebSearchConfig",
    # Core types
    "Result",
    "Maybe",
    "safe_call",
    "pipe",
    "compose",
    # Legacy compatibility
    "LangchainPipeline",
    "VectorStore",
    "TextProcessor",
]
