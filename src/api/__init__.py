"""
API module for the chatbot application.
"""

from .auth import jwt_auth
from .routes import routers
from .schemas import (
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    SuccessResponse,
)

__all__ = [
    # Auth
    "jwt_auth",
    # Routes
    "routers",
    # Schemas
    "ChatRequest",
    "ChatResponse",
    "LoginRequest",
    "LoginResponse",
    "RegisterRequest",
    "RegisterResponse",
    "ErrorResponse",
    "SuccessResponse",
]

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"
