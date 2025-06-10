"""
Data ingestion script for loading product data into the vector database.
"""

import argparse
import os

from src import TextProcessor, VectorStore

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


def main():
    """Run data ingestion process."""
    parser = argparse.ArgumentParser(
        description="Ingest product data into vector database"
    )
    parser.add_argument(
        "--data-path",
        type=str,
        default="cleaned_data.json",
        help="Path to the JSON data file",
    )
    parser.add_argument(
        "--recreate", action="store_true", help="Recreate the vector store collection"
    )

    args = parser.parse_args()

    # Check if data file exists
    if not os.path.exists(args.data_path):
        print(f"Error: Data file {args.data_path} not found.")
        return

    # Initialize components
    text_processor = TextProcessor()
    vector_store = VectorStore()

    # Create collection if needed
    vector_store.create_collection()

    # Load and process data
    print(f"Loading data from {args.data_path}")
    raw_data = text_processor.load_data(args.data_path)

    if not raw_data:
        print("No data found or error loading data.")
        return

    print(f"Processing {len(raw_data)} products...")
    processed_chunks = text_processor.process_all_products(raw_data)

    # Convert to documents for indexing
    print("Preparing documents for indexing...")
    documents = vector_store.prepare_documents(processed_chunks)

    # Index documents
    print("Indexing documents in vector database...")
    vector_store.index_documents(documents)

    print("Data ingestion completed successfully.")


if __name__ == "__main__":
    main()
