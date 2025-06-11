#!/usr/bin/env python3
"""
Script to initialize conversation collections in Qdrant.
Run this script once to create the required collections for conversation storage.
"""

import asyncio
import sys
from pathlib import Path
from qdrant_client import QdrantClient
from src.api.services.conversation_service import ConversationService
from src.config import config, logger

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def check_conversation_collections_exist():
    """Check if conversation collections already exist"""
    try:
        client = QdrantClient(url=config.qdrant_url, port=config.qdrant_port)
        collections = client.get_collections()
        collection_names = [collection.name for collection in collections.collections]

        conversations_exists = "conversations" in collection_names
        messages_exists = "conversation_messages" in collection_names

        if conversations_exists and messages_exists:
            logger.info("Both conversation collections already exist")
            return True
        elif conversations_exists or messages_exists:
            logger.warning("Only some conversation collections exist")
            logger.warning("⚠️  Partial conversation collections found:")
            if conversations_exists:
                logger.info("✅ conversations")
            else:
                logger.error("❌ conversations (missing)")
            if messages_exists:
                logger.info("✅ conversation_messages")
            else:
                logger.error("❌ conversation_messages (missing)")
            logger.info("Will create missing collections...")
            return False
        else:
            logger.info("No conversation collections found - will create new ones")
            return False
    except Exception as e:
        logger.error("❌ Error checking conversation collections", error=str(e))
        return False


async def init_conversation_collections():
    """Initialize conversation collections in Qdrant"""
    try:
        logger.info("Initializing conversation collections...")

        # Check if collections already exist
        if await check_conversation_collections_exist():
            logger.info(
                "✅ Conversation collections initialization skipped - collections already exist"
            )
            return

        logger.info("🔄 Creating conversation collections...")

        # Create ConversationService instance (this will create collections automatically)
        conversation_service = ConversationService()

        # Verify collections were created successfully
        from qdrant_client import QdrantClient

        client = QdrantClient(url=config.qdrant_url, port=config.qdrant_port)
        collections = client.get_collections()
        collection_names = [collection.name for collection in collections.collections]

        conversations_created = "conversations" in collection_names
        messages_created = "conversation_messages" in collection_names

        if conversations_created and messages_created:
            logger.info(
                "✅ Conversation collections initialized successfully",
                conversations=conversation_service.conversations_collection,
                messages=conversation_service.messages_collection,
            )
        else:
            logger.error(
                "❌ Failed to create some conversation collections",
                conversations="✅" if conversations_created else "❌",
                conversation_messages="✅" if messages_created else "❌",
            )
            raise Exception("Collection creation verification failed")

    except Exception as e:
        logger.error("❌ Error initializing conversation collections", error=str(e))
        sys.exit(1)


async def check_qdrant_connection():
    """Check if Qdrant is available"""
    try:
        client = QdrantClient(url=config.qdrant_url, port=config.qdrant_port)
        collections = client.get_collections()

        logger.info(
            "✅ Qdrant connection successful",
            numbers=len(collections.collections),
            collections=[collection.name for collection in collections.collections],
        )

        return True
    except Exception as e:
        logger.error(
            "❌ Qdrant connection failed! Please make sure Qdrant is running and accessible!",
            host=config.qdrant_url,
            port=config.qdrant_port,
            error=str(e),
        )
        return False


async def main():
    """Main function"""
    logger.info(
        "🚀 Initializing Qdrant collections for conversation storage...",
        host=config.qdrant_url,
        port=config.qdrant_port,
    )

    # Check Qdrant connection first
    if not await check_qdrant_connection():
        sys.exit(1)

    # Initialize conversation collections
    await init_conversation_collections()

    logger.info(
        "✅ Conversation collections initialization completed!The system is now ready to store chat history in Qdrant."
    )


if __name__ == "__main__":
    asyncio.run(main())
