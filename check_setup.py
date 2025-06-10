#!/usr/bin/env python3
"""
Utility script to check and verify LangChain and Qdrant setup.
This script helps diagnose common issues with the implementation.
"""

import argparse
import json
import os

from dotenv import load_dotenv

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


def check_environment():
    """Check if environment variables are set correctly."""
    load_dotenv()

    print("\n=== Checking Environment ===")

    # Check LLM API Key
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if not openai_key:
        print("❌ OPENAI_API_KEY not found in environment or .env file")
    elif openai_key == "your-openai-api-key-here":
        print(
            "❌ OPENAI_API_KEY is set to default value. Please update with your actual API key"
        )
    else:
        masked_key = (
            openai_key[:5] + "..." + openai_key[-5:] if len(openai_key) > 10 else "***"
        )
        print(f"✅ OPENAI_API_KEY found: {masked_key}")

    # Check other configuration
    required_vars = [
        "QDRANT_URL",
        "QDRANT_PORT",
        "QDRANT_COLLECTION_NAME",
        "EMBEDDING_MODEL_NAME",
        "LLM_MODEL_NAME",
        "LLM_TEMPERATURE",
        "LLM_MAX_TOKENS",
        "CHUNK_SIZE",
        "CHUNK_OVERLAP",
    ]

    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var} = {value}")
        else:
            print(f"❌ {var} not found")


def check_dependencies():
    """Check if required packages are installed."""
    print("\n=== Checking Dependencies ===")

    dependencies = [
        "langchain",
        "langchain_openai",
        "langchain_community",
        "langchain_qdrant",
        "langchain_huggingface",
        "qdrant_client",
        "sentence_transformers",
        "python_dotenv",
        "torch",
        "pandas",
        "numpy",
        "pydantic",
        "typer",
        "rich",
        "structlog",
    ]

    for dep in dependencies:
        try:
            __import__(dep.replace("-", "_"))
            print(f"✅ {dep} is installed")
        except ImportError:
            print(f"❌ {dep} is NOT installed. Run: pip install {dep}")


def check_qdrant_connection():
    """Check if Qdrant is running and accessible."""
    print("\n=== Checking Qdrant Connection ===")

    # Only import if the package is installed
    try:
        from qdrant_client import QdrantClient
    except ImportError:
        print("❌ qdrant-client not installed. Skipping Qdrant connection test.")
        return

    load_dotenv()
    url = os.getenv("QDRANT_URL", "localhost")
    port = int(os.getenv("QDRANT_PORT", 6333))
    collection_name = os.getenv("QDRANT_COLLECTION_NAME", "product_data")

    try:
        client = QdrantClient(url=url, port=port)
        status = client.http.healthcheck()
        print(f"✅ Connected to Qdrant at {url}:{port}")
        print(f"   Status: {status}")

        # Check for collection
        try:
            collections = client.get_collections().collections
            collection_names = [c.name for c in collections]

            if collection_name in collection_names:
                collection_info = client.get_collection(collection_name)
                point_count = client.count(collection_name=collection_name).count
                print(
                    f"✅ Collection '{collection_name}' exists with {point_count} vectors"
                )
                print(f"   Vector size: {collection_info.config.params.vectors.size}")
                print(f"   Distance: {collection_info.config.params.vectors.distance}")
            else:
                print(
                    f"❌ Collection '{collection_name}' not found. Available collections: {collection_names}"
                )
                print(
                    "   Run 'python ingest.py' to create the collection and index data"
                )
        except Exception as e:
            print(f"❌ Error checking collections: {e!s}")
    except Exception as e:
        print(f"❌ Failed to connect to Qdrant at {url}:{port}")
        print(f"   Error: {e!s}")
        print("\n   Is Qdrant running? Try: docker-compose up -d")


def check_data():
    """Check if data files exist and are accessible."""
    print("\n=== Checking Data Files ===")

    load_dotenv()
    data_path = os.getenv("CLEANED_DATA_PATH", "cleaned_data.json")

    if os.path.exists(data_path):
        try:
            with open(data_path, "r", encoding="utf-8") as file:
                data = json.load(file)
                print(f"✅ Data file found: {data_path}")
                print(f"   Contains {len(data)} products")

                # Sample a random product
                if data:
                    import random

                    sample = random.choice(data)
                    print(f"\n   Sample product: {sample.get('Tên', 'Unknown')}")
                    print(f"   Fields: {', '.join(list(sample.keys())[:5])}...")
        except Exception as e:
            print(f"❌ Error reading data file: {e!s}")
    else:
        print(f"❌ Data file not found: {data_path}")


def check_langchain_integration():
    """Check if LangChain components are set up correctly."""
    print("\n=== Checking LangChain Integration ===")

    try:
        from src.langchain_integration.text_processor import TextProcessor
        from src.langchain_integration.vectorstore import VectorStore

        print("✅ LangChain integration modules imported successfully")

        # Attempt to initialize components without calling external services
        try:
            TextProcessor()
            print("✅ TextProcessor initialized")
        except Exception as e:
            print(f"❌ Error initializing TextProcessor: {e!s}")

        try:
            vector_store = VectorStore()
            print("✅ VectorStore initialized")
            print(f"   Collection name: {vector_store.collection_name}")
            print(f"   Embedding model: {vector_store.embedding_model.model_name}")
        except Exception as e:
            print(f"❌ Error initializing VectorStore: {e!s}")
    except ImportError as e:
        print(f"❌ Error importing LangChain integration modules: {e!s}")
        print("   Check that the module structure is correct")


def run_test_query(query="Điện thoại nào có camera tốt nhất trong tầm giá 15 triệu?"):
    """Run a test query through the pipeline."""
    print(f"\n=== Running Test Query: '{query}' ===")

    try:
        from src.langchain_integration.pipeline import LangchainPipeline
        from src.langchain_integration.vectorstore import VectorStore

        # Check if Qdrant is running and collection exists
        try:
            from qdrant_client import QdrantClient

            load_dotenv()
            url = os.getenv("QDRANT_URL", "localhost")
            port = int(os.getenv("QDRANT_PORT", 6333))
            collection_name = os.getenv("QDRANT_COLLECTION_NAME", "product_data")

            client = QdrantClient(url=url, port=port)
            collections = client.get_collections().collections
            collection_names = [c.name for c in collections]

            if collection_name not in collection_names:
                print(
                    f"❌ Collection '{collection_name}' not found. Run 'python ingest.py' first"
                )
                return

            # Check if collection has data
            count = client.count(collection_name=collection_name).count
            if count == 0:
                print(
                    f"❌ Collection '{collection_name}' is empty. Run 'python ingest.py' first"
                )
                return
        except Exception as e:
            print(f"❌ Error checking Qdrant: {e!s}")
            return

        # Initialize pipeline
        vector_store = VectorStore()
        qa_pipeline = LangchainPipeline(vector_store=vector_store)

        print("⏳ Processing query...")
        try:
            answer = qa_pipeline.answer_question(query)
            print("\n=== Query Result ===")
            print(f"Q: {query}")
            print(f"A: {answer}")
        except Exception as e:
            print(f"❌ Error processing query: {e!s}")
    except ImportError as e:
        print(f"❌ Error importing modules: {e!s}")


def main():
    """Run all checks."""
    parser = argparse.ArgumentParser(
        description="Check and verify LangChain and Qdrant setup"
    )
    parser.add_argument("--test-query", action="store_true", help="Run a test query")
    parser.add_argument(
        "--query",
        type=str,
        default="Điện thoại nào có camera tốt nhất trong tầm giá 15 triệu?",
        help="Custom query to test",
    )

    args = parser.parse_args()

    print("=== LangChain & Qdrant Setup Checker ===")
    print("This script checks if your setup is working correctly.")

    check_environment()
    check_dependencies()
    check_qdrant_connection()
    check_data()
    check_langchain_integration()

    if args.test_query:
        run_test_query(args.query)

    print("\n=== Check Complete ===")


if __name__ == "__main__":
    main()
