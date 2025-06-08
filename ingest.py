"""
Data ingestion script using the new functional architecture.
"""

import argparse
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src import create_application, get_logger

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


def main():
    """Run data ingestion process using functional architecture."""
    parser = argparse.ArgumentParser(
        description="Ingest product data into vector database using functional architecture"
    )
    parser.add_argument(
        "--data-path",
        type=str,
        default="cleaned_data.json",
        help="Path to the JSON data file (default: cleaned_data.json)",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate the vector store collection (currently not implemented)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Check if data file exists
    if not os.path.exists(args.data_path):
        print(f"❌ Error: Data file '{args.data_path}' not found.")
        print(f"Please ensure the file exists in the current directory: {os.getcwd()}")
        return 1

    print("🚀 Starting data ingestion with functional architecture...")
    print(f"📁 Data file: {args.data_path}")

    # Initialize application
    print("⚙️  Initializing application...")
    app_result = create_application()

    if app_result.is_failure:
        print(f"❌ Failed to initialize application: {app_result.error}")
        return 1

    app = app_result.value
    logger = get_logger()

    print("✅ Application initialized successfully")

    # Run data ingestion
    print("📊 Starting data ingestion...")

    try:
        ingest_result = app.ingest_data(args.data_path)

        if ingest_result.is_success:
            indexed_count = ingest_result.value
            print("✅ Data ingestion completed successfully!")
            print(f"📈 Indexed {indexed_count} documents into vector database")

            # Get application status for verification
            status = app.get_status()
            if args.verbose:
                print(f"📋 Application status: {status}")

            return 0
        else:
            print(f"❌ Data ingestion failed: {ingest_result.error}")
            logger.error("Data ingestion failed", error=ingest_result.error)
            return 1

    except KeyboardInterrupt:
        print("\n⚠️  Data ingestion interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error during data ingestion: {e}")
        logger.error("Unexpected error during ingestion", error=e)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
