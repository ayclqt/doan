"""
Functional web search service using DuckDuckGo with immutable operations.
"""

from typing import List, Optional
from functools import partial

from ..core.types import Result, safe_call, pipe, memoize, retry
from ..domain.models import SearchResult, WebSearchConfig
from ..utils.text_processing import enhance_query_with_keywords

try:
    from duckduckgo_search import DDGS
    from duckduckgo_search.exceptions import (
        DuckDuckGoSearchException,
        RatelimitException,
        TimeoutException,
    )

    DDGS_AVAILABLE = True
except ImportError:
    DDGS = None
    DuckDuckGoSearchException = Exception
    RatelimitException = Exception
    TimeoutException = Exception
    DDGS_AVAILABLE = False


__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


# Pure functions for search operations


def is_search_available() -> bool:
    """Check if web search is available."""
    return DDGS_AVAILABLE


def create_electronics_keywords() -> List[str]:
    """Create list of electronics-related keywords."""
    return ["điện tử", "công nghệ", "smartphone", "laptop", "máy tính"]


def create_product_keywords() -> List[str]:
    """Create list of product-related keywords."""
    return ["sản phẩm", "giá", "thông số", "đánh giá", "review", "mua", "bán"]


def enhance_product_query(
    query: str, product_keywords: Optional[List[str]] = None
) -> str:
    """Enhance search query with product-specific terms."""
    electronics_terms = create_electronics_keywords()

    # Start with original query
    enhanced_query = query

    # Add provided keywords
    if product_keywords:
        enhanced_query = enhance_query_with_keywords(enhanced_query, product_keywords)

    # Add electronics context if not present
    if not any(term in enhanced_query.lower() for term in electronics_terms):
        enhanced_query += " điện tử"

    return enhanced_query


def calculate_relevance_score(result_dict: dict, query: str) -> float:
    """Calculate relevance score for a search result."""
    title = result_dict.get("title", "").lower()
    body = result_dict.get("body", "").lower()
    query_lower = query.lower()

    score = 0.0
    query_terms = query_lower.split()

    if not query_terms:
        return 0.0

    # Score based on query terms in title (higher weight)
    title_matches = sum(1 for term in query_terms if term in title)
    score += (title_matches / len(query_terms)) * 0.6

    # Score based on query terms in body
    body_matches = sum(1 for term in query_terms if term in body)
    score += (body_matches / len(query_terms)) * 0.4

    # Bonus for product-related terms
    product_terms = create_product_keywords()
    product_matches = sum(1 for term in product_terms if term in title or term in body)
    score += min(product_matches * 0.1, 0.2)  # Max 0.2 bonus

    return min(score, 1.0)  # Cap at 1.0


def create_search_result(result_dict: dict, query: str) -> SearchResult:
    """Create SearchResult from DuckDuckGo result dictionary."""
    relevance_score = calculate_relevance_score(result_dict, query)

    return SearchResult(
        title=result_dict.get("title", ""),
        body=result_dict.get("body", ""),
        href=result_dict.get("href", ""),
        relevance_score=relevance_score,
    )


def sort_results_by_relevance(results: List[SearchResult]) -> List[SearchResult]:
    """Sort search results by relevance score."""
    return sorted(results, key=lambda x: x.relevance_score, reverse=True)


def filter_relevant_results(
    results: List[SearchResult], min_score: float = 0.1
) -> List[SearchResult]:
    """Filter results by minimum relevance score."""
    return [result for result in results if result.relevance_score >= min_score]


# Search execution functions


@safe_call
def execute_ddg_search(enhanced_query: str, config: WebSearchConfig) -> List[dict]:
    """Execute DuckDuckGo search safely."""
    if not DDGS_AVAILABLE:
        raise RuntimeError("DuckDuckGo search is not available")

    search_params = {
        "keywords": enhanced_query,
        "region": config.region,
        "safesearch": config.safesearch,
        "max_results": config.max_results,
        "backend": config.backend,
    }

    # Add timelimit if specified
    if config.timelimit:
        search_params["timelimit"] = config.timelimit

    with DDGS() as ddgs:
        return list(ddgs.text(**search_params))


@retry(max_attempts=3, delay=1.0)
def search_with_retry(enhanced_query: str, config: WebSearchConfig) -> Result:
    """Execute search with retry logic."""
    return execute_ddg_search(enhanced_query, config)


def process_search_results(raw_results: List[dict], query: str) -> List[SearchResult]:
    """Process raw search results into SearchResult objects."""
    if not raw_results:
        return []

    # Create SearchResult objects
    results = [create_search_result(result, query) for result in raw_results]

    # Filter and sort by relevance
    return pipe(
        results,
        partial(filter_relevant_results, min_score=0.1),
        sort_results_by_relevance,
    )


# High-level search functions


def search_product_info(
    query: str, config: WebSearchConfig, product_keywords: Optional[List[str]] = None
) -> Result:
    """Search for product information using DuckDuckGo."""
    if not config.enabled:
        return Result.success([])

    if not is_search_available():
        return Result.failure(RuntimeError("Web search not available"))

    # Enhance query
    enhanced_query = enhance_product_query(query, product_keywords)

    # Execute search
    search_result = search_with_retry(enhanced_query, config)

    if search_result.is_failure:
        return search_result

    # Process results
    processed_results = process_search_results(search_result.value, query)

    return Result.success(processed_results)


@memoize
def get_cached_search_results(query: str, config_hash: str) -> Result:
    """Get cached search results (memoized for performance)."""
    # This would be called by the main search function with a config hash
    # The actual implementation would call search_product_info
    pass


# Result formatting functions


def format_search_results_for_context(results: List[SearchResult]) -> str:
    """Format search results for LLM context."""
    if not results:
        return "Không tìm thấy thông tin từ tìm kiếm web."

    formatted_results = []
    for i, result in enumerate(results, 1):
        formatted_result = f"""
Kết quả tìm kiếm {i}:
Tiêu đề: {result.title}
Nội dung: {result.body}
Nguồn: {result.href}
Độ phù hợp: {result.relevance_score:.2f}
""".strip()
        formatted_results.append(formatted_result)

    return "\n\n".join(formatted_results)


def format_search_summary(results: List[SearchResult]) -> str:
    """Format search results summary."""
    if not results:
        return "Không có kết quả tìm kiếm"

    total_results = len(results)
    avg_relevance = sum(r.relevance_score for r in results) / total_results
    top_sources = list(
        set(result.href.split("/")[2] for result in results[:3] if result.href)
    )

    return (
        f"Tìm thấy {total_results} kết quả với độ phù hợp trung bình {avg_relevance:.2f}. "
        f"Nguồn chính: {', '.join(top_sources[:3])}"
    )


# Hybrid search decision functions


def should_use_web_search_for_query(
    query: str, vector_results_count: int, similarity_threshold: float = 0.7
) -> bool:
    """Determine if web search should be used based on query analysis."""
    # Always search if no vector results
    if vector_results_count == 0:
        return True

    # Search if insufficient vector results
    if vector_results_count < 2:
        return True

    # Check for time-sensitive queries
    from ..utils.text_processing import is_time_sensitive_query

    if is_time_sensitive_query(query):
        return True

    # Check for specific product comparison queries
    comparison_keywords = ["so sánh", "khác nhau", "tốt hơn", "vs", "versus"]
    if any(keyword in query.lower() for keyword in comparison_keywords):
        return True

    return False


def combine_vector_and_web_context(
    vector_context: str, web_results: List[SearchResult]
) -> str:
    """Combine vector store and web search results into unified context."""
    combined_parts = []

    if vector_context and vector_context.strip():
        combined_parts.append("=== THÔNG TIN TỪ CƠ SỞ DỮ LIỆU SẢN PHẨM ===")
        combined_parts.append(vector_context)

    if web_results:
        combined_parts.append("\n=== THÔNG TIN BỔ SUNG TỪ TÌM KIẾM WEB ===")
        combined_parts.append(format_search_results_for_context(web_results))

    return "\n\n".join(combined_parts)


# Configuration validation


def validate_web_search_config(config: WebSearchConfig) -> Result:
    """Validate web search configuration."""
    if config.max_results <= 0:
        return Result.failure(ValueError("max_results must be positive"))

    if config.max_results > 20:
        return Result.failure(ValueError("max_results should not exceed 20"))

    if not (0.0 <= config.similarity_threshold <= 1.0):
        return Result.failure(
            ValueError("similarity_threshold must be between 0 and 1")
        )

    valid_regions = ["vn-vi", "us-en", "uk-en", "au-en"]
    if config.region not in valid_regions:
        return Result.failure(
            ValueError(f"Invalid region. Must be one of: {valid_regions}")
        )

    valid_safesearch = ["on", "moderate", "off"]
    if config.safesearch not in valid_safesearch:
        return Result.failure(
            ValueError(f"Invalid safesearch. Must be one of: {valid_safesearch}")
        )

    return Result.success(config)


# Factory functions


def create_web_search_config(
    enabled: bool = True,
    max_results: int = 5,
    region: str = "vn-vi",
    similarity_threshold: float = 0.7,
) -> Result:
    """Create and validate web search configuration."""
    config = WebSearchConfig(
        enabled=enabled,
        max_results=max_results,
        region=region,
        similarity_threshold=similarity_threshold,
    )

    return validate_web_search_config(config)


def create_search_function(config: WebSearchConfig):
    """Create a partially applied search function with configuration."""
    return partial(search_product_info, config=config)


# Error handling utilities


def handle_search_exception(exception: Exception) -> str:
    """Handle search exceptions and return user-friendly message."""
    if isinstance(exception, RatelimitException):
        return "Tìm kiếm web bị giới hạn tần suất. Vui lòng thử lại sau."
    elif isinstance(exception, TimeoutException):
        return "Tìm kiếm web quá thời gian chờ. Vui lòng thử lại."
    elif isinstance(exception, DuckDuckGoSearchException):
        return "Có lỗi xảy ra với dịch vụ tìm kiếm web."
    else:
        return f"Lỗi không xác định khi tìm kiếm web: {str(exception)}"


# Monitoring and metrics


def calculate_search_metrics(results: List[SearchResult]) -> dict:
    """Calculate metrics for search results."""
    if not results:
        return {
            "total_results": 0,
            "average_relevance": 0.0,
            "high_relevance_count": 0,
            "unique_sources": 0,
        }

    total_results = len(results)
    average_relevance = sum(r.relevance_score for r in results) / total_results
    high_relevance_count = sum(1 for r in results if r.relevance_score > 0.5)
    unique_sources = len(
        set(r.href.split("/")[2] if r.href else "unknown" for r in results)
    )

    return {
        "total_results": total_results,
        "average_relevance": average_relevance,
        "high_relevance_count": high_relevance_count,
        "unique_sources": unique_sources,
    }
