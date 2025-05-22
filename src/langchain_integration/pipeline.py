"""
Core LangChain pipeline for question answering over product data.
"""

from typing import Optional, Iterator

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import (
    RunnableParallel,
    RunnablePassthrough,
    RunnableLambda,
)

from .config import config
from .vectorstore import VectorStore


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
    ):
        """Initialize the LangChain pipeline."""
        # Initialize the language model
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=config.openai_api_key,
            base_url=config.openai_base_url,
            streaming=True,
        )

        # Initialize or use provided vector store
        self.vector_store = vector_store or VectorStore()
        self.vector_store.initialize_vectorstore()

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
        2. Chỉ sử dụng thông tin trong bối cảnh đã cung cấp.
        3. Nếu không tìm thấy thông tin trong bối cảnh, hãy nói "Tôi không có thông tin về điều này."
        4. Nếu người dùng yêu cầu so sánh các sản phẩm, hãy so sánh dựa trên các thông số kỹ thuật có sẵn.
        """

        rag_prompt = ChatPromptTemplate.from_messages(
            [("system", system_template), ("human", "{question}")]
        )

        # Create a retrieval-augmented generation pipeline
        retriever = self.vector_store.get_vectorstore().as_retriever(
            search_kwargs={"k": 3}
        )

        # Define a function to format context from retrieved documents
        def format_context(docs):
            return "\n\n".join(
                [
                    f"Sản phẩm {i + 1}:\n" + doc.page_content
                    for i, doc in enumerate(docs)
                ]
            )

        # Build the pipeline
        rag_chain = (
            RunnableParallel(
                {
                    "context": retriever | RunnableLambda(format_context),
                    "question": RunnablePassthrough(),
                }
            )
            | rag_prompt
            | self.llm
            | StrOutputParser()
        )

        return rag_chain

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
