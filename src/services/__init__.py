"""
Services module containing business logic and application services.
"""

from .qa_pipeline import (
    QAPipelineService,
    create_qa_service,
    create_simple_qa_function,
    create_streaming_qa_function,
    validate_qa_pipeline_configs,
    calculate_pipeline_metrics,
)

from .vector_store import (
    initialize_vector_store,
    search_vector_store,
    index_chunks_to_vector_store,
    create_vector_store_config,
    create_search_function,
    calculate_vector_store_metrics,
    get_vector_store_status,
    estimate_storage_size,
)

from .web_search import (
    search_product_info,
    is_search_available,
    create_web_search_config,
    create_search_function as create_web_search_function,
    format_search_results_for_context,
    should_use_web_search_for_query,
    combine_vector_and_web_context,
    calculate_search_metrics,
)

__all__ = [
    # Q&A Pipeline Services
    "QAPipelineService",
    "create_qa_service",
    "create_simple_qa_function",
    "create_streaming_qa_function",
    "validate_qa_pipeline_configs",
    "calculate_pipeline_metrics",
    # Vector Store Services
    "initialize_vector_store",
    "search_vector_store",
    "index_chunks_to_vector_store",
    "create_vector_store_config",
    "create_search_function",
    "calculate_vector_store_metrics",
    "get_vector_store_status",
    "estimate_storage_size",
    # Web Search Services
    "search_product_info",
    "is_search_available",
    "create_web_search_config",
    "create_web_search_function",
    "format_search_results_for_context",
    "should_use_web_search_for_query",
    "combine_vector_and_web_context",
    "calculate_search_metrics",
]
