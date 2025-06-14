"""
Intelligent Product Deduplication System
Removes duplicate products from search results to ensure diverse recommendations.
"""

import re
from typing import List, Dict, Any
from difflib import SequenceMatcher

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class ProductDeduplicator:
    """
    Smart product deduplication based on product names, specs, and similarity analysis.
    """

    def __init__(self, similarity_threshold: float = 0.8):
        """
        Initialize the deduplicator.

        Args:
            similarity_threshold: Threshold for considering products as duplicates (0.0-1.0)
        """
        self.similarity_threshold = similarity_threshold

        # Common brand patterns for normalization
        self.brand_patterns = {
            "realme": ["realme", "real me"],
            "samsung": ["samsung", "galaxy"],
            "xiaomi": ["xiaomi", "redmi", "poco", "mi "],
            "oppo": ["oppo"],
            "vivo": ["vivo", "iqoo"],
            "iphone": ["iphone", "apple"],
            "oneplus": ["oneplus", "one plus"],
            "huawei": ["huawei", "honor"],
            "nokia": ["nokia"],
            "sony": ["sony"],
            "lg": ["lg"],
            "motorola": ["motorola", "moto"],
        }

    def extract_product_signature(self, product_data: Dict[str, Any]) -> str:
        """
        Extract a unique signature for a product based on name and key specs.

        Args:
            product_data: Product data with 'name' and 'content' fields

        Returns:
            Normalized product signature for deduplication
        """
        name = product_data.get("name", "").lower().strip()
        content = product_data.get("page_content", "")

        # Normalize brand name
        normalized_name = self._normalize_brand_name(name)

        # Extract model information
        model = self._extract_model(normalized_name)

        # Extract key specs for signature
        ram = self._extract_spec(content, ["ram:", "ram", "bộ nhớ trong:"])
        storage = self._extract_spec(
            content, ["dung lượng lưu trữ:", "storage", "gb", "tb"]
        )

        # Create signature: brand_model_ram_storage
        signature_parts = []

        if model:
            signature_parts.append(model)

        if ram:
            # Normalize RAM (e.g., "6GB" -> "6gb")
            ram_normalized = re.sub(r"[^\d]", "", ram) + "gb"
            signature_parts.append(ram_normalized)

        if storage:
            # Normalize storage (e.g., "128GB" -> "128gb")
            storage_normalized = re.sub(r"[^\d]", "", storage) + "gb"
            signature_parts.append(storage_normalized)

        signature = "_".join(signature_parts)
        return signature if signature else normalized_name

    def _normalize_brand_name(self, name: str) -> str:
        """Normalize brand names to standard format."""
        name_lower = name.lower()

        for standard_brand, variants in self.brand_patterns.items():
            for variant in variants:
                if variant in name_lower:
                    # Replace variant with standard brand name
                    name_lower = name_lower.replace(variant, standard_brand)
                    break

        return name_lower.strip()

    def _extract_model(self, normalized_name: str) -> str:
        """Extract model information from product name."""
        # Remove common words
        excluded_words = ["điện thoại", "smartphone", "phone", "mobile"]

        name_parts = normalized_name.split()
        model_parts = []

        for part in name_parts:
            if part not in excluded_words and len(part) > 1:
                model_parts.append(part)

        return "_".join(model_parts[:3])  # Take first 3 significant parts

    def _extract_spec(self, content: str, spec_keywords: List[str]) -> str:
        """Extract specification value from content."""
        content_lower = content.lower()

        for keyword in spec_keywords:
            pattern = rf"{keyword}\s*:?\s*([0-9]+(?:\s*gb|tb)?)"
            match = re.search(pattern, content_lower)
            if match:
                return match.group(1).strip()

        return ""

    def calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two product names."""
        return SequenceMatcher(None, name1.lower(), name2.lower()).ratio()

    def deduplicate_products(self, search_results: List[Any]) -> List[Any]:
        """
        Remove duplicate products from search results.

        Args:
            search_results: List of search results (Qdrant points or similar)

        Returns:
            Deduplicated list of unique products
        """
        if not search_results:
            return search_results

        unique_products = []
        seen_signatures = set()
        processed_names = []

        for result in search_results:
            # Extract product data
            if hasattr(result, "payload") and result.payload:
                payload = result.payload
                product_data = {
                    "name": payload.get("name", ""),
                    "page_content": payload.get("page_content", ""),
                }
            else:
                # Handle other formats (Document objects, etc.)
                product_data = {
                    "name": getattr(result, "name", ""),
                    "page_content": getattr(result, "page_content", str(result)),
                }

            product_name = product_data["name"]

            # Skip if no name
            if not product_name:
                continue

            # Generate signature
            signature = self.extract_product_signature(product_data)

            # Check for exact signature match
            if signature in seen_signatures:
                continue

            # Check for name similarity with already processed products
            is_duplicate = False
            for processed_name in processed_names:
                similarity = self.calculate_similarity(product_name, processed_name)
                if similarity >= self.similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_products.append(result)
                seen_signatures.add(signature)
                processed_names.append(product_name)

        return unique_products

    def diversify_results(
        self, search_results: List[Any], max_per_brand: int = 1
    ) -> List[Any]:
        """
        Ensure diversity by limiting products per brand.

        Args:
            search_results: List of deduplicated results
            max_per_brand: Maximum products per brand

        Returns:
            Diversified product list
        """
        brand_counts = {}
        diversified_results = []

        for result in search_results:
            # Extract product name
            if hasattr(result, "payload") and result.payload:
                product_name = result.payload.get("name", "")
            else:
                product_name = getattr(result, "name", str(result))

            if not product_name:
                continue

            # Determine brand
            brand = self._determine_brand(product_name.lower())

            # Check brand limit
            if brand_counts.get(brand, 0) < max_per_brand:
                diversified_results.append(result)
                brand_counts[brand] = brand_counts.get(brand, 0) + 1

        return diversified_results

    def _determine_brand(self, product_name: str) -> str:
        """Determine product brand from name."""
        name_lower = product_name.lower()

        for brand, variants in self.brand_patterns.items():
            for variant in variants:
                if variant in name_lower:
                    return brand

        # Extract first word as brand if no match
        first_word = name_lower.split()[0] if name_lower.split() else "unknown"
        return first_word

    def get_deduplication_stats(
        self, original_count: int, final_count: int
    ) -> Dict[str, Any]:
        """Get statistics about deduplication process."""
        return {
            "original_count": original_count,
            "final_count": final_count,
            "duplicates_removed": original_count - final_count,
            "deduplication_ratio": (original_count - final_count) / original_count
            if original_count > 0
            else 0,
            "similarity_threshold": self.similarity_threshold,
        }


# Global deduplicator instance
_deduplicator_instance = ProductDeduplicator()


def get_deduplicator() -> ProductDeduplicator:
    """Get global deduplicator instance."""
    return _deduplicator_instance


def deduplicate_search_results(
    search_results: List[Any], diversify: bool = True
) -> List[Any]:
    """
    Convenience function to deduplicate search results.

    Args:
        search_results: Search results to deduplicate
        diversify: Whether to ensure brand diversity

    Returns:
        Deduplicated and optionally diversified results
    """
    deduplicator = get_deduplicator()

    # First pass: remove duplicates
    unique_results = deduplicator.deduplicate_products(search_results)

    # Second pass: ensure diversity if requested
    if diversify:
        final_results = deduplicator.diversify_results(unique_results, max_per_brand=1)
    else:
        final_results = unique_results

    return final_results
