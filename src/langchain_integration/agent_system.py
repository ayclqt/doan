"""
True Agent System with LangChain Function Calling

This module implements a real AI agent that can:
1. Decide which tools to use based on conversation context
2. Call multiple functions in sequence
3. Reason about tool results and make follow-up decisions
4. Handle complex multi-step queries with tool chaining

Author: Assistant
"""

import json
import time
from typing import Any, Dict, List, Optional, Sequence, Union
from datetime import datetime

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate
from langchain.tools import BaseTool, tool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI

from ..config import config, logger
from .vectorstore import VectorStore
from .web_search import WebSearcher


class VectorSearchInput(BaseModel):
    """Input schema for vector search tool."""
    query: str = Field(description="Search query for product database")
    top_k: int = Field(default=3, description="Number of results to return")


class WebSearchInput(BaseModel):
    """Input schema for web search tool."""
    query: str = Field(description="Search query for web search")
    max_results: int = Field(default=5, description="Maximum number of results")


class ConversationMemoryInput(BaseModel):
    """Input schema for conversation memory tool."""
    reference: str = Field(description="Reference to resolve (e.g., 'điện thoại trên')")
    conversation_history: List[dict] = Field(description="Recent conversation history")


class ProductComparisonInput(BaseModel):
    """Input schema for product comparison tool."""
    product1: str = Field(description="First product to compare")
    product2: str = Field(description="Second product to compare")
    comparison_aspects: List[str] = Field(default=["price", "specs", "features"], description="Aspects to compare")


class PriceAnalysisInput(BaseModel):
    """Input schema for price analysis tool."""
    product_name: str = Field(description="Product name to analyze price")
    include_promotions: bool = Field(default=True, description="Include current promotions")


class ConversationAnalysisInput(BaseModel):
    """Input schema for conversation analysis tool."""
    conversation_history: List[dict] = Field(description="Conversation history to analyze")
    current_question: str = Field(description="Current user question")


@tool("vector_search", args_schema=VectorSearchInput)
def vector_search_tool(query: str, top_k: int = 3) -> str:
    """
    Search the product database for relevant information.
    Use this when you need to find specific product details, specifications, or features.
    
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
            formatted_results.append(f"Kết quả {i}:\n{doc.page_content}\n")
        
        return "\n".join(formatted_results)
        
    except Exception as e:
        return f"Lỗi khi tìm kiếm trong cơ sở dữ liệu: {e}"


@tool("web_search", args_schema=WebSearchInput)
def web_search_tool(query: str, max_results: int = 5) -> str:
    """
    Search the web for current information about products, prices, or reviews.
    Use this when you need up-to-date information that might not be in the database.
    
    Args:
        query: Search query for web search
        max_results: Maximum number of results to return
    
    Returns:
        Formatted web search results
    """
    try:
        web_searcher = WebSearcher()
        if not web_searcher.is_available():
            return "Web search không khả dụng hiện tại."
        
        results = web_searcher.search_product_info(query)
        
        if not results:
            return f"Không tìm thấy kết quả web nào cho: {query}"
        
        formatted_results = []
        for i, result in enumerate(results[:max_results], 1):
            formatted_results.append(
                f"Kết quả web {i}:\n"
                f"Tiêu đề: {result.title}\n"
                f"Nội dung: {result.body}\n"
                f"Nguồn: {result.href}\n"
            )
        
        return "\n".join(formatted_results)
        
    except Exception as e:
        return f"Lỗi khi tìm kiếm trên web: {e}"


@tool("resolve_conversation_reference", args_schema=ConversationMemoryInput)
def resolve_conversation_reference_tool(reference: str, conversation_history: List[dict]) -> str:
    """
    Resolve conversational references like 'điện thoại trên', 'sản phẩm đó' to specific products.
    Use this when the user refers to something mentioned earlier in the conversation.
    
    Args:
        reference: Reference to resolve (e.g., 'điện thoại trên')
        conversation_history: Recent conversation history
    
    Returns:
        Resolved product name or entity
    """
    try:
        if not conversation_history:
            return f"Không thể resolve '{reference}' - không có lịch sử cuộc trò chuyện."
        
        # Common reference patterns
        reference_patterns = [
            "điện thoại trên", "điện thoại đó", "điện thoại này",
            "sản phẩm trên", "sản phẩm đó", "sản phẩm này",
            "thiết bị trên", "thiết bị đó", "thiết bị này",
            "máy trên", "máy đó", "máy này"
        ]
        
        if reference.lower() not in [p.lower() for p in reference_patterns]:
            return f"'{reference}' không phải là tham chiếu cần resolve."
        
        # Look for product names in recent conversation
        product_keywords = [
            'iphone', 'samsung', 'galaxy', 'xiaomi', 'oppo', 'vivo',
            'realme', 'oneplus', 'huawei', 'nokia', 'sony', 'lg',
            'asus', 'acer', 'dell', 'hp', 'lenovo', 'macbook'
        ]
        
        # Search in reverse order (most recent first)
        for msg in reversed(conversation_history[-5:]):  # Last 5 messages
            user_msg = msg.get('message', '').lower()
            bot_response = msg.get('response', '').lower()
            
            for keyword in product_keywords:
                if keyword in user_msg or keyword in bot_response:
                    # Extract more specific product name if possible
                    text = user_msg + " " + bot_response
                    
                    # Look for specific models
                    if 'iphone' in text:
                        for model in ['15', '14', '13', 'pro', 'max', 'plus']:
                            if model in text:
                                return f"iPhone {model.upper()}" if model in ['pro', 'max', 'plus'] else f"iPhone {model}"
                        return "iPhone"
                    
                    elif 'samsung' in text or 'galaxy' in text:
                        for model in ['s24', 's23', 's22', 'ultra', 'note']:
                            if model in text:
                                return f"Samsung Galaxy {model.upper()}"
                        return "Samsung Galaxy"
                    
                    elif 'xiaomi' in text:
                        for model in ['14', '13', '12', 'pro', 'ultra']:
                            if model in text:
                                return f"Xiaomi {model}"
                        return "Xiaomi"
                    
                    else:
                        return keyword.title()
        
        return f"Không thể xác định '{reference}' từ lịch sử cuộc trò chuyện."
        
    except Exception as e:
        return f"Lỗi khi resolve reference: {e}"


@tool("compare_products", args_schema=ProductComparisonInput)
def compare_products_tool(product1: str, product2: str, comparison_aspects: List[str] = None) -> str:
    """
    Compare two products across multiple aspects like price, specifications, features.
    Use this when user asks to compare specific products.
    
    Args:
        product1: First product to compare
        product2: Second product to compare
        comparison_aspects: Aspects to compare (price, specs, features, etc.)
    
    Returns:
        Detailed product comparison
    """
    try:
        if comparison_aspects is None:
            comparison_aspects = ["specs", "features", "price"]
        
        # First, get information about both products
        vector_store = VectorStore()
        vector_store.initialize_vectorstore()
        retriever = vector_store.get_vectorstore().as_retriever(search_kwargs={"k": 3})
        
        # Search for product1
        results1 = retriever.invoke(f"{product1} thông số cấu hình")
        product1_info = "\n".join([doc.page_content for doc in results1[:2]]) if results1 else "Không tìm thấy thông tin"
        
        # Search for product2
        results2 = retriever.invoke(f"{product2} thông số cấu hình")
        product2_info = "\n".join([doc.page_content for doc in results2[:2]]) if results2 else "Không tìm thấy thông tin"
        
        # If we need current price info, search web
        if "price" in comparison_aspects:
            web_searcher = WebSearcher()
            if web_searcher.is_available():
                price_query = f"so sánh giá {product1} vs {product2}"
                price_results = web_searcher.search_product_info(price_query)
                price_info = "\n".join([r.body for r in price_results[:2]]) if price_results else ""
            else:
                price_info = "Thông tin giá hiện tại không khả dụng"
        else:
            price_info = ""
        
        # Format comparison
        comparison_result = f"""
SO SÁNH {product1.upper()} VS {product2.upper()}

=== {product1.upper()} ===
{product1_info}

=== {product2.upper()} ===
{product2_info}
"""
        
        if price_info:
            comparison_result += f"\n=== THÔNG TIN GIÁ HIỆN TẠI ===\n{price_info}"
        
        return comparison_result
        
    except Exception as e:
        return f"Lỗi khi so sánh sản phẩm: {e}"


@tool("analyze_price_trends", args_schema=PriceAnalysisInput)
def analyze_price_trends_tool(product_name: str, include_promotions: bool = True) -> str:
    """
    Analyze current prices and trends for a specific product.
    Use this when user asks about pricing, deals, or cost analysis.
    
    Args:
        product_name: Product name to analyze
        include_promotions: Whether to include current promotions
    
    Returns:
        Price analysis and trends
    """
    try:
        web_searcher = WebSearcher()
        if not web_searcher.is_available():
            return "Web search không khả dụng để phân tích giá."
        
        # Search for current prices
        price_query = f"{product_name} giá hiện tại"
        if include_promotions:
            price_query += " khuyến mãi sale"
        
        results = web_searcher.search_product_info(price_query)
        
        if not results:
            return f"Không tìm thấy thông tin giá cho {product_name}"
        
        price_analysis = f"PHÂN TÍCH GIÁ - {product_name.upper()}\n\n"
        
        for i, result in enumerate(results[:3], 1):
            price_analysis += f"Nguồn {i}: {result.title}\n{result.body}\n\n"
        
        return price_analysis
        
    except Exception as e:
        return f"Lỗi khi phân tích giá: {e}"


@tool("analyze_conversation_context", args_schema=ConversationAnalysisInput)
def analyze_conversation_context_tool(conversation_history: List[dict], current_question: str) -> str:
    """
    Analyze conversation context to understand user intent and provide relevant insights.
    Use this to understand what the user is really asking for based on conversation flow.
    
    Args:
        conversation_history: Full conversation history
        current_question: Current user question
    
    Returns:
        Context analysis and user intent insights
    """
    try:
        if not conversation_history:
            return f"Phân tích câu hỏi: '{current_question}' - Không có ngữ cảnh trước đó."
        
        # Analyze conversation patterns
        recent_topics = []
        mentioned_products = set()
        question_types = []
        
        for msg in conversation_history[-3:]:  # Last 3 exchanges
            user_msg = msg.get('message', '').lower()
            
            # Extract topics
            if 'giá' in user_msg or 'price' in user_msg:
                question_types.append('price_inquiry')
            elif any(word in user_msg for word in ['so sánh', 'compare', 'vs']):
                question_types.append('comparison')
            elif any(word in user_msg for word in ['cấu hình', 'thông số', 'specs']):
                question_types.append('specification')
            elif any(word in user_msg for word in ['đánh giá', 'review', 'tốt']):
                question_types.append('review')
            
            # Extract product mentions
            products = ['iphone', 'samsung', 'galaxy', 'xiaomi', 'oppo', 'vivo']
            for product in products:
                if product in user_msg:
                    mentioned_products.add(product)
        
        # Analyze current question intent
        current_intent = "general_inquiry"
        if any(word in current_question.lower() for word in ['giá', 'price', 'cost']):
            current_intent = "price_inquiry"
        elif any(word in current_question.lower() for word in ['so sánh', 'compare']):
            current_intent = "comparison_request"
        elif any(ref in current_question.lower() for ref in ['trên', 'đó', 'này']):
            current_intent = "reference_resolution"
        
        # Generate analysis
        analysis = f"""
PHÂN TÍCH NGỮ CẢNH CUỘC TRÒ CHUYỆN

Câu hỏi hiện tại: "{current_question}"
Intent được phát hiện: {current_intent}

Sản phẩm đã được nhắc đến: {', '.join(mentioned_products) if mentioned_products else 'Chưa có'}
Loại câu hỏi trước đó: {', '.join(set(question_types)) if question_types else 'Chưa có'}

Khuyến nghị:
"""
        
        if current_intent == "reference_resolution":
            analysis += "- Cần resolve tham chiếu từ lịch sử cuộc trò chuyện\n"
        if current_intent == "comparison_request":
            analysis += "- Cần thông tin chi tiết để so sánh sản phẩm\n"
        if current_intent == "price_inquiry":
            analysis += "- Cần thông tin giá cả mới nhất từ web\n"
        
        return analysis
        
    except Exception as e:
        return f"Lỗi khi phân tích ngữ cảnh: {e}"


class ProductAssistantAgent:
    """
    Intelligent Product Assistant Agent with tool calling capabilities.
    
    This agent can:
    - Automatically decide which tools to use
    - Chain multiple tools together
    - Resolve conversational references
    - Provide comprehensive product assistance
    """
    
    def __init__(
        self,
        model_name: str = None,
        temperature: float = 0.3,
        max_iterations: int = 10,
        verbose: bool = True
    ):
        """Initialize the agent with tools and LLM."""
        self.llm = ChatOpenAI(
            model=model_name or config.llm_model_name,
            temperature=temperature,
            api_key=config.openai_api_key,
            base_url=config.openai_base_url,
        )
        
        # Define available tools
        self.tools = [
            vector_search_tool,
            web_search_tool,
            resolve_conversation_reference_tool,
            compare_products_tool,
            analyze_price_trends_tool,
            analyze_conversation_context_tool,
        ]
        
        # Create agent prompt
        self.prompt = self._create_agent_prompt()
        
        # Create agent
        self.agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        # Create agent executor
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=verbose,
            max_iterations=max_iterations,
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
        
        self.logger = logger
        
        # Performance tracking
        self.stats = {
            "total_queries": 0,
            "tool_calls": 0,
            "successful_resolutions": 0,
            "average_tools_per_query": 0.0
        }
    
    def _create_agent_prompt(self) -> ChatPromptTemplate:
        """Create the agent system prompt."""
        system_message = """Bạn là một AI Agent thông minh chuyên về sản phẩm điện tử.

KHẢ NĂNG CỦA BẠN:
- Tìm kiếm thông tin sản phẩm trong cơ sở dữ liệu
- Tìm kiếm thông tin mới nhất trên web
- Giải quyết tham chiếu trong cuộc trò chuyện ("điện thoại trên", "sản phẩm đó")
- So sánh sản phẩm chi tiết
- Phân tích giá cả và xu hướng
- Hiểu ngữ cảnh cuộc trò chuyện

NGUYÊN TẮC HOẠT ĐỘNG:
1. Luôn phân tích ngữ cảnh cuộc trò chuyện trước
2. Nếu có tham chiếu ("điện thoại trên"), resolve nó trước
3. Sử dụng vector search cho thông tin cơ bản
4. Sử dụng web search cho giá cả, khuyến mãi, thông tin mới
5. So sánh sản phẩm khi được yêu cầu
6. Luôn cung cấp thông tin chính xác và hữu ích

KHI NÀO SỬ DỤNG TOOL NÀO:
- vector_search: Thông số kỹ thuật, tính năng sản phẩm
- web_search: Giá cả, khuyến mãi, đánh giá mới nhất
- resolve_conversation_reference: Khi có "điện thoại trên", "sản phẩm đó"
- compare_products: Khi cần so sánh 2+ sản phẩm
- analyze_price_trends: Phân tích giá cả chi tiết
- analyze_conversation_context: Hiểu ý định người dùng

Hãy sử dụng tools một cách thông minh để trả lời chính xác và đầy đủ nhất."""

        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
    
    def process_query(
        self, 
        query: str, 
        conversation_history: Optional[List[dict]] = None
    ) -> Dict[str, Any]:
        """
        Process user query with intelligent tool usage.
        
        Args:
            query: User query
            conversation_history: Previous conversation messages
            
        Returns:
            Response with tool usage details
        """
        start_time = time.time()
        self.stats["total_queries"] += 1
        
        try:
            # Prepare input with conversation history
            agent_input = {
                "input": query,
                "chat_history": self._format_chat_history(conversation_history or []),
                "conversation_history": conversation_history or []
            }
            
            # Execute agent
            result = self.agent_executor.invoke(agent_input)
            
            # Extract information
            response = result["output"]
            intermediate_steps = result.get("intermediate_steps", [])
            
            # Count tool usage
            tools_used = []
            for step in intermediate_steps:
                action, observation = step
                tools_used.append({
                    "tool": action.tool,
                    "input": action.tool_input,
                    "output": observation[:200] + "..." if len(str(observation)) > 200 else str(observation)
                })
            
            self.stats["tool_calls"] += len(tools_used)
            self.stats["successful_resolutions"] += 1
            
            processing_time = time.time() - start_time
            
            # Update average tools per query
            self.stats["average_tools_per_query"] = (
                self.stats["tool_calls"] / self.stats["total_queries"]
            )
            
            self.logger.info(f"Agent processed query with {len(tools_used)} tools in {processing_time:.2f}s")
            
            return {
                "response": response,
                "tools_used": tools_used,
                "processing_time": processing_time,
                "success": True,
                "agent_reasoning": self._extract_reasoning(intermediate_steps)
            }
            
        except Exception as e:
            self.logger.error(f"Agent processing failed: {e}")
            return {
                "response": f"Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi: {e}",
                "tools_used": [],
                "processing_time": time.time() - start_time,
                "success": False,
                "error": str(e)
            }
    
    def _format_chat_history(self, conversation_history: List[dict]) -> List[BaseMessage]:
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
    
    def _extract_reasoning(self, intermediate_steps: List) -> List[str]:
        """Extract agent reasoning from intermediate steps."""
        reasoning = []
        
        for i, (action, observation) in enumerate(intermediate_steps, 1):
            reasoning.append(
                f"Step {i}: Used {action.tool} - {action.tool_input.get('query', str(action.tool_input)[:50])}"
            )
        
        return reasoning
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent performance statistics."""
        return {
            "performance": self.stats.copy(),
            "available_tools": [tool.name for tool in self.tools],
            "agent_status": "operational",
            "timestamp": datetime.now().isoformat()
        }
    
    def reset_stats(self):
        """Reset performance statistics."""
        self.stats = {
            "total_queries": 0,
            "tool_calls": 0,
            "successful_resolutions": 0,
            "average_tools_per_query": 0.0
        }


# Global agent instance
_agent_instance: Optional[ProductAssistantAgent] = None


def get_agent() -> ProductAssistantAgent:
    """Get or create global agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = ProductAssistantAgent()
        logger.info("Product Assistant Agent initialized")
    return _agent_instance


def create_custom_agent(**kwargs) -> ProductAssistantAgent:
    """Create a custom agent with specific parameters."""
    return ProductAssistantAgent(**kwargs)