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
            version="2.0.0",
            services={
                "api": "healthy",
                "clean_facade": "healthy",
                "vector_store": "healthy",
                "llm": "healthy",
            },
        )

    @get("/detailed", status_code=HTTP_200_OK)
    async def detailed_health_check(self) -> Dict:
        """Detailed health check với thông tin chi tiết."""
        try:
            # Kiểm tra các service components
            services_status = {}

            # Check Clean Facade System
            try:
                from ...langchain_integration import get_facade, VectorStore

                vector_store = VectorStore()
                services_status["vector_store"] = "healthy"

                # Quick test facade
                facade = get_facade()
                if facade:
                    services_status["product_assistant_facade"] = "healthy"
                    system_info = facade.get_system_info()
                    services_status["clean_agent"] = (
                        "healthy"
                        if system_info["clean_agent_available"]
                        else "degraded"
                    )
                    services_status["facade_version"] = system_info.get(
                        "facade_version", "unknown"
                    )
            except Exception as e:
                services_status["vector_store"] = f"unhealthy: {e!s}"
                services_status["product_assistant_facade"] = f"unhealthy: {e!s}"

            # Check configuration
            services_status["config"] = (
                "healthy" if hasattr(config, "openai_api_key") else "missing config"
            )

            overall_status = (
                "healthy"
                if all(
                    "unhealthy" not in str(status)
                    for status in services_status.values()
                )
                else "degraded"
            )

            return {
                "status": overall_status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "2.0.0",
                "environment": config.deploy_env,
                "services": services_status,
                "migration_status": "phase_3_cleanup_in_progress",
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "version": "2.0.0",
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

            # Check Facade System
            try:
                from ...langchain_integration import get_facade

                facade = get_facade()
                if facade:
                    system_info = facade.get_system_info()
                    checks["clean_agent"] = (
                        "ready" if system_info["clean_agent_available"] else "not ready"
                    )
                    if not system_info["clean_agent_available"]:
                        ready = False
                else:
                    checks["facade"] = "not ready"
                    ready = False
            except Exception as e:
                checks["facade"] = f"not ready: {e!s}"
                ready = False

            # Check LLM config
            try:
                checks["llm_config"] = (
                    "ready" if hasattr(config, "openai_api_key") else "not ready"
                )
                if not hasattr(config, "openai_api_key"):
                    ready = False
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
