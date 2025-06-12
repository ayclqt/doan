"""
Core LangChain pipeline for question answering over product data.
"""

from typing import Any, Iterator, List, Optional

from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import (
    RunnableLambda,
    RunnableParallel,
)
from langchain_openai import ChatOpenAI

from ..config import config, logger
from .vectorstore import VectorStore
from .web_search import HybridSearcher, WebSearcher
from .product_introduction_agent import get_product_introduction_agent

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class LangchainPipeline:
    """LangChain pipeline for product data Q&A."""

    def __init__(
        self,
        model_name: str = config.llm_model_name,
        temperature: float = config.llm_temperature,
        max_tokens: int = config.llm_max_tokens,
        vector_store: Optional[VectorStore] = None,
        enable_web_search: bool = None,
        web_search_threshold: float = None,
        use_llm_search_system: bool = True,
        use_agent_system: bool = True,
    ):
        """Initialize the LangChain pipeline."""
        # Initialize the language model
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=config.openai_api_key,
            base_url=config.openai_base_url,
            stream_usage=True,
        )

        # Initialize or use provided vector store
        self.vector_store = vector_store or VectorStore()
        self.vector_store.initialize_vectorstore()

        # Initialize web search components
        self.enable_web_search = (
            enable_web_search
            if enable_web_search is not None
            else config.web_search_enabled
        )
        self.web_searcher = WebSearcher() if self.enable_web_search else None
        self.hybrid_searcher = (
            HybridSearcher(self.web_searcher, similarity_threshold=web_search_threshold)
            if self.enable_web_search
            and self.web_searcher
            and self.web_searcher.is_available()
            else None
        )

        # Initialize Product Introduction Agent (new system)
        self.use_agent_system = use_agent_system
        self.agent_system = (
            get_product_introduction_agent() if self.use_agent_system else None
        )

        # Legacy systems disabled - only using ProductIntroductionAgent
        self.use_llm_search_system = False
        self.llm_search_system = None

        # Set up the pipeline
        self.pipeline = self._create_pipeline()

        # Initialize logger
        self.logger = logger

    def _create_pipeline(self):
        """Create the LangChain pipeline for Q&A."""
        # Template for retrieval augmented generation using ChatPromptTemplate
        system_template = """
        Bạn là một trợ lý AI chuyên về sản phẩm điện tử. Hãy trả lời câu hỏi của người dùng dựa trên thông tin sản phẩm được cung cấp bên dưới.

        Bối cảnh:
        {context}

        Yêu cầu:
        1. Trả lời ngắn gọn, chính xác và chuyên nghiệp.
        2. Ưu tiên thông tin từ cơ sở dữ liệu sản phẩm (nếu có).
        3. Có thể tham khảo thông tin bổ sung từ tìm kiếm web để cung cấp thông tin cập nhật.
        4. Nếu không tìm thấy thông tin trong bối cảnh, hãy sử dụng tìm kiếm web để tìm thông tin liên quan đến lĩnh vực điện tử.
        5. Nếu người dùng yêu cầu so sánh các sản phẩm, hãy so sánh dựa trên các thông số kỹ thuật có sẵn.
        6. Chú ý đến các từ tham chiếu như "điện thoại trên", "sản phẩm đó", "thiết bị này" - hãy tham khảo lịch sử cuộc trò chuyện để hiểu rõ người dùng đang nói về sản phẩm nào.
        7. Khi người dùng nói "so sánh với điện thoại trên" hoặc tương tự, hãy xác định sản phẩm được nhắc đến trước đó trong cuộc trò chuyện.
        8. Chỉ trả lời "Tôi không có thông tin về điều này" khi câu hỏi hoàn toàn không liên quan đến lĩnh vực điện tử hoặc sản phẩm.
        """

        rag_prompt = ChatPromptTemplate.from_messages(
            [("system", system_template), ("human", "{question}")]
        )

        # Create a retrieval-augmented generation pipeline with hybrid search
        retriever = self.vector_store.get_vectorstore().as_retriever(
            search_kwargs={"k": 3}
        )

        # Define hybrid context retrieval function
        def get_hybrid_context(input_data: dict) -> str:
            # Extract original question and enhanced question
            original_question = input_data.get(
                "original_question", input_data.get("question", "")
            )
            enhanced_question = input_data.get("question", "")
            # Use enhanced question for vector search (with history context)
            vector_docs = retriever.invoke(enhanced_question)
            vector_context = self._format_vector_context(vector_docs)

            # Get conversation history for context
            conversation_history = getattr(self, "_current_conversation_history", None)

            # Use ProductIntroductionAgent if available (new system)
            if self.use_agent_system and self.agent_system:
                try:
                    agent_result = self.agent_system.process_query(
                        original_question, conversation_history
                    )

                    if agent_result["success"]:
                        self.logger.info(
                            f"ProductIntroductionAgent completed in {agent_result['processing_time']:.2f}s"
                        )
                        # Return agent response directly - agent handles all logic internally
                        return agent_result["response"]
                    else:
                        self.logger.warning(
                            f"ProductIntroductionAgent failed: {agent_result.get('error', 'Unknown error')}"
                        )
                        # Fall through to fallback logic

                except Exception as e:
                    self.logger.warning(
                        f"ProductIntroductionAgent failed, falling back: {e}"
                    )
                    # Fall through to fallback logic

            # Fallback to simplified rule-based logic (only when LLM system fails)
            should_search = (
                not vector_docs
                or len(vector_docs) < 2
                or any(
                    keyword in original_question.lower()
                    for keyword in [
                        "giá",
                        "so sánh",
                        "mới",
                        "2024",
                        "2025",
                        "khuyến mãi",
                    ]
                )
            )

            if should_search and self.web_searcher:
                # Extract clean search query that resolves references from history
                search_query = self._extract_search_query(
                    original_question, conversation_history
                )
                # Perform web search using clean search query
                web_results = self.web_searcher.search_product_info(search_query)

                # Combine results
                if vector_context and vector_context.strip():
                    formatted_web_results = self.web_searcher.format_search_results(
                        web_results
                    )
                    return f"{vector_context}\n\n{formatted_web_results}"
                return self.web_searcher.format_search_results(web_results)

            return vector_context

        # Build the pipeline
        rag_chain = (
            RunnableParallel(
                {
                    "context": RunnableLambda(get_hybrid_context),
                    "question": RunnableLambda(
                        lambda x: x.get("question", x) if isinstance(x, dict) else x
                    ),
                }
            )
            | rag_prompt
            | self.llm
            | StrOutputParser()
        )

        return rag_chain

    def _format_vector_context(self, docs: List[Any]) -> str:
        """Format context from vector store documents."""
        if not docs:
            return ""

        return "\n\n".join(
            [f"Sản phẩm {i + 1}:\n" + doc.page_content for i, doc in enumerate(docs)]
        )

    def answer_question(
        self, question: str, conversation_history: Optional[List[dict]] = None
    ) -> str:
        """Process a user question and return an answer."""
        try:
            # Store conversation history for web search access
            self._current_conversation_history = conversation_history
            # Include conversation history in the question context
            enhanced_question = self._enhance_question_with_history(
                question, conversation_history
            )
            # Create input with both original and enhanced questions
            pipeline_input = {
                "question": enhanced_question,
                "original_question": question,
            }
            response = self.pipeline.invoke(pipeline_input)
            return response
        except Exception as e:
            self.logger.error("Error answering question", error=e)
            return "Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi của bạn."
        finally:
            # Clean up temporary storage
            self._current_conversation_history = None

    def answer_question_stream(
        self, question: str, conversation_history: Optional[List[dict]] = None
    ) -> Iterator[str]:
        """Process a user question and stream the answer."""
        try:
            # Store conversation history for web search access
            self._current_conversation_history = conversation_history
            # Include conversation history in the question context
            enhanced_question = self._enhance_question_with_history(
                question, conversation_history
            )
            # Create input with both original and enhanced questions
            pipeline_input = {
                "question": enhanced_question,
                "original_question": question,
            }
            for chunk in self.pipeline.stream(pipeline_input):
                yield chunk
        except Exception as e:
            self.logger.error("Error streaming answer", error=e)
            yield "Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi của bạn."
        finally:
            # Clean up temporary storage
            self._current_conversation_history = None

    def _enhance_question_with_history(
        self, question: str, conversation_history: Optional[List[dict]] = None
    ) -> str:
        """Enhance the question with conversation history context."""
        if not conversation_history or len(conversation_history) == 0:
            return question
        # Build context from recent conversation history (last 2 messages for better performance)
        recent_history = (
            conversation_history[-2:]
            if len(conversation_history) > 2
            else conversation_history
        )
        context_parts = []
        for msg in recent_history:
            user_msg = msg.get("message", "")
            bot_response = msg.get("response", "")
            if user_msg and bot_response:
                context_parts.append(f"Người dùng: {user_msg}")
                context_parts.append(f"Trợ lý: {bot_response}")
        if context_parts:
            history_context = "\n".join(context_parts)
            enhanced_question = f"""Lịch sử cuộc trò chuyện gần đây:
{history_context}

Câu hỏi hiện tại: {question}

Lưu ý: Khi người dùng nói "điện thoại trên", "sản phẩm trên", "thiết bị đó" hoặc các từ tham chiếu tương tự, hãy tham khảo thông tin từ lịch sử cuộc trò chuyện ở trên."""
            return enhanced_question
        return question

    def _extract_search_query(
        self, question: str, conversation_history: Optional[List[dict]] = None
    ) -> str:
        """Extract clean search query from question, resolving references from history."""
        if not conversation_history:
            return question
        # Check if question contains references
        reference_phrases = [
            "điện thoại trên",
            "sản phẩm trên",
            "thiết bị trên",
            "máy trên",
            "điện thoại đó",
            "sản phẩm đó",
            "thiết bị đó",
            "máy đó",
            "điện thoại này",
            "sản phẩm này",
            "thiết bị này",
            "máy này",
        ]

        has_reference = any(phrase in question.lower() for phrase in reference_phrases)
        if not has_reference:
            return question
        # Find the most recent product mentioned in history
        recent_history = (
            conversation_history[-3:]
            if len(conversation_history) > 3
            else conversation_history
        )
        for msg in reversed(recent_history):
            user_msg = msg.get("message", "").lower()
            bot_response = msg.get("response", "").lower()
            # Look for product names in user messages and bot responses
            product_names = [
                "iphone",
                "samsung",
                "xiaomi",
                "oppo",
                "vivo",
                "realme",
                "oneplus",
                "huawei",
                "nokia",
                "sony",
                "lg",
                "motorola",
                "asus",
                "acer",
                "dell",
                "hp",
                "lenovo",
                "macbook",
                "ipad",
                "galaxy",
                "redmi",
                "mi ",
                "poco",
                "iqoo",
            ]
            for name in product_names:
                if name in user_msg or name in bot_response:
                    # Replace reference with the product name
                    clean_query = question.lower()
                    for phrase in reference_phrases:
                        clean_query = clean_query.replace(phrase, name)
                    return clean_query
        return question

    def add_conversation_memory(self, memory):
        """Add conversation memory to the pipeline (deprecated - use conversation_history parameter instead)."""
        # This method is kept for backward compatibility
        # Use conversation_history parameter in answer_question methods instead
        pass

    def get_search_info(self, question: str) -> dict:
        """Get detailed search information for debugging purposes."""
        try:
            # Get vector store results
            retriever = self.vector_store.get_vectorstore().as_retriever(
                search_kwargs={"k": 3}
            )
            vector_docs = retriever.invoke(question)

            info = {
                "vector_results_count": len(vector_docs),
                "vector_results": [
                    {"content": doc.page_content[:200] + "..."}
                    for doc in vector_docs[:2]
                ],
                "web_search_enabled": self.enable_web_search,
                "llm_search_system_enabled": self.use_llm_search_system,
                "agent_system_enabled": self.use_agent_system,
            }

            # Get ProductIntroductionAgent info if available
            if self.use_agent_system and self.agent_system:
                conversation_history = getattr(
                    self, "_current_conversation_history", None
                )
                agent_result = self.agent_system.process_query(
                    question, conversation_history
                )

                info.update(
                    {
                        "product_introduction_agent": {
                            "success": agent_result["success"],
                            "processing_time": agent_result["processing_time"],
                            "query_type": agent_result.get("query_type", "unknown"),
                        },
                        "agent_stats": self.agent_system.get_stats(),
                    }
                )

            # Fallback info for rule-based logic when agent is disabled
            elif self.hybrid_searcher:
                should_use_web = self.hybrid_searcher.should_use_web_search(
                    vector_docs, question
                )
                info["would_use_web_search"] = should_use_web

                if should_use_web:
                    web_results = self.web_searcher.search_product_info(question)
                    info["web_results_count"] = len(web_results)
                    info["web_results"] = [
                        {"title": result.title, "relevance": result.relevance_score}
                        for result in web_results[:2]
                    ]

            return info

        except Exception as e:
            return {"error": str(e)}

    def disable_web_search(self):
        """Disable web search functionality."""
        self.enable_web_search = False
        self.hybrid_searcher = None

    def enable_web_search_feature(self):
        """Enable web search functionality."""
        if not self.web_searcher:
            self.web_searcher = WebSearcher()

        if self.web_searcher and self.web_searcher.is_available():
            self.enable_web_search = True
            self.hybrid_searcher = HybridSearcher(self.web_searcher)

            # Recreate ProductIntroductionAgent with updated settings
            if self.use_agent_system:
                self.agent_system = get_product_introduction_agent()

            # Recreate pipeline with new settings
            self.pipeline = self._create_pipeline()
