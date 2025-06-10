"""
CORS middleware cho cross-origin requests.
"""

from litestar.config.cors import CORSConfig

from ...config import config


__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class CORSMiddleware:
    """CORS middleware configuration cho API."""

    @staticmethod
    def get_cors_config() -> CORSConfig:
        """Get CORS configuration."""

        # Development settings - cho phép tất cả origins
        if config.deploy_env in ["dev", "development", "develop", "local"]:
            return CORSConfig(
                allow_origins=["*"],
                allow_methods=["*"],
                allow_headers=["*"],
                allow_credentials=True,
                expose_headers=["X-Request-ID", "X-Response-Time", "X-Total-Count"],
                max_age=86400,  # 24 hours
            )

        # Production settings - restrictive
        allowed_origins = [
            "https://yourapp.com",
            "https://www.yourapp.com",
            "https://admin.yourapp.com",
        ]

        # Add custom origins từ config nếu có
        if hasattr(config, "cors_allowed_origins") and config.cors_allowed_origins:
            if isinstance(config.cors_allowed_origins, str):
                allowed_origins.extend(config.cors_allowed_origins.split(","))
            elif isinstance(config.cors_allowed_origins, list):
                allowed_origins.extend(config.cors_allowed_origins)

        return CORSConfig(
            allow_origins=allowed_origins,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=[
                "Accept",
                "Accept-Language",
                "Content-Language",
                "Content-Type",
                "Authorization",
                "X-API-Key",
                "X-Request-ID",
                "X-Requested-With",
            ],
            allow_credentials=True,
            expose_headers=[
                "X-Request-ID",
                "X-Response-Time",
                "X-Total-Count",
                "X-Rate-Limit-Remaining",
                "X-Rate-Limit-Reset",
            ],
            max_age=3600,  # 1 hour
        )
