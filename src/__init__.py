from .config import config, logger
from .langchain_integration import LangchainPipeline, VectorStore, TextProcessor
from .api import (
    AuthHandler,
    get_current_user,
    require_auth,
    optional_auth,
    auth_router,
    chat_router,
    health_router,
    ChatRequest,
    ChatResponse,
    LoginRequest,
    LoginResponse,
    UserResponse,
    ErrorResponse,
    SuccessResponse,
)

__all__ = [
    "config",
    "logger",
    "LangchainPipeline",
    "VectorStore",
    "TextProcessor",
    # API components
    "AuthHandler",
    "get_current_user",
    "require_auth",
    "optional_auth",
    "auth_router",
    "chat_router",
    "health_router",
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
