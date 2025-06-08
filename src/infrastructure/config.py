"""
Configuration management using Pydantic Settings with functional approach.
"""

import structlog
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from structlog import configure, make_filtering_bound_logger
from structlog.dev import ConsoleRenderer, set_exc_info
from structlog.processors import StackInfoRenderer, TimeStamper, add_log_level
from structlog.stdlib import PositionalArgumentsFormatter

from ..domain.models import (
    LLMConfig,
    VectorStoreConfig,
    EmbeddingConfig,
    WebSearchConfig,
)
from ..core.types import Result

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"

load_dotenv()

class AppSettings(BaseSettings):
    """Application settings using Pydantic BaseSettings."""

    # LLM Configuration
    openai_api_key: str = ""
    openai_base_url: str = "https://api.x.ai/v1"
    llm_model_name: str = "grok-3-mini"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 1024

    # Vector Store Configuration
    qdrant_url: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "product_data"
    vector_size: int = 1024
    distance_metric: str = "cosine"

    # Embedding Configuration
    embedding_model_name: str = "AITeamVN/Vietnamese_Embedding"
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Web Search Configuration
    web_search_enabled: bool = True
    web_search_max_results: int = 5
    web_search_region: str = "vn-vi"
    web_search_safesearch: str = "moderate"
    web_search_timelimit: str = ""
    web_search_backend: str = "auto"
    web_search_similarity_threshold: float = 0.7

    # Data Configuration
    cleaned_data_path: str = "cleaned_data.json"

    # Application Configuration
    deploy_env: str = "dev"
    log_level: str = "INFO"


# Pure functions for configuration creation


def create_llm_config_from_settings(settings: AppSettings) -> LLMConfig:
    """Create LLM configuration from app settings."""
    return LLMConfig(
        model_name=settings.llm_model_name,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )


def create_vector_store_config_from_settings(
    settings: AppSettings,
) -> VectorStoreConfig:
    """Create vector store configuration from app settings."""
    return VectorStoreConfig(
        collection_name=settings.qdrant_collection_name,
        url=settings.qdrant_url,
        port=settings.qdrant_port,
        vector_size=settings.vector_size,
        distance_metric=settings.distance_metric,
    )


def create_embedding_config_from_settings(settings: AppSettings) -> EmbeddingConfig:
    """Create embedding configuration from app settings."""
    return EmbeddingConfig(
        model_name=settings.embedding_model_name,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )


def create_web_search_config_from_settings(settings: AppSettings) -> WebSearchConfig:
    """Create web search configuration from app settings."""
    return WebSearchConfig(
        enabled=settings.web_search_enabled,
        max_results=settings.web_search_max_results,
        region=settings.web_search_region,
        safesearch=settings.web_search_safesearch,
        timelimit=settings.web_search_timelimit
        if settings.web_search_timelimit
        else None,
        backend=settings.web_search_backend,
        similarity_threshold=settings.web_search_similarity_threshold,
    )


def validate_settings(settings: AppSettings) -> Result:
    """Validate application settings."""
    errors = []

    # Validate required fields
    if not settings.openai_api_key:
        errors.append("OpenAI API key is required")

    if not settings.embedding_model_name:
        errors.append("Embedding model name is required")

    if not settings.qdrant_collection_name:
        errors.append("Qdrant collection name is required")

    # Validate ranges
    if not (0.0 <= settings.llm_temperature <= 2.0):
        errors.append("LLM temperature must be between 0.0 and 2.0")

    if settings.llm_max_tokens <= 0:
        errors.append("LLM max tokens must be positive")

    if settings.qdrant_port <= 0 or settings.qdrant_port > 65535:
        errors.append("Qdrant port must be between 1 and 65535")

    if settings.chunk_size <= 0:
        errors.append("Chunk size must be positive")

    if settings.chunk_overlap < 0:
        errors.append("Chunk overlap cannot be negative")

    if settings.chunk_overlap >= settings.chunk_size:
        errors.append("Chunk overlap must be less than chunk size")

    if settings.web_search_max_results <= 0:
        errors.append("Web search max results must be positive")

    if not (0.0 <= settings.web_search_similarity_threshold <= 1.0):
        errors.append("Web search similarity threshold must be between 0.0 and 1.0")

    if errors:
        return Result.failure(ValueError("; ".join(errors)))

    return Result.success(settings)


def setup_logging(settings: AppSettings) -> None:
    """Setup structured logging based on settings."""
    log_level = (
        10
        if settings.deploy_env.lower() in ["dev", "development", "develop", "local"]
        else 20
    )

    configure(
        processors=[
            add_log_level,
            set_exc_info,
            PositionalArgumentsFormatter(),
            StackInfoRenderer(),
            TimeStamper(fmt="iso"),
            ConsoleRenderer(),
        ],
        context_class=dict,
        wrapper_class=make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def load_and_validate_settings() -> Result:
    """Load and validate application settings."""
    # Load environment variables
    load_dotenv()

    # Create settings
    try:
        settings = AppSettings()
    except Exception as e:
        return Result.failure(e)

    # Validate settings
    validation_result = validate_settings(settings)
    if validation_result.is_failure:
        return validation_result

    # Setup logging
    setup_logging(settings)

    return Result.success(settings)


def create_all_configs_from_settings(settings: AppSettings) -> dict:
    """Create all configuration objects from app settings."""
    return {
        "llm": create_llm_config_from_settings(settings),
        "vector_store": create_vector_store_config_from_settings(settings),
        "embedding": create_embedding_config_from_settings(settings),
        "web_search": create_web_search_config_from_settings(settings),
    }


# Global configuration management


class ConfigurationManager:
    """Functional configuration manager."""

    def __init__(self):
        self._settings = None
        self._configs = None
        self._logger = None

    def initialize(self) -> Result:
        """Initialize configuration manager."""
        settings_result = load_and_validate_settings()

        if settings_result.is_failure:
            return settings_result

        self._settings = settings_result.value
        self._configs = create_all_configs_from_settings(self._settings)
        self._logger = structlog.get_logger()

        self._logger.info(
            "Configuration loaded successfully",
            env=self._settings.deploy_env,
            collection=self._settings.qdrant_collection_name,
        )

        return Result.success(self)

    @property
    def settings(self) -> AppSettings:
        """Get application settings."""
        if self._settings is None:
            raise RuntimeError("Configuration not initialized")
        return self._settings

    @property
    def llm_config(self) -> LLMConfig:
        """Get LLM configuration."""
        if self._configs is None:
            raise RuntimeError("Configuration not initialized")
        return self._configs["llm"]

    @property
    def vector_store_config(self) -> VectorStoreConfig:
        """Get vector store configuration."""
        if self._configs is None:
            raise RuntimeError("Configuration not initialized")
        return self._configs["vector_store"]

    @property
    def embedding_config(self) -> EmbeddingConfig:
        """Get embedding configuration."""
        if self._configs is None:
            raise RuntimeError("Configuration not initialized")
        return self._configs["embedding"]

    @property
    def web_search_config(self) -> WebSearchConfig:
        """Get web search configuration."""
        if self._configs is None:
            raise RuntimeError("Configuration not initialized")
        return self._configs["web_search"]

    @property
    def logger(self):
        """Get structured logger."""
        if self._logger is None:
            return structlog.get_logger()
        return self._logger

    def update_web_search_enabled(self, enabled: bool) -> None:
        """Update web search enabled setting."""
        if self._settings is None:
            raise RuntimeError("Configuration not initialized")

        # Create new settings with updated value
        self._settings.web_search_enabled = enabled

        # Recreate web search config
        self._configs["web_search"] = create_web_search_config_from_settings(
            self._settings
        )

        self._logger.info("Web search configuration updated", enabled=enabled)

    def get_config_summary(self) -> dict:
        """Get configuration summary for debugging."""
        if self._settings is None:
            return {"error": "Configuration not initialized"}

        return {
            "llm_model": self._settings.llm_model_name,
            "embedding_model": self._settings.embedding_model_name,
            "vector_store": {
                "url": self._settings.qdrant_url,
                "port": self._settings.qdrant_port,
                "collection": self._settings.qdrant_collection_name,
            },
            "web_search_enabled": self._settings.web_search_enabled,
            "environment": self._settings.deploy_env,
            "data_path": self._settings.cleaned_data_path,
        }


# Global configuration instance
config_manager = ConfigurationManager()


# Convenience functions for backward compatibility
def get_config() -> ConfigurationManager:
    """Get the global configuration manager."""
    return config_manager


def get_logger():
    """Get the global logger."""
    return config_manager.logger


# Factory function for creating configuration manager
def create_config_manager() -> Result:
    """Create and initialize a new configuration manager."""
    manager = ConfigurationManager()
    return manager.initialize()
