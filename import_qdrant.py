#!/usr/bin/env python3
"""
Import script for Qdrant vector database export.
This script imports a previously exported Qdrant collection into a local Qdrant instance.
"""

import argparse
import pickle

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


def import_to_qdrant(export_file, host="localhost", port=6333):
    """Import a previously exported Qdrant collection."""
    print(f"Connecting to Qdrant at {host}:{port}...")
    client = QdrantClient(host=host, port=port)

    # Load the export data
    with open(export_file, "rb") as f:
        export_data = pickle.load(f)

    collection_info = export_data["collection_info"]
    points = export_data["points"]

    collection_name = collection_info["name"]
    vector_size = collection_info["vector_size"]
    distance_str = collection_info["vector_distance"]

    # Map string distance to enum
    distance_map = {
        "COSINE": Distance.COSINE,
        "EUCLID": Distance.EUCLID,
        "DOT": Distance.DOT,
    }
    distance = distance_map.get(distance_str, Distance.COSINE)

    # Check if collection exists and recreate it
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]

    if collection_name in collection_names:
        print(f"Collection '{collection_name}' already exists. Recreating...")
        client.delete_collection(collection_name=collection_name)

    # Create collection
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=distance),
    )

    print(
        f"Created collection '{collection_name}' with {vector_size} vector dimensions"
    )

    # Import points in batches
    batch_size = 100
    total_points = len(points)

    for i in range(0, total_points, batch_size):
        batch = points[i : i + batch_size]

        # Format points for upsert
        upsert_points = [
            {"id": point["id"], "vector": point["vector"], "payload": point["payload"]}
            for point in batch
        ]

        # Upsert points
        client.upsert(collection_name=collection_name, points=upsert_points)

        print(f"Imported {min(i + batch_size, total_points)}/{total_points} points")

    # Verify import
    count = client.count(collection_name=collection_name).count
    print(f"Import complete. Collection '{collection_name}' now has {count} points.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import Qdrant collection from export file"
    )
    parser.add_argument(
        "export_file", help="Path to the export file (qdrant_export.pkl)"
    )
    parser.add_argument("--host", default="localhost", help="Qdrant host")
    parser.add_argument("--port", type=int, default=6333, help="Qdrant port")

    args = parser.parse_args()
    import_to_qdrant(args.export_file, args.host, args.port)
