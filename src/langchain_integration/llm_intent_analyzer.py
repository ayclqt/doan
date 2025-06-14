"""
LLM-Enhanced Order Intent Analyzer.
Combines rule-based scoring with LLM contextual understanding for more accurate intent detection.
"""

import json
import time
from typing import Dict, List, Optional
from datetime import datetime

from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from ..config import config, logger
from .order_intent_analyzer import OrderIntentAnalyzer

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class LLMIntentAnalyzer:
    """
    LLM-enhanced intent analyzer that combines rule-based scoring with contextual understanding.

    Uses LLM to analyze complex conversational patterns that rule-based systems might miss,
    while maintaining fast rule-based scoring for clear-cut cases.
    """

    def __init__(
        self, use_llm_fallback: bool = True, llm_confidence_threshold: float = 0.3
    ):
        """
        Initialize the LLM-enhanced intent analyzer.

        Args:
            use_llm_fallback: Whether to use LLM analysis for borderline cases
            llm_confidence_threshold: Threshold below which to trigger LLM analysis
        """
        self.rule_analyzer = OrderIntentAnalyzer()
        self.use_llm_fallback = use_llm_fallback
        self.llm_confidence_threshold = llm_confidence_threshold

        if use_llm_fallback:
            self.llm = ChatOpenAI(
                model=config.llm_model_name,
                temperature=0.1,  # Low temperature for consistent decisions
                api_key=config.openai_api_key,
                base_url=config.openai_base_url,
                streaming=False,  # Disable streaming for intent analysis
            )

            self.intent_prompt = self._create_intent_prompt()
            self.intent_chain = self.intent_prompt | self.llm | StrOutputParser()
            self.max_retries = 2  # Maximum number of retries for failed API calls

    def _create_intent_prompt(self) -> ChatPromptTemplate:
        """Create LLM prompt for intent analysis."""
        system_template = """
        Bạn là chuyên gia phân tích ý định khách hàng trong bán hàng điện tử.

        NHIỆM VỤ: Phân tích xem khách hàng có ý định ĐẶT HÀNG hay chỉ TƯ VẤN.

        CÁC DẤU HIỆU ĐẶT HÀNG:
        - Từ khóa rõ ràng: "đặt hàng", "mua", "order"
        - Hỏi tồn kho: "còn hàng không", "có hàng không"
        - Hỏi giá khi đã biết sản phẩm cụ thể
        - Tham chiếu đến sản phẩm đã thảo luận: "cái này", "điện thoại trên"
        - Hỏi lại về cùng sản phẩm nhiều lần

        CÁC DẤU HIỆU TƯ VẤN:
        - Hỏi so sánh chung: "điện thoại nào tốt"
        - Xin tư vấn: "nên chọn gì", "gợi ý"
        - Hỏi thông số kỹ thuật tổng quát
        - Chưa có sản phẩm cụ thể trong đầu

        NGỮ CẢNH:
        Tin nhắn hiện tại: {current_message}
        Lịch sử cuộc trò chuyện: {conversation_history}

        Trả lời JSON:
        {{
            "intent": "ORDER" hoặc "CONSULTATION",
            "confidence": 0.0-1.0,
            "reasoning": "giải thích ngắn gọn",
            "key_signals": ["tín hiệu chính đã phát hiện"]
        }}
        """

        return ChatPromptTemplate.from_messages(
            [
                ("system", system_template),
                ("human", "Phân tích ý định của tin nhắn này."),
            ]
        )

    def analyze_intent(
        self, message: str, conversation_history: Optional[List[dict]] = None
    ) -> Dict:
        """
        Analyze intent using LLM-first approach with rule-based context.

        Args:
            message: User's current message
            conversation_history: List of previous conversation exchanges

        Returns:
            Dict containing comprehensive intent analysis
        """
        # Step 1: Get rule-based analysis for context/scoring
        rule_result = self.rule_analyzer.analyze_intent(message, conversation_history)

        # Step 2: ALWAYS use LLM analysis when available
        if self.use_llm_fallback:
            try:
                llm_result = self._get_llm_analysis(message, conversation_history)
                return self._combine_analyses(rule_result, llm_result, message)
            except Exception as e:
                logger.warning(f"LLM analysis failed, using rule-based result: {e}")
                return self._format_rule_result(rule_result, "llm_failed")
        else:
            return self._format_rule_result(rule_result, "rule_only")

    def _get_llm_analysis(
        self, message: str, conversation_history: Optional[List[dict]]
    ) -> Dict:
        """Get LLM analysis for the message with enhanced error handling and retry logic."""
        # Format conversation history for LLM
        history_text = self._format_history_for_llm(conversation_history)

        llm_input = {"current_message": message, "conversation_history": history_text}

        logger.debug(
            f"LLM analysis input: message='{message[:50]}...', history_length={len(conversation_history) if conversation_history else 0}"
        )

        # Retry logic for API calls
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.intent_chain.invoke(llm_input)

                # Validate response before parsing
                if not isinstance(response, str):
                    error_msg = f"LLM returned invalid response type: {type(response)}"
                    logger.warning(error_msg)
                    raise ValueError(error_msg)

                if not response or len(response.strip()) < 10:
                    error_msg = (
                        f"LLM returned empty or too short response: '{response}'"
                    )
                    logger.warning(error_msg)
                    raise ValueError(error_msg)

                logger.debug(
                    f"LLM raw response (attempt {attempt + 1}): {response[:100]}..."
                )
                return self._parse_llm_response(response)

            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    logger.warning(
                        f"LLM analysis attempt {attempt + 1} failed: {e}. Retrying..."
                    )
                    time.sleep(0.5)  # Brief delay before retry
                    continue
                else:
                    logger.error(
                        f"LLM analysis failed after {self.max_retries + 1} attempts for message '{message[:50]}...': {e}"
                    )
                    break

        # Return fallback result with error info
        return {
            "intent": "CONSULTATION",
            "confidence": 0.3,
            "reasoning": f"LLM analysis failed after {self.max_retries + 1} attempts: {str(last_error)}",
            "key_signals": ["llm_analysis_error"],
            "error_type": type(last_error).__name__ if last_error else "unknown",
            "retry_attempts": self.max_retries + 1,
        }

    def _format_history_for_llm(
        self, conversation_history: Optional[List[dict]]
    ) -> str:
        """Format conversation history for LLM context."""
        if not conversation_history:
            return "Không có lịch sử cuộc trò chuyện"

        formatted = []
        for msg in conversation_history[-3:]:  # Last 3 exchanges
            user_msg = msg.get("message", "")
            bot_response = msg.get("response", "")

            if user_msg:
                formatted.append(f"Khách: {user_msg}")
            if bot_response:
                # Truncate long responses
                short_response = (
                    bot_response[:100] + "..."
                    if len(bot_response) > 100
                    else bot_response
                )
                formatted.append(f"Bot: {short_response}")

        return "\n".join(formatted)

    def _parse_llm_response(self, response: str) -> Dict:
        """Parse LLM response to extract intent analysis."""
        try:
            # Try to find JSON in response
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                # Look for JSON object
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]

            data = json.loads(json_str)

            return {
                "intent": data.get("intent", "CONSULTATION"),
                "confidence": float(data.get("confidence", 0.5)),
                "reasoning": data.get("reasoning", "LLM analysis"),
                "key_signals": data.get("key_signals", []),
            }

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(
                f"Failed to parse LLM response: {e}. Raw response: {response}"
            )
            # Fallback to CONSULTATION (more conservative approach)
            return {
                "intent": "CONSULTATION",
                "confidence": 0.3,
                "reasoning": "Fallback due to parse error, defaulting to consultation",
                "key_signals": ["parse error fallback"],
                "raw_response": response[:200],  # Include raw response for debugging
            }

    def _combine_analyses(
        self, rule_result: Dict, llm_result: Dict, message: str
    ) -> Dict:
        """Combine rule-based and LLM analyses with preference for order intent."""
        # Convert LLM intent to our format
        llm_intent_type = (
            "ORDER_PROCESSING"
            if llm_result["intent"] == "ORDER"
            else "PRODUCT_CONSULTATION"
        )

        # Calculate combined confidence
        rule_confidence = rule_result["confidence"]
        llm_confidence = llm_result["confidence"]

        # Weighted combination (favor LLM more when it suggests ORDER)
        if llm_intent_type == "ORDER_PROCESSING":
            combined_confidence = (rule_confidence * 0.4) + (llm_confidence * 0.6)
        else:
            combined_confidence = (rule_confidence * 0.6) + (llm_confidence * 0.4)

        # LLM-first decision making (always validate with LLM)
        if rule_result["intent_type"] == llm_intent_type:
            # Both agree - use LLM confidence as primary
            final_intent = llm_intent_type
            decision_method = "rule_llm_agreement"
        elif llm_confidence >= 0.5:
            # LLM has reasonable confidence - use LLM decision
            final_intent = llm_intent_type
            decision_method = "llm_primary_decision"
        else:
            # LLM has low confidence - conservative fallback
            final_intent = "PRODUCT_CONSULTATION"
            decision_method = "llm_low_confidence_fallback"

        return {
            "intent_type": final_intent,
            "confidence": combined_confidence,
            "score": rule_result["score"],
            "triggers": rule_result["triggers"],
            "confidence_factors": rule_result["confidence_factors"],
            "analysis_timestamp": datetime.now().isoformat(),
            "message_analyzed": message[:50] + "..." if len(message) > 50 else message,
            "decision_method": decision_method,
            "rule_analysis": {
                "intent": rule_result["intent_type"],
                "confidence": rule_confidence,
                "score": rule_result["score"],
            },
            "llm_analysis": {
                "intent": llm_intent_type,
                "confidence": llm_confidence,
                "reasoning": llm_result["reasoning"],
                "key_signals": llm_result["key_signals"],
            },
        }

    def _format_rule_result(self, rule_result: Dict, method: str) -> Dict:
        """Format rule-based result with method indicator."""
        result = rule_result.copy()
        result["decision_method"] = method
        return result

    def get_product_from_context(
        self, message: str, conversation_history: Optional[List[dict]] = None
    ) -> Optional[str]:
        """Extract product from context (delegate to rule analyzer)."""
        return self.rule_analyzer.get_product_from_context(
            message, conversation_history
        )


# Global analyzer instance
_llm_analyzer_instance: Optional[LLMIntentAnalyzer] = None


def get_llm_intent_analyzer() -> LLMIntentAnalyzer:
    """Get or create global LLM intent analyzer instance."""
    global _llm_analyzer_instance
    if _llm_analyzer_instance is None:
        _llm_analyzer_instance = LLMIntentAnalyzer()
        logger.info("LLM Intent Analyzer initialized")
    return _llm_analyzer_instance
