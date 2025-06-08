"""
Authentication and authorization module for the API.
"""

from .auth_handler import AuthHandler
from .dependencies import (
    get_current_user,
    require_auth,
    optional_auth,
    get_auth_handler,
    require_admin,
    flexible_auth,
)
from .models import User, UserInDB
from .utils import create_access_token, verify_token, hash_password, verify_password

__all__ = [
    "AuthHandler",
    "get_current_user",
    "require_auth",
    "optional_auth",
    "get_auth_handler",
    "require_admin",
    "flexible_auth",
    "User",
    "UserInDB",
    "create_access_token",
    "verify_token",
    "hash_password",
    "verify_password",
]

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"
