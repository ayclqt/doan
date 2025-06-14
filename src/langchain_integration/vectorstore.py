"""
Vector database integration with Qdrant.
"""

import json
from typing import Any, Dict, List

from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from ..config import config, logger

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class VectorStore:
    """Manages vector database operations with Qdrant."""

    def __init__(
        self,
        collection_name: str = config.qdrant_collection_name,
        url: str = config.qdrant_url,
        port: int = config.qdrant_port,
        embedding_model: str = config.embedding_model_name,
    ):
        """Initialize the vector database connection with gRPC."""
        self.collection_name = collection_name
        self.embedding_model = HuggingFaceEmbeddings(model_name=embedding_model)
        self.url = url
        self.port = port

        # Create Qdrant client with gRPC
        self.client = self._create_qdrant_client()
        # self.client = QdrantClient(":memory:")

        # Initialize Langchain's Qdrant wrapper
        self.vectorstore = None

    def _create_qdrant_client(self) -> QdrantClient:
        """Create Qdrant client with gRPC connection only."""
        try:
            # Create gRPC client with optimized settings
            client = QdrantClient(
                url=self.url,
                port=self.port,
                grpc_port=self.port,
                prefer_grpc=True,
                timeout=10.0,
            )

            # Test the connection
            client.get_collections()
            logger.info("Connected to Qdrant via gRPC", url=self.url, port=self.port)
            return client

        except Exception as error:
            logger.error(
                "gRPC connection failed",
                url=self.url,
                port=self.port,
                error=str(error),
            )
            raise ConnectionError(f"Unable to connect to Qdrant via gRPC: {error}")

    def get_connection_info(self) -> Dict[str, Any]:
        """Get current connection information."""
        try:
            collections = self.client.get_collections()
            is_connected = True
        except Exception:
            is_connected = False

        return {
            "connected": is_connected,
            "url": self.url,
            "port": self.port,
            "protocol": "gRPC",
            "collection_name": self.collection_name,
            "collections_count": len(collections.collections) if is_connected else 0,
        }

    def create_collection(self, vector_size: int = 1024) -> None:
        """Create a new collection if it doesn't exist."""
        collections = self.client.get_collections().collections
        collection_names = [collection.name for collection in collections]

        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=vector_size,  # Embedding dimension (384 for 'all-MiniLM-L6-v2')
                    distance=Distance.COSINE,
                ),
            )
            logger.info(
                "Collection created successfully.", collection=self.collection_name
            )
        else:
            logger.warning(
                "Collection already exists.", collection=self.collection_name
            )

    def initialize_vectorstore(self) -> QdrantVectorStore:
        """Initialize the vector store for LangChain operations."""
        self.vectorstore = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            embedding=self.embedding_model,
        )
        return self.vectorstore

    def get_vectorstore(self) -> QdrantVectorStore:
        """Get the initialized vector store."""
        if not self.vectorstore:
            return self.initialize_vectorstore()
        return self.vectorstore

    @staticmethod
    def load_data_from_json(
        json_path: str = config.cleaned_data_path,
    ) -> List[Dict[str, Any]]:
        """Load data from JSON file."""
        with open(json_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data

    @staticmethod
    def prepare_documents(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert raw data to document format for embedding and storage."""
        documents = []

        for i, product in enumerate(data):
            # Extract product name
            product_name = product.get("Tên", f"Product {i}")

            # Convert product details to a formatted text string
            product_text = "\n".join(
                [f"{key}: {value}" for key, value in product.items()]
            )

            # Create document with metadata
            document = {
                "product_id": i,
                "product_name": product_name,
                "text": product_text,
                "metadata": product,
            }
            documents.append(document)

        return documents

    def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Index documents into the vector database."""
        if not self.vectorstore:
            self.initialize_vectorstore()

        # Extract text and metadata
        texts = [doc["text"] for doc in documents]
        metadatas = [
            {
                "product_id": doc["product_id"],
                "product_name": doc["product_name"],
                **doc["metadata"],
            }
            for doc in documents
        ]

        # Add texts to the vector store
        self.vectorstore.add_texts(texts=texts, metadatas=metadatas)
        logger.info(f"Indexed {len(documents)} documents into Qdrant.")

    def similarity_search(self, query: str, k: int = 3) -> List[Dict]:
        """Perform similarity search on the vector database."""
        if not self.vectorstore:
            self.initialize_vectorstore()

        results = self.vectorstore.similarity_search_with_score(query, k=k)
        formatted_results = []

        for doc, score in results:
            formatted_results.append(
                {
                    "metadata": doc.metadata,
                    "content": doc.page_content,
                    "similarity_score": score,
                }
            )

        return formatted_results
