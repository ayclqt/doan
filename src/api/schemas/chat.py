"""
Chat schemas cho chatbot interactions.
"""

from typing import Any

from msgspec import Struct


__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class ChatRequest(Struct):
    """Schema cho chat request."""

    message: str
    conversation_id: str | None = None
    stream: bool = False
    include_search_info: bool = False
    web_search_enabled: bool | None = None


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
    conversation_id: str | None = None
    metadata: dict[str, Any] | None = None


class ChatStreamResponse(Struct):
    """Schema cho chat stream response metadata."""

    conversation_id: str
    message: str
    started_at: str
    stream_url: str | None = None


class ConversationHistory(Struct):
    """Schema cho conversation history item."""

    id: str
    message: str
    response: str
    timestamp: str
    response_time: float
    search_info: dict[str, Any] | None = None


class ChatHistoryResponse(Struct):
    """Schema cho chat history response."""

    conversation_id: str
    messages: list[ConversationHistory]
    total_messages: int
    created_at: str
    last_updated: str


class SearchInfoResponse(Struct):
    """Schema cho search information."""

    vector_results_count: int
    vector_results: list[dict[str, Any]]
    web_search_enabled: bool
    web_search_available: bool
    would_use_web_search: bool | None = None
    web_results_count: int | None = None
    web_results: list[dict[str, Any]] | None = None


class ConversationCreate(Struct):
    """Schema cho tạo conversation mới."""

    title: str | None = None
    description: str | None = None


class ConversationResponse(Struct):
    """Schema cho conversation response."""

    id: str
    title: str | None
    description: str | None
    created_at: str
    last_updated: str
    message_count: int


class ConversationUpdate(Struct):
    """Schema cho update conversation."""

    title: str | None = None
    description: str | None = None


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
    payload: str | None = None


class ChatSuggestion(Struct):
    """Schema cho chat suggestions."""

    suggestions: list[str]
    context: str | None = None


class ChatMetrics(Struct):
    """Schema cho chat metrics."""

    total_conversations: int
    total_messages: int
    average_response_time: float
    web_search_usage: float
    most_common_topics: list[str]
