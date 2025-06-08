"""
User models cho authentication system.
"""

from typing import Optional
from datetime import datetime
from msgspec import Struct


class User(Struct):
    """User model cho public data."""

    id: int
    username: str
    email: str
    full_name: Optional[str]
    created_at: datetime
    is_active: bool = True
    last_login: datetime | None = None


class UserInDB(Struct):
    """User model với sensitive data cho database."""

    id: int
    username: str
    email: str
    full_name: Optional[str]
    hashed_password: str
    created_at: datetime
    updated_at: datetime | None = None
    last_login: datetime | None = None
    is_active: bool = True
    is_superuser: bool = False
    login_count: int = 0


class UserCreate(Struct):
    """Model cho tạo user mới."""

    username: str
    email: str
    password: str
    full_name: Optional[str] = None


class UserUpdate(Struct):
    """Model cho cập nhật user."""

    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class TokenData(Struct):
    """Model cho token data."""

    user_id: int
    username: str
    exp: int
    iat: int
    token_type: str = "access"


class RefreshToken(Struct):
    """Model cho refresh token."""

    token: str
    user_id: int
    expires_at: datetime
    created_at: datetime
    is_active: bool = True


__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"
