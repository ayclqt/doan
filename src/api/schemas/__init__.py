"""
API Schemas sử dụng msgspec Struct cho hệ thống chatbot hỗ trợ sản phẩm.
"""

from .auth import (
    LoginRequest,
    LoginResponse,
    UserCreate,
    UserResponse,
    TokenResponse,
    RefreshTokenRequest,
    ChangePasswordRequest,
)
from .chat import (
    ChatRequest,
    ChatResponse,
    ChatStreamResponse,
    ChatHistoryResponse,
    SearchInfoResponse,
    ChatStreamChunk,
    ConversationHistory,
    ConversationCreate,
    ConversationResponse,
)
from .common import ErrorResponse, SuccessResponse, PaginationParams, HealthResponse

__all__ = [
    # Auth schemas
    "LoginRequest",
    "LoginResponse",
    "UserCreate",
    "UserResponse",
    "TokenResponse",
    "RefreshTokenRequest",
    "ChangePasswordRequest",
    # Chat schemas
    "ChatRequest",
    "ChatResponse",
    "ChatStreamResponse",
    "ChatHistoryResponse",
    "SearchInfoResponse",
    "ChatStreamChunk",
    "ConversationHistory",
    "ConversationCreate",
    "ConversationResponse",
    # Common schemas
    "ErrorResponse",
    "SuccessResponse",
    "PaginationParams",
    "HealthResponse",
]

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"
