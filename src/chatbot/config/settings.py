"""
Module cấu hình của ứng dụng sử dụng pydantic-settings.
"""

import os

from pydantic import SecretStr
from pydantic_settings import BaseSettings

import structlog
from structlog import configure, make_filtering_bound_logger
from structlog.dev import ConsoleRenderer, set_exc_info
from structlog.processors import StackInfoRenderer, TimeStamper, add_log_level
from structlog.stdlib import PositionalArgumentsFormatter

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__license__ = "MIT"
__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"

class Settings(BaseSettings):
    """Cấu hình chính của ứng dụng."""
    
    # Cấu hình chung của ứng dụng
    app_name: str = "Product Chatbot"
    debug: bool = True
    
    # Cấu hình cho ChromaDB
    chroma_db_directory: str = ".chroma_db" # Thư mục lưu trữ ChromaDB
    collection_name: str = "product_info" # Tên collection trong ChromaDB
    
    # Cấu hình LLM (OpenAI Compatible)
    openai_api_base: str = "https://api.openai.com/v1" # Địa chỉ API của OpenAI
    openai_api_key: SecretStr = "sk-proj-xxxxxxxxxxxxxxxxxxx-xxxxxxxxxxxxxxxxxx" # OpenAI API key
    model_name: str = "gpt-3.5-turbo" # Model của OpenAI
    temperature: float = 0.7 # Nhiệt độ cho model
    
    # Cấu hình Embedding
    embedding_model: str = "text-embedding-3-small" # Model embedding


# Cấu hình logging
configure(
    processors=[
        add_log_level,
        set_exc_info,
        PositionalArgumentsFormatter(),
        StackInfoRenderer(),
        TimeStamper(fmt="iso"),
        StackInfoRenderer(),
        ConsoleRenderer(),
    ],
    context_class=dict,
    wrapper_class=make_filtering_bound_logger(
        10
        if os.getenv("DEPLOY_ENV") in ["dev", "development", "develop", "local"]
        else 20
    ),
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

# Khởi tạo logger và settings
logger = structlog.get_logger()
settings = Settings()