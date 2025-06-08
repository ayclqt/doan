"""
Web search integration using DuckDuckGo for product information retrieval.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..config import config, logger

try:
    from duckduckgo_search import DDGS
    from duckduckgo_search.exceptions import (
        DuckDuckGoSearchException,
        RatelimitException,
        TimeoutException,
    )
except ImportError:
    DDGS = None
    DuckDuckGoSearchException = Exception
    RatelimitException = Exception
    TimeoutException = Exception
    logger.warning(
        "duckduckgo-search not installed. Web search functionality will be disabled."
    )


__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


@dataclass
class SearchResult:
    """Data class for search results."""

    title: str
    body: str
    href: str
    relevance_score: float = 0.0


class WebSearcher:
    """DuckDuckGo web search integration for product information."""

    def __init__(
        self,
        max_results: int = None,
        region: str = None,
        safesearch: str = "moderate",
        timelimit: str = None,
        backend: str = "auto",
    ):
        """
        Initialize WebSearcher.

        Args:
            max_results: Maximum number of search results to return
            region: Search region (vn-vi for Vietnam Vietnamese)
            safesearch: Safe search setting (on, moderate, off)
            timelimit: Time limit for search results (d, w, m, y)
            backend: Search backend (auto, html, lite)
        """
        self.max_results = max_results or config.web_search_max_results
        self.region = region or config.web_search_region
        self.safesearch = safesearch
        self.timelimit = timelimit or (
            config.web_search_timelimit if config.web_search_timelimit else None
        )
        self.backend = backend or config.web_search_backend
        self.logger = logger

        if DDGS is None:
            self.logger.error(
                "DuckDuckGo search is not available. Please install duckduckgo-search package."
            )
            self.enabled = False
        else:
            self.enabled = True

    def search_product_info(
        self, query: str, product_keywords: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """
        Search for product information using DuckDuckGo.

        Args:
            query: Search query
            product_keywords: Additional product-related keywords to enhance search

        Returns:
            List of SearchResult objects
        """
        if not self.enabled:
            self.logger.warning("Web search is disabled due to missing dependencies.")
            return []

        try:
            # Enhance query with product-specific terms
            enhanced_query = self._enhance_product_query(query, product_keywords)

            # Perform search
            with DDGS() as ddgs:
                results = ddgs.text(
                    keywords=enhanced_query,
                    region=self.region,
                    safesearch=self.safesearch,
                    max_results=self.max_results,
                    timelimit=self.timelimit,
                    backend=self.backend,
                )

                search_results = []
                for result in results:
                    search_result = SearchResult(
                        title=result.get("title", ""),
                        body=result.get("body", ""),
                        href=result.get("href", ""),
                        relevance_score=self._calculate_relevance(result, query),
                    )
                    search_results.append(search_result)

                # Sort by relevance score
                search_results.sort(key=lambda x: x.relevance_score, reverse=True)

                self.logger.info(
                    f"Found {len(search_results)} results for query: {enhanced_query}"
                )
                return search_results

        except RatelimitException as e:
            self.logger.warning(f"Rate limit exceeded for web search: {e}")
            return []
        except TimeoutException as e:
            self.logger.warning(f"Web search timeout: {e}")
            return []
        except DuckDuckGoSearchException as e:
            self.logger.error(f"DuckDuckGo search error: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error during web search: {e}")
            return []

    def _enhance_product_query(
        self, query: str, product_keywords: Optional[List[str]] = None
    ) -> str:
        """
        Enhance search query with product-specific terms.

        Args:
            query: Original search query
            product_keywords: Additional keywords to add

        Returns:
            Enhanced search query
        """
        # Base product-related terms in Vietnamese
        # base_terms = ["sản phẩm", "giá", "thông số", "đánh giá", "review"]

        # Electronics-specific terms
        electronics_terms = ["điện tử", "công nghệ", "smartphone", "laptop", "máy tính"]

        enhanced_query = query

        # Add product keywords if provided
        if product_keywords:
            for keyword in product_keywords:
                if keyword.lower() not in enhanced_query.lower():
                    enhanced_query += f" {keyword}"

        # Add electronics context if not present
        if not any(term in enhanced_query.lower() for term in electronics_terms):
            enhanced_query += " điện tử"

        return enhanced_query

    def _calculate_relevance(self, result: Dict[str, Any], query: str) -> float:
        """
        Calculate relevance score for a search result.

        Args:
            result: Search result dictionary
            query: Original search query

        Returns:
            Relevance score between 0 and 1
        """
        title = result.get("title", "").lower()
        body = result.get("body", "").lower()
        query_lower = query.lower()

        score = 0.0
        query_terms = query_lower.split()

        # Score based on query terms in title (higher weight)
        title_matches = sum(1 for term in query_terms if term in title)
        score += (title_matches / len(query_terms)) * 0.6

        # Score based on query terms in body
        body_matches = sum(1 for term in query_terms if term in body)
        score += (body_matches / len(query_terms)) * 0.4

        # Bonus for product-related terms
        product_terms = [
            "sản phẩm",
            "giá",
            "thông số",
            "đánh giá",
            "review",
            "mua",
            "bán",
        ]
        product_matches = sum(
            1 for term in product_terms if term in title or term in body
        )
        score += min(product_matches * 0.1, 0.2)  # Max 0.2 bonus

        return min(score, 1.0)  # Cap at 1.0

    def format_search_results(self, results: List[SearchResult]) -> str:
        """
        Format search results for context in LLM prompt.

        Args:
            results: List of SearchResult objects

        Returns:
            Formatted string of search results
        """
        if not results:
            return "Không tìm thấy thông tin từ tìm kiếm web."

        formatted_results = []
        for i, result in enumerate(results, 1):
            formatted_result = f"""
Thông tin {i}:
{result.title}
{result.body}
"""
            formatted_results.append(formatted_result.strip())

        return "\n\n".join(formatted_results)

    def is_available(self) -> bool:
        """Check if web search functionality is available."""
        return self.enabled


class HybridSearcher:
    """Hybrid searcher that combines vector store and web search results."""

    def __init__(self, web_searcher: WebSearcher, similarity_threshold: float = None):
        """
        Initialize HybridSearcher.

        Args:
            web_searcher: WebSearcher instance
            similarity_threshold: Minimum similarity score to consider vector results sufficient
        """
        self.web_searcher = web_searcher
        self.similarity_threshold = (
            similarity_threshold or config.web_search_similarity_threshold
        )
        self.logger = logger

    def should_use_web_search(self, vector_results: List[Any], query: str) -> bool:
        """
        Determine if web search should be used based on vector search results.

        Args:
            vector_results: Results from vector store search
            query: Original search query

        Returns:
            True if web search should be used
        """
        # Always use web search if no vector results found
        if not vector_results:
            self.logger.info("No vector results found, will use web search")
            return True

        # Always use web search if we have insufficient results
        if len(vector_results) < 3:
            self.logger.info(
                f"Only {len(vector_results)} vector results found, will use web search for better coverage"
            )
            return True

        # Check if query is related to electronics/tech field
        electronics_keywords = [
            "điện tử",
            "công nghệ",
            "smartphone",
            "laptop",
            "máy tính",
            "điện thoại",
            "tablet",
            "smartwatch",
            "tai nghe",
            "loa",
            "camera",
            "tivi",
            "smart tv",
            "gaming",
            "console",
            "pc",
            "macbook",
            "iphone",
            "samsung",
            "xiaomi",
            "oppo",
            "vivo",
            "realme",
            "asus",
            "acer",
            "dell",
            "hp",
            "lenovo",
        ]

        is_electronics_related = any(
            keyword in query.lower() for keyword in electronics_keywords
        )

        # If query is electronics-related but vector results seem insufficient, use web search
        if is_electronics_related:
            # Check if vector results have enough content (simple heuristic)
            total_content_length = sum(len(doc.page_content) for doc in vector_results)
            if total_content_length < 500:  # Less than 500 characters total
                self.logger.info(
                    "Vector results seem insufficient for electronics query, will use web search"
                )
                return True

        # Always use web search for time-sensitive queries
        time_sensitive_keywords = [
            "giá",
            "khuyến mãi",
            "sale",
            "discount",
            "mới",
            "2024",
            "2025",
            "hiện tại",
            "bây giờ",
        ]
        if any(keyword in query.lower() for keyword in time_sensitive_keywords):
            self.logger.info(
                "Query contains time-sensitive keywords, will use web search"
            )
            return True

        # Use web search for comparison queries
        comparison_keywords = [
            "so sánh",
            "compare",
            "vs",
            "tốt hơn",
            "khác nhau",
            "nên chọn",
        ]
        if any(keyword in query.lower() for keyword in comparison_keywords):
            self.logger.info(
                "Query is asking for comparison, will use web search for comprehensive info"
            )
            return True

        return False

    def combine_results(
        self, vector_context: str, web_results: List[SearchResult]
    ) -> str:
        """
        Combine vector store and web search results into a single context.

        Args:
            vector_context: Formatted context from vector store
            web_results: Web search results

        Returns:
            Combined context string
        """
        combined_context = []

        if vector_context and vector_context.strip():
            combined_context.append(vector_context)

        if web_results:
            if combined_context:  # Add separator only if we have vector context
                combined_context.append("")
            combined_context.append(
                self.web_searcher.format_search_results(web_results)
            )

        return "\n\n".join(combined_context)
