"""
Auth dependencies cho Litestar API endpoints.
"""

from typing import Optional

from litestar import Request
from litestar.exceptions import NotAuthorizedException
from litestar.connection import ASGIConnection
from litestar.handlers.base import BaseRouteHandler

from ...config import logger
from .auth_handler import AuthHandler
from .models import User


# Global auth handler instance
auth_handler = AuthHandler()


async def get_auth_handler() -> AuthHandler:
    """Get auth handler instance."""
    return auth_handler


async def get_current_user(request: Request) -> Optional[User]:
    """Get current user từ request headers."""
    try:
        # Lấy token từ Authorization header
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None

        # Parse Bearer token
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                return None
        except ValueError:
            return None

        # Verify token và get user
        user = auth_handler.get_current_user_from_token(token)
        return user

    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        return None


async def require_auth(connection: ASGIConnection, _: BaseRouteHandler) -> User:
    """Dependency để require authentication."""
    try:
        # Lấy token từ Authorization header
        authorization = connection.headers.get("Authorization")
        if not authorization:
            raise NotAuthorizedException("Missing authorization header")

        # Parse Bearer token
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise NotAuthorizedException("Invalid authorization scheme")
        except ValueError:
            raise NotAuthorizedException("Invalid authorization header format")

        # Verify token và get user
        user = auth_handler.get_current_user_from_token(token)
        if not user:
            raise NotAuthorizedException("Invalid or expired token")

        return user

    except NotAuthorizedException:
        raise
    except Exception as e:
        logger.error(f"Error in require_auth: {e}")
        raise NotAuthorizedException("Authentication failed")


async def optional_auth(
    connection: ASGIConnection, _: BaseRouteHandler
) -> Optional[User]:
    """Dependency cho optional authentication."""
    try:
        # Lấy token từ Authorization header
        authorization = connection.headers.get("Authorization")
        if not authorization:
            return None

        # Parse Bearer token
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                return None
        except ValueError:
            return None

        # Verify token và get user
        user = auth_handler.get_current_user_from_token(token)
        return user

    except Exception as e:
        logger.error(f"Error in optional_auth: {e}")
        return None


async def require_admin(connection: ASGIConnection, _: BaseRouteHandler) -> User:
    """Dependency để require admin privileges."""
    try:
        # First check authentication
        user = await require_auth(connection, _)

        # Check if user is admin (superuser)
        user_in_db = auth_handler._users.get(user.id)
        if not user_in_db or not user_in_db.is_superuser:
            raise NotAuthorizedException("Admin privileges required")

        return user

    except NotAuthorizedException:
        raise
    except Exception as e:
        logger.error(f"Error in require_admin: {e}")
        raise NotAuthorizedException("Admin authentication failed")


def get_api_key_user(api_key: str) -> Optional[User]:
    """Get user từ API key."""
    try:
        from .utils import verify_api_key

        payload = verify_api_key(api_key)
        if not payload:
            return None

        user_id = payload.get("user_id")
        if not user_id:
            return None

        return auth_handler.get_user_by_id(user_id)

    except Exception as e:
        logger.error(f"Error getting user from API key: {e}")
        return None


async def api_key_auth(
    connection: ASGIConnection, _: BaseRouteHandler
) -> Optional[User]:
    """Dependency cho API key authentication."""
    try:
        # Check for API key in headers
        api_key = connection.headers.get("X-API-Key")
        if not api_key:
            # Check query params
            api_key = connection.query_params.get("api_key")

        if not api_key:
            return None

        user = get_api_key_user(api_key)
        return user

    except Exception as e:
        logger.error(f"Error in api_key_auth: {e}")
        return None


async def flexible_auth(
    connection: ASGIConnection, _: BaseRouteHandler
) -> Optional[User]:
    """Dependency hỗ trợ cả Bearer token và API key."""
    try:
        # Thử Bearer token trước
        user = await optional_auth(connection, _)
        if user:
            return user

        # Thử API key
        user = await api_key_auth(connection, _)
        return user

    except Exception as e:
        logger.error(f"Error in flexible_auth: {e}")
        return None


__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"
