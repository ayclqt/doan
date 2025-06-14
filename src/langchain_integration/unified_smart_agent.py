"""
Unified Smart Agent - Intelligent routing between consultation and order flows.
Combines intent detection with appropriate tool selection for seamless user experience.
"""

import time
from typing import Any, Dict, Iterator, List, Optional
from datetime import datetime

from .order_intent_analyzer import get_order_intent_analyzer
from .llm_intent_analyzer import get_llm_intent_analyzer
from .product_introduction_agent import get_product_introduction_agent
from .simplified_order_handler import SimplifiedOrderHandler

from ..config import logger

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class UnifiedSmartAgent:
    """
    Unified Smart Agent that intelligently routes between consultation and order flows.

    Uses intent analysis to determine whether users want product information or to place orders,
    then executes the appropriate flow with the right tools.
    """

    def __init__(self, use_llm_intent: bool = False, enable_streaming: bool = True):
        """
        Initialize the unified smart agent.

        Args:
            use_llm_intent: Whether to use LLM-enhanced intent analysis
            enable_streaming: Whether to support streaming responses
        """
        # Initialize intent analyzers
        self.rule_intent_analyzer = get_order_intent_analyzer()
        self.llm_intent_analyzer = get_llm_intent_analyzer() if use_llm_intent else None
        self.use_llm_intent = use_llm_intent

        # Initialize product agent for consultation flow
        self.product_agent = get_product_introduction_agent()

        # Initialize simplified order handler for order flow
        self.order_handler = SimplifiedOrderHandler()

        self.enable_streaming = enable_streaming
        self.logger = logger

        # Performance tracking
        self.stats = {
            "total_queries": 0,
            "consultation_queries": 0,
            "order_queries": 0,
            "contact_responses": 0,
            "intent_detection_accuracy": 0.0,
            "average_response_time": 0.0,
        }

    def process_query(
        self, message: str, conversation_history: Optional[List[dict]] = None
    ) -> Dict[str, Any]:
        """
        Process user query with intelligent routing.

        Args:
            message: User's current message
            conversation_history: Previous conversation exchanges

        Returns:
            Response with appropriate flow handling
        """
        start_time = time.time()
        self.stats["total_queries"] += 1

        try:
            # Step 1: Analyze intent
            intent_result = self._analyze_intent(message, conversation_history)

            # Step 2: Route to appropriate flow
            if intent_result["intent_type"] == "ORDER_PROCESSING":
                self.stats["order_queries"] += 1
                response_result = self._handle_order_flow(
                    message, conversation_history, intent_result
                )
            else:
                self.stats["consultation_queries"] += 1
                response_result = self._handle_consultation_flow(
                    message, conversation_history
                )

            # Step 3: Add metadata and performance tracking
            processing_time = time.time() - start_time
            self._update_stats(processing_time)

            response_result.update(
                {
                    "processing_time": processing_time,
                    "intent_analysis": intent_result,
                    "agent_type": "unified_smart_agent",
                    "timestamp": datetime.now().isoformat(),
                }
            )

            self.logger.info(
                f"Query processed: {intent_result['intent_type']} "
                f"(confidence: {intent_result['confidence']:.2f}, time: {processing_time:.2f}s)"
            )

            return response_result

        except Exception as e:
            self.logger.error(f"Unified agent processing failed: {e}")
            processing_time = time.time() - start_time

            return {
                "response": "Xin lỗi, đã xảy ra lỗi khi xử lý yêu cầu. Vui lòng thử lại sau.",
                "success": False,
                "error": str(e),
                "processing_time": processing_time,
                "agent_type": "unified_smart_agent",
            }

    def process_query_stream(
        self, message: str, conversation_history: Optional[List[dict]] = None
    ) -> Iterator[str]:
        """
        Process query with streaming support.

        Args:
            message: User's current message
            conversation_history: Previous conversation exchanges

        Yields:
            Progressive response chunks
        """
        if not self.enable_streaming:
            # Fallback to non-streaming
            result = self.process_query(message, conversation_history)
            yield result.get("response", "")
            return

        start_time = time.time()
        self.stats["total_queries"] += 1

        try:
            # Quick intent analysis
            intent_result = self._analyze_intent(message, conversation_history)

            if intent_result["intent_type"] == "ORDER_PROCESSING":
                self.stats["order_queries"] += 1
                # Order flow - typically non-streaming tool calls
                response_result = self._handle_order_flow(
                    message, conversation_history, intent_result
                )
                yield response_result.get("response", "")
            else:
                self.stats["consultation_queries"] += 1
                # Consultation flow - use streaming from product agent
                yield from self.product_agent.process_query_stream(
                    message, conversation_history
                )

            processing_time = time.time() - start_time
            self._update_stats(processing_time)

        except Exception as e:
            self.logger.error(f"Streaming processing failed: {e}")
            yield "Xin lỗi, đã xảy ra lỗi khi xử lý yêu cầu."

    def _analyze_intent(
        self, message: str, conversation_history: Optional[List[dict]] = None
    ) -> Dict:
        """Analyze user intent using LLM analyzer."""
        if self.llm_intent_analyzer:
            return self.llm_intent_analyzer.analyze_intent(
                message, conversation_history
            )
        else:
            self.logger.warning(
                "LLM Intent Analyzer not initialized, falling back to rule-based analyzer."
            )
            return self.rule_intent_analyzer.analyze_intent(
                message, conversation_history
            )

    def _handle_consultation_flow(
        self, message: str, conversation_history: Optional[List[dict]] = None
    ) -> Dict:
        """Handle product consultation flow."""
        try:
            result = self.product_agent.process_query(message, conversation_history)
            result["flow_type"] = "consultation"
            return result
        except Exception as e:
            self.logger.error(f"Consultation flow failed: {e}")
            return {
                "response": "Xin lỗi, đã xảy ra lỗi khi tư vấn sản phẩm. Vui lòng thử lại sau.",
                "success": False,
                "flow_type": "consultation",
                "error": str(e),
            }

    def _handle_order_flow(
        self,
        message: str,
        conversation_history: Optional[List[dict]] = None,
        intent_result: Optional[Dict] = None,
    ) -> Dict:
        """Handle order processing flow using SimplifiedOrderHandler."""
        try:
            # Extract product from message or context
            product = self._extract_product_from_context(message, conversation_history)

            if not product:
                return {
                    "response": "Em cần biết anh/chị muốn đặt sản phẩm gì ạ? Vui lòng cho em biết tên sản phẩm cụ thể.",
                    "success": True,
                    "flow_type": "order",
                    "order_state": "NEED_PRODUCT",
                }

            # Use SimplifiedOrderHandler to process order intent
            response = self.order_handler.handle_order_intent(product)

            # Track contact response
            self.stats["contact_responses"] += 1

            return {
                "response": response,
                "success": True,
                "flow_type": "order",
                "order_state": "CONTACT_PROVIDED",
                "product": product,
            }

        except Exception as e:
            self.logger.error(f"Order flow failed: {e}")
            return {
                "response": "Xin lỗi, đã xảy ra lỗi khi xử lý đơn hàng. Vui lòng thử lại sau.",
                "success": False,
                "flow_type": "order",
                "order_state": "error",
                "error": str(e),
            }

    def _extract_product_from_context(
        self, message: str, conversation_history: Optional[List[dict]] = None
    ) -> Optional[str]:
        """Extract product from message or conversation context using LLM analyzer if available."""
        analyzer = (
            self.llm_intent_analyzer
            if self.llm_intent_analyzer
            else self.rule_intent_analyzer
        )
        return analyzer.get_product_from_context(message, conversation_history)

    def _update_stats(self, processing_time: float):
        """Update performance statistics."""
        current_avg = self.stats["average_response_time"]
        total_queries = self.stats["total_queries"]
        self.stats["average_response_time"] = (
            current_avg * (total_queries - 1) + processing_time
        ) / total_queries

    def get_stats(self) -> Dict[str, Any]:
        """Get agent performance statistics."""
        return {
            "performance": self.stats.copy(),
            "intent_analyzer": "llm" if self.use_llm_intent else "rule_based",
            "streaming_enabled": self.enable_streaming,
            "agent_status": "operational",
            "timestamp": datetime.now().isoformat(),
        }

    def reset_stats(self):
        """Reset performance statistics."""
        self.stats = {
            "total_queries": 0,
            "consultation_queries": 0,
            "order_queries": 0,
            "contact_responses": 0,
            "intent_detection_accuracy": 0.0,
            "average_response_time": 0.0,
        }


# Global agent instance
_unified_agent_instance: Optional[UnifiedSmartAgent] = None


def get_unified_smart_agent(use_llm_intent: bool = True) -> UnifiedSmartAgent:
    """Get or create global unified smart agent instance with LLM intent enabled by default."""
    global _unified_agent_instance
    if _unified_agent_instance is None:
        _unified_agent_instance = UnifiedSmartAgent(use_llm_intent=use_llm_intent)
        logger.info(f"Unified Smart Agent initialized (LLM intent: {use_llm_intent})")
    return _unified_agent_instance
