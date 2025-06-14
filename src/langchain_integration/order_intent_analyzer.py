"""
Order Intent Analyzer - Smart detection for order vs consultation flows.
Analyzes user messages and conversation context to determine purchase intent.
"""

from typing import Dict, List, Optional, Set
from datetime import datetime

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class OrderIntentAnalyzer:
    """
    Rule-based order intent detection using multi-trigger scoring system.
    This analyzer serves as a fallback when LLM-based intent analysis is unavailable.

    Combines explicit keywords, behavioral signals, and conversation context
    to determine when users want to place orders vs just seeking information.
    Note: The system prioritizes LLM-based analysis for more accurate intent detection.
    """

    def __init__(self):
        """Initialize the intent analyzer with predefined patterns."""
        # Explicit order keywords (+50 points)
        self.explicit_order_keywords = [
            "đặt hàng",
            "mua",
            "order",
            "đặt",
            "mình muốn mua",
            "cho tôi đặt",
            "tôi cần mua",
            "em muốn đặt",
            "book",
            "mình đặt",
            "đặt mua",
            "order ngay",
            "mua ngay",
            "tôi muốn đặt",
            "tôi muốn mua",
            "muốn đặt hàng",
            "muốn mua",
        ]

        # Stock/availability keywords (+25 points)
        self.stock_keywords = [
            "còn hàng",
            "có hàng",
            "còn không",
            "hết hàng",
            "tình trạng hàng",
            "stock",
            "available",
            "availability",
        ]

        # Price inquiry keywords (+20-30 points)
        self.price_keywords = [
            "giá",
            "price",
            "cost",
            "tiền",
            "bao nhiêu",
            "giá cả",
            "giá bán",
            "phí",
            "chi phí",
        ]

        # Product brands for context matching
        self.product_brands = [
            "iphone",
            "samsung",
            "galaxy",
            "xiaomi",
            "oppo",
            "vivo",
            "realme",
            "oneplus",
            "huawei",
            "nokia",
            "sony",
            "lg",
            "asus",
            "acer",
            "dell",
            "hp",
            "lenovo",
            "macbook",
            "ipad",
            "redmi",
            "mi",
            "poco",
        ]

        # Reference patterns that need context resolution
        self.reference_patterns = [
            "điện thoại trên",
            "điện thoại đó",
            "điện thoại này",
            "sản phẩm trên",
            "sản phẩm đó",
            "sản phẩm này",
            "thiết bị trên",
            "thiết bị đó",
            "thiết bị này",
            "máy trên",
            "máy đó",
            "máy này",
            "cái này",
            "cái đó",
        ]

    def analyze_intent(
        self, message: str, conversation_history: Optional[List[dict]] = None
    ) -> Dict:
        """
        Analyze user message and conversation context to determine intent.

        Args:
            message: User's current message
            conversation_history: List of previous conversation exchanges

        Returns:
            Dict containing intent analysis results
        """
        score = 0
        triggers = []
        confidence_factors = []

        message_lower = message.lower().strip()

        # 1. Explicit Order Intent Analysis (+50 points)
        explicit_score = self._analyze_explicit_intent(message_lower)
        if explicit_score > 0:
            score += explicit_score
            triggers.append("explicit_order_intent")
            confidence_factors.append(f"Explicit keywords: +{explicit_score}")

        # 2. Stock/Availability Inquiry (+25 points)
        stock_score = self._analyze_stock_inquiry(message_lower)
        if stock_score > 0:
            score += stock_score
            triggers.append("stock_inquiry")
            confidence_factors.append(f"Stock inquiry: +{stock_score}")

        # 3. Price Inquiry with Product Context (+20-30 points)
        price_score = self._analyze_price_inquiry(message_lower, conversation_history)
        if price_score > 0:
            score += price_score
            triggers.append("price_inquiry_with_product")
            confidence_factors.append(f"Price inquiry: +{price_score}")

        # 4. Product Context Analysis (+25 points)
        context_score = self._analyze_product_context(
            message_lower, conversation_history
        )
        if context_score > 0:
            score += context_score
            triggers.append("product_context_available")
            confidence_factors.append(f"Product context: +{context_score}")

        # 5. Repeat Inquiry Pattern (+20 points)
        repeat_score = self._analyze_repeat_inquiry(message_lower, conversation_history)
        if repeat_score > 0:
            score += repeat_score
            triggers.append("repeat_product_inquiry")
            confidence_factors.append(f"Repeat inquiry: +{repeat_score}")

        # 6. Reference Resolution (+15 points)
        reference_score = self._analyze_reference_patterns(
            message_lower, conversation_history
        )
        if reference_score > 0:
            score += reference_score
            triggers.append("reference_to_previous_product")
            confidence_factors.append(f"Reference resolution: +{reference_score}")

        # Determine intent type based on threshold
        intent_type = "ORDER_PROCESSING" if score >= 40 else "PRODUCT_CONSULTATION"
        confidence = min(score / 100, 1.0)

        return {
            "intent_type": intent_type,
            "confidence": confidence,
            "score": score,
            "triggers": triggers,
            "confidence_factors": confidence_factors,
            "analysis_timestamp": datetime.now().isoformat(),
            "message_analyzed": message[:50] + "..." if len(message) > 50 else message,
        }

    def _analyze_explicit_intent(self, message_lower: str) -> int:
        """Analyze explicit order keywords in the message."""
        for keyword in self.explicit_order_keywords:
            if keyword in message_lower:
                return 50
        return 0

    def _analyze_stock_inquiry(self, message_lower: str) -> int:
        """Analyze stock/availability inquiry keywords."""
        for keyword in self.stock_keywords:
            if keyword in message_lower:
                return 40  # Increased score to prioritize order intent
        return 0

    def _analyze_price_inquiry(
        self, message_lower: str, conversation_history: Optional[List[dict]]
    ) -> int:
        """Analyze price inquiry with product context."""
        has_price_keyword = any(
            keyword in message_lower for keyword in self.price_keywords
        )
        if not has_price_keyword:
            return 0

        # Check if price inquiry includes specific product
        has_product = any(brand in message_lower for brand in self.product_brands)
        if has_product:
            return 30

        # Check if there's product context from conversation
        if self._has_product_context(conversation_history):
            return 25

        return 10  # Generic price inquiry

    def _analyze_product_context(
        self, message_lower: str, conversation_history: Optional[List[dict]]
    ) -> int:
        """Analyze if there's relevant product context from conversation history."""
        if not conversation_history:
            return 0

        # Check if previous conversation mentioned products
        if not self._has_product_context(conversation_history):
            return 0

        # Give context points for reference patterns
        has_reference = any(
            pattern in message_lower for pattern in self.reference_patterns
        )
        if has_reference:
            return 25

        # Give partial context points for stock/price inquiries without explicit product mention
        # but with product context from conversation
        has_stock_inquiry = any(
            keyword in message_lower for keyword in self.stock_keywords
        )
        has_price_inquiry = any(
            keyword in message_lower for keyword in self.price_keywords
        )
        has_specific_product = any(
            brand in message_lower for brand in self.product_brands
        )

        if (has_stock_inquiry or has_price_inquiry) and not has_specific_product:
            return 25  # Implicit reference to product from context (increased for better detection)

        return 0

    def _analyze_repeat_inquiry(
        self, message_lower: str, conversation_history: Optional[List[dict]]
    ) -> int:
        """Analyze if user is making repeat inquiries about the same product."""
        if not conversation_history or len(conversation_history) < 2:
            return 0

        # Extract products mentioned in current message
        current_products = self._extract_products_from_text(message_lower)
        if not current_products:
            return 0

        # Check if same products were mentioned in recent history
        for msg in conversation_history[-3:]:  # Check last 3 messages
            user_text = msg.get("message", "").lower()
            bot_text = msg.get("response", "").lower()

            historical_products = self._extract_products_from_text(
                user_text + " " + bot_text
            )

            # If same product mentioned multiple times, likely order intent
            if current_products.intersection(historical_products):
                return 20

        return 0

    def _analyze_reference_patterns(
        self, message_lower: str, conversation_history: Optional[List[dict]]
    ) -> int:
        """Analyze reference patterns like 'điện thoại trên', 'sản phẩm đó'."""
        has_reference = any(
            pattern in message_lower for pattern in self.reference_patterns
        )
        if not has_reference:
            return 0

        # Check if there's something to reference in conversation history
        if self._has_product_context(conversation_history):
            return 15

        return 0

    def _has_product_context(self, conversation_history: Optional[List[dict]]) -> bool:
        """Check if conversation history contains product mentions."""
        if not conversation_history:
            return False

        # Check last few messages for product mentions
        for msg in conversation_history[-3:]:
            user_text = msg.get("message", "").lower()
            bot_text = msg.get("response", "").lower()
            combined_text = user_text + " " + bot_text

            if any(brand in combined_text for brand in self.product_brands):
                return True

        return False

    def _extract_products_from_text(self, text: str) -> Set[str]:
        """Extract product brands mentioned in text."""
        products = set()
        for brand in self.product_brands:
            if brand in text:
                products.add(brand)
        return products

    def get_product_from_context(
        self, message: str, conversation_history: Optional[List[dict]] = None
    ) -> Optional[str]:
        """
        Extract specific product from current message or conversation context.

        Args:
            message: Current user message
            conversation_history: Previous conversation exchanges

        Returns:
            Product name if found, None otherwise
        """
        message_lower = message.lower()

        # First, try to extract product from current message
        for brand in self.product_brands:
            if brand in message_lower:
                # Try to extract more specific model if possible
                return self._extract_specific_model(message_lower, brand)

        # If not found, check conversation history
        if conversation_history:
            for msg in reversed(conversation_history[-3:]):  # Most recent first
                user_text = msg.get("message", "").lower()
                bot_text = msg.get("response", "").lower()

                for brand in self.product_brands:
                    if brand in user_text or brand in bot_text:
                        return self._extract_specific_model(
                            user_text + " " + bot_text, brand
                        )

        return None

    def _extract_specific_model(self, text: str, brand: str) -> str:
        """Extract specific product model from text."""
        text_lower = text.lower()

        if brand == "iphone":
            # Look for specific iPhone models
            models = [
                "15 pro max",
                "15 pro",
                "15 plus",
                "15",
                "14 pro max",
                "14 pro",
                "14 plus",
                "14",
                "13 pro",
                "13",
                "12 pro",
                "12",
            ]
            for model in models:
                if model in text_lower:
                    return f"iPhone {model.title()}"
            return "iPhone"

        elif brand in ["samsung", "galaxy"]:
            models = [
                "s24 ultra",
                "s24",
                "s23 ultra",
                "s23",
                "s22 ultra",
                "s22",
                "a54",
                "a34",
                "a15",
                "note",
            ]
            for model in models:
                if model in text_lower:
                    return f"Samsung Galaxy {model.upper()}"
            return "Samsung Galaxy"

        elif brand == "xiaomi":
            models = ["14 pro", "14 ultra", "14", "13 pro", "13", "12 pro", "12", "11"]
            for model in models:
                if model in text_lower:
                    return f"Xiaomi {model.title()}"
            return "Xiaomi"

        elif brand == "oppo":
            models = ["find x7", "find x6", "reno 11", "reno 10", "a78", "a58", "a18"]
            for model in models:
                if model in text_lower:
                    return f"Oppo {model.upper()}"
            return "Oppo"

        elif brand == "realme":
            # Be more specific with Realme models to avoid confusion
            models = ["note 60", "11 pro", "11", "12 pro", "12", "c75x", "c55", "c53"]
            for model in models:
                if model in text_lower:
                    return f"Realme {model.title()}"
            return "Realme"

        return brand.title()


# Global analyzer instance for efficient reuse
_analyzer_instance: Optional[OrderIntentAnalyzer] = None


def get_order_intent_analyzer() -> OrderIntentAnalyzer:
    """Get or create global order intent analyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = OrderIntentAnalyzer()
    return _analyzer_instance
