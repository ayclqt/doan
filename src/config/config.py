import secrets
import re

import structlog
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import validator

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class Config(BaseSettings):
    """Configuration settings for the application."""

    prefix: str = "/"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.x.ai/v1"

    qdrant_url: str = "localhost"
    qdrant_port: int = 6334  # gRPC API port (only protocol supported)
    qdrant_collection_name: str = "product_data"

    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    redis_url: str = "redis://localhost:6379/"

    embedding_model_name: str = "AITeamVN/Vietnamese_Embedding"

    llm_model_name: str = "grok-3-mini"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 1024

    chunk_size: int = 1000
    chunk_overlap: int = 200

    cleaned_data_path: str = "cleaned_data.json"

    # Web search settings
    web_search_enabled: bool = True
    web_search_max_results: int = 5
    web_search_region: str = "vn-vi"
    web_search_timelimit: str = ""
    web_search_backend: str = "auto"
    web_search_similarity_threshold: float = 0.7

    # JWT and Authentication settings
    jwt_secret: str = secrets.token_urlsafe(32)
    jwt_algorithm: str = "HS256"
    api_user: str = "admin"
    api_pass: str = "admin"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS settings
    cors_allowed_origins: str = "*"

    deploy_env: str = "dev"

    # Shop settings
    shop_name: str = "TechStore Pro"
    shop_phone: str = "0901234567"
    shop_email: str = "contact@techstore.vn"

    @validator("shop_phone")
    def validate_shop_phone(cls, v):
        """Validate Vietnamese phone number format"""
        if not v:
            return v

        # Remove spaces and special characters
        phone_clean = re.sub(r"[\s\-\(\)]", "", v)

        # Vietnamese phone patterns
        patterns = [
            r"^(0[3|5|7|8|9])\d{8}$",  # Mobile: 03x, 05x, 07x, 08x, 09x + 8 digits
            r"^(84[3|5|7|8|9])\d{8}$",  # International: 84 + mobile
            r"^(\+84[3|5|7|8|9])\d{8}$",  # +84 format
        ]

        if not any(re.match(pattern, phone_clean) for pattern in patterns):
            raise ValueError("Shop phone number must be valid Vietnamese phone number")

        return v

    @validator("shop_email")
    def validate_shop_email(cls, v):
        """Validate email format"""
        if not v:
            return v

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v):
            raise ValueError("Shop email must be valid email format")

        return v


load_dotenv()
config = Config()
logger = structlog.get_logger()
logger.debug("Config", config=config)
