"""
Complete LLM-driven search decision system with caching, fallback, and optimization.

This module replaces the rule-based search system with an intelligent LLM agent that:
1. Makes contextual search decisions
2. Generates optimized search queries
3. Caches decisions for performance
4. Provides fallback mechanisms
5. Optimizes costs through smart batching

Author: Assistant
"""

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from ..config import config, logger
from .web_search import SearchResult, WebSearcher

__author__ = "Assistant"
__copyright__ = "Copyright 2025"
__maintainer__ = "Assistant"
__status__ = "Production"


@dataclass
class SearchDecision:
    """Comprehensive search decision with metadata."""

    should_search: bool
    search_queries: List[str]
    reasoning: str
    confidence: float
    search_type: str  # "web", "vector", "hybrid", "none"
    expected_info_types: List[str]
    urgency: str  # "high", "medium", "low"
    cache_duration: int  # seconds to cache this decision
    decision_id: str
    timestamp: float

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "SearchDecision":
        return cls(**data)


@dataclass
class QueryGenerationResult:
    """Result of query generation process."""

    primary_query: str
    alternative_queries: List[str]
    query_reasoning: str
    estimated_search_cost: float
    query_id: str


class DecisionCache:
    """High-performance cache for search decisions."""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.cache: Dict[str, Tuple[SearchDecision, float]] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.hit_count = 0
        self.miss_count = 0

    def _generate_key(
        self, question: str, vector_summary: str, conversation_context: str
    ) -> str:
        """Generate cache key from inputs."""
        combined = f"{question}||{vector_summary}||{conversation_context}"
        return hashlib.md5(combined.encode()).hexdigest()

    def get(
        self, question: str, vector_summary: str, conversation_context: str
    ) -> Optional[SearchDecision]:
        """Get cached decision if available and not expired."""
        key = self._generate_key(question, vector_summary, conversation_context)

        if key in self.cache:
            decision, expiry_time = self.cache[key]
            if time.time() < expiry_time:
                self.hit_count += 1
                logger.debug(f"Cache hit for decision: {decision.decision_id}")
                return decision
            else:
                # Expired, remove from cache
                del self.cache[key]

        self.miss_count += 1
        return None

    def set(
        self,
        question: str,
        vector_summary: str,
        conversation_context: str,
        decision: SearchDecision,
    ):
        """Cache a search decision."""
        key = self._generate_key(question, vector_summary, conversation_context)
        expiry_time = time.time() + decision.cache_duration

        # Evict oldest entries if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]

        self.cache[key] = (decision, expiry_time)
        logger.debug(f"Cached decision: {decision.decision_id}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total_requests if total_requests > 0 else 0

        return {
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": hit_rate,
            "cache_size": len(self.cache),
            "max_size": self.max_size,
        }

    def clear(self):
        """Clear all cached decisions."""
        self.cache.clear()
        self.hit_count = 0
        self.miss_count = 0


class LLMSearchSystem:
    """Complete LLM-driven search decision and execution system."""

    def __init__(
        self,
        model_name: str = None,
        temperature: float = 0.2,
        max_tokens: int = 800,
        web_searcher: Optional[WebSearcher] = None,
        cache_enabled: bool = True,
        fallback_enabled: bool = True,
    ):
        """Initialize the LLM search system."""
        self.llm = ChatOpenAI(
            model=model_name or config.llm_model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=config.openai_api_key,
            base_url=config.openai_base_url,
        )

        self.web_searcher = web_searcher or WebSearcher()
        self.cache = DecisionCache() if cache_enabled else None
        self.fallback_enabled = fallback_enabled
        self.logger = logger

        # Performance tracking
        self.stats = {
            "total_decisions": 0,
            "llm_decisions": 0,
            "cached_decisions": 0,
            "fallback_decisions": 0,
            "avg_decision_time": 0.0,
            "total_search_cost": 0.0,
        }

        # Create optimized prompts
        self.decision_prompt = self._create_decision_prompt()
        self.query_prompt = self._create_query_prompt()

        # Create chains
        self.decision_chain = self.decision_prompt | self.llm | StrOutputParser()
        self.query_chain = self.query_prompt | self.llm | StrOutputParser()

        logger.info("LLM Search System initialized successfully")

    def _create_decision_prompt(self) -> ChatPromptTemplate:
        """Create optimized decision prompt template."""
        system_template = """
        Bạn là AI Search Strategy Expert cho hệ thống chatbot sản phẩm điện tử.

        NHIỆM VỤ: Phân tích và quyết định chiến lược tìm kiếm tối ưu.

        NGUYÊN TẮC QUYẾT ĐỊNH:
        1. WEB SEARCH khi:
           - Thông tin về giá cả, khuyến mãi (thay đổi thường xuyên)
           - So sánh sản phẩm cần data mới nhất
           - Sản phẩm mới/trend/công nghệ 2024-2025
           - Vector search không đủ thông tin
           - Câu hỏi mua bán, tư vấn (cần thông tin thị trường)

        2. VECTOR ONLY khi:
           - Thông số kỹ thuật cơ bản (ổn định)
           - Vector results đầy đủ và chính xác
           - Câu hỏi về tính năng sản phẩm đã có

        3. URGENCY LEVELS:
           - high: Giá cả, khuyến mãi, mua hàng ngay
           - medium: So sánh, tư vấn chung
           - low: Thông số kỹ thuật, tính năng

        INPUT:
        Câu hỏi: {question}
        Vector Results: {vector_summary}
        Ngữ cảnh: {conversation_context}

        OUTPUT (JSON format):
        {{
            "should_search": true/false,
            "reasoning": "lý do chi tiết (2-3 câu)",
            "confidence": 0.0-1.0,
            "search_type": "web|vector|hybrid|none",
            "expected_info_types": ["giá cả", "thông số", "đánh giá"],
            "urgency": "high|medium|low",
            "cache_duration": 300-7200
        }}
        """

        return ChatPromptTemplate.from_messages(
            [
                ("system", system_template),
                ("human", "Hãy quyết định chiến lược tìm kiếm cho câu hỏi này."),
            ]
        )

    def _create_query_prompt(self) -> ChatPromptTemplate:
        """Create optimized query generation prompt."""
        system_template = """
        Bạn là chuyên gia tạo search queries cho sản phẩm điện tử.

        NHIỆM VỤ: Tạo search queries tối ưu cho web search.

        NGUYÊN TẮC:
        1. Query ngắn gọn (5-12 từ)
        2. Bao gồm tên sản phẩm cụ thể
        3. Loại bỏ tham chiếu ("điện thoại trên" → "iPhone 15")
        4. Ưu tiên tiếng Việt + keyword quan trọng
        5. Tối đa 3 alternative queries

        CONTEXT RESOLUTION:
        - "điện thoại trên/đó/này" → tìm tên cụ thể từ lịch sử
        - "sản phẩm trên/đó/này" → xác định sản phẩm từ ngữ cảnh
        - "máy này/đó" → resolve về model cụ thể

        INPUT:
        Câu hỏi gốc: {original_question}
        Ngữ cảnh: {conversation_context}
        Loại thông tin cần: {expected_info_types}

        OUTPUT (JSON format):
        {{
            "primary_query": "query chính tối ưu",
            "alternative_queries": ["query phụ 1", "query phụ 2"],
            "query_reasoning": "giải thích logic tạo query",
            "estimated_cost": 0.1-0.5
        }}
        """

        return ChatPromptTemplate.from_messages(
            [
                ("system", system_template),
                ("human", "Tạo search queries tối ưu cho yêu cầu này."),
            ]
        )

    def _summarize_vector_results(self, vector_results: List[Any]) -> str:
        """Create concise summary of vector search results."""
        if not vector_results:
            return "Không có kết quả vector"

        # Analyze content quality and relevance
        total_length = sum(len(doc.page_content) for doc in vector_results)
        result_count = len(vector_results)

        # Extract key product mentions
        products_mentioned = set()
        for doc in vector_results:
            content_lower = doc.page_content.lower()
            for product in [
                "iphone",
                "samsung",
                "galaxy",
                "xiaomi",
                "oppo",
                "vivo",
                "realme",
            ]:
                if product in content_lower:
                    products_mentioned.add(product)

        summary = f"Vector: {result_count} kết quả, {total_length} ký tự"
        if products_mentioned:
            summary += f", sản phẩm: {', '.join(list(products_mentioned)[:3])}"

        return summary

    def _format_conversation_context(
        self, conversation_history: Optional[List[dict]]
    ) -> str:
        """Format conversation context efficiently."""
        if not conversation_history:
            return "Không có lịch sử"

        # Get last 2 exchanges for context
        recent = (
            conversation_history[-2:]
            if len(conversation_history) > 2
            else conversation_history
        )

        context_parts = []
        for msg in recent:
            user_msg = msg.get("message", "")[:100]  # Truncate for efficiency
            if user_msg:
                context_parts.append(f"Q: {user_msg}")

        return " | ".join(context_parts) if context_parts else "Không có ngữ cảnh"

    async def decide_search_strategy_async(
        self,
        question: str,
        vector_results: List[Any],
        conversation_history: Optional[List[dict]] = None,
    ) -> SearchDecision:
        """Async version of search decision."""
        return await asyncio.to_thread(
            self.decide_search_strategy, question, vector_results, conversation_history
        )

    def decide_search_strategy(
        self,
        question: str,
        vector_results: List[Any],
        conversation_history: Optional[List[dict]] = None,
    ) -> SearchDecision:
        """Make intelligent search decision using LLM."""
        start_time = time.time()
        self.stats["total_decisions"] += 1

        try:
            # Prepare context
            vector_summary = self._summarize_vector_results(vector_results)
            conversation_context = self._format_conversation_context(
                conversation_history
            )

            # Check cache first
            if self.cache:
                cached_decision = self.cache.get(
                    question, vector_summary, conversation_context
                )
                if cached_decision:
                    self.stats["cached_decisions"] += 1
                    decision_time = time.time() - start_time
                    self._update_avg_time(decision_time)
                    logger.info(f"Using cached decision: {cached_decision.decision_id}")
                    return cached_decision

            # Generate decision with LLM
            decision_input = {
                "question": question,
                "vector_summary": vector_summary,
                "conversation_context": conversation_context,
            }

            llm_response = self.decision_chain.invoke(decision_input)
            decision = self._parse_decision_response(llm_response, question)

            # Cache the decision
            if self.cache:
                self.cache.set(question, vector_summary, conversation_context, decision)

            self.stats["llm_decisions"] += 1
            decision_time = time.time() - start_time
            self._update_avg_time(decision_time)

            logger.info(
                f"LLM decision: {decision.should_search}, confidence: {decision.confidence:.2f}, time: {decision_time:.3f}s"
            )
            return decision

        except Exception as e:
            logger.error(f"LLM decision failed: {e}")
            if self.fallback_enabled:
                fallback_decision = self._create_fallback_decision(
                    question, vector_results
                )
                self.stats["fallback_decisions"] += 1
                decision_time = time.time() - start_time
                self._update_avg_time(decision_time)
                return fallback_decision
            else:
                raise

    def generate_search_queries(
        self,
        original_question: str,
        expected_info_types: List[str],
        conversation_history: Optional[List[dict]] = None,
    ) -> QueryGenerationResult:
        """Generate optimized search queries using LLM."""
        try:
            conversation_context = self._format_conversation_context(
                conversation_history
            )

            query_input = {
                "original_question": original_question,
                "conversation_context": conversation_context,
                "expected_info_types": ", ".join(expected_info_types),
            }

            llm_response = self.query_chain.invoke(query_input)
            return self._parse_query_response(llm_response, original_question)

        except Exception as e:
            logger.error(f"Query generation failed: {e}")
            # Fallback to simple query extraction
            return self._create_fallback_queries(
                original_question, conversation_history
            )

    def execute_complete_search(
        self,
        question: str,
        vector_results: List[Any],
        conversation_history: Optional[List[dict]] = None,
    ) -> Tuple[List[SearchResult], SearchDecision]:
        """Execute complete intelligent search process."""
        # Step 1: Decide search strategy
        decision = self.decide_search_strategy(
            question, vector_results, conversation_history
        )

        search_results = []

        if (
            decision.should_search
            and self.web_searcher
            and self.web_searcher.is_available()
        ):
            try:
                # Step 2: Generate optimized queries
                query_result = self.generate_search_queries(
                    question, decision.expected_info_types, conversation_history
                )

                # Step 3: Execute searches with cost tracking
                all_queries = [
                    query_result.primary_query
                ] + query_result.alternative_queries

                for i, query in enumerate(all_queries[:2]):  # Limit to 2 queries
                    try:
                        results = self.web_searcher.search_product_info(query)
                        search_results.extend(results)

                        # Estimate and track cost
                        estimated_cost = 0.05 * (
                            i + 1
                        )  # Increasing cost for additional queries
                        self.stats["total_search_cost"] += estimated_cost

                        if len(search_results) >= 5:  # Stop if sufficient results
                            break

                    except Exception as e:
                        logger.warning(f"Search failed for query '{query}': {e}")
                        continue

                # Step 4: Deduplicate and rank results
                search_results = self._deduplicate_and_rank_results(search_results)

                logger.info(
                    f"Executed search: {len(search_results)} results from {len(all_queries)} queries"
                )

            except Exception as e:
                logger.error(f"Search execution failed: {e}")
                # Return empty results but keep the decision for transparency

        return search_results, decision

    def _parse_decision_response(
        self, llm_response: str, question: str
    ) -> SearchDecision:
        """Parse LLM decision response."""
        try:
            # Try to parse JSON
            if "```json" in llm_response:
                json_start = llm_response.find("```json") + 7
                json_end = llm_response.find("```", json_start)
                json_str = llm_response[json_start:json_end].strip()
            else:
                # Look for JSON object
                start = llm_response.find("{")
                end = llm_response.rfind("}") + 1
                json_str = llm_response[start:end]

            data = json.loads(json_str)

            decision_id = hashlib.md5(f"{question}{time.time()}".encode()).hexdigest()[
                :8
            ]

            return SearchDecision(
                should_search=data.get("should_search", False),
                search_queries=[],  # Will be populated separately
                reasoning=data.get("reasoning", "LLM decision"),
                confidence=float(data.get("confidence", 0.5)),
                search_type=data.get("search_type", "web"),
                expected_info_types=data.get("expected_info_types", ["general"]),
                urgency=data.get("urgency", "medium"),
                cache_duration=int(data.get("cache_duration", 1800)),
                decision_id=decision_id,
                timestamp=time.time(),
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse LLM decision response: {e}")
            # Create fallback decision based on response content
            should_search = (
                "true" in llm_response.lower() or "search" in llm_response.lower()
            )

            decision_id = hashlib.md5(f"{question}{time.time()}".encode()).hexdigest()[
                :8
            ]

            return SearchDecision(
                should_search=should_search,
                search_queries=[],
                reasoning="Parsed from LLM response (fallback)",
                confidence=0.4,
                search_type="web" if should_search else "vector",
                expected_info_types=["general"],
                urgency="medium",
                cache_duration=900,  # Shorter cache for uncertain decisions
                decision_id=decision_id,
                timestamp=time.time(),
            )

    def _parse_query_response(
        self, llm_response: str, original_question: str
    ) -> QueryGenerationResult:
        """Parse LLM query generation response."""
        try:
            # Similar JSON parsing logic
            if "```json" in llm_response:
                json_start = llm_response.find("```json") + 7
                json_end = llm_response.find("```", json_start)
                json_str = llm_response[json_start:json_end].strip()
            else:
                start = llm_response.find("{")
                end = llm_response.rfind("}") + 1
                json_str = llm_response[start:end]

            data = json.loads(json_str)

            query_id = hashlib.md5(
                f"{original_question}{time.time()}".encode()
            ).hexdigest()[:8]

            return QueryGenerationResult(
                primary_query=data.get("primary_query", original_question),
                alternative_queries=data.get("alternative_queries", []),
                query_reasoning=data.get("query_reasoning", "LLM generated"),
                estimated_search_cost=float(data.get("estimated_cost", 0.1)),
                query_id=query_id,
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse query response: {e}")
            return self._create_fallback_queries(original_question, None)

    def _create_fallback_decision(
        self, question: str, vector_results: List[Any]
    ) -> SearchDecision:
        """Create rule-based fallback decision."""
        should_search = (
            not vector_results
            or len(vector_results) < 2
            or any(
                keyword in question.lower()
                for keyword in ["giá", "so sánh", "mới", "2024", "2025", "khuyến mãi"]
            )
        )

        decision_id = hashlib.md5(
            f"fallback_{question}{time.time()}".encode()
        ).hexdigest()[:8]

        return SearchDecision(
            should_search=should_search,
            search_queries=[question],
            reasoning="Fallback rule-based decision",
            confidence=0.6,
            search_type="web" if should_search else "vector",
            expected_info_types=["general"],
            urgency="medium",
            cache_duration=600,  # Shorter cache for fallback decisions
            decision_id=decision_id,
            timestamp=time.time(),
        )

    def _create_fallback_queries(
        self, original_question: str, conversation_history: Optional[List[dict]]
    ) -> QueryGenerationResult:
        """Create fallback queries when LLM fails."""
        # Simple reference resolution
        query = original_question

        if conversation_history:
            # Basic product name extraction
            for msg in conversation_history[-2:]:
                text = (msg.get("message", "") + " " + msg.get("response", "")).lower()
                for product in [
                    "iphone",
                    "samsung",
                    "galaxy",
                    "xiaomi",
                    "oppo",
                    "vivo",
                ]:
                    if product in text:
                        query = query.replace("điện thoại trên", product)
                        query = query.replace("sản phẩm trên", product)
                        break

        query_id = hashlib.md5(
            f"fallback_{original_question}{time.time()}".encode()
        ).hexdigest()[:8]

        return QueryGenerationResult(
            primary_query=query,
            alternative_queries=[],
            query_reasoning="Fallback query generation",
            estimated_search_cost=0.05,
            query_id=query_id,
        )

    def _deduplicate_and_rank_results(
        self, results: List[SearchResult]
    ) -> List[SearchResult]:
        """Remove duplicates and rank search results."""
        seen_urls = set()
        deduplicated = []

        for result in results:
            if result.href not in seen_urls:
                seen_urls.add(result.href)
                deduplicated.append(result)

        # Sort by relevance score
        return sorted(deduplicated, key=lambda x: x.relevance_score, reverse=True)[:5]

    def _update_avg_time(self, decision_time: float):
        """Update average decision time."""
        current_avg = self.stats["avg_decision_time"]
        total_decisions = self.stats["total_decisions"]
        self.stats["avg_decision_time"] = (
            current_avg * (total_decisions - 1) + decision_time
        ) / total_decisions

    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        cache_stats = self.cache.get_stats() if self.cache else {}

        return {
            "performance": self.stats,
            "cache": cache_stats,
            "llm_model": config.llm_model_name,
            "web_search_available": self.web_searcher.is_available()
            if self.web_searcher
            else False,
            "fallback_enabled": self.fallback_enabled,
            "uptime": time.time() - getattr(self, "_start_time", time.time()),
        }

    def optimize_performance(self):
        """Perform system optimization."""
        if self.cache:
            # Clear expired entries
            current_time = time.time()
            expired_keys = [
                key
                for key, (_, expiry) in self.cache.cache.items()
                if current_time >= expiry
            ]
            for key in expired_keys:
                del self.cache.cache[key]

            logger.info(f"Cleared {len(expired_keys)} expired cache entries")

        # Reset stats periodically
        if self.stats["total_decisions"] > 10000:
            self.stats = {
                k: 0 if isinstance(v, (int, float)) else v
                for k, v in self.stats.items()
            }
            logger.info("Reset performance statistics")

    def __enter__(self):
        """Context manager entry."""
        self._start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        if self.cache:
            final_stats = self.get_system_stats()
            logger.info(f"LLM Search System final stats: {final_stats}")
