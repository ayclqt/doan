"""
Auth schemas cho authentication và authorization.
"""

from typing import Optional
from msgspec import Struct


class LoginRequest(Struct):
    """Schema cho login request."""

    username: str
    password: str


class UserCreate(Struct):
    """Schema cho tạo user mới."""

    username: str
    email: str
    password: str
    full_name: Optional[str] = None


class UserResponse(Struct):
    """Schema cho user response."""

    id: int
    username: str
    email: str
    created_at: str
    full_name: Optional[str] = None
    is_active: bool = True


class TokenResponse(Struct):
    """Schema cho token response."""

    access_token: str
    expires_in: int
    token_type: str = "bearer"


class LoginResponse(Struct):
    """Schema cho login response."""

    user: UserResponse
    token: TokenResponse


class RefreshTokenRequest(Struct):
    """Schema cho refresh token request."""

    refresh_token: str


class ChangePasswordRequest(Struct):
    """Schema cho đổi mật khẩu."""

    current_password: str
    new_password: str
    confirm_password: str


class ResetPasswordRequest(Struct):
    """Schema cho reset mật khẩu."""

    email: str


class ResetPasswordConfirm(Struct):
    """Schema cho xác nhận reset mật khẩu."""

    token: str
    new_password: str
    confirm_password: str
