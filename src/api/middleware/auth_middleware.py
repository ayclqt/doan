"""
Auth middleware cho request processing và user context.
"""

from typing import Optional

from litestar import Request
from litestar.middleware.base import AbstractMiddleware
from litestar.types import ASGIApp, Receive, Scope, Send

from ...config import logger
from ..auth.dependencies import get_auth_handler
from ..auth.models import User


class AuthMiddleware(AbstractMiddleware):
    """Middleware để xử lý authentication context."""

    def __init__(self, app: ASGIApp, exclude_paths: list[str] = None):
        """Initialize auth middleware."""
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/schema",
            "/favicon.ico",
            "/api/v1/health",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
        ]
        self.auth_handler = get_auth_handler()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process request with auth context."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope=scope, receive=receive)
        path = request.url.path

        # Skip auth processing for excluded paths
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            await self.app(scope, receive, send)
            return

        # Try to get user from token
        user = await self._get_user_from_request(request)

        # Add user to scope for later use
        scope["user"] = user
        scope["user_id"] = user.id if user else None
        scope["is_authenticated"] = user is not None

        # Log authentication context
        if user:
            logger.debug(
                "Request with authenticated user",
                user_id=user.id,
                username=user.username,
                path=path,
            )
        else:
            logger.debug("Request without authentication", path=path)

        await self.app(scope, receive, send)

    async def _get_user_from_request(self, request: Request) -> Optional[User]:
        """Extract user từ request headers."""
        try:
            # Check Authorization header
            authorization = request.headers.get("Authorization")
            if authorization:
                try:
                    scheme, token = authorization.split()
                    if scheme.lower() == "bearer":
                        user = self.auth_handler.get_current_user_from_token(token)
                        if user:
                            return user
                except ValueError:
                    pass

            # Check API key header
            api_key = request.headers.get("X-API-Key")
            if api_key:
                from ..auth.dependencies import get_api_key_user

                user = get_api_key_user(api_key)
                if user:
                    return user

            # Check API key in query params
            api_key = request.query_params.get("api_key")
            if api_key:
                from ..auth.dependencies import get_api_key_user

                user = get_api_key_user(api_key)
                if user:
                    return user

            return None

        except Exception as e:
            logger.warning(f"Error extracting user from request: {e}")
            return None


__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"
