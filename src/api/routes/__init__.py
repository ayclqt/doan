"""
Routes module for the API.
"""

from .auth import auth_router
from .chat import chat_router
from .health import health_router

__all__ = [
    "auth_router",
    "chat_router",
    "health_router",
]

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"
