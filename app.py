import taskiq_litestar
from litestar import Litestar
from litestar.config.compression import CompressionConfig
from litestar.logging import StructLoggingConfig
from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import ScalarRenderPlugin
from litestar.plugins.structlog import StructlogPlugin, StructlogConfig
from litestar_granian import GranianPlugin
from taskiq_aio_pika import AioPikaBroker
from structlog import make_filtering_bound_logger, PrintLoggerFactory
from structlog.dev import ConsoleRenderer, set_exc_info
from structlog.processors import StackInfoRenderer, TimeStamper, add_log_level
from structlog.stdlib import PositionalArgumentsFormatter
from taskiq_redis import RedisAsyncResultBackend

from src import config, auth_router, chat_router, health_router

result_backend = RedisAsyncResultBackend(config.redis_url)
broker = AioPikaBroker(config.rabbitmq_url).with_result_backend(result_backend)
taskiq_litestar.init(broker, "app:app")

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
        10 if config.deploy_env in ["dev", "development", "develop", "local"] else 20
    ),
    logger_factory=PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
app = Litestar(
    route_handlers=[
        auth_router,
        chat_router,
        health_router,
    ],
    plugins=[StructlogPlugin(StructlogConfig(logging_config))],
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
    # debug=config.deploy_env in ["dev", "development", "develop", "local"],
)
