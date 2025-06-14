"""
Rate limiting middleware cho API protection.
"""

import time
from collections import defaultdict, deque
from typing import Callable, Dict, Optional

from litestar import Request, Response
from litestar.exceptions import HTTPException
from litestar.middleware.base import AbstractMiddleware
from litestar.status_codes import HTTP_429_TOO_MANY_REQUESTS
from litestar.types import ASGIApp, Receive, Scope, Send

from ...config import logger


__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class RateLimitMiddleware(AbstractMiddleware):
    """Rate limiting middleware với sliding window algorithm."""

    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_limit: int = 10,
        exclude_paths: list[str] = None,
        key_func: Optional[Callable[[Request], str]] = None,
    ):
        """Initialize rate limit middleware."""
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit
        self.exclude_paths = exclude_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/schema",
            "/favicon.ico",
        ]
        self.key_func = key_func or self._default_key_func

        # Storage cho rate limiting
        self._minute_windows: Dict[str, deque] = defaultdict(deque)
        self._hour_windows: Dict[str, deque] = defaultdict(deque)
        self._burst_windows: Dict[str, deque] = defaultdict(deque)

        # Cleanup interval
        self._last_cleanup = time.time()
        self._cleanup_interval = 60  # 1 minute

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process request với rate limiting."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope=scope, receive=receive)
        path = request.url.path

        # Skip rate limiting for excluded paths
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            await self.app(scope, receive, send)
            return

        # Get client key
        client_key = self.key_func(request)

        # Cleanup old entries periodically
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            self._cleanup_old_entries(current_time)
            self._last_cleanup = current_time

        # Check rate limits
        try:
            self._check_rate_limits(client_key, current_time)
        except HTTPException:
            # Send rate limit exceeded response
            response = Response(
                content={
                    "error": True,
                    "message": "Rate limit exceeded",
                    "retry_after": self._get_retry_after(client_key, current_time),
                },
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                headers={
                    "Retry-After": str(self._get_retry_after(client_key, current_time)),
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(current_time + 60)),
                },
            )

            await response(scope, receive, send)
            return

        # Record the request
        self._record_request(client_key, current_time)

        # Add rate limit headers to response
        remaining = self._get_remaining_requests(client_key, current_time)

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                headers.update(
                    {
                        b"X-RateLimit-Limit": str(self.requests_per_minute).encode(),
                        b"X-RateLimit-Remaining": str(remaining).encode(),
                        b"X-RateLimit-Reset": str(int(current_time + 60)).encode(),
                    }
                )
                message["headers"] = list(headers.items())
            await send(message)

        await self.app(scope, receive, send_wrapper)

    def _default_key_func(self, request: Request) -> str:
        """Default function để tạo client key."""
        # Ưu tiên user ID nếu có authentication
        user_id = getattr(request.scope.get("user"), "id", None)
        if user_id:
            return f"user:{user_id}"

        # Fallback to IP address
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}"

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fallback to client from scope
        client = request.scope.get("client")
        if client:
            return client[0]

        return "unknown"

    def _check_rate_limits(self, client_key: str, current_time: float) -> None:
        """Kiểm tra rate limits cho client."""
        # Check burst limit (last 10 seconds)
        burst_window = self._burst_windows[client_key]
        burst_cutoff = current_time - 10
        while burst_window and burst_window[0] < burst_cutoff:
            burst_window.popleft()

        if len(burst_window) >= self.burst_limit:
            logger.warning(f"Burst rate limit exceeded for {client_key}")
            raise HTTPException(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                detail="Burst rate limit exceeded",
            )

        # Check minute limit
        minute_window = self._minute_windows[client_key]
        minute_cutoff = current_time - 60
        while minute_window and minute_window[0] < minute_cutoff:
            minute_window.popleft()

        if len(minute_window) >= self.requests_per_minute:
            logger.warning(f"Minute rate limit exceeded for {client_key}")
            raise HTTPException(
                status_code=HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
            )

        # Check hour limit
        hour_window = self._hour_windows[client_key]
        hour_cutoff = current_time - 3600
        while hour_window and hour_window[0] < hour_cutoff:
            hour_window.popleft()

        if len(hour_window) >= self.requests_per_hour:
            logger.warning(f"Hour rate limit exceeded for {client_key}")
            raise HTTPException(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                detail="Hourly rate limit exceeded",
            )

    def _record_request(self, client_key: str, current_time: float) -> None:
        """Record request timestamp."""
        self._burst_windows[client_key].append(current_time)
        self._minute_windows[client_key].append(current_time)
        self._hour_windows[client_key].append(current_time)

    def _get_remaining_requests(self, client_key: str, current_time: float) -> int:
        """Get số requests còn lại trong minute window."""
        minute_window = self._minute_windows[client_key]
        minute_cutoff = current_time - 60

        # Count requests trong minute window
        valid_requests = sum(
            1 for timestamp in minute_window if timestamp >= minute_cutoff
        )
        return max(0, self.requests_per_minute - valid_requests)

    def _get_retry_after(self, client_key: str, current_time: float) -> int:
        """Get retry after seconds."""
        minute_window = self._minute_windows[client_key]
        if not minute_window:
            return 1

        # Tìm request cũ nhất trong window
        oldest_request = minute_window[0]
        retry_after = int(oldest_request + 60 - current_time)
        return max(1, retry_after)

    def _cleanup_old_entries(self, current_time: float) -> None:
        """Cleanup old entries để tiết kiệm memory."""
        keys_to_remove = []

        # Cleanup minute windows
        for client_key, window in self._minute_windows.items():
            minute_cutoff = current_time - 60
            while window and window[0] < minute_cutoff:
                window.popleft()
            if not window:
                keys_to_remove.append(client_key)

        for key in keys_to_remove:
            del self._minute_windows[key]

        # Cleanup hour windows
        keys_to_remove = []
        for client_key, window in self._hour_windows.items():
            hour_cutoff = current_time - 3600
            while window and window[0] < hour_cutoff:
                window.popleft()
            if not window:
                keys_to_remove.append(client_key)

        for key in keys_to_remove:
            del self._hour_windows[key]

        # Cleanup burst windows
        keys_to_remove = []
        for client_key, window in self._burst_windows.items():
            burst_cutoff = current_time - 10
            while window and window[0] < burst_cutoff:
                window.popleft()
            if not window:
                keys_to_remove.append(client_key)

        for key in keys_to_remove:
            del self._burst_windows[key]

        logger.debug(
            f"Rate limit cleanup completed. Active clients: {len(self._minute_windows)}"
        )


class APIKeyRateLimitMiddleware(RateLimitMiddleware):
    """Rate limiting với different limits cho API keys."""

    def __init__(self, app: ASGIApp, **kwargs):
        super().__init__(app, **kwargs)
        # API keys có higher limits
        self.api_key_requests_per_minute = kwargs.get(
            "api_key_requests_per_minute", 300
        )
        self.api_key_requests_per_hour = kwargs.get("api_key_requests_per_hour", 10000)

    def _check_rate_limits(self, client_key: str, current_time: float) -> None:
        """Override để áp dụng different limits cho API keys."""
        # Check if this is an API key user
        if client_key.startswith("user:"):
            # Use higher limits for authenticated users
            original_minute_limit = self.requests_per_minute
            original_hour_limit = self.requests_per_hour

            self.requests_per_minute = self.api_key_requests_per_minute
            self.requests_per_hour = self.api_key_requests_per_hour

            try:
                super()._check_rate_limits(client_key, current_time)
            finally:
                # Restore original limits
                self.requests_per_minute = original_minute_limit
                self.requests_per_hour = original_hour_limit
        else:
            # Use default limits for IP-based requests
            super()._check_rate_limits(client_key, current_time)
