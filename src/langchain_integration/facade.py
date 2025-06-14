"""
Unified Facade for Product Assistant System
Provides stable API interface that doesn't change when internal implementations change.
"""

from typing import Any, Dict, Iterator, List, Optional
from datetime import datetime

from ..config import logger

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class ProductAssistantFacade:
    """
    Unified facade for all product assistant functionality.

    This facade provides a stable interface for the API layer,
    hiding internal implementation details and ensuring that
    API code doesn't need to change when we modify internal systems.
    """

    def __init__(self):
        """Initialize the facade with clean, working systems."""
        self._agent = None
        self.logger = logger

    def _get_agent(self):
        """Get unified smart agent with order flow capability."""
        if self._agent is None:
            try:
                # Try to load unified smart agent first
                from .unified_smart_agent import get_unified_smart_agent

                self._agent = get_unified_smart_agent(
                    use_llm_intent=True
                )  # Use LLM-enhanced intent analysis
                self.logger.info("UnifiedSmartAgent loaded via facade with LLM intent")
            except Exception as e:
                self.logger.warning(
                    f"Failed to load UnifiedSmartAgent, falling back to ProductIntroductionAgent: {e}"
                )
                try:
                    # Fallback to original product agent
                    from .product_introduction_agent import (
                        get_product_introduction_agent,
                    )

                    self._agent = get_product_introduction_agent()
                    self.logger.info("ProductIntroductionAgent loaded as fallback")
                except Exception as e2:
                    self.logger.error(f"Failed to load fallback agent: {e2}")
                    self._agent = None
        return self._agent

    def get_product_recommendations(
        self, query: str, conversation_history: Optional[List[dict]] = None
    ) -> Dict[str, Any]:
        """
        Get product recommendations with clean, ID-free responses.

        Args:
            query: User query about products
            conversation_history: Previous conversation messages

        Returns:
            Clean product recommendation response
        """
        try:
            agent = self._get_agent()

            if agent:
                # Use clean product introduction agent
                result = agent.process_query(query, conversation_history)

                if result["success"]:
                    return {
                        "response": result["response"],
                        "processing_time": result["processing_time"],
                        "success": True,
                        "method": "clean_agent",
                        "query_type": result.get("query_type", "unknown"),
                    }
                else:
                    self.logger.warning(f"Agent failed: {result.get('error')}")

            # No fallback - clean agent is the primary system
            return {
                "response": "Xin lỗi, hệ thống tư vấn sản phẩm tạm thời không khả dụng. Vui lòng thử lại sau.",
                "processing_time": 0.0,
                "success": False,
                "error": "Clean agent not available",
                "method": "no_fallback",
            }

        except Exception as e:
            self.logger.error(f"Product recommendation failed: {e}")
            return {
                "response": "Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi về sản phẩm. Vui lòng thử lại sau.",
                "processing_time": 0.0,
                "success": False,
                "error": str(e),
                "method": "error",
            }

    def get_product_recommendations_stream(
        self, query: str, conversation_history: Optional[List[dict]] = None
    ) -> Iterator[str]:
        """
        Stream product recommendations with clean, ID-free responses.

        Args:
            query: User query about products
            conversation_history: Previous conversation messages

        Yields:
            Clean product recommendation chunks
        """
        try:
            agent = self._get_agent()

            if agent:
                # Use clean product introduction agent streaming
                try:
                    for chunk in agent.process_query_stream(
                        query, conversation_history
                    ):
                        yield chunk
                    return
                except Exception as e:
                    self.logger.warning(f"Agent streaming failed: {e}")

            # No pipeline fallback - clean agent only
            yield "Xin lỗi, hệ thống tư vấn sản phẩm tạm thời không khả dụng."

        except Exception as e:
            self.logger.error(f"Streaming failed: {e}")
            yield "Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi về sản phẩm."

    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information and status.

        Returns:
            System status and capabilities
        """
        try:
            agent = self._get_agent()

            info = {
                "facade_version": "2.0",
                "clean_agent_available": agent is not None,
                "timestamp": datetime.now().isoformat(),
                "capabilities": [
                    "product_recommendations",
                    "enhanced_search",
                    "smart_deduplication",
                    "conversation_context",
                    "id_cleaning",
                    "professional_responses",
                ],
                "status": "operational" if agent else "degraded",
            }

            if agent:
                try:
                    agent_stats = agent.get_stats()
                    info["agent_stats"] = agent_stats
                except Exception:
                    pass

            return info

        except Exception as e:
            return {
                "facade_version": "2.0",
                "clean_agent_available": False,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }


# Global facade instance
_facade_instance: Optional[ProductAssistantFacade] = None


def get_facade() -> ProductAssistantFacade:
    """Get or create global facade instance."""
    global _facade_instance
    if _facade_instance is None:
        _facade_instance = ProductAssistantFacade()
        logger.info("ProductAssistantFacade v2.0 initialized")
    return _facade_instance


def create_custom_facade(**kwargs) -> ProductAssistantFacade:
    """Create a custom facade with specific parameters."""
    return ProductAssistantFacade(**kwargs)
