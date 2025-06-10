"""
Common schemas cho API responses và pagination.
"""

from typing import Any, Dict, List, Optional

from msgspec import Struct


__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class ErrorResponse(Struct):
    """Schema cho error response."""

    error: bool = True
    message: str = ""
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class SuccessResponse(Struct):
    """Schema cho success response."""

    success: bool = True
    message: str = ""
    data: Optional[Dict[str, Any]] = None


class PaginationParams(Struct):
    """Schema cho pagination parameters."""

    page: int = 1
    limit: int = 20
    offset: Optional[int] = None


class PaginationResponse(Struct):
    """Schema cho paginated response."""

    items: List[Dict[str, Any]]
    total: int
    page: int
    limit: int
    has_next: bool
    has_prev: bool


class HealthResponse(Struct):
    """Schema cho health check response."""

    status: str
    timestamp: str
    version: str
    services: Dict[str, str]
