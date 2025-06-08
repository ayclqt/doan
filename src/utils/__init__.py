"""
Utilities module containing helper functions and text processing utilities.
"""

from .text_processing import (
    calculate_text_similarity,
    create_all_chunks,
    create_chunks_from_product,
    create_context_from_chunks,
    create_embedding_config,
    create_text_chunk,
    enhance_query_with_keywords,
    extract_keywords_from_text,
    extract_product_type_from_query,
    filter_successful_products,
    format_chunks_for_display,
    format_products_summary,
    is_time_sensitive_query,
    load_and_parse_products,
    load_and_process_data,
    load_json_data,
    log_parsing_errors,
    parse_product_from_dict,
    parse_products_from_data,
    process_products_to_chunks,
    product_to_formatted_text,
    split_text_into_chunks,
    validate_chunk_size,
    validate_overlap_ratio,
    validate_text_content,
)

__all__ = [
    # Data loading and parsing
    "load_json_data",
    "parse_product_from_dict",
    "load_and_parse_products",
    "parse_products_from_data",
    "filter_successful_products",
    "log_parsing_errors",
    # Text processing
    "product_to_formatted_text",
    "split_text_into_chunks",
    "create_text_chunk",
    "create_chunks_from_product",
    "create_all_chunks",
    "process_products_to_chunks",
    "load_and_process_data",
    # Text analysis
    "extract_keywords_from_text",
    "calculate_text_similarity",
    "enhance_query_with_keywords",
    "is_time_sensitive_query",
    "extract_product_type_from_query",
    # Validation
    "validate_text_content",
    "validate_chunk_size",
    "validate_overlap_ratio",
    # Configuration
    "create_embedding_config",
    # Formatting
    "format_chunks_for_display",
    "format_products_summary",
    "create_context_from_chunks",
]
