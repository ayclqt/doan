"""
Product Introduction Agent - Updated version with strengthened prompt.
Uses pure LLM reasoning with optimized tools for natural product introductions.
"""

import time
from typing import Any, Dict, Iterator, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate
from langchain.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun

from ..config import config, logger

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


def clean_garbage_ids(content: str) -> str:
    """Clean garbage IDs from page content"""
    if not content:
        return content

    lines = content.split("\n")
    cleaned_lines = []

    for line in lines:
        line = line.strip()
        # Skip lines that are just garbage IDs
        if (
            line.startswith("id:")
            or line.startswith("ID:")
            or line == "id"
            or line == "ID"
            or (line.startswith("id") and line[2:].strip().isdigit())
            or (line.startswith("ID") and line[2:].strip().isdigit())
        ):
            continue

        # Keep non-ID lines
        if line:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


@tool("product_search", args_schema=VectorSearchInput)
def product_search_tool(query: str, top_k: int = 3) -> str:
    """
    Search with enhanced diversity and deduplication.
    Use this when you need to find specific product details, specifications, or features.
    This is your PRIMARY source of product information with smart deduplication.

    Args:
        query: Search query for product database
        top_k: Number of results to return

    Returns:
        Formatted search results from product database with enhanced diversity
    """
    try:
        # Use enhanced search instead of direct vector search
        from .enhanced_search import search_diverse_products

        # Get diverse, deduplicated results
        search_results = search_diverse_products(query, top_k)

        if not search_results:
            return "Không tìm thấy thông tin sản phẩm nào trong cơ sở dữ liệu."

        formatted_results = []
        for point in search_results:
            if hasattr(point, "payload") and point.payload:
                payload = point.payload

                # Get clean product data
                name = payload.get("name", "")
                page_content = payload.get("page_content", "")

                # CLEAN garbage IDs from page_content
                page_content = clean_garbage_ids(page_content)

                # Format without any ID references
                if name:
                    product_info = f"Sản phẩm: {name}\n{page_content}\n"
                else:
                    product_info = f"{page_content}\n"

                formatted_results.append(product_info)

        return "\n---\n".join(formatted_results)

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
            streaming=True,  # Enable streaming for LLM
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

QUY TẮC KIỂM TRA SẢN PHẨM:
- KHI khách hàng hỏi về sản phẩm cụ thể (ví dụ: "có iQOO Z9 Turbo không?")
- PHẢI kiểm tra product_search trước
- SAU KHI có kết quả từ tool → VALIDATE xem có match với sản phẩm được hỏi không
- NẾU tool trả về sản phẩm KHÁC (ví dụ: hỏi iQOO Z9 Turbo nhưng tool trả về Xiaomi)
  → THÔNG BÁO rõ ràng "Rất tiếc, cửa hàng không có [sản phẩm được hỏi]"
- KHÔNG được sử dụng thông tin sai sản phẩm
- CHỈ đưa ra thông tin khi tool results MATCH chính xác với requested product
- CÓ THỂ đề xuất sản phẩm tương tự có sẵn trong cửa hàng

VÍ DỤ VALIDATION:
Khách hỏi: "có iQOO Z9 Turbo không?"
Tool trả về: "Sản phẩm: Xiaomi Redmi 13"
→ PHẢI trả lời: "Rất tiếc, cửa hàng không có iQOO Z9 Turbo. Tuy nhiên em có thể tư vấn..."
→ KHÔNG được nói về Xiaomi Redmi 13 như thể đó là iQOO Z9 Turbo

QUY TẮC NGHIÊM NGẶT - KHÔNG BAO GIỜ VI PHẠM:
❌ TUYỆT ĐỐI KHÔNG đề cập "tìm kiếm", "tìm kiếm điện thoại", "nhu cầu tìm kiếm", "search", "kết quả search", "cơ sở dữ liệu", "deduplication"
❌ TUYỆT ĐỐI KHÔNG cung cấp links, URLs, hay references của bất kỳ nguồn nào
❌ TUYỆT ĐỐI KHÔNG nói "dựa trên thông tin tìm được", "từ các nguồn", "theo kết quả"
❌ TUYỆT ĐỐI KHÔNG tiết lộ bất kỳ công cụ tìm kiếm nào được sử dụng
❌ TUYỆT ĐỐI KHÔNG BAO GIỜ hiển thị ID sản phẩm, số thứ tự, hay bất kỳ mã định danh nào
❌ TUYỆT ĐỐI KHÔNG viết "(ID: 37)", "(Sản phẩm 1)", hay bất kỳ định danh số nào
❌ TUYỆT ĐỐI KHÔNG sử dụng cấu trúc "1. Product A (ID: X)", "2. Product B (ID: Y)"
❌ TUYỆT ĐỐI KHÔNG nói "em thấy có một số gợi ý từ cơ sở dữ liệu"
❌ TUYỆT ĐỐI KHÔNG nói "em sẽ tóm tắt ngắn gọn để anh/chị dễ theo dõi"
❌ TUYỆT ĐỐI KHÔNG đề cập "enhanced search", "vector search", "diversified results"
❌ TUYỆT ĐỐI KHÔNG nói "từ kết quả đa dạng", "sau khi lọc trùng lặp"
❌ TUYỆT ĐỐI KHÔNG dùng cụm từ "dựa trên nhu cầu tìm kiếm" hoặc bất kỳ biến thể nào chứa từ "tìm kiếm"
❌ TUYỆT ĐỐI KHÔNG nói "với nhu cầu tìm kiếm", "yêu cầu tìm kiếm", "việc tìm kiếm"
❌ TUYỆT ĐỐI KHÔNG trả lời về sản phẩm KHÁC khi khách hàng hỏi về sản phẩm CỤ THỂ
❌ TUYỆT ĐỐI KHÔNG dùng thông tin của sản phẩm A để nói về sản phẩm B
❌ TUYỆT ĐỐI KHÔNG giả vờ có hàng khi tool không trả về đúng sản phẩm

✅ LUÔN trả lời như thể bạn là chuyên gia am hiểu sản phẩm từ kinh nghiệm
✅ LUÔN sử dụng thông tin một cách tự nhiên như kiến thức nội tại
✅ LUÔN chỉ đề cập TÊN SẢN PHẨM CỤ THỂ, không bao giờ kèm ID hay số
✅ LUÔN tập trung vào lợi ích và giá trị sản phẩm mang lại
✅ LUÔN giữ tone thân thiện, chuyên nghiệp và tự tin
✅ LUÔN kết thúc bằng lời khuyên cụ thể phù hợp với nhu cầu

THAY VÌ: "Dựa trên nhu cầu tìm kiếm điện thoại..."
HÃY NÓI: "Với nhu cầu về điện thoại..." hoặc "Anh/chị đang quan tâm đến điện thoại..."

VÍ DỤ ĐỊNH DẠNG CHUẨN:

### 1. KHI CÓ SẢN PHẨM ĐÚNG:
## Điện thoại tầm giá 4 triệu - Những lựa chọn đáng chú ý

Với ngân sách 4 triệu, anh/chị có những lựa chọn tuyệt vời sau:

### Realme Note 60
**Realme Note 60** thực sự là một lựa chọn ấn tượng với **pin 5000mAh bền bỉ** và thiết kế hiện đại. Điểm mạnh của máy là khả năng sử dụng cả ngày dài mà không lo hết pin.

### Samsung Galaxy A15
**Samsung Galaxy A15** mang đến trải nghiệm cao cấp với camera chụp đêm xuất sắc và giao diện One UI thân thiện.

## Khuyến nghị

Nếu anh/chị ưu tiên pin trâu, **Realme Note 60** là lựa chọn tối ưu. Nếu thích camera đẹp, **Samsung Galaxy A15** sẽ phù hợp hơn.

### 2. KHI KHÔNG CÓ SẢN PHẨM CỤ THỂ:
Khách hỏi: "Shop có iQOO Z9 Turbo không?"
Tool trả về: "Sản phẩm: Xiaomi Redmi 13"

ĐÚNG: "Rất tiếc, hiện tại cửa hàng không có iQOO Z9 Turbo trong kho ạ. Tuy nhiên, em có thể tư vấn anh/chị về các sản phẩm tương tự có sẵn như Xiaomi Redmi 13 với hiệu năng tốt trong cùng tầm giá."

SAI: Đưa thông tin Xiaomi Redmi 13 như thể đó là iQOO Z9 Turbo

ĐỊNH DẠNG MARKDOWN BẮT BUỘC:
- LUÔN sử dụng ## cho headers chính (ví dụ: ## Điểm nổi bật chính)
- Sử dụng ### cho sub-headers (ví dụ: ### Hiệu năng và thiết kế)
- Sử dụng **text** cho highlight quan trọng
- Sử dụng - cho bullet points
- Sử dụng 1. 2. 3. cho numbered lists
- LUÔN có ít nhất 2 empty lines giữa các sections chính
- Kết thúc mỗi section với 1 empty line

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

    def process_query_stream(
        self, query: str, conversation_history: Optional[List[dict]] = None
    ) -> Iterator[str]:
        """
        Stream agent processing with real-time updates.

        Args:
            query: User query about products
            conversation_history: Previous conversation messages

        Yields:
            Progressive response chunks from LLM only
        """
        start_time = time.time()
        self.stats["total_queries"] += 1

        try:
            # Prepare agent input
            agent_input = {
                "input": query,
                "chat_history": self._format_chat_history(conversation_history or []),
                "conversation_history": conversation_history or [],
            }

            # Execute agent with streaming callback
            result = self._execute_agent_with_streaming(agent_input)

            if result["success"]:
                # Stream the final response naturally
                response_text = result["response"]
                yield from self._stream_text_naturally(response_text)

                self.stats["successful_introductions"] += 1

                processing_time = time.time() - start_time
                self.logger.info(f"Streaming agent completed in {processing_time:.2f}s")
            else:
                yield result.get("error", "Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi.")

        except Exception as e:
            self.logger.error(f"Agent streaming failed: {e}")
            yield "Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi về sản phẩm."

    def _execute_agent_with_streaming(self, agent_input: dict) -> dict:
        """Execute agent with streaming progress updates."""
        try:
            # For now, execute normally and return result
            # In future, we can implement streaming callbacks
            result = self.agent_executor.invoke(agent_input)

            return {
                "response": result["output"],
                "success": True,
            }

        except Exception as e:
            return {
                "response": "",
                "success": False,
                "error": str(e),
            }

    def _stream_text_naturally(self, text: str, chunk_size: int = 15) -> Iterator[str]:
        """Stream text naturally word by word with appropriate delays, preserving line breaks."""
        import re

        # Split text into tokens (words + whitespace/newlines) while preserving structure
        tokens = re.findall(r"\S+|\s+", text)
        current_chunk = []
        word_count = 0

        for token in tokens:
            current_chunk.append(token)

            # Count only words (non-whitespace tokens)
            if token.strip():
                word_count += 1

            # Send chunk when word limit reached or at sentence/phrase end
            if word_count >= chunk_size or (
                token.strip()
                and (
                    token.endswith(".")
                    or token.endswith("!")
                    or token.endswith("?")
                    or token.endswith(",")
                    or token.endswith(";")
                )
            ):
                chunk_text = "".join(current_chunk)
                yield chunk_text
                current_chunk = []
                word_count = 0

                # Natural streaming delay
                time.sleep(0.08)

        # Send remaining tokens
        if current_chunk:
            yield "".join(current_chunk)

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
