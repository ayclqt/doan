"""
Domain models using msgspec for high performance serialization/deserialization.
"""

from typing import Any, Dict, List, Optional
from msgspec import Struct, field


__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class Product(Struct, frozen=True):
    """Immutable product model."""

    id: Optional[str] = None
    name: str = field(name="Tên", default="")
    price: Optional[str] = field(name="Giá", default=None)
    brand: Optional[str] = field(name="Thương hiệu", default=None)
    category: Optional[str] = field(name="Danh mục", default=None)
    description: Optional[str] = field(name="Mô tả", default=None)
    specifications: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Product":
        """Create Product from dictionary with Vietnamese keys."""
        # Extract known fields
        product_data = {
            "id": data.get("id"),
            "name": data.get("Tên", ""),
            "price": data.get("Giá"),
            "brand": data.get("Thương hiệu"),
            "category": data.get("Danh mục"),
            "description": data.get("Mô tả"),
        }

        # Everything else goes to specifications
        specifications = {
            k: v
            for k, v in data.items()
            if k not in {"id", "Tên", "Giá", "Thương hiệu", "Danh mục", "Mô tả"}
        }
        product_data["specifications"] = specifications

        return cls(**product_data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with Vietnamese keys."""
        result = {
            "Tên": self.name,
        }
        if self.id:
            result["id"] = self.id
        if self.price:
            result["Giá"] = self.price
        if self.brand:
            result["Thương hiệu"] = self.brand
        if self.category:
            result["Danh mục"] = self.category
        if self.description:
            result["Mô tả"] = self.description

        # Add specifications
        result.update(self.specifications)
        return result

    def to_text(self) -> str:
        """Convert product to formatted text."""
        lines = [f"Tên sản phẩm: {self.name}"]

        if self.price:
            lines.append(f"Giá: {self.price}")
        if self.brand:
            lines.append(f"Thương hiệu: {self.brand}")
        if self.category:
            lines.append(f"Danh mục: {self.category}")
        if self.description:
            lines.append(f"Mô tả: {self.description}")

        # Add specifications
        for key, value in self.specifications.items():
            lines.append(f"{key}: {value}")

        return "\n".join(lines)


class TextChunk(Struct, frozen=True):
    """Immutable text chunk model."""

    text: str
    product_id: Optional[str] = None
    product_name: str = ""
    chunk_id: int = 0
    total_chunks: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_product(
        cls, product: Product, text: str, chunk_id: int = 0, total_chunks: int = 1
    ) -> "TextChunk":
        """Create TextChunk from Product."""
        return cls(
            text=text,
            product_id=product.id,
            product_name=product.name,
            chunk_id=chunk_id,
            total_chunks=total_chunks,
            metadata=product.to_dict(),
        )


class SearchResult(Struct, frozen=True):
    """Immutable search result model."""

    title: str
    body: str
    href: str
    relevance_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "body": self.body,
            "href": self.href,
            "relevance_score": self.relevance_score,
        }


class VectorSearchResult(Struct, frozen=True):
    """Immutable vector search result model."""

    content: str
    metadata: Dict[str, Any]
    similarity_score: float

    @classmethod
    def from_langchain_doc(cls, doc: Any, score: float) -> "VectorSearchResult":
        """Create from LangChain document with score."""
        return cls(
            content=doc.page_content,
            metadata=dict(doc.metadata),
            similarity_score=score,
        )


class QueryContext(Struct, frozen=True):
    """Immutable query context model."""

    query: str
    vector_results: List[VectorSearchResult] = field(default_factory=list)
    web_results: List[SearchResult] = field(default_factory=list)
    combined_context: str = ""

    def has_sufficient_vector_results(self, min_results: int = 2) -> bool:
        """Check if vector results are sufficient."""
        return len(self.vector_results) >= min_results

    def has_time_sensitive_keywords(self) -> bool:
        """Check if query contains time-sensitive keywords."""
        time_sensitive_keywords = [
            "giá",
            "khuyến mãi",
            "sale",
            "discount",
            "mới",
            "2024",
            "2025",
        ]
        return any(keyword in self.query.lower() for keyword in time_sensitive_keywords)


class QAResponse(Struct, frozen=True):
    """Immutable Q&A response model."""

    question: str
    answer: str
    processing_time: float = 0.0
    vector_results_count: int = 0
    web_results_count: int = 0
    sources: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "question": self.question,
            "answer": self.answer,
            "processing_time": self.processing_time,
            "vector_results_count": self.vector_results_count,
            "web_results_count": self.web_results_count,
            "sources": self.sources,
        }


class EmbeddingConfig(Struct, frozen=True):
    """Immutable embedding configuration."""

    model_name: str
    chunk_size: int = 1000
    chunk_overlap: int = 200

    def get_text_splitter_config(self) -> Dict[str, Any]:
        """Get text splitter configuration."""
        return {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "separators": ["\n\n", "\n", " ", ""],
        }


class VectorStoreConfig(Struct, frozen=True):
    """Immutable vector store configuration."""

    collection_name: str
    url: str = "localhost"
    port: int = 6333
    vector_size: int = 1024
    distance_metric: str = "cosine"


class LLMConfig(Struct, frozen=True):
    """Immutable LLM configuration."""

    model_name: str
    temperature: float = 0.0
    max_tokens: int = 1024
    api_key: str = ""
    base_url: str = ""


class WebSearchConfig(Struct, frozen=True):
    """Immutable web search configuration."""

    enabled: bool = True
    max_results: int = 5
    region: str = "vn-vi"
    safesearch: str = "moderate"
    timelimit: Optional[str] = None
    backend: str = "auto"
    similarity_threshold: float = 0.7
