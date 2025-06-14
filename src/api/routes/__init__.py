"""
Routes module for the API.
"""

from litestar import Router

from .auth import Auth
from .chat import Chat
from .health import Health

routers = Router(path="/", route_handlers=[Auth, Chat, Health])

__all__ = ["routers"]

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"
