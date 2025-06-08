"""
API module for the chatbot application.
"""

from .auth import AuthHandler, get_current_user, require_auth, optional_auth
from .routes import auth_router, chat_router, health_router
from .schemas import (
    ChatRequest,
    ChatResponse,
    LoginRequest,
    LoginResponse,
    UserResponse,
    ErrorResponse,
    SuccessResponse,
)

__all__ = [
    # Auth
    "AuthHandler",
    "get_current_user",
    "require_auth",
    "optional_auth",
    # Routes
    "auth_router",
    "chat_router",
    "health_router",
    # Schemas
    "ChatRequest",
    "ChatResponse",
    "LoginRequest",
    "LoginResponse",
    "UserResponse",
    "ErrorResponse",
    "SuccessResponse",
]

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"
