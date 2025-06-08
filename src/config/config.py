import secrets

import structlog
from dotenv import load_dotenv
from pydantic_settings import BaseSettings


__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class Config(BaseSettings):
    """Configuration settings for the application."""

    openai_api_key: str = ""
    openai_base_url: str = "https://api.x.ai/v1"

    qdrant_url: str = "localhost"
    qdrant_port: int = 6333
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
    secret_key: str = secrets.token_urlsafe(32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS settings
    cors_allowed_origins: str = "*"

    deploy_env: str = "dev"


load_dotenv()
config = Config()
logger = structlog.get_logger()
logger.debug("Config", config=config)
