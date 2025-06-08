"""
Chat routes cho chatbot interactions với streaming support.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, AsyncIterator

from litestar import Router, post, get, delete
from litestar.di import Provide
from litestar.exceptions import HTTPException
from litestar.response import Stream
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from ...config import logger
from ...langchain_integration import LangchainPipeline, VectorStore
from ..auth import optional_auth, flexible_auth
from ..auth.models import User
from ..schemas import (
    ChatRequest,
    ChatResponse,
    ChatStreamChunk,
    ChatHistoryResponse,
    ConversationHistory,
    SearchInfoResponse,
    ConversationCreate,
    ConversationResponse,
    SuccessResponse,
)


# Global instances
_qa_pipeline: Optional[LangchainPipeline] = None
_conversations: Dict[str, Dict] = {}  # In-memory storage cho demo


def struct_to_dict(struct_obj) -> Dict:
    """Convert msgspec Struct to dictionary for JSON serialization."""
    if hasattr(struct_obj, '__struct_fields__'):
        # msgspec Struct object
        result = {}
        for field in struct_obj.__struct_fields__:
            result[field] = getattr(struct_obj, field)
        return result
    else:
        # Fallback to __dict__ if available
        return struct_obj.__dict__ if hasattr(struct_obj, '__dict__') else {}


def get_qa_pipeline() -> LangchainPipeline:
    """Get or create QA pipeline instance."""
    global _qa_pipeline
    if _qa_pipeline is None:
        try:
            vector_store = VectorStore()
            _qa_pipeline = LangchainPipeline(vector_store=vector_store)
            logger.info("QA Pipeline initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize QA Pipeline: {e}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize chatbot service",
            )
    return _qa_pipeline


def create_conversation_id() -> str:
    """Tạo conversation ID mới."""
    return str(uuid.uuid4())


def get_or_create_conversation(
    conversation_id: Optional[str], user_id: Optional[int] = None
) -> str:
    """Get existing hoặc tạo conversation mới."""
    if not conversation_id:
        conversation_id = create_conversation_id()

    if conversation_id not in _conversations:
        _conversations[conversation_id] = {
            "id": conversation_id,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc),
            "messages": [],
            "title": None,
            "description": None,
        }

    return conversation_id


async def stream_chat_response(
    message: str,
    conversation_id: str,
    qa_pipeline: LangchainPipeline,
    include_search_info: bool = False,
) -> AsyncIterator[str]:
    """Stream chat response với Server-Sent Events format."""
    try:
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
        for chunk in qa_pipeline.answer_question_stream(message):
            full_response += chunk

            chunk_data = ChatStreamChunk(
                type="chunk", content=chunk, conversation_id=conversation_id
            )
            yield f"data: {json.dumps(struct_to_dict(chunk_data))}\n\n"

        # Get search info if requested
        search_info = None
        if include_search_info:
            try:
                search_info = qa_pipeline.get_search_info(message)
            except Exception as e:
                logger.warning(f"Could not get search info: {e}")

        # Save to conversation history
        if conversation_id in _conversations:
            history_item = ConversationHistory(
                id=str(uuid.uuid4()),
                message=message,
                response=full_response,
                timestamp=datetime.now(timezone.utc).isoformat(),
                response_time=0.0,
                search_info=search_info,
            )
            _conversations[conversation_id]["messages"].append(struct_to_dict(history_item))
            _conversations[conversation_id]["last_updated"] = datetime.now(timezone.utc)

        # Send end event with metadata
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

    except Exception as e:
        logger.error(f"Error in stream_chat_response: {e}")
        error_chunk = ChatStreamChunk(
            type="error",
            content=str(e),
            conversation_id=conversation_id,
            metadata={"error_type": type(e).__name__},
        )
        yield f"data: {json.dumps(struct_to_dict(error_chunk))}\n\n"


# @post("/chat", status_code=HTTP_200_OK, dependencies={"user": Provide(flexible_auth)})
@post("/chat", status_code=HTTP_200_OK)
async def chat(data: ChatRequest, user: Optional[User] = None) -> ChatResponse | Stream:
    """Main chat endpoint với streaming support."""
    try:
        qa_pipeline = get_qa_pipeline()

        # Get or create conversation
        conversation_id = get_or_create_conversation(
            data.conversation_id, user.id if user else None
        )

        # Configure web search if specified
        if data.web_search_enabled is not None:
            if data.web_search_enabled:
                qa_pipeline.enable_web_search_feature()
            else:
                qa_pipeline.disable_web_search()

        # Return streaming response if requested
        if data.stream:
            return Stream(
                stream_chat_response(
                    data.message, conversation_id, qa_pipeline, data.include_search_info
                ),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Content-Type": "text/event-stream",
                    "X-Conversation-ID": conversation_id,
                },
            )

        # Non-streaming response
        start_time = datetime.now(timezone.utc)
        response = qa_pipeline.answer_question(data.message)
        end_time = datetime.now(timezone.utc)
        response_time = (end_time - start_time).total_seconds()

        # Get search info if requested
        search_info = None
        if data.include_search_info:
            try:
                search_info = qa_pipeline.get_search_info(data.message)
            except Exception as e:
                logger.warning(f"Could not get search info: {e}")

        # Save to conversation history
        if conversation_id in _conversations:
            history_item = ConversationHistory(
                id=str(uuid.uuid4()),
                message=data.message,
                response=response,
                timestamp=datetime.now(timezone.utc).isoformat(),
                response_time=response_time,
                search_info=search_info,
            )
            _conversations[conversation_id]["messages"].append(struct_to_dict(history_item))
            _conversations[conversation_id]["last_updated"] = datetime.now(timezone.utc)

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
            detail=f"Internal server error during chat: {str(e)}",
        )


@post(
    "/chat/conversations",
    status_code=HTTP_201_CREATED,
    # dependencies={"user": Provide(optional_auth)},
)
async def create_conversation(
    data: ConversationCreate, user: Optional[User] = None
) -> ConversationResponse:
    """Tạo conversation mới."""
    try:
        conversation_id = create_conversation_id()

        _conversations[conversation_id] = {
            "id": conversation_id,
            "user_id": user.id if user else None,
            "created_at": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc),
            "messages": [],
            "title": data.title,
            "description": data.description,
        }

        conv = _conversations[conversation_id]

        return ConversationResponse(
            id=conv["id"],
            title=conv["title"],
            description=conv["description"],
            created_at=conv["created_at"].isoformat(),
            last_updated=conv["last_updated"].isoformat(),
            message_count=0,
        )

    except Exception as e:
        logger.error(f"Create conversation error: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while creating conversation",
        )


@get(
    "/chat/conversations",
    status_code=HTTP_200_OK,
    # dependencies={"user": Provide(optional_auth)},
)
async def list_conversations(
    user: Optional[User] = None, limit: int = 20, offset: int = 0
) -> List[ConversationResponse]:
    """Lấy danh sách conversations."""
    try:
        conversations = []
        user_id = user.id if user else None

        for conv in _conversations.values():
            # Filter by user if authenticated
            if user and conv["user_id"] != user_id:
                continue
            # For anonymous users, only show conversations without user_id
            if not user and conv["user_id"] is not None:
                continue

            conversations.append(
                ConversationResponse(
                    id=conv["id"],
                    title=conv["title"],
                    description=conv["description"],
                    created_at=conv["created_at"].isoformat(),
                    last_updated=conv["last_updated"].isoformat(),
                    message_count=len(conv["messages"]),
                )
            )

        # Sort by last_updated desc
        conversations.sort(key=lambda x: x.last_updated, reverse=True)

        # Apply pagination
        return conversations[offset : offset + limit]

    except Exception as e:
        logger.error(f"List conversations error: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while listing conversations",
        )


@get(
    "/chat/conversations/{conversation_id:str}",
    status_code=HTTP_200_OK,
    # dependencies={"user": Provide(optional_auth)},
)
async def get_conversation_history(
    conversation_id: str, user: Optional[User] = None
) -> ChatHistoryResponse:
    """Lấy lịch sử conversation."""
    try:
        if conversation_id not in _conversations:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail="Conversation not found"
            )

        conv = _conversations[conversation_id]

        # Check permissions
        if user and conv["user_id"] != user.id:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail="Conversation not found"
            )
        if not user and conv["user_id"] is not None:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail="Conversation not found"
            )

        # Convert messages to ConversationHistory objects
        messages = []
        for msg in conv["messages"]:
            messages.append(
                ConversationHistory(
                    id=msg["id"],
                    message=msg["message"],
                    response=msg["response"],
                    timestamp=msg["timestamp"],
                    response_time=msg["response_time"],
                    search_info=msg.get("search_info"),
                )
            )

        return ChatHistoryResponse(
            conversation_id=conversation_id,
            messages=messages,
            total_messages=len(messages),
            created_at=conv["created_at"].isoformat(),
            last_updated=conv["last_updated"].isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get conversation history error: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while getting conversation history",
        )


@delete(
    "/chat/conversations/{conversation_id:str}",
    status_code=HTTP_200_OK,
    # dependencies={"user": Provide(optional_auth)},
)
async def delete_conversation(
    conversation_id: str, user: Optional[User] = None
) -> SuccessResponse:
    """Xóa conversation."""
    try:
        if conversation_id not in _conversations:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail="Conversation not found"
            )

        conv = _conversations[conversation_id]

        # Check permissions
        if user and conv["user_id"] != user.id:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail="Conversation not found"
            )
        if not user and conv["user_id"] is not None:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail="Conversation not found"
            )

        # Delete conversation
        del _conversations[conversation_id]

        logger.info(f"Conversation deleted: {conversation_id}")

        return SuccessResponse(message="Conversation deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete conversation error: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while deleting conversation",
        )


@get(
    "/chat/search-info",
    status_code=HTTP_200_OK,
    # dependencies={"user": Provide(optional_auth)},
)
async def get_search_info(
    query: str, user: Optional[User] = None
) -> SearchInfoResponse:
    """Lấy thông tin search debug."""
    try:
        if not query.strip():
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, detail="Query parameter is required"
            )

        qa_pipeline = get_qa_pipeline()
        search_info = qa_pipeline.get_search_info(query)

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


@get("/chat/suggestions", status_code=HTTP_200_OK)
async def get_chat_suggestions() -> dict:
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
    ]

    return {"suggestions": suggestions, "context": "Sản phẩm điện tử và công nghệ"}


# Router
chat_router = Router(
    path="/api/v1",
    route_handlers=[
        chat,
        create_conversation,
        list_conversations,
        get_conversation_history,
        delete_conversation,
        get_search_info,
        get_chat_suggestions,
    ],
    tags=["Chat"],
)


__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"
