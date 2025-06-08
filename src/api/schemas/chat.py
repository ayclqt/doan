"""
Chat schemas cho chatbot interactions.
"""

from typing import Any, Dict, List, Optional
from msgspec import Struct


class ChatRequest(Struct):
    """Schema cho chat request."""

    message: str
    conversation_id: str | None = None
    stream: bool = False
    include_search_info: bool = False
    web_search_enabled: Optional[bool] = None


class ChatResponse(Struct):
    """Schema cho chat response (non-streaming)."""

    message: str
    response: str
    conversation_id: str
    response_time: float
    timestamp: str
    search_info: dict[str, Any] | None = None


class ChatStreamChunk(Struct):
    """Schema cho streaming chunk."""

    type: str  # "chunk", "start", "end", "error"
    content: str
    conversation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatStreamResponse(Struct):
    """Schema cho chat stream response metadata."""

    conversation_id: str
    message: str
    started_at: str
    stream_url: Optional[str] = None


class ConversationHistory(Struct):
    """Schema cho conversation history item."""

    id: str
    message: str
    response: str
    timestamp: str
    response_time: float
    search_info: Optional[Dict[str, Any]] = None


class ChatHistoryResponse(Struct):
    """Schema cho chat history response."""

    conversation_id: str
    messages: List[ConversationHistory]
    total_messages: int
    created_at: str
    last_updated: str


class SearchInfoResponse(Struct):
    """Schema cho search information."""

    vector_results_count: int
    vector_results: List[Dict[str, Any]]
    web_search_enabled: bool
    web_search_available: bool
    would_use_web_search: Optional[bool] = None
    web_results_count: Optional[int] = None
    web_results: Optional[List[Dict[str, Any]]] = None


class ConversationCreate(Struct):
    """Schema cho tạo conversation mới."""

    title: Optional[str] = None
    description: Optional[str] = None


class ConversationResponse(Struct):
    """Schema cho conversation response."""

    id: str
    title: Optional[str]
    description: Optional[str]
    created_at: str
    last_updated: str
    message_count: int


class ConversationUpdate(Struct):
    """Schema cho update conversation."""

    title: Optional[str] = None
    description: Optional[str] = None


class ChatSettings(Struct):
    """Schema cho chat settings."""

    web_search_enabled: bool = True
    stream_enabled: bool = True
    include_search_info: bool = False
    max_history: int = 50


class ChatSettingsResponse(Struct):
    """Schema cho chat settings response."""

    settings: ChatSettings
    updated_at: str | None = None


class QuickReply(Struct):
    """Schema cho quick replies."""

    text: str
    payload: Optional[str] = None


class ChatSuggestion(Struct):
    """Schema cho chat suggestions."""

    suggestions: List[str]
    context: Optional[str] = None


class ChatMetrics(Struct):
    """Schema cho chat metrics."""

    total_conversations: int
    total_messages: int
    average_response_time: float
    web_search_usage: float
    most_common_topics: List[str]
