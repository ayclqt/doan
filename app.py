from litestar import Litestar
from litestar.config.compression import CompressionConfig
from litestar.logging import StructLoggingConfig
from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import ScalarRenderPlugin
from litestar.plugins.structlog import StructlogConfig, StructlogPlugin
from litestar_granian import GranianPlugin
from structlog import PrintLoggerFactory, make_filtering_bound_logger
from structlog.dev import ConsoleRenderer, set_exc_info
from structlog.processors import StackInfoRenderer, TimeStamper, add_log_level
from structlog.stdlib import PositionalArgumentsFormatter

from src import config, jwt_auth, routers, redis_user_service
from init_admin_user import main as au
from init_conversation_collections import main as cc

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


async def cleanup_redis(_app):
    """Cleanup Redis connections on app shutdown"""
    await redis_user_service.close()


logging_config = StructLoggingConfig(
    processors=[
        add_log_level,
        set_exc_info,
        PositionalArgumentsFormatter(),
        StackInfoRenderer(),
        TimeStamper(fmt="iso"),
        StackInfoRenderer(),
        ConsoleRenderer(),
    ],
    wrapper_class=make_filtering_bound_logger(
        10 if config.deploy_env in {"dev", "development", "develop", "local"} else 20
    ),
    logger_factory=PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
app = Litestar(  # Cách chạy server: chạy litestar run và server sẽ deploy ở port 8000, không cần dùng python -m
    [routers],
    path=config.prefix,
    on_app_init=[jwt_auth.on_app_init],
    on_startup=[au, cc],
    on_shutdown=[cleanup_redis],
    plugins=[StructlogPlugin(StructlogConfig(logging_config)), GranianPlugin()],
    # middleware=[
    #     LoggingMiddleware,
    # ],
    # cors_config=CORSMiddleware.get_cors_config(),
    compression_config=CompressionConfig(backend="brotli", brotli_gzip_fallback=False),
    openapi_config=OpenAPIConfig(
        title="Chatbot hỗ trợ giới thiệu sản phẩm",
        version="1.0.0",
        description="API cho hệ thống chatbot hỗ trợ tư vấn sản phẩm điện tử sử dụng LangChain và Qdrant",
        render_plugins=[ScalarRenderPlugin()],
    ),
)
