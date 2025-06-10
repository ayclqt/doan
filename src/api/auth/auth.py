from datetime import datetime, timedelta
from typing import Optional

import jwt
from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException
from litestar.security.jwt import JWTAuth, Token

from ...config import config
from ..schemas.auth import User
from .redis_service import redis_user_service

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class AuthService:
    """JWT Authentication Service"""

    @staticmethod
    async def authenticate_user(username: str, password: str) -> Optional[User]:
        """
        Authenticate user with username and password using Redis and bcrypt

        Args:
            username: The username
            password: The password

        Returns:
            User object if authentication successful, None otherwise
        """
        user = await redis_user_service.authenticate_user(username, password)
        if user:
            # Update last login time
            await redis_user_service.update_user_last_login(username)
        return user

    @staticmethod
    async def create_user(username: str, password: str) -> Optional[User]:
        """
        Create a new user

        Args:
            username: The username
            password: The password

        Returns:
            User object if created successfully, None if username exists
        """
        return await redis_user_service.create_user(username, password)

    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[User]:
        """
        Get user by ID

        Args:
            user_id: User ID

        Returns:
            User object if found, None otherwise
        """
        return await redis_user_service.get_user_by_id(user_id)

    @staticmethod
    def create_token(user: User, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create JWT token for authenticated user

        Args:
            user: Authenticated user
            expires_delta: Token expiration time

        Returns:
            JWT token string
        """
        if expires_delta is None:
            expires_delta = timedelta(hours=24)  # Default 24 hours

        now = datetime.utcnow()
        expire = now + expires_delta

        payload = {
            "sub": user.id,  # Use user ID as subject
            "exp": expire,
            "iat": now,
            "username": user.username,
            "user_id": user.id,
        }

        return jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)


async def retrieve_user_handler(token: Token, connection: ASGIConnection) -> User:
    """
    Retrieve user from JWT token

    Args:
        token: JWT token
        connection: ASGI connection

    Returns:
        User object

    Raises:
        NotAuthorizedException: If token is invalid or user not found
    """
    try:
        user_id = token.sub
        user = await AuthService.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise NotAuthorizedException("User not found or inactive")
        return user
    except Exception as e:
        raise NotAuthorizedException(f"Invalid token: {e!s}") from e


# JWT Auth configuration
jwt_auth = JWTAuth[User](
    retrieve_user_handler=retrieve_user_handler,
    token_secret=config.jwt_secret,
    exclude=["/auth/login", "/schema", "/health"],  # Public endpoints
    default_token_expiration=timedelta(hours=24),
)


def get_current_user(connection: ASGIConnection) -> User:
    """
    Get current authenticated user from connection

    Args:
        connection: ASGI connection

    Returns:
        Current authenticated user
    """
    return connection.user
