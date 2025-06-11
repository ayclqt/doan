"""
Health check routes cho API monitoring.
"""

from datetime import datetime, timezone
from typing import Dict

from litestar import Controller, get
from litestar.status_codes import HTTP_200_OK

from ...config import config
from ..schemas import HealthResponse

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class Health(Controller):
    """Health check controller for the API."""

    path = "/health"
    tags = ["Health"]

    @get("/", status_code=HTTP_200_OK)
    async def health_check(self) -> HealthResponse:
        """Health check endpoint."""
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(timezone.utc).isoformat(),
            version="1.0.0",
            services={
                "api": "healthy",
                "database": "healthy",  # Placeholder
                "vector_store": "healthy",  # Placeholder
                "llm": "healthy",  # Placeholder
            },
        )

    @get("/detailed", status_code=HTTP_200_OK)
    async def detailed_health_check(self) -> Dict:
        """Detailed health check với thông tin chi tiết."""
        try:
            # Kiểm tra các service components
            services_status = {}

            # Check LangChain pipeline
            try:
                from ...langchain_integration import LangchainPipeline, VectorStore

                vector_store = VectorStore()
                services_status["vector_store"] = "healthy"

                # Quick test
                if LangchainPipeline(vector_store=vector_store):
                    services_status["langchain_pipeline"] = "healthy"
            except Exception as e:
                services_status["vector_store"] = f"unhealthy: {e!s}"
                services_status["langchain_pipeline"] = f"unhealthy: {e!s}"

            # Check configuration
            services_status["config"] = (
                "healthy" if hasattr(config, "openai_api_key") else "missing config"
            )

            overall_status = (
                "healthy"
                if all(status == "healthy" for status in services_status.values())
                else "degraded"
            )

            return {
                "status": overall_status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "environment": config.deploy_env,
                "services": services_status,
                # "uptime": "N/A",  # Có thể implement sau
                # "memory_usage": "N/A",  # Có thể implement sau
                # "system_info": {
                #     "python_version": "3.11+",
                #     "litestar_version": "2.x",
                #     "langchain_version": "0.x",
                # },
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "version": "1.0.0",
            }

    @get("/ready", status_code=HTTP_200_OK)
    async def readiness_check(self) -> Dict:
        """Readiness check cho Kubernetes."""
        try:
            # Kiểm tra các dependency cần thiết
            ready = True
            checks = {}

            # Check vector store
            try:
                from ...langchain_integration import VectorStore

                vector_store = VectorStore()
                vector_store.initialize_vectorstore()
                checks["vector_store"] = "ready"
            except Exception as e:
                checks["vector_store"] = f"not ready: {e!s}"
                ready = False

            # Check LLM connection
            try:
                # Không tạo pipeline thật để tránh tốn tài nguyên
                checks["llm_config"] = (
                    "ready" if hasattr(config, "openai_api_key") else "not ready"
                )
            except Exception as e:
                checks["llm_config"] = f"not ready: {e!s}"
                ready = False

            return {
                "ready": ready,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "checks": checks,
            }

        except Exception as e:
            return {
                "ready": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
            }

    @get("/live", status_code=HTTP_200_OK)
    async def liveness_check(self) -> Dict:
        """Liveness check cho Kubernetes."""
        return {"alive": True, "timestamp": datetime.now(timezone.utc).isoformat()}
