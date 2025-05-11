"""
Module xử lý tương tác với người dùng qua chatbot
"""

from typing import List, Dict, Any, Optional

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnablePassthrough

from ..config import settings, logger
from .vector_store import VectorStore

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__license__ = "MIT"
__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"

class ProductChatbot:
    """
    Lớp xử lý tương tác với người dùng qua chatbot
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """
        Khởi tạo ProductChatbot

        Args:
            vector_store: Đối tượng VectorStore để tra cứu dữ liệu
            model: Tên model LLM (Large Language Model)
            temperature: Nhiệt độ của model LLM
        """
        self.vector_store = vector_store or VectorStore()
        
        # Khởi tạo model LLM
        self.model = model or settings.model_name
        self.temperature = temperature or settings.temperature
        
        self.llm = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            api_key=settings.openai_api_key.get_secret_value(),
            base_url=settings.openai_api_base,
        )
        
        # Xây dựng chain RAG (Retrieval Augmented Generation)
        self._build_retrieval_chain()
        
        # Lưu trữ lịch sử hội thoại
        self.chat_history = []
        
        logger.info(
            "Khởi tạo ProductChatbot",
            model=self.model,
            temperature=self.temperature,
        )

    def _build_retrieval_chain(self) -> None:
        """Xây dựng chain RAG (Retrieval Augmented Generation)"""
        # Khởi tạo retriever
        retriever = self.vector_store.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 4},
        )
        
        # Template cho context
        context_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Bạn là một trợ lý ảo giới thiệu sản phẩm. "
                    "Sử dụng thông tin dưới đây để trả lời câu hỏi của người dùng. "
                    "Nếu bạn không biết câu trả lời, hãy nói rằng bạn không có thông tin "
                    "và đề nghị người dùng liên hệ với bộ phận hỗ trợ khách hàng.\n\n"
                    "Thông tin sản phẩm:\n{context}",
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}"),
            ]
        )
        
        # Tạo chain RAG
        self.retrieval_chain = (
            {
                "context": retriever, 
                "question": RunnablePassthrough(),
                "chat_history": lambda _: self.chat_history,
            }
            | context_prompt
            | self.llm
            | StrOutputParser()
        )

    def _format_chat_history(self) -> List[Dict[str, Any]]:
        """
        Định dạng lịch sử hội thoại cho prompt
        
        Returns:
            Danh sách tin nhắn đã định dạng
        """
        formatted_history = []
        
        for message in self.chat_history:
            if isinstance(message, HumanMessage):
                formatted_history.append({"type": "human", "content": message.content})
            elif isinstance(message, AIMessage):
                formatted_history.append({"type": "ai", "content": message.content})
                
        return formatted_history

    def ask(self, question: str) -> str:
        """
        Đặt câu hỏi cho chatbot

        Args:
            question: Câu hỏi của người dùng

        Returns:
            Câu trả lời từ chatbot
        """
        if not question.strip():
            return "Vui lòng đặt một câu hỏi."
        
        logger.info("Nhận câu hỏi", question=question)
        
        # Thêm câu hỏi vào lịch sử hội thoại
        self.chat_history.append(HumanMessage(content=question))
        
        try:
            # Lấy câu trả lời từ chain RAG
            response = self.retrieval_chain.invoke(question)
            
            # Thêm câu trả lời vào lịch sử hội thoại
            self.chat_history.append(AIMessage(content=response))
            
            logger.info("Trả lời câu hỏi", response=response[:100] + "..." if len(response) > 100 else response)
            return response
            
        except Exception as e:
            error_message = f"Đã xảy ra lỗi khi xử lý câu hỏi: {str(e)}"
            logger.error(error_message)
            return error_message

    def reset_chat_history(self) -> None:
        """Xóa lịch sử hội thoại"""
        self.chat_history = []
        logger.info("Đã xóa lịch sử hội thoại")

    def get_chat_history(self) -> List[Dict[str, str]]:
        """
        Lấy lịch sử hội thoại

        Returns:
            Danh sách tin nhắn trong lịch sử hội thoại
        """
        history = []
        
        for message in self.chat_history:
            if isinstance(message, HumanMessage):
                history.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage):
                history.append({"role": "assistant", "content": message.content})
                
        return history