"""
Chat routes cho chatbot interactions với streaming support.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator, Dict, List, Optional, Any

from litestar import Controller, delete, get, post, Request
from litestar.exceptions import HTTPException
from litestar.security.jwt import Token
from litestar.response import Stream
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from ...config import config, logger
from ...langchain_integration.facade import get_facade, ProductAssistantFacade
from ..schemas import (
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    ChatStreamChunk,
    ConversationCreate,
    ConversationHistory,
    ConversationResponse,
    SearchInfoResponse,
    SuccessResponse,
    User,
)
from ..services import ConversationService

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"

# Global instances
_facade_instance: Optional[ProductAssistantFacade] = None
_conversation_service: Optional[ConversationService] = None


def struct_to_dict(struct_obj) -> Dict:
    """Convert msgspec Struct to dictionary for JSON serialization."""
    if hasattr(struct_obj, "__struct_fields__"):
        # msgspec Struct object
        result = {}
        for field in struct_obj.__struct_fields__:
            result[field] = getattr(struct_obj, field)
        return result
    else:
        # Fallback to __dict__ if available
        return struct_obj.__dict__ if hasattr(struct_obj, "__dict__") else {}


def get_product_assistant() -> ProductAssistantFacade:
    """Get or create ProductAssistantFacade instance."""
    global _facade_instance
    if _facade_instance is None:
        try:
            _facade_instance = get_facade()
            logger.info("ProductAssistantFacade initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ProductAssistantFacade: {e}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize product assistant service",
            )
    return _facade_instance


async def get_conversation_service() -> ConversationService:
    """Get or create ConversationService instance."""
    global _conversation_service
    try:
        if _conversation_service is None:
            logger.info(
                f"Initializing ConversationService with admin_username: {config.api_user}"
            )
            _conversation_service = ConversationService(
                admin_username=config.api_user, redis_url=config.redis_url
            )
            logger.info("ConversationService initialized successfully")
        else:
            # Update admin_username in case it wasn't set correctly before
            if _conversation_service.admin_username != config.api_user:
                logger.warning(
                    f"Updating ConversationService admin_username from {_conversation_service.admin_username} to {config.api_user}"
                )
                _conversation_service.admin_username = config.api_user
            logger.debug(
                f"Using ConversationService with admin_username: {_conversation_service.admin_username}"
            )

        return _conversation_service
    except Exception as e:
        logger.error(f"Failed to initialize ConversationService: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize conversation service",
        )


def create_conversation_id() -> str:
    """Tạo conversation ID mới."""
    return str(uuid.uuid4())


async def get_or_create_conversation(
    conversation_id: Optional[str], user_id: str, username: str
) -> str:
    """Get existing hoặc tạo conversation mới."""
    conversation_service = await get_conversation_service()

    if not conversation_id:
        conversation_id = await conversation_service.create_conversation(
            user_id=user_id
        )
    else:
        # Check if conversation exists
        existing_conversation = await conversation_service.get_conversation(
            conversation_id, user_id, username
        )
        if not existing_conversation:
            # Create new conversation with the provided ID
            conversation_id = await conversation_service.create_conversation(
                user_id=user_id
            )

    return conversation_id


async def stream_chat_response(
    message: str,
    conversation_id: str,
    facade: ProductAssistantFacade,
    user_id: str,
    username: str,
    include_search_info: bool = False,
) -> AsyncIterator[str]:
    """Stream chat response với Server-Sent Events format."""
    try:
        conversation_service = await get_conversation_service()

        # Get conversation history for context
        conversation_messages = await conversation_service.get_conversation_messages(
            conversation_id, user_id, username
        )
        conversation_history = []
        for msg in conversation_messages:
            conversation_history.append(
                {
                    "message": msg["message"],
                    "response": msg["response"],
                    "timestamp": msg["timestamp"],
                }
            )

        # Send start event
        start_chunk = ChatStreamChunk(
            type="start",
            content="",
            conversation_id=conversation_id,
            metadata={
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        yield f"data: {json.dumps(struct_to_dict(start_chunk))}\n\n"

        # Stream response chunks
        full_response = ""
        facade = get_product_assistant()
        for chunk in facade.get_product_recommendations_stream(
            message, conversation_history
        ):
            full_response += chunk

            chunk_data = ChatStreamChunk(
                type="chunk", content=chunk, conversation_id=conversation_id
            )
            yield f"data: {json.dumps(struct_to_dict(chunk_data))}\n\n"

        # Get search info if requested (enhanced with LLM decision details)
        search_info = None
        if include_search_info:
            try:
                system_info = facade.get_system_info()
                search_info = {
                    "system_status": system_info["status"],
                    "clean_agent_available": system_info["clean_agent_available"],
                    "capabilities": system_info["capabilities"],
                    "facade_version": system_info.get("facade_version", "1.0"),
                }

                # Add agent stats if available
                if "agent_stats" in system_info:
                    search_info["agent_stats"] = system_info["agent_stats"]

            except Exception as e:
                logger.warning(f"Could not get search info: {e}")

        # Send end event with metadata IMMEDIATELY
        end_chunk = ChatStreamChunk(
            type="end",
            content="",
            conversation_id=conversation_id,
            metadata={
                "total_length": len(full_response),
                "search_info": search_info if include_search_info else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        yield f"data: {json.dumps(struct_to_dict(end_chunk))}\n\n"

        # Save to conversation history in background (non-blocking)
        async def save_message_background():
            try:
                conversation_service = await get_conversation_service()
                await conversation_service.add_message(
                    conversation_id=conversation_id,
                    message=message,
                    response=full_response,
                    user_id=user_id,
                    username=username,
                    response_time=0.0,
                    search_info=search_info,
                )
                logger.debug(f"Message saved to conversation {conversation_id}")
            except Exception as e:
                logger.warning(f"Failed to save streaming message to conversation: {e}")

        # Start background task for saving
        asyncio.create_task(save_message_background())

    except Exception as e:
        logger.error(f"Error in stream_chat_response: {e}")
        error_chunk = ChatStreamChunk(
            type="error",
            content=str(e),
            conversation_id=conversation_id,
            metadata={"error_type": type(e).__name__},
        )
        yield f"data: {json.dumps(struct_to_dict(error_chunk))}\n\n"


class Chat(Controller):
    """Chat controller for handling chat requests."""

    path = "/chat"
    tags = ["Chat"]

    @post("/", status_code=HTTP_200_OK)
    async def chat(
        self, request: Request[User, Token, Any], data: ChatRequest
    ) -> ChatResponse | Stream:
        """Main chat endpoint với streaming support."""
        try:
            user: User = request.user
            facade = get_product_assistant()

            # Get or create conversation
            conversation_id = await get_or_create_conversation(
                data.conversation_id, user.id, user.username
            )

            # Configure web search if specified
            # Web search configuration moved to facade system
            # The facade handles web search internally based on query needs

            # Return streaming response if requested
            if data.stream:
                return Stream(
                    stream_chat_response(
                        data.message,
                        conversation_id,
                        facade,
                        user.id,
                        user.username,
                        data.include_search_info,
                    ),
                    media_type="text/plain",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "Content-Type": "text/event-stream",
                        "X-Conversation-ID": conversation_id,
                    },
                )

            # Get conversation history for context
            conversation_service = await get_conversation_service()
            conversation_messages = (
                await conversation_service.get_conversation_messages(
                    conversation_id,
                    user.id,
                    user.username,
                )
            )
            conversation_history = []
            for msg in conversation_messages:
                conversation_history.append(
                    {
                        "message": msg["message"],
                        "response": msg["response"],
                        "timestamp": msg["timestamp"],
                    }
                )

            # Non-streaming response
            start_time = datetime.now(timezone.utc)
            facade = get_product_assistant()
            result = facade.get_product_recommendations(
                data.message, conversation_history
            )
            response = result["response"]
            end_time = datetime.now(timezone.utc)
            response_time = (end_time - start_time).total_seconds()

            # Get search info if requested (enhanced with LLM decision details)
            search_info = None
            if data.include_search_info:
                try:
                    system_info = facade.get_system_info()
                    search_info = {
                        "system_status": system_info["status"],
                        "clean_agent_available": system_info["clean_agent_available"],
                        "capabilities": system_info["capabilities"],
                        "facade_version": system_info.get("facade_version", "1.0"),
                    }

                    # Add agent stats if available
                    if "agent_stats" in system_info:
                        search_info["agent_stats"] = system_info["agent_stats"]

                except Exception as e:
                    logger.warning(f"Could not get search info: {e}")

            # Save to conversation history
            conversation_service = await get_conversation_service()
            try:
                await conversation_service.add_message(
                    conversation_id=conversation_id,
                    message=data.message,
                    response=response,
                    user_id=user.id,
                    username=user.username,
                    response_time=response_time,
                    search_info=search_info,
                )
            except Exception as e:
                logger.warning(f"Failed to save message to conversation: {e}")

            logger.info(f"Chat request processed: {len(data.message)} chars")

            return ChatResponse(
                message=data.message,
                response=response,
                conversation_id=conversation_id,
                response_time=response_time,
                search_info=search_info,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Chat error: {e}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error during chat: {e!s}",
            )

    @post("/conversations", status_code=HTTP_201_CREATED)
    async def create_conversation(
        self, request: Request[User, Token, Any], data: ConversationCreate
    ) -> ConversationResponse:
        """Tạo conversation mới."""
        try:
            user: User = request.user
            conversation_service = await get_conversation_service()

            conversation_id = await conversation_service.create_conversation(
                user_id=user.id,
                title=data.title,
                description=data.description,
            )

            conv = await conversation_service.get_conversation(
                conversation_id, user.id, user.username
            )

            return ConversationResponse(
                id=conv["id"],
                title=conv["title"],
                description=conv["description"],
                created_at=conv["created_at"],
                last_updated=conv["last_updated"],
                message_count=conv.get("message_count", 0),
            )

        except Exception as e:
            logger.error(f"Create conversation error: {e}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while creating conversation",
            )

    @get("/conversations", status_code=HTTP_200_OK)
    async def list_conversations(
        self, request: Request[User, Token, Any], limit: int = 20, offset: int = 0
    ) -> List[ConversationResponse]:
        """Lấy danh sách conversations."""
        try:
            user: User = request.user
            conversation_service = await get_conversation_service()

            conversations_data = await conversation_service.list_conversations(
                user_id=user.id,
                username=user.username,
                limit=limit,
                offset=offset,
            )

            conversations = []
            for conv in conversations_data:
                conversations.append(
                    ConversationResponse(
                        id=conv["id"],
                        title=conv["title"],
                        description=conv["description"],
                        created_at=conv["created_at"],
                        last_updated=conv["last_updated"],
                        message_count=conv.get("message_count", 0),
                    )
                )

            return conversations
        except Exception as e:
            logger.error(f"List conversations error: {e}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while listing conversations",
            )

    @get("/conversations/{conversation_id:str}", status_code=HTTP_200_OK)
    async def get_conversation_history(
        self, request: Request[User, Token, Any], conversation_id: str
    ) -> ChatHistoryResponse:
        """Lấy lịch sử conversation."""
        try:
            user: User = request.user
            conversation_service = await get_conversation_service()

            # Get conversation metadata
            conversation = await conversation_service.get_conversation(
                conversation_id,
                user.id,
                user.username,
            )
            if not conversation:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND, detail="Conversation not found"
                )

            # Get conversation messages
            messages_data = await conversation_service.get_conversation_messages(
                conversation_id,
                user.id,
                user.username,
                limit=100,  # Override default limit for full history
            )

            # Convert messages to ConversationHistory objects
            messages = []
            for msg in messages_data:
                messages.append(
                    ConversationHistory(
                        id=msg["id"],
                        message=msg["message"],
                        response=msg["response"],
                        timestamp=msg["timestamp"],
                        response_time=msg.get("response_time"),
                        search_info=msg.get("search_info"),
                    )
                )

            return ChatHistoryResponse(
                conversation_id=conversation_id,
                messages=messages,
                total_messages=len(messages),
                created_at=conversation["created_at"],
                last_updated=conversation["last_updated"],
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get conversation history error: {e}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while getting conversation history",
            )

    @delete("/conversations/{conversation_id:str}", status_code=HTTP_200_OK)
    async def delete_conversation(
        self, request: Request[User, Token, Any], conversation_id: str
    ) -> SuccessResponse:
        """Xóa conversation."""
        try:
            user: User = request.user
            conversation_service = await get_conversation_service()

            success = await conversation_service.delete_conversation(
                conversation_id,
                user.id,
                user.username,
            )
            if not success:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND, detail="Conversation not found"
                )

            return SuccessResponse(
                success=True, message="Conversation deleted successfully"
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Delete conversation error: {e}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while deleting conversation",
            )

    @get("/search-info", status_code=HTTP_200_OK)
    async def get_search_info(self, query: str) -> SearchInfoResponse:
        """Lấy thông tin search debug."""
        try:
            if not query.strip():
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail="Query parameter is required",
                )

            facade = get_product_assistant()
            system_info = facade.get_system_info()
            search_info = {
                "system_status": system_info["status"],
                "clean_agent_available": system_info["clean_agent_available"],
                "capabilities": system_info["capabilities"],
                "facade_version": system_info.get("facade_version", "1.0"),
                "vector_results_count": 0,  # Placeholder for compatibility
                "web_search_enabled": True,  # Facade handles this internally
                "web_search_available": True,
            }

            return SearchInfoResponse(
                vector_results_count=search_info.get("vector_results_count", 0),
                vector_results=search_info.get("vector_results", []),
                web_search_enabled=search_info.get("web_search_enabled", False),
                web_search_available=search_info.get("web_search_available", False),
                would_use_web_search=search_info.get("would_use_web_search"),
                web_results_count=search_info.get("web_results_count"),
                web_results=search_info.get("web_results", []),
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get search info error: {e}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while getting search info",
            )

    @get("/agent-stats", status_code=HTTP_200_OK)
    async def get_agent_system_stats(self) -> dict:
        """Lấy thống kê Agent system."""
        try:
            facade = get_product_assistant()
            system_info = facade.get_system_info()

            response = {
                "clean_agent_available": system_info["clean_agent_available"],
                "facade_version": system_info.get("facade_version", "1.0"),
                "system_status": system_info["status"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Add agent stats if available
            if "agent_stats" in system_info:
                response.update(
                    {"agent_enabled": True, "system_stats": system_info["agent_stats"]}
                )
            else:
                response.update(
                    {
                        "agent_enabled": False,
                        "message": "Clean product agent operational via facade",
                    }
                )

            return response

        except Exception as e:
            logger.error(f"Get agent stats error: {e}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while getting agent stats",
            )

    @post("/agent-reset", status_code=HTTP_200_OK)
    async def reset_agent_stats(self) -> dict:
        """Reset Agent system statistics."""
        try:
            facade = get_product_assistant()

            try:
                # Try to reset stats via facade
                agent = facade._get_agent()
                if agent:
                    agent.reset_stats()
                    stats = agent.get_stats()
                    return {
                        "success": True,
                        "message": "Product introduction agent statistics reset successfully",
                        "stats": stats,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                else:
                    return {
                        "success": False,
                        "message": "Product introduction agent not available",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
            except Exception as e:
                logger.warning(f"Could not reset agent stats: {e}")
                return {
                    "success": False,
                    "message": f"Failed to reset stats: {e}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

        except Exception as e:
            logger.error(f"Reset agent system error: {e}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while resetting agent system",
            )

    @get("/agent-tools", status_code=HTTP_200_OK)
    async def get_available_tools(self) -> dict:
        """Lấy danh sách tools khả dụng của Agent."""
        try:
            facade = get_product_assistant()

            try:
                agent = facade._get_agent()
                if agent and hasattr(agent, "tools"):
                    tools_info = []
                    for tool in agent.tools:
                        tools_info.append(
                            {
                                "name": tool.name,
                                "description": tool.description,
                                "args_schema": tool.args_schema.schema()
                                if tool.args_schema
                                else None,
                            }
                        )

                    return {
                        "agent_enabled": True,
                        "available_tools": tools_info,
                        "total_tools": len(tools_info),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                else:
                    # Return clean agent tools information
                    return {
                        "agent_enabled": True,
                        "available_tools": [
                            {
                                "name": "product_search",
                                "description": "Search for product information",
                                "type": "clean_search",
                            },
                            {
                                "name": "web_knowledge",
                                "description": "Additional web knowledge",
                                "type": "supplementary",
                            },
                            {
                                "name": "conversation_context",
                                "description": "Resolve conversation references",
                                "type": "context",
                            },
                        ],
                        "total_tools": 3,
                        "message": "Clean product introduction agent operational",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
            except Exception as e:
                logger.warning(f"Could not get agent tools: {e}")
                return {
                    "agent_enabled": False,
                    "message": f"Failed to get tools: {e}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

        except Exception as e:
            logger.error(f"Get tools error: {e}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while getting tools",
            )

    @get("/suggestions", status_code=HTTP_200_OK)
    async def get_chat_suggestions(self) -> dict:
        """Lấy gợi ý câu hỏi."""
        suggestions = [
            "Tư vấn laptop gaming tầm giá 20 triệu?",
            "So sánh iPhone 15 Pro và Samsung Galaxy S24 Ultra",
            "Điện thoại chụp ảnh đẹp giá dưới 10 triệu?",
            "Tai nghe không dây tốt nhất hiện tại?",
            "Smart TV 55 inch nào đáng mua nhất?",
            "Macbook Air M2 có phù hợp cho lập trình không?",
            "Máy tính bàn để chơi game và làm việc?",
            "Smartwatch tốt nhất cho người tập thể thao?",
            # Order flow examples
            "Tôi muốn đặt hàng iPhone 15",
            "Shop còn hàng Oppo A18 không?",
        ]

        return {"suggestions": suggestions, "context": "Sản phẩm điện tử và công nghệ"}

    @post("/intent-analysis", status_code=HTTP_200_OK)
    async def analyze_intent(
        self, request: Request[User, Token, Any], data: dict
    ) -> dict:
        """Analyze intent for debugging purposes."""
        try:
            message = data.get("message", "").strip()
            conversation_history = data.get("conversation_history", [])

            if not message:
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail="Message is required",
                )

            # Get the agent and analyze intent
            facade = get_product_assistant()
            agent = facade._get_agent()

            # Check if it's our UnifiedSmartAgent
            if hasattr(agent, "_analyze_intent"):
                # Direct access to intent analysis
                intent_result = agent._analyze_intent(message, conversation_history)

                return {
                    "message": message,
                    "intent_analysis": intent_result,
                    "agent_type": "unified_smart_agent",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            else:
                # Fallback for older agents
                return {
                    "message": message,
                    "intent_analysis": {
                        "intent_type": "PRODUCT_CONSULTATION",
                        "confidence": 0.0,
                        "score": 0,
                        "triggers": [],
                        "note": "Intent analysis not available with current agent",
                    },
                    "agent_type": "legacy_agent",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Intent analysis error: {e}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during intent analysis",
            )

    @get("/order-flow-status", status_code=HTTP_200_OK)
    async def get_order_flow_status(self) -> dict:
        """Get Smart Order Flow system status."""
        try:
            facade = get_product_assistant()
            agent = facade._get_agent()

            # Check agent type and capabilities
            agent_type = type(agent).__name__
            has_order_flow = hasattr(agent, "_analyze_intent")
            has_order_tools = hasattr(agent, "order_tools") if has_order_flow else False

            response = {
                "smart_order_flow_enabled": has_order_flow,
                "agent_type": agent_type,
                "capabilities": {
                    "intent_analysis": has_order_flow,
                    "order_processing": has_order_tools,
                    "consultation_flow": True,  # Always available
                    "streaming": hasattr(agent, "process_query_stream"),
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Add stats if available
            if hasattr(agent, "get_stats"):
                try:
                    stats = agent.get_stats()
                    response["statistics"] = stats
                except Exception as e:
                    logger.warning(f"Could not get agent stats: {e}")

            return response

        except Exception as e:
            logger.error(f"Order flow status error: {e}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while getting order flow status",
            )

    @post("/conversations/{conversation_id:str}/title", status_code=HTTP_200_OK)
    async def update_conversation_title(
        self, request: Request[User, Token, Any], conversation_id: str, data: dict
    ) -> SuccessResponse:
        """Cập nhật title của conversation."""
        try:
            user: User = request.user
            conversation_service = await get_conversation_service()

            title = data.get("title", "").strip()
            if not title:
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST, detail="Title cannot be empty"
                )

            success = await conversation_service.update_conversation_title(
                conversation_id,
                title,
                user.id,
                username=user.username,
            )

            if not success:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND, detail="Conversation not found"
                )

            return SuccessResponse(
                success=True, message="Conversation title updated successfully"
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Update conversation title error: {e}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while updating conversation title",
            )
