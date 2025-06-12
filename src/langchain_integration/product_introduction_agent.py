"""
Product Introduction Agent - Intelligent product recommendation system.
Uses pure LLM reasoning with optimized tools for natural product introductions.
"""

import time
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate
from langchain.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun

from ..config import config, logger
from .vectorstore import VectorStore

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class VectorSearchInput(BaseModel):
    """Input schema for vector search tool."""

    query: str = Field(description="Search query for product database")
    top_k: int = Field(default=3, description="Number of results to return")


class WebSearchInput(BaseModel):
    """Input schema for web search tool."""

    query: str = Field(description="Search query for web search")
    max_results: int = Field(default=3, description="Maximum number of results")


class ConversationContextInput(BaseModel):
    """Input schema for conversation context tool."""

    reference: str = Field(description="Reference to resolve (e.g., 'điện thoại trên')")
    conversation_history: List[dict] = Field(description="Recent conversation history")


@tool("product_search", args_schema=VectorSearchInput)
def product_search_tool(query: str, top_k: int = 3) -> str:
    """
    Search the product database for relevant information.
    Use this when you need to find specific product details, specifications, or features.
    This is your PRIMARY source of product information.

    Args:
        query: Search query for product database
        top_k: Number of results to return

    Returns:
        Formatted search results from product database
    """
    try:
        vector_store = VectorStore()
        vector_store.initialize_vectorstore()

        retriever = vector_store.get_vectorstore().as_retriever(
            search_kwargs={"k": top_k}
        )

        results = retriever.invoke(query)

        if not results:
            return "Không tìm thấy thông tin sản phẩm nào trong cơ sở dữ liệu."

        formatted_results = []
        for i, doc in enumerate(results, 1):
            formatted_results.append(f"Sản phẩm {i}:\n{doc.page_content}\n")

        return "\n".join(formatted_results)

    except Exception as e:
        return f"Lỗi khi tìm kiếm trong cơ sở dữ liệu: {e}"


@tool("web_knowledge", args_schema=WebSearchInput)
def web_knowledge_tool(query: str, max_results: int = 3) -> str:
    """
    Search for additional product knowledge on the web.
    Use this ONLY when product_search doesn't provide sufficient information.
    This provides supplementary information to enhance your product knowledge.

    Args:
        query: Search query for web search
        max_results: Maximum number of results to return

    Returns:
        Additional product information from web sources (for internal knowledge only)
    """
    try:
        search_tool = DuckDuckGoSearchRun()

        # Enhance query for electronics products
        enhanced_query = f"{query} điện tử công nghệ"

        results = search_tool.invoke(enhanced_query)

        if not results:
            return f"Không tìm thấy thông tin bổ sung cho: {query}"

        # Limit results and clean up
        limited_results = results[:1000] if len(results) > 1000 else results

        return f"Thông tin bổ sung: {limited_results}"

    except Exception as e:
        return f"Không thể tìm kiếm thông tin bổ sung: {e}"


@tool("conversation_context", args_schema=ConversationContextInput)
def conversation_context_tool(reference: str, conversation_history: List[dict]) -> str:
    """
    Resolve conversational references like 'điện thoại trên', 'sản phẩm đó' to specific products.
    Use this when the user refers to something mentioned earlier in the conversation.

    Args:
        reference: Reference to resolve (e.g., 'điện thoại trên')
        conversation_history: Recent conversation history

    Returns:
        Resolved product name or context information
    """
    try:
        if not conversation_history:
            return (
                f"Không thể resolve '{reference}' - không có lịch sử cuộc trò chuyện."
            )

        # Common reference patterns
        reference_patterns = [
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
        ]

        if reference.lower() not in [p.lower() for p in reference_patterns]:
            return f"'{reference}' không phải là tham chiếu cần resolve."

        # Look for product names in recent conversation
        product_keywords = [
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

        # Search in reverse order (most recent first)
        for msg in reversed(conversation_history[-5:]):
            user_msg = msg.get("message", "").lower()
            bot_response = msg.get("response", "").lower()

            for keyword in product_keywords:
                if keyword in user_msg or keyword in bot_response:
                    # Extract more specific product name if possible
                    text = user_msg + " " + bot_response

                    # Look for specific models
                    if "iphone" in text:
                        for model in ["15", "14", "13", "pro", "max", "plus"]:
                            if model in text:
                                return (
                                    f"iPhone {model.upper()}"
                                    if model in ["pro", "max", "plus"]
                                    else f"iPhone {model}"
                                )
                        return "iPhone"

                    elif "samsung" in text or "galaxy" in text:
                        for model in ["s24", "s23", "s22", "ultra", "note"]:
                            if model in text:
                                return f"Samsung Galaxy {model.upper()}"
                        return "Samsung Galaxy"

                    elif "xiaomi" in text:
                        for model in ["14", "13", "12", "pro", "ultra"]:
                            if model in text:
                                return f"Xiaomi {model}"
                        return "Xiaomi"

                    else:
                        return keyword.title()

        return f"Không thể xác định '{reference}' từ lịch sử cuộc trò chuyện."

    except Exception as e:
        return f"Lỗi khi resolve reference: {e}"


class ProductIntroductionAgent:
    """
    Intelligent Product Introduction Agent using pure LLM reasoning.

    This agent specializes in natural product introductions and recommendations
    without exposing search sources or internal tool usage to users.
    """

    def __init__(
        self,
        model_name: str = None,
        temperature: float = 0.7,
        max_iterations: int = 8,
        verbose: bool = False,
    ):
        """Initialize the product introduction agent."""
        self.llm = ChatOpenAI(
            model=model_name or config.llm_model_name,
            temperature=temperature,
            api_key=config.openai_api_key,
            base_url=config.openai_base_url,
        )

        # Define available tools - simplified but powerful
        self.tools = [
            product_search_tool,
            web_knowledge_tool,
            conversation_context_tool,
        ]

        # Create agent prompt with strict guidelines
        self.prompt = self._create_agent_prompt()

        # Create agent
        self.agent = create_openai_tools_agent(
            llm=self.llm, tools=self.tools, prompt=self.prompt
        )

        # Create agent executor
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=verbose,
            max_iterations=max_iterations,
            handle_parsing_errors=True,
            return_intermediate_steps=False,  # Hide tool usage from output
        )

        self.logger = logger

        # Performance tracking
        self.stats = {
            "total_queries": 0,
            "product_searches": 0,
            "web_searches": 0,
            "context_resolutions": 0,
            "successful_introductions": 0,
            "average_response_time": 0.0,
        }

    def _create_agent_prompt(self) -> ChatPromptTemplate:
        """Create the agent system prompt with strict guidelines."""
        system_message = """Bạn là một chuyên gia giới thiệu sản phẩm điện tử hàng đầu với kiến thức sâu rộng về công nghệ.

NHIỆM VỤ CHÍNH:
- Giới thiệu sản phẩm một cách hấp dẫn, chuyên nghiệp và tự nhiên
- Tư vấn sản phẩm phù hợp với nhu cầu khách hàng  
- Cung cấp thông tin chính xác về tính năng, ưu điểm của sản phẩm
- So sánh sản phẩm một cách khách quan và chuyên nghiệp

CÔNG CỤ CỦA BẠN:
1. product_search - Tìm kiếm thông tin sản phẩm (SỬ DỤNG ĐẦU TIÊN)
2. web_knowledge - Tìm thêm thông tin bổ sung (CHỈ KHI CẦN THIẾT)
3. conversation_context - Hiểu ngữ cảnh cuộc trò chuyện

CHIẾN LƯỢC SỬ DỤNG CÔNG CỤ:
- LUÔN dùng product_search trước để tìm thông tin sản phẩm
- CHỈ dùng web_knowledge khi product_search không đủ thông tin
- Dùng conversation_context khi có tham chiếu ("điện thoại trên", "sản phẩm đó")

QUY TẮC NGHIÊM NGẶT - KHÔNG BAO GIỜ VI PHẠM:
❌ KHÔNG đề cập "tìm kiếm trên web", "theo kết quả search", "dựa trên tìm kiếm"
❌ KHÔNG cung cấp links, URLs, hay references của bất kỳ nguồn nào
❌ KHÔNG nói "dựa trên thông tin tìm được", "từ các nguồn", "theo kết quả"
❌ KHÔNG tiết lộ bất kỳ công cụ tìm kiếm nào được sử dụng
❌ KHÔNG đề cập đến việc sử dụng tools hay search engines

✅ Trả lời như thể bạn là chuyên gia am hiểu sản phẩm từ kinh nghiệm
✅ Sử dụng thông tin một cách tự nhiên như kiến thức nội tại
✅ Tập trung vào lợi ích và giá trị sản phẩm mang lại
✅ Giữ tone thân thiện, chuyên nghiệp và tự tin
✅ Kết thúc bằng lời khuyên cụ thể phù hợp với nhu cầu

CÁCH TRÌNH BÀY:
- Bắt đầu với điểm nổi bật của sản phẩm
- Phân tích ưu nhược điểm một cách khách quan
- Đưa ra recommendation phù hợp với nhu cầu người dùng
- Kết thúc bằng tóm tắt và lời khuyên thực tế

VÍ DỤ PHONG CÁCH PHẢN HỒI:
"iPhone 15 Pro thực sự là một chiếc điện thoại ấn tượng với chip A17 Pro mạnh mẽ và hệ thống camera tiên tiến. Với thiết kế titanium cao cấp, máy vừa nhẹ vừa bền bỉ. Camera chính 48MP cho chất lượng ảnh xuất sắc, đặc biệt trong điều kiện thiếu sáng. Tuy nhiên, giá thành khá cao so với các đối thủ. Nếu bạn đang tìm một chiếc flagship Android với hiệu năng tương đương nhưng giá tốt hơn, Samsung Galaxy S24 Ultra có thể là lựa chọn phù hợp."

Hãy luôn nhớ: Bạn là CHUYÊN GIA SẢN PHẨM, không phải công cụ tìm kiếm!"""

        return ChatPromptTemplate.from_messages(
            [
                ("system", system_message),
                ("placeholder", "{chat_history}"),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ]
        )

    def process_query(
        self, query: str, conversation_history: Optional[List[dict]] = None
    ) -> Dict[str, Any]:
        """
        Process user query and generate natural product introduction.

        Args:
            query: User query about products
            conversation_history: Previous conversation messages

        Returns:
            Response with natural product introduction
        """
        start_time = time.time()
        self.stats["total_queries"] += 1

        try:
            # Prepare input with conversation history
            agent_input = {
                "input": query,
                "chat_history": self._format_chat_history(conversation_history or []),
                "conversation_history": conversation_history or [],
            }

            # Execute agent
            result = self.agent_executor.invoke(agent_input)

            # Extract response
            response = result["output"]

            processing_time = time.time() - start_time
            self.stats["successful_introductions"] += 1

            # Update average response time
            total_time = self.stats["average_response_time"] * (
                self.stats["total_queries"] - 1
            )
            self.stats["average_response_time"] = (
                total_time + processing_time
            ) / self.stats["total_queries"]

            self.logger.info(
                f"Product introduction generated in {processing_time:.2f}s"
            )

            return {
                "response": response,
                "processing_time": processing_time,
                "success": True,
                "query_type": self._classify_query_type(query),
            }

        except Exception as e:
            self.logger.error(f"Product introduction failed: {e}")
            return {
                "response": "Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi về sản phẩm. Vui lòng thử lại sau.",
                "processing_time": time.time() - start_time,
                "success": False,
                "error": str(e),
            }

    def _format_chat_history(
        self, conversation_history: List[dict]
    ) -> List[BaseMessage]:
        """Format conversation history for agent."""
        messages = []

        for msg in conversation_history[-5:]:  # Last 5 exchanges
            user_msg = msg.get("message")
            bot_response = msg.get("response")

            if user_msg:
                messages.append(HumanMessage(content=user_msg))
            if bot_response:
                messages.append(AIMessage(content=bot_response))

        return messages

    def _classify_query_type(self, query: str) -> str:
        """Classify the type of query for analytics."""
        query_lower = query.lower()

        if any(
            word in query_lower for word in ["so sánh", "compare", "vs", "khác nhau"]
        ):
            return "comparison"
        elif any(word in query_lower for word in ["giá", "price", "cost", "tiền"]):
            return "price_inquiry"
        elif any(
            word in query_lower for word in ["tư vấn", "recommend", "nên chọn", "gợi ý"]
        ):
            return "recommendation"
        elif any(
            word in query_lower
            for word in ["cấu hình", "thông số", "specs", "tính năng"]
        ):
            return "specification"
        elif any(word in query_lower for word in ["đánh giá", "review", "tốt", "xấu"]):
            return "review"
        else:
            return "general_inquiry"

    def get_stats(self) -> Dict[str, Any]:
        """Get agent performance statistics."""
        return {
            "performance": self.stats.copy(),
            "available_tools": [tool.name for tool in self.tools],
            "agent_status": "operational",
            "timestamp": datetime.now().isoformat(),
        }

    def reset_stats(self):
        """Reset performance statistics."""
        self.stats = {
            "total_queries": 0,
            "product_searches": 0,
            "web_searches": 0,
            "context_resolutions": 0,
            "successful_introductions": 0,
            "average_response_time": 0.0,
        }


# Global agent instance
_agent_instance: Optional[ProductIntroductionAgent] = None


def get_product_introduction_agent() -> ProductIntroductionAgent:
    """Get or create global product introduction agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = ProductIntroductionAgent()
        logger.info("Product Introduction Agent initialized")
    return _agent_instance


def create_custom_product_agent(**kwargs) -> ProductIntroductionAgent:
    """Create a custom product introduction agent with specific parameters."""
    return ProductIntroductionAgent(**kwargs)
