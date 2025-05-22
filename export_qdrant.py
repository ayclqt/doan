#!/usr/bin/env python3
"""
Export script for Qdrant vector database.
This script exports a Qdrant collection to a portable file format.
"""

import pickle
import argparse
from qdrant_client import QdrantClient


def export_qdrant_collection(
    collection_name, output_file="qdrant_export.pkl", host="localhost", port=6333
):
    """Export a Qdrant collection to a portable file format."""
    print(f"Connecting to Qdrant at {host}:{port}...")
    client = QdrantClient(host=host, port=port)

    # Check if collection exists
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]

    if collection_name not in collection_names:
        raise ValueError(f"Collection '{collection_name}' does not exist")

    # Get collection info
    print(f"Getting collection info for '{collection_name}'...")
    collection_info = client.get_collection(collection_name=collection_name)

    # Get all points with their vectors and payloads
    # We'll retrieve in batches to handle large collections
    limit = 1000
    offset = 0
    all_points = []

    print("Retrieving points from collection...")
    while True:
        points = client.scroll(
            collection_name=collection_name,
            limit=limit,
            offset=offset,
            with_vectors=True,
            with_payload=True,
        )[0]

        if not points:
            break

        all_points.extend(points)
        offset += limit

        print(f"Retrieved {len(all_points)} points so far...")

        if len(points) < limit:
            break

    # Create the export data structure
    export_data = {
        "collection_info": {
            "name": collection_name,
            "vector_size": collection_info.config.params.vectors.size,
            "vector_distance": collection_info.config.params.vectors.distance.name,
        },
        "points": [
            {"id": point.id, "vector": point.vector, "payload": point.payload}
            for point in all_points
        ],
    }

    # Save to file
    print(f"Saving {len(all_points)} points to {output_file}...")
    with open(output_file, "wb") as f:
        pickle.dump(export_data, f)

    print(f"Export complete. Saved {len(all_points)} points to {output_file}")
    return output_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export Qdrant collection to a portable file"
    )
    parser.add_argument("collection_name", help="Name of the collection to export")
    parser.add_argument(
        "--output", default="qdrant_export.pkl", help="Output file path"
    )
    parser.add_argument("--host", default="localhost", help="Qdrant host")
    parser.add_argument("--port", type=int, default=6333, help="Qdrant port")

    args = parser.parse_args()
    export_qdrant_collection(args.collection_name, args.output, args.host, args.port)
