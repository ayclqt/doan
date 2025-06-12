"""
Conversation service for managing chat history in Qdrant vector database.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
import json
import redis.asyncio as redis

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    PointStruct,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
)

from ...config import config, logger

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class ConversationService:
    """Service for managing conversations in Qdrant vector database."""

    def __init__(
        self,
        url: str = config.qdrant_url,
        port: int = config.qdrant_port,
        admin_username: str = config.api_user,
        redis_url: str = config.redis_url,
    ):
        """Initialize the conversation service."""
        self.client = QdrantClient(url=url, port=port)
        self.conversations_collection = "conversations"
        self.messages_collection = "conversation_messages"
        self.admin_username = admin_username
        self.redis_client = None
        self.redis_url = redis_url
        self._ensure_collections()

    def _ensure_collections(self) -> None:
        """Ensure required collections exist."""
        collections = self.client.get_collections().collections
        collection_names = [collection.name for collection in collections]

        # Create conversations collection if not exists
        if self.conversations_collection not in collection_names:
            self.client.create_collection(
                collection_name=self.conversations_collection,
                vectors_config=VectorParams(
                    size=1,  # Minimal vector size since we don't need semantic search for conversations
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created collection: {self.conversations_collection}")

        # Create messages collection if not exists
        if self.messages_collection not in collection_names:
            self.client.create_collection(
                collection_name=self.messages_collection,
                vectors_config=VectorParams(
                    size=1,  # Minimal vector size since we don't need semantic search for messages
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created collection: {self.messages_collection}")

    async def get_redis_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self.redis_client is None:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            logger.info("Redis client initialized for ConversationService")
        return self.redis_client

    async def create_conversation(
        self,
        user_id: str = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> str:
        """Create a new conversation."""
        conversation_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Create conversation metadata
        conversation_data = {
            "id": conversation_id,
            "title": title,
            "description": description,
            "created_at": now.isoformat(),
            "last_updated": now.isoformat(),
            "message_count": 0,
        }

        # Only add user_id if it's not None (to avoid Qdrant issues with null values)
        if user_id is not None:
            conversation_data["user_id"] = user_id

        # Store in Qdrant with minimal vector
        point = PointStruct(
            id=conversation_id,
            vector=[0.0],  # Dummy vector
            payload=conversation_data,
        )

        self.client.upsert(
            collection_name=self.conversations_collection, points=[point]
        )

        logger.info(f"Created conversation: {conversation_id}")
        return conversation_id

    async def get_conversation(
        self,
        conversation_id: str,
        user_id: str,
        username: str,
    ) -> Optional[Dict]:
        """Get conversation by ID with user permission check."""
        try:
            result = self.client.retrieve(
                collection_name=self.conversations_collection, ids=[conversation_id]
            )

            if not result:
                return None

            conversation = result[0].payload

            # Check permissions
            # Only admin username can see all conversations
            if username == self.admin_username:
                logger.debug(f"Admin access granted for conversation {conversation_id}")
                return conversation

            # Block anonymous access completely
            if user_id is None or username is None:
                logger.warning(
                    f"Anonymous access blocked for conversation {conversation_id}"
                )
                return None

            # Regular users can only see their own conversations
            if conversation.get("user_id") == user_id:
                logger.debug(
                    f"User access granted for own conversation {conversation_id}"
                )
                return conversation

            # Access denied
            logger.debug(
                f"Access denied for conversation {conversation_id}: user_id={user_id}, username={username}"
            )
            return None

        except Exception as e:
            logger.error(f"Error getting conversation {conversation_id}: {e}")
            return None

    async def list_conversations(
        self,
        user_id: str,
        username: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict]:
        """List conversations for a user with strict permission control."""
        try:
            logger.info(
                f"Listing conversations for user_id={user_id}, username={username}, admin_username={self.admin_username}"
            )

            # Block anonymous access completely
            if user_id is None or username is None:
                logger.warning(
                    f"Anonymous access blocked: user_id={user_id}, username={username}"
                )
                return []

            # Check Redis cache first
            redis_client = await self.get_redis_client()
            cache_key = f"conversations:{user_id}:{limit}:{offset}"
            cached_conversations = await redis_client.get(cache_key)
            if cached_conversations:
                logger.info(f"Cache hit for conversations list: {cache_key}")
                return json.loads(cached_conversations)

            # Prepare filter for Qdrant query
            scroll_filter = None
            if username != self.admin_username:
                scroll_filter = Filter(
                    must=[
                        FieldCondition(key="user_id", match=MatchValue(value=user_id))
                    ]
                )

            # Use Qdrant scroll with pagination and filter
            # Note: Cannot use order_by without a range index, so we retrieve items and sort manually
            result = self.client.scroll(
                collection_name=self.conversations_collection,
                scroll_filter=scroll_filter,
                limit=limit + offset,
            )

            conversations = []
            if result and result[0]:
                logger.info(f"Retrieved {len(result[0])} conversations from Qdrant")
                for point in result[0]:
                    conv_data = point.payload
                    conversations.append(conv_data)
                # Sort by created_at descending manually
                conversations.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                # Manually apply offset and limit for pagination
                conversations = conversations[offset:offset + limit]

            logger.info(
                f"Returning {len(conversations)} conversations for user {username} (ID: {user_id})"
            )

            # Cache the result in Redis with TTL of 5 minutes
            await redis_client.setex(cache_key, 300, json.dumps(conversations))
            logger.info(f"Cached conversations list: {cache_key}")

            return conversations

        except Exception as e:
            logger.error(f"Error listing conversations for user {username}: {e}")
            return []

    async def delete_conversation(
        self,
        conversation_id: str,
        user_id: str,
        username: str,
    ) -> bool:
        """Delete a conversation and all its messages."""
        try:
            # Check if conversation exists and user has permission
            conversation = await self.get_conversation(
                conversation_id, user_id, username
            )
            if not conversation:
                return False

            # Delete all messages in the conversation
            self.client.delete(
                collection_name=self.messages_collection,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="conversation_id",
                            match=MatchValue(value=conversation_id),
                        )
                    ]
                ),
            )

            # Delete the conversation
            self.client.delete(
                collection_name=self.conversations_collection,
                points_selector=[conversation_id],
            )

            # Invalidate cache for this conversation
            redis_client = await self.get_redis_client()
            keys = await redis_client.keys(f"conversations:{user_id}:*")
            if keys:
                await redis_client.delete(*keys)
                logger.info(f"Invalidated cache for conversations of user {user_id}")
            keys = await redis_client.keys(f"messages:{conversation_id}:*")
            if keys:
                await redis_client.delete(*keys)
                logger.info(
                    f"Invalidated cache for messages of conversation {conversation_id}"
                )

            logger.info(f"Deleted conversation: {conversation_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting conversation {conversation_id}: {e}")
            return False

    async def add_message(
        self,
        conversation_id: str,
        message: str,
        response: str,
        user_id: str,
        username: str,
        response_time: Optional[float] = None,
        search_info: Optional[Dict] = None,
    ) -> str:
        """Add a message to a conversation."""
        try:
            # Check if conversation exists and user has permission
            conversation = await self.get_conversation(
                conversation_id, user_id, username
            )
            if not conversation:
                raise ValueError("Conversation not found or access denied")

            message_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            # Create message data
            message_data = {
                "id": message_id,
                "conversation_id": conversation_id,
                "message": message,
                "response": response,
                "timestamp": now.isoformat(),
                "response_time": response_time,
                "search_info": search_info,
            }

            # Store message in Qdrant
            point = PointStruct(
                id=message_id,
                vector=[0.0],  # Dummy vector
                payload=message_data,
            )

            self.client.upsert(collection_name=self.messages_collection, points=[point])

            # Update conversation metadata in a single operation
            result = self.client.retrieve(
                collection_name=self.conversations_collection, ids=[conversation_id]
            )
            if result:
                conversation_data = result[0].payload
                conversation_data["last_updated"] = now.isoformat()
                conversation_data["message_count"] = (
                    conversation_data.get("message_count", 0) + 1
                )

                update_point = PointStruct(
                    id=conversation_id, vector=[0.0], payload=conversation_data
                )
                self.client.upsert(
                    collection_name=self.conversations_collection, points=[update_point]
                )

            # Invalidate cache for this conversation's messages
            redis_client = await self.get_redis_client()
            keys = await redis_client.keys(f"messages:{conversation_id}:*")
            if keys:
                await redis_client.delete(*keys)
                logger.info(
                    f"Invalidated cache for messages of conversation {conversation_id}"
                )

            # Invalidate cache for user's conversation list
            keys = await redis_client.keys(f"conversations:{user_id}:*")
            if keys:
                await redis_client.delete(*keys)
                logger.info(f"Invalidated cache for conversations of user {user_id}")

            logger.info(f"Added message to conversation {conversation_id}")
            return message_id

        except Exception as e:
            logger.error(f"Error adding message to conversation {conversation_id}: {e}")
            raise

    async def get_conversation_messages(
        self,
        conversation_id: str,
        user_id: str,
        username: str,
        limit: int = 3,
        offset: int = 0,
    ) -> List[Dict]:
        """Get messages for a conversation."""
        try:
            # Check if conversation exists and user has permission
            conversation = await self.get_conversation(conversation_id, user_id, username)
            if not conversation:
                return []

            # Check Redis cache first
            redis_client = await self.get_redis_client()
            cache_key = f"messages:{conversation_id}:{limit}:{offset}"
            cached_messages = await redis_client.get(cache_key)
            if cached_messages:
                logger.info(f"Cache hit for messages: {cache_key}")
                return json.loads(cached_messages)

            # Get messages for the conversation from Qdrant
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="conversation_id", match=MatchValue(value=conversation_id)
                    )
                ]
            )

            result = self.client.scroll(
                collection_name=self.messages_collection,
                scroll_filter=filter_condition,
                limit=limit + offset,
            )

            messages = []
            if result and result[0]:
                for point in result[0]:
                    messages.append(point.payload)
                # Sort by timestamp ascending manually
                messages.sort(key=lambda x: x.get("timestamp", ""))
                # Manually apply offset and limit for pagination
                messages = messages[offset:offset + limit]

            # Cache the result in Redis with TTL of 5 minutes
            await redis_client.setex(cache_key, 300, json.dumps(messages))
            logger.info(f"Cached messages: {cache_key}")

            return messages

        except Exception as e:
            logger.error(
                f"Error getting messages for conversation {conversation_id}: {e}"
            )
            return []

    # Deprecated methods, replaced by combined update in add_message
    def _update_conversation_last_updated(self, conversation_id: str) -> None:
        """Deprecated: Update conversation's last_updated timestamp."""
        logger.warning(
            "_update_conversation_last_updated is deprecated, use combined update in add_message"
        )
        pass

    def _increment_message_count(self, conversation_id: str) -> None:
        """Deprecated: Increment message count for a conversation."""
        logger.warning(
            "_increment_message_count is deprecated, use combined update in add_message"
        )
        pass

    def set_admin_username(self, admin_username: str) -> None:
        """Set the admin username."""
        self.admin_username = admin_username

    def update_conversation_title(
        self,
        conversation_id: str,
        title: str,
        user_id: str,
        username: str,
    ) -> bool:
        """Update conversation title."""
        try:
            # Check if conversation exists and user has permission
            conversation = self.get_conversation(conversation_id, user_id, username)
            if not conversation:
                return False

            conversation["title"] = title
            conversation["last_updated"] = datetime.now(timezone.utc).isoformat()

            # Update the conversation
            point = PointStruct(id=conversation_id, vector=[0.0], payload=conversation)

            self.client.upsert(
                collection_name=self.conversations_collection, points=[point]
            )

            logger.info(f"Updated title for conversation {conversation_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating conversation title {conversation_id}: {e}")
            return False
