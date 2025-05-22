import structlog
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from structlog import configure, make_filtering_bound_logger
from structlog.dev import ConsoleRenderer, set_exc_info
from structlog.processors import StackInfoRenderer, TimeStamper, add_log_level
from structlog.stdlib import PositionalArgumentsFormatter


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

    embedding_model_name: str = "AITeamVN/Vietnamese_Embedding"

    llm_model_name: str = "grok-3-mini"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 1024

    chunk_size: int = 1000
    chunk_overlap: int = 200

    cleaned_data_path: str = "cleaned_data.json"

    deploy_env: str = "dev"


load_dotenv()
config = Config()
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
        10 if config.deploy_env in ["dev", "development", "develop", "local"] else 20
    ),
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()
logger.debug("Config", config=config)
