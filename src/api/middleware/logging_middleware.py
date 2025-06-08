"""
Logging middleware cho request/response logging.
"""

import time
import uuid

from litestar import Request
from litestar.middleware.base import AbstractMiddleware
from litestar.types import ASGIApp, Receive, Scope, Send

from ...config import logger


class LoggingMiddleware(AbstractMiddleware):
    """Middleware để log requests và responses."""

    def __init__(self, app: ASGIApp, exclude_paths: list[str] = None):
        """Initialize logging middleware."""
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/schema",
            "/favicon.ico",
        ]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process request and response logging."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Generate request ID
        request_id = str(uuid.uuid4())

        # Get request info
        request = Request(scope=scope, receive=receive)
        path = request.url.path
        method = request.method

        # Skip logging for excluded paths
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            await self.app(scope, receive, send)
            return

        # Add request ID to scope
        scope["request_id"] = request_id

        # Log request start
        start_time = time.time()

        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        logger.info(
            "Request started",
            request_id=request_id,
            method=method,
            path=path,
            client_ip=client_ip,
            user_agent=user_agent,
            query_params=dict(request.query_params) if request.query_params else None,
        )

        # Capture response
        response_captured = {"status_code": None, "headers": None}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                response_captured["status_code"] = message["status"]
                response_captured["headers"] = dict(message.get("headers", []))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)

            # Log successful response
            end_time = time.time()
            duration = end_time - start_time

            logger.info(
                "Request completed",
                request_id=request_id,
                method=method,
                path=path,
                status_code=response_captured["status_code"],
                duration_ms=round(duration * 1000, 2),
                client_ip=client_ip,
            )

        except Exception as e:
            # Log error
            end_time = time.time()
            duration = end_time - start_time

            logger.error(
                "Request failed",
                request_id=request_id,
                method=method,
                path=path,
                error=str(e),
                duration_ms=round(duration * 1000, 2),
                client_ip=client_ip,
            )
            raise

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address từ request."""
        # Kiểm tra các headers phổ biến cho real IP
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Lấy IP đầu tiên nếu có nhiều
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fallback to client IP từ scope
        client = request.scope.get("client")
        if client:
            return client[0]

        return "unknown"


__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"
