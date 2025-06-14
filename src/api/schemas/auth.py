from datetime import datetime
from typing import Optional

from msgspec import Struct

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class User(Struct):
    """User model for authentication"""

    id: str
    username: str
    hashed_password: str
    created_at: datetime
    is_active: bool = True
    last_login: Optional[datetime] = None


class LoginRequest(Struct):
    """Request model for login"""

    username: str
    password: str


class LoginResponse(Struct, kw_only=True):
    """Response model for successful login"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    username: str


class TokenPayload(Struct):
    """JWT token payload"""

    sub: str  # subject (user_id)
    exp: datetime  # expiration time
    iat: datetime  # issued at
    username: str
    user_id: str


class RegisterRequest(Struct):
    """Request model for user registration"""

    username: str
    password: str


class RegisterResponse(Struct, kw_only=True):
    """Response model for successful registration"""

    user_id: str
    username: str
    message: str = "User registered successfully"
