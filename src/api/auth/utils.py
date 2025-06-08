"""
Authentication utilities cho JWT handling và password security.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from jwt.exceptions import InvalidTokenError

from ...config import config


def hash_password(password: str) -> str:
    """Hash password sử dụng bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password với hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Tạo JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=config.access_token_expire_minutes
        )

    to_encode.update(
        {"exp": expire, "iat": datetime.now(timezone.utc), "token_type": "access"}
    )

    encoded_jwt = jwt.encode(to_encode, config.secret_key, algorithm=config.algorithm)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Tạo JWT refresh token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=config.refresh_token_expire_days
        )

    to_encode.update(
        {"exp": expire, "iat": datetime.now(timezone.utc), "token_type": "refresh"}
    )

    encoded_jwt = jwt.encode(to_encode, config.secret_key, algorithm=config.algorithm)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token và trả về payload."""
    try:
        payload = jwt.decode(token, config.secret_key, algorithms=[config.algorithm])
        return payload
    except InvalidTokenError:
        return None


def decode_token(token: str) -> Optional[dict]:
    """Decode JWT token without verification (for debugging)."""
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except Exception:
        return None


def is_token_expired(token: str) -> bool:
    """Kiểm tra token có hết hạn không."""
    payload = decode_token(token)
    if not payload:
        return True

    exp = payload.get("exp")
    if not exp:
        return True

    return datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc)


def generate_random_token(length: int = 32) -> str:
    """Tạo random token cho các mục đích khác."""
    return secrets.token_urlsafe(length)


def extract_user_id_from_token(token: str) -> Optional[int]:
    """Extract user ID từ token."""
    payload = verify_token(token)
    if payload:
        return payload.get("user_id")
    return None


def extract_username_from_token(token: str) -> Optional[str]:
    """Extract username từ token."""
    payload = verify_token(token)
    if payload:
        return payload.get("username")
    return None


def create_api_key(user_id: int, name: str = "default") -> str:
    """Tạo API key cho user."""
    data = {"user_id": user_id, "key_name": name, "type": "api_key"}

    # API key không hết hạn hoặc có thời hạn rất dài
    expires_delta = timedelta(days=365 * 10)  # 10 năm

    return create_access_token(data, expires_delta)


def verify_api_key(api_key: str) -> Optional[dict]:
    """Verify API key."""
    payload = verify_token(api_key)
    if payload and payload.get("type") == "api_key":
        return payload
    return None


__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"
