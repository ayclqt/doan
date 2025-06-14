"""
API module for the chatbot application.
"""

from .auth import jwt_auth, redis_user_service
from .routes import routers
from .schemas import (
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    LoginRequest,
    LoginResponse,
    SuccessResponse,
    User,
)
from .services import ConversationService

__all__ = [
    # Auth
    "jwt_auth",
    "redis_user_service",
    # Routes
    "routers",
    # Schemas
    "ChatRequest",
    "ChatResponse",
    "LoginRequest",
    "LoginResponse",
    "ErrorResponse",
    "SuccessResponse",
    "User",
    # Services
    "ConversationService",
]

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"
