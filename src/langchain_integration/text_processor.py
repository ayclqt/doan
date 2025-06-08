"""
Text processing utilities for preparing data for vector embedding.
"""

from typing import Dict, List, Any
import json

from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import config, logger


__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class TextProcessor:
    """Process text data for embedding."""

    def __init__(
        self,
        chunk_size: int = config.chunk_size,
        chunk_overlap: int = config.chunk_overlap,
    ):
        """Initialize text processor with chunking parameters."""
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

    def load_data(
        self, file_path: str = config.cleaned_data_path
    ) -> List[Dict[str, Any]]:
        """Load product data from JSON file."""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
                logger.info(f"Loaded {len(data)} products from {file_path}")
                return data
        except Exception as e:
            logger.error("Error loading data", error=e)
            return []

    def product_to_text(self, product: Dict[str, Any]) -> str:
        """Convert a product dictionary to formatted text."""
        product_name = product.get("Tên", "Unknown Product")
        product_text = [f"Tên sản phẩm: {product_name}"]

        # Add all other properties
        for key, value in product.items():
            if key != "Tên":  # Skip name as we already included it
                product_text.append(f"{key}: {value}")

        return "\n".join(product_text)

    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks for embedding."""
        chunks = self.text_splitter.split_text(text)
        return chunks

    def chunk_product(self, product: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process a single product into chunks with metadata."""
        product_text = self.product_to_text(product)

        # For products, we might want smaller chunks if there's a lot of info
        chunks = self.chunk_text(product_text)
        product_chunks = []

        for i, chunk in enumerate(chunks):
            # Create a chunk document with metadata
            product_chunks.append(
                {
                    "text": chunk,
                    "metadata": {
                        "product_id": product.get("id", i),
                        "product_name": product.get("Tên", "Unknown"),
                        "chunk_id": i,
                        "total_chunks": len(chunks),
                        **product,  # Include all product data in metadata
                    },
                }
            )

        return product_chunks

    def process_all_products(
        self, products: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Process all products into chunks ready for embedding."""
        all_chunks = []

        for i, product in enumerate(products):
            # Add an ID if not present
            if "id" not in product:
                product["id"] = i

            product_chunks = self.chunk_product(product)
            all_chunks.extend(product_chunks)

        logger.info(f"Created {len(all_chunks)} chunks from {len(products)} products")
        return all_chunks
