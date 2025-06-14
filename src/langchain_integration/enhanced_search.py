"""
Enhanced Search Strategy with Aggressive Deduplication and Diversity Enforcement
"""

from typing import List, Any
import re
from .vectorstore import VectorStore
from .product_deduplication import deduplicate_search_results

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class EnhancedProductSearch:
    """
    Enhanced product search with multiple strategies to ensure diversity.
    """

    def __init__(self):
        self.vector_store = VectorStore()
        self.vector_store.initialize_vectorstore()

    def search_diverse_products(self, query: str, top_k: int = 3) -> List[Any]:
        """
        Search for diverse products using multiple strategies.

        Args:
            query: Search query
            top_k: Number of diverse products to return

        Returns:
            List of diverse products
        """
        all_results = []

        # Strategy 1: Original query
        results1 = self._search_with_query(query, limit=top_k * 5)
        all_results.extend(results1)

        # Strategy 2: Brand-specific searches if not enough diversity
        if len(self._get_unique_brands(all_results)) < 2:
            brand_queries = self._generate_brand_queries(query)
            for brand_query in brand_queries:
                brand_results = self._search_with_query(brand_query, limit=5)
                all_results.extend(brand_results)

        # Strategy 3: Price-range specific searches
        price_queries = self._generate_price_queries(query)
        for price_query in price_queries:
            price_results = self._search_with_query(price_query, limit=3)
            all_results.extend(price_results)

        # Apply aggressive deduplication
        unique_results = deduplicate_search_results(all_results, diversify=True)

        # Ensure we have enough diverse results
        if len(unique_results) < top_k:
            # Fallback: search with very broad terms
            fallback_results = self._fallback_search(query, top_k * 3)
            all_results.extend(fallback_results)
            unique_results = deduplicate_search_results(all_results, diversify=True)

        return unique_results[:top_k]

    def _search_with_query(self, query: str, limit: int = 10) -> List[Any]:
        """Execute a single search query."""
        try:
            query_vector = self.vector_store.get_vectorstore().embeddings.embed_query(
                query
            )

            results = self.vector_store.client.search(
                collection_name=self.vector_store.collection_name,
                query_vector=query_vector,
                limit=limit,
                with_payload=True,
                score_threshold=0.3,  # Lower threshold for diversity
            )

            return results
        except Exception:
            return []

    def _generate_brand_queries(self, original_query: str) -> List[str]:
        """Generate brand-specific queries for diversity."""
        brands = ["samsung", "xiaomi", "oppo", "vivo", "iphone", "oneplus"]
        queries = []

        # Extract price information from original query
        price_info = self._extract_price_info(original_query)

        for brand in brands:
            if price_info:
                brand_query = f"{brand} {price_info}"
            else:
                brand_query = f"{brand} điện thoại"
            queries.append(brand_query)

        return queries[:3]  # Limit to 3 brand queries

    def _generate_price_queries(self, original_query: str) -> List[str]:
        """Generate price-range specific queries."""
        price_ranges = [
            "điện thoại dưới 5 triệu",
            "smartphone giá rẻ",
            "điện thoại tầm trung",
        ]

        # Only return price queries if original query mentions price
        if any(
            price_word in original_query.lower()
            for price_word in ["giá", "triệu", "price", "cost"]
        ):
            return price_ranges[:2]

        return []

    def _fallback_search(self, query: str, limit: int = 10) -> List[Any]:
        """Fallback search with very broad terms."""
        fallback_queries = [
            "điện thoại",
            "smartphone",
            "mobile phone",
            "điện thoại android",
            "điện thoại giá rẻ",
        ]

        results = []
        for fb_query in fallback_queries:
            fb_results = self._search_with_query(fb_query, limit=3)
            results.extend(fb_results)

        return results

    def _extract_price_info(self, query: str) -> str:
        """Extract price information from query."""
        price_patterns = [
            r"(\d+)\s*triệu",
            r"tầm\s*(\d+)",
            r"dưới\s*(\d+)",
            r"khoảng\s*(\d+)",
        ]

        for pattern in price_patterns:
            match = re.search(pattern, query.lower())
            if match:
                price = match.group(1)
                return f"tầm giá {price} triệu"

        return ""

    def _get_unique_brands(self, results: List[Any]) -> List[str]:
        """Get list of unique brands from results."""
        brands = set()

        for result in results:
            if hasattr(result, "payload") and result.payload:
                name = result.payload.get("name", "").lower()

                brand_keywords = [
                    "samsung",
                    "xiaomi",
                    "realme",
                    "oppo",
                    "vivo",
                    "iphone",
                    "oneplus",
                    "huawei",
                ]
                for brand in brand_keywords:
                    if brand in name:
                        brands.add(brand)
                        break

        return list(brands)


# Global instance
_enhanced_search = EnhancedProductSearch()


def search_diverse_products(query: str, top_k: int = 3) -> List[Any]:
    """
    Convenience function for diverse product search.

    Args:
        query: Search query
        top_k: Number of diverse products to return

    Returns:
        List of diverse products
    """
    return _enhanced_search.search_diverse_products(query, top_k)
