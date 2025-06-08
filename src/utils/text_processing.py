"""
Functional text processing utilities with immutable operations.
"""

import json
from functools import partial
from typing import Any, Dict, List, Optional

from ..core.types import Result, safe_call
from ..domain.models import EmbeddingConfig, Product, TextChunk

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


# Pure functions for text processing

def load_json_data(file_path: str) -> Result:
    """Load JSON data from file safely."""
    @safe_call
    def _load():
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)

    return _load()


def parse_product_from_dict(data: Dict[str, Any], index: Optional[int] = None) -> Result:
    """Parse product from dictionary safely."""
    @safe_call
    def _parse():
        # Add ID if not present
        if "id" not in data and index is not None:
            data["id"] = str(index)
        return Product.from_dict(data)

    return _parse()


def product_to_formatted_text(product: Product) -> str:
    """Convert product to formatted text (pure function)."""
    return product.to_text()


def split_text_into_chunks(text: str, config: EmbeddingConfig) -> List[str]:
    """Split text into chunks based on configuration."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        **config.get_text_splitter_config()
    )
    return splitter.split_text(text)


def create_text_chunk(product: Product, text: str, chunk_id: int, total_chunks: int) -> TextChunk:
    """Create text chunk from product and text (pure function)."""
    return TextChunk.from_product(product, text, chunk_id, total_chunks)


def create_chunks_from_product(product: Product, config: EmbeddingConfig) -> List[TextChunk]:
    """Create text chunks from a single product."""
    product_text = product_to_formatted_text(product)
    text_chunks = split_text_into_chunks(product_text, config)

    return [
        create_text_chunk(product, chunk, i, len(text_chunks))
        for i, chunk in enumerate(text_chunks)
    ]


# Functional composition operations

def parse_products_from_data(data: List[Dict[str, Any]]) -> List[Result]:
    """Parse list of products from raw data."""
    return [
        parse_product_from_dict(item, index)
        for index, item in enumerate(data)
    ]


def filter_successful_products(results: List[Result]) -> List[Product]:
    """Filter only successful product parsing results."""
    return [result.value for result in results if result.is_success]


def log_parsing_errors(results: List[Result], logger=None) -> List[Result]:
    """Log parsing errors (side effect function)."""
    if logger:
        errors = [result for result in results if result.is_failure]
        if errors:
            logger.warning(f"Failed to parse {len(errors)} products")
            for result in errors:
                logger.error(f"Parsing error: {result.error}")
    return results


def create_all_chunks(products: List[Product], config: EmbeddingConfig) -> List[TextChunk]:
    """Create all text chunks from products."""
    chunk_lists = [create_chunks_from_product(product, config) for product in products]
    # Flatten the list of lists
    return [chunk for chunk_list in chunk_lists for chunk in chunk_list]


# High-level functional pipelines

def load_and_parse_products(file_path: str, logger=None) -> Result:
    """Complete pipeline to load and parse products."""
    return (
        load_json_data(file_path)
        .map(parse_products_from_data)
        .map(partial(log_parsing_errors, logger=logger))
        .map(filter_successful_products)
    )


def process_products_to_chunks(products: List[Product], config: EmbeddingConfig, logger=None) -> List[TextChunk]:
    """Process products into text chunks."""
    chunks = create_all_chunks(products, config)

    if logger:
        logger.info(f"Created {len(chunks)} chunks from {len(products)} products")

    return chunks


def load_and_process_data(file_path: str, config: EmbeddingConfig, logger=None) -> Result:
    """Complete pipeline from file to text chunks."""
    return (
        load_and_parse_products(file_path, logger)
        .map(lambda products: process_products_to_chunks(products, config, logger))
    )


# Utility functions for text analysis

def extract_keywords_from_text(text: str, min_length: int = 3) -> List[str]:
    """Extract keywords from text (simple implementation)."""
    import re

    # Simple keyword extraction - remove punctuation and split
    words = re.findall(r'\b\w+\b', text.lower())
    return [word for word in words if len(word) >= min_length]


def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate simple text similarity based on common words."""
    words1 = set(extract_keywords_from_text(text1))
    words2 = set(extract_keywords_from_text(text2))

    if not words1 or not words2:
        return 0.0

    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))

    return intersection / union if union > 0 else 0.0


def enhance_query_with_keywords(query: str, additional_keywords: Optional[List[str]] = None) -> str:
    """Enhance query with additional keywords."""
    enhanced_query = query

    if additional_keywords:
        for keyword in additional_keywords:
            if keyword.lower() not in enhanced_query.lower():
                enhanced_query += f" {keyword}"

    return enhanced_query.strip()


def is_time_sensitive_query(query: str) -> bool:
    """Check if query contains time-sensitive keywords."""
    time_sensitive_keywords = [
        "giá", "khuyến mãi", "sale", "discount", "mới", "2024", "2025",
        "hiện tại", "bây giờ", "mới nhất", "cập nhật"
    ]
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in time_sensitive_keywords)


def extract_product_type_from_query(query: str) -> Optional[str]:
    """Extract product type from query."""
    product_types = {
        "điện thoại": ["điện thoại", "smartphone", "phone", "mobile"],
        "laptop": ["laptop", "máy tính xách tay", "notebook"],
        "máy tính": ["máy tính", "computer", "pc", "desktop"],
        "tai nghe": ["tai nghe", "headphone", "earphone", "earbud"],
        "loa": ["loa", "speaker"],
        "màn hình": ["màn hình", "monitor", "display"],
        "bàn phím": ["bàn phím", "keyboard"],
        "chuột": ["chuột", "mouse"],
    }

    query_lower = query.lower()
    for product_type, keywords in product_types.items():
        if any(keyword in query_lower for keyword in keywords):
            return product_type

    return None


# Validation functions for text processing

def validate_text_content(text: str) -> Result:
    """Validate text content."""
    if not text or not text.strip():
        return Result.failure(ValueError("Text content cannot be empty"))

    if len(text.strip()) < 10:
        return Result.failure(ValueError("Text content too short"))

    return Result.success(text.strip())


def validate_chunk_size(chunk_size: int) -> Result:
    """Validate chunk size parameter."""
    if chunk_size <= 0:
        return Result.failure(ValueError("Chunk size must be positive"))

    if chunk_size > 10000:
        return Result.failure(ValueError("Chunk size too large (max 10000)"))

    return Result.success(chunk_size)


def validate_overlap_ratio(chunk_size: int, overlap: int) -> Result:
    """Validate chunk overlap ratio."""
    if overlap < 0:
        return Result.failure(ValueError("Overlap cannot be negative"))

    if overlap >= chunk_size:
        return Result.failure(ValueError("Overlap must be less than chunk size"))

    overlap_ratio = overlap / chunk_size
    if overlap_ratio > 0.5:
        return Result.failure(ValueError("Overlap ratio should not exceed 50%"))

    return Result.success(overlap)


# Configuration builders

def create_embedding_config(
    model_name: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> Result:
    """Create validated embedding configuration."""
    validations = [
        validate_text_content(model_name).map(lambda _: model_name),
        validate_chunk_size(chunk_size),
        validate_overlap_ratio(chunk_size, chunk_overlap).map(lambda _: chunk_overlap)
    ]

    # Check all validations
    for validation in validations:
        if validation.is_failure:
            return validation

    return Result.success(EmbeddingConfig(
        model_name=model_name,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    ))


# Text formatting utilities

def format_chunks_for_display(chunks: List[TextChunk], max_length: int = 200) -> List[str]:
    """Format chunks for display with truncation."""
    return [
        f"Chunk {chunk.chunk_id + 1}/{chunk.total_chunks} - {chunk.product_name}: "
        f"{chunk.text[:max_length]}{'...' if len(chunk.text) > max_length else ''}"
        for chunk in chunks
    ]


def format_products_summary(products: List[Product]) -> str:
    """Format products summary for logging."""
    if not products:
        return "No products found"

    total = len(products)
    brands = set(product.brand for product in products if product.brand)
    categories = set(product.category for product in products if product.category)

    summary_parts = [f"Total products: {total}"]

    if brands:
        summary_parts.append(f"Brands: {len(brands)} ({', '.join(list(brands)[:5])})")

    if categories:
        summary_parts.append(f"Categories: {len(categories)} ({', '.join(list(categories)[:5])})")

    return "; ".join(summary_parts)


def create_context_from_chunks(chunks: List[TextChunk], max_chunks: int = 5) -> str:
    """Create context string from text chunks."""
    if not chunks:
        return ""

    selected_chunks = chunks[:max_chunks]
    formatted_chunks = [
        f"Sản phẩm {i + 1}:\n{chunk.text}"
        for i, chunk in enumerate(selected_chunks)
    ]

    return "\n\n".join(formatted_chunks)
