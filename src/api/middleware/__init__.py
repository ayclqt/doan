"""
Middleware module for the API.
"""

from .cors_middleware import CORSMiddleware
from .logging_middleware import LoggingMiddleware
from .rate_limit_middleware import RateLimitMiddleware

__all__ = [
    "CORSMiddleware",
    "LoggingMiddleware",
    "RateLimitMiddleware",
]

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"
