"""
Functional vector store service using Qdrant with immutable operations.
"""

from typing import Any, Dict, List, Tuple
from functools import partial

from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from ..core.types import Result, safe_call, pipe, memoize
from ..domain.models import (
    TextChunk,
    VectorSearchResult,
    VectorStoreConfig,
    EmbeddingConfig,
)

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


# Pure functions for vector operations


def create_qdrant_client(config: VectorStoreConfig) -> Result:
    """Create Qdrant client safely."""

    @safe_call
    def _create():
        return QdrantClient(url=config.url, port=config.port)

    return _create()


def create_embedding_model(model_name: str) -> Result:
    """Create embedding model safely."""

    @safe_call
    def _create():
        return HuggingFaceEmbeddings(model_name=model_name)

    return _create()


def get_collection_names(client: QdrantClient) -> Result:
    """Get existing collection names safely."""

    @safe_call
    def _get():
        collections = client.get_collections().collections
        return [collection.name for collection in collections]

    return _get()


def collection_exists(client: QdrantClient, collection_name: str) -> bool:
    """Check if collection exists."""
    result = get_collection_names(client)
    if result.is_failure:
        return False
    return collection_name in result.value


def create_vector_params(config: VectorStoreConfig) -> VectorParams:
    """Create vector parameters configuration."""
    distance_map = {
        "cosine": Distance.COSINE,
        "euclidean": Distance.EUCLID,
        "dot": Distance.DOT,
    }

    distance = distance_map.get(config.distance_metric.lower(), Distance.COSINE)

    return VectorParams(size=config.vector_size, distance=distance)


def create_collection_if_not_exists(
    client: QdrantClient, config: VectorStoreConfig
) -> Result:
    """Create collection if it doesn't exist."""

    @safe_call
    def _create():
        if not collection_exists(client, config.collection_name):
            vector_params = create_vector_params(config)
            client.create_collection(
                collection_name=config.collection_name, vectors_config=vector_params
            )
            return f"Collection '{config.collection_name}' created successfully"
        else:
            return f"Collection '{config.collection_name}' already exists"

    return _create()


def create_langchain_vectorstore(
    client: QdrantClient, embedding_model: HuggingFaceEmbeddings, collection_name: str
) -> Result:
    """Create LangChain QdrantVectorStore safely."""

    @safe_call
    def _create():
        return QdrantVectorStore(
            client=client, collection_name=collection_name, embedding=embedding_model
        )

    return _create()


# Document preparation functions


def chunk_to_document_data(chunk: TextChunk) -> Tuple[str, Dict[str, Any]]:
    """Convert TextChunk to document data (text, metadata)."""
    metadata = {
        "product_id": chunk.product_id,
        "product_name": chunk.product_name,
        "chunk_id": chunk.chunk_id,
        "total_chunks": chunk.total_chunks,
        **chunk.metadata,
    }

    return chunk.text, metadata


def chunks_to_document_data(
    chunks: List[TextChunk],
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Convert list of TextChunks to document data."""
    texts, metadatas = zip(*[chunk_to_document_data(chunk) for chunk in chunks])
    return list(texts), list(metadatas)


def index_documents_to_vectorstore(
    vectorstore: QdrantVectorStore, texts: List[str], metadatas: List[Dict[str, Any]]
) -> Result:
    """Index documents to vector store safely."""

    @safe_call
    def _index():
        vectorstore.add_texts(texts=texts, metadatas=metadatas)
        return len(texts)

    return _index()


# Search functions


def perform_similarity_search(
    vectorstore: QdrantVectorStore, query: str, k: int = 3
) -> Result:
    """Perform similarity search safely."""

    @safe_call
    def _search():
        return vectorstore.similarity_search_with_score(query, k=k)

    return _search()


def langchain_results_to_vector_results(
    langchain_results: List[Tuple[Any, float]],
) -> List[VectorSearchResult]:
    """Convert LangChain results to VectorSearchResult objects."""
    return [
        VectorSearchResult.from_langchain_doc(doc, score)
        for doc, score in langchain_results
    ]


def filter_results_by_score(
    results: List[VectorSearchResult], min_score: float = 0.0
) -> List[VectorSearchResult]:
    """Filter results by minimum similarity score."""
    return [result for result in results if result.similarity_score >= min_score]


def sort_results_by_score(
    results: List[VectorSearchResult],
) -> List[VectorSearchResult]:
    """Sort results by similarity score (descending)."""
    return sorted(results, key=lambda x: x.similarity_score, reverse=True)


# High-level vector store operations


def initialize_vector_store(
    vector_config: VectorStoreConfig, embedding_config: EmbeddingConfig
) -> Result:
    """Initialize complete vector store setup."""

    def _initialize():
        # Create client
        client_result = create_qdrant_client(vector_config)
        if client_result.is_failure:
            return client_result

        client = client_result.value

        # Create collection
        collection_result = create_collection_if_not_exists(client, vector_config)
        if collection_result.is_failure:
            return collection_result

        # Create embedding model
        embedding_result = create_embedding_model(embedding_config.model_name)
        if embedding_result.is_failure:
            return embedding_result

        embedding_model = embedding_result.value

        # Create vectorstore
        vectorstore_result = create_langchain_vectorstore(
            client, embedding_model, vector_config.collection_name
        )
        if vectorstore_result.is_failure:
            return vectorstore_result

        return Result.success(
            {
                "client": client,
                "embedding_model": embedding_model,
                "vectorstore": vectorstore_result.value,
                "collection_status": collection_result.value,
            }
        )

    return _initialize()


def index_chunks_to_vector_store(
    chunks: List[TextChunk], vectorstore: QdrantVectorStore
) -> Result:
    """Index text chunks to vector store."""
    if not chunks:
        return Result.failure(ValueError("No chunks to index"))

    texts, metadatas = chunks_to_document_data(chunks)
    return index_documents_to_vectorstore(vectorstore, texts, metadatas)


def search_vector_store(
    vectorstore: QdrantVectorStore, query: str, k: int = 3, min_score: float = 0.0
) -> Result:
    """Perform complete vector store search with filtering and sorting."""
    search_result = perform_similarity_search(vectorstore, query, k)

    if search_result.is_failure:
        return search_result

    # Convert and process results
    vector_results = pipe(
        search_result.value,
        langchain_results_to_vector_results,
        partial(filter_results_by_score, min_score=min_score),
        sort_results_by_score,
    )

    return Result.success(vector_results)


# Context creation functions


def create_vector_context_from_results(results: List[VectorSearchResult]) -> str:
    """Create context string from vector search results."""
    if not results:
        return ""

    formatted_results = []
    for i, result in enumerate(results):
        formatted_result = f"Sản phẩm {i + 1}:\n{result.content}"
        formatted_results.append(formatted_result)

    return "\n\n".join(formatted_results)


def create_detailed_vector_context(
    results: List[VectorSearchResult], include_scores: bool = False
) -> str:
    """Create detailed context with optional similarity scores."""
    if not results:
        return "Không tìm thấy thông tin trong cơ sở dữ liệu sản phẩm."

    formatted_results = []
    for i, result in enumerate(results, 1):
        header = f"Sản phẩm {i}"
        if include_scores:
            header += f" (độ tương đồng: {result.similarity_score:.3f})"

        formatted_result = f"{header}:\n{result.content}"
        formatted_results.append(formatted_result)

    return "\n\n".join(formatted_results)


# Validation functions


def validate_vector_store_config(config: VectorStoreConfig) -> Result:
    """Validate vector store configuration."""
    if not config.collection_name or not config.collection_name.strip():
        return Result.failure(ValueError("Collection name cannot be empty"))

    if config.port <= 0 or config.port > 65535:
        return Result.failure(ValueError("Port must be between 1 and 65535"))

    if config.vector_size <= 0:
        return Result.failure(ValueError("Vector size must be positive"))

    valid_distances = ["cosine", "euclidean", "dot"]
    if config.distance_metric.lower() not in valid_distances:
        return Result.failure(
            ValueError(f"Distance metric must be one of: {valid_distances}")
        )

    return Result.success(config)


def validate_search_parameters(query: str, k: int, min_score: float) -> Result:
    """Validate search parameters."""
    if not query or not query.strip():
        return Result.failure(ValueError("Query cannot be empty"))

    if k <= 0:
        return Result.failure(ValueError("k must be positive"))

    if k > 100:
        return Result.failure(ValueError("k should not exceed 100"))

    if not (0.0 <= min_score <= 1.0):
        return Result.failure(ValueError("min_score must be between 0 and 1"))

    return Result.success((query.strip(), k, min_score))


# Factory functions


def create_vector_store_config(
    collection_name: str,
    url: str = "localhost",
    port: int = 6333,
    vector_size: int = 1024,
    distance_metric: str = "cosine",
) -> Result:
    """Create and validate vector store configuration."""
    config = VectorStoreConfig(
        collection_name=collection_name,
        url=url,
        port=port,
        vector_size=vector_size,
        distance_metric=distance_metric,
    )

    return validate_vector_store_config(config)


def create_search_function(
    vectorstore: QdrantVectorStore, default_k: int = 3, default_min_score: float = 0.0
):
    """Create a partially applied search function."""
    return partial(
        search_vector_store, vectorstore, k=default_k, min_score=default_min_score
    )


# Monitoring and metrics


def calculate_vector_store_metrics(results: List[VectorSearchResult]) -> Dict[str, Any]:
    """Calculate metrics for vector store search results."""
    if not results:
        return {
            "total_results": 0,
            "average_score": 0.0,
            "high_score_count": 0,
            "score_distribution": {},
        }

    total_results = len(results)
    average_score = sum(r.similarity_score for r in results) / total_results
    high_score_count = sum(1 for r in results if r.similarity_score > 0.8)

    # Score distribution
    score_ranges = {
        "excellent": sum(1 for r in results if r.similarity_score > 0.9),
        "good": sum(1 for r in results if 0.7 < r.similarity_score <= 0.9),
        "fair": sum(1 for r in results if 0.5 < r.similarity_score <= 0.7),
        "poor": sum(1 for r in results if r.similarity_score <= 0.5),
    }

    return {
        "total_results": total_results,
        "average_score": average_score,
        "high_score_count": high_score_count,
        "score_distribution": score_ranges,
    }


def get_vector_store_status(client: QdrantClient, collection_name: str) -> Result:
    """Get vector store status information."""

    @safe_call
    def _get_status():
        collection_info = client.get_collection(collection_name)

        return {
            "collection_name": collection_name,
            "vectors_count": collection_info.vectors_count,
            "indexed_vectors_count": collection_info.indexed_vectors_count,
            "points_count": collection_info.points_count,
            "config": {
                "distance": collection_info.config.params.vectors.distance.value,
                "size": collection_info.config.params.vectors.size,
            },
        }

    return _get_status()


# Utility functions


@memoize
def get_embedding_dimension(model_name: str) -> int:
    """Get embedding dimension for a model (memoized for performance)."""
    # Common embedding dimensions
    dimension_map = {
        "AITeamVN/Vietnamese_Embedding": 1024,
        "sentence-transformers/all-MiniLM-L6-v2": 384,
        "sentence-transformers/all-mpnet-base-v2": 768,
        "intfloat/e5-base": 768,
        "intfloat/e5-large": 1024,
    }

    return dimension_map.get(model_name, 768)  # Default to 768


def estimate_storage_size(
    num_documents: int, vector_size: int, avg_metadata_size: int = 500
) -> Dict[str, float]:
    """Estimate storage requirements."""
    # Each vector: vector_size * 4 bytes (float32) + metadata
    vector_storage_mb = (num_documents * vector_size * 4) / (1024 * 1024)
    metadata_storage_mb = (num_documents * avg_metadata_size) / (1024 * 1024)
    total_storage_mb = vector_storage_mb + metadata_storage_mb

    return {
        "vector_storage_mb": vector_storage_mb,
        "metadata_storage_mb": metadata_storage_mb,
        "total_storage_mb": total_storage_mb,
        "estimated_total_gb": total_storage_mb / 1024,
    }
