"""
Core LangChain pipeline for question answering over product data.
"""

from typing import Any, Iterator, List, Optional

from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import (
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)
from langchain_openai import ChatOpenAI

from .config import config
from .vectorstore import VectorStore
from .web_search import HybridSearcher, WebSearcher

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
        self.enable_web_search = enable_web_search if enable_web_search is not None else config.web_search_enabled
        self.web_searcher = WebSearcher() if self.enable_web_search else None
        self.hybrid_searcher = HybridSearcher(
            self.web_searcher,
            similarity_threshold=web_search_threshold
        ) if self.enable_web_search and self.web_searcher and self.web_searcher.is_available() else None

        # Set up the pipeline
        self.pipeline = self._create_pipeline()

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
        4. Nếu không tìm thấy thông tin trong bối cảnh, hãy nói "Tôi không có thông tin về điều này."
        5. Nếu người dùng yêu cầu so sánh các sản phẩm, hãy so sánh dựa trên các thông số kỹ thuật có sẵn.
        6. Khi sử dụng thông tin từ web, hãy ghi rõ nguồn tham khảo.
        """

        rag_prompt = ChatPromptTemplate.from_messages(
            [("system", system_template), ("human", "{question}")]
        )

        # Create a retrieval-augmented generation pipeline with hybrid search
        retriever = self.vector_store.get_vectorstore().as_retriever(
            search_kwargs={"k": 3}
        )

        # Define hybrid context retrieval function
        def get_hybrid_context(question: str) -> str:
            # Get vector store results
            vector_docs = retriever.invoke(question)
            vector_context = self._format_vector_context(vector_docs)

            # Check if we need web search
            if (self.hybrid_searcher and
                self.hybrid_searcher.should_use_web_search(vector_docs, question)):

                # Perform web search
                web_results = self.web_searcher.search_product_info(question)

                # Combine results
                return self.hybrid_searcher.combine_results(vector_context, web_results)

            return vector_context

        # Build the pipeline
        rag_chain = (
            RunnableParallel(
                {
                    "context": RunnableLambda(get_hybrid_context),
                    "question": RunnablePassthrough(),
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
            [
                f"Sản phẩm {i + 1}:\n" + doc.page_content
                for i, doc in enumerate(docs)
            ]
        )

    def answer_question(self, question: str) -> str:
        """Process a user question and return an answer."""
        try:
            response = self.pipeline.invoke(question)
            return response
        except Exception as e:
            print(f"Error answering question: {e}")
            return "Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi của bạn."

    def answer_question_stream(self, question: str) -> Iterator[str]:
        """Process a user question and stream the answer."""
        try:
            for chunk in self.pipeline.stream(question):
                yield chunk
        except Exception as e:
            print(f"Error streaming answer: {e}")
            yield "Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi của bạn."

    def add_conversation_memory(self, memory):
        """Add conversation memory to the pipeline (to be implemented)."""
        # This would be implemented to incorporate conversation history
        # Will require setting up a conversational chain with memory
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
                "vector_results": [{"content": doc.page_content[:200] + "..."} for doc in vector_docs[:2]],
                "web_search_enabled": self.enable_web_search,
                "web_search_available": self.hybrid_searcher is not None,
            }

            # Check if web search would be used
            if self.hybrid_searcher:
                should_use_web = self.hybrid_searcher.should_use_web_search(vector_docs, question)
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
            # Recreate pipeline with new settings
            self.pipeline = self._create_pipeline()
