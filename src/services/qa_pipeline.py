"""
Functional Q&A pipeline service with immutable operations and streaming support.
"""

from typing import Any, Dict, Iterator, List, Optional

from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import (
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)
from langchain_openai import ChatOpenAI

from ..core.types import Result, safe_call, timing
from ..domain.models import (
    QAResponse,
    QueryContext,
    VectorSearchResult,
    LLMConfig,
    VectorStoreConfig,
    WebSearchConfig,
    EmbeddingConfig,
)
from ..services.vector_store import (
    initialize_vector_store,
    search_vector_store,
    create_vector_context_from_results,
)
from ..services.web_search import (
    search_product_info,
    should_use_web_search_for_query,
    combine_vector_and_web_context,
)

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


# Pure functions for prompt creation


def create_system_prompt() -> str:
    """Create system prompt for the Q&A pipeline."""
    return """
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


def create_chat_prompt() -> ChatPromptTemplate:
    """Create chat prompt template."""
    system_template = create_system_prompt()
    return ChatPromptTemplate.from_messages(
        [("system", system_template), ("human", "{question}")]
    )


def create_llm_instance(config: LLMConfig) -> Result:
    """Create LLM instance safely."""

    @safe_call
    def _create():
        return ChatOpenAI(
            model=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            api_key=config.api_key,
            base_url=config.base_url,
            stream_usage=True,
        )

    return _create()


# Context retrieval functions


def retrieve_vector_context(query: str, vectorstore, k: int = 3) -> Result:
    """Retrieve context from vector store."""
    return search_vector_store(vectorstore, query, k).map(
        create_vector_context_from_results
    )


def should_retrieve_web_context(
    query: str, vector_results: List[VectorSearchResult], web_config: WebSearchConfig
) -> bool:
    """Determine if web search should be performed."""
    if not web_config.enabled:
        return False

    return should_use_web_search_for_query(
        query, len(vector_results), web_config.similarity_threshold
    )


def retrieve_web_context(query: str, web_config: WebSearchConfig) -> Result:
    """Retrieve context from web search."""
    return search_product_info(query, web_config)


def create_hybrid_context(
    query: str, vectorstore, web_config: WebSearchConfig
) -> Result:
    """Create hybrid context from vector and web sources."""
    # Get vector context
    vector_result = retrieve_vector_context(query, vectorstore)

    if vector_result.is_failure:
        return vector_result

    vector_context = vector_result.value

    # Determine if web search is needed
    vector_search_result = search_vector_store(vectorstore, query, 3)
    if vector_search_result.is_failure:
        vector_results = []
    else:
        vector_results = vector_search_result.value

    if should_retrieve_web_context(query, vector_results, web_config):
        web_result = retrieve_web_context(query, web_config)

        if web_result.is_success:
            web_results = web_result.value
            combined_context = combine_vector_and_web_context(
                vector_context, web_results
            )

            return Result.success(
                QueryContext(
                    query=query,
                    vector_results=vector_results,
                    web_results=web_results,
                    combined_context=combined_context,
                )
            )

    return Result.success(
        QueryContext(
            query=query,
            vector_results=vector_results,
            web_results=[],
            combined_context=vector_context,
        )
    )


# Pipeline creation functions


def create_context_retriever(vectorstore, web_config: WebSearchConfig):
    """Create context retrieval function."""

    def retrieve_context(query: str) -> str:
        context_result = create_hybrid_context(query, vectorstore, web_config)

        if context_result.is_failure:
            return "Không thể lấy thông tin từ cơ sở dữ liệu."

        return context_result.value.combined_context

    return retrieve_context


def create_rag_pipeline(llm: ChatOpenAI, context_retriever) -> Any:
    """Create RAG (Retrieval Augmented Generation) pipeline."""
    prompt = create_chat_prompt()

    return (
        RunnableParallel(
            {
                "context": RunnableLambda(context_retriever),
                "question": RunnablePassthrough(),
            }
        )
        | prompt
        | llm
        | StrOutputParser()
    )


# High-level pipeline operations


def initialize_qa_pipeline(
    llm_config: LLMConfig,
    vector_config: VectorStoreConfig,
    embedding_config: EmbeddingConfig,
    web_config: WebSearchConfig,
) -> Result:
    """Initialize complete Q&A pipeline."""

    def _initialize():
        # Initialize LLM
        llm_result = create_llm_instance(llm_config)
        if llm_result.is_failure:
            return llm_result

        llm = llm_result.value

        # Initialize vector store
        vector_store_result = initialize_vector_store(vector_config, embedding_config)
        if vector_store_result.is_failure:
            return vector_store_result

        vectorstore = vector_store_result.value["vectorstore"]

        # Create context retriever
        context_retriever = create_context_retriever(vectorstore, web_config)

        # Create RAG pipeline
        rag_pipeline = create_rag_pipeline(llm, context_retriever)

        return Result.success(
            {
                "llm": llm,
                "vectorstore": vectorstore,
                "context_retriever": context_retriever,
                "rag_pipeline": rag_pipeline,
                "vector_store_info": vector_store_result.value,
            }
        )

    return _initialize()


@timing
def answer_question_with_pipeline(pipeline: Any, question: str) -> str:
    """Answer question using the pipeline."""

    @safe_call
    def _answer():
        return pipeline.invoke(question)

    result = _answer()

    if result.is_failure:
        return "Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi của bạn."

    return result.value


def answer_question_streaming(pipeline: Any, question: str) -> Iterator[str]:
    """Answer question with streaming response."""
    try:
        for chunk in pipeline.stream(question):
            yield chunk
    except Exception as e:
        yield f"Lỗi khi xử lý streaming: {e}"


def create_qa_response(
    question: str,
    answer: str,
    processing_time: float,
    context: Optional[QueryContext] = None,
) -> QAResponse:
    """Create QAResponse object."""
    vector_count = len(context.vector_results) if context else 0
    web_count = len(context.web_results) if context else 0
    sources = []

    if context and context.web_results:
        sources = [result.href for result in context.web_results if result.href]

    return QAResponse(
        question=question,
        answer=answer,
        processing_time=processing_time,
        vector_results_count=vector_count,
        web_results_count=web_count,
        sources=sources,
    )


# Service class for stateful operations


class QAPipelineService:
    """Q&A Pipeline Service with functional composition."""

    def __init__(
        self,
        llm_config: LLMConfig,
        vector_config: VectorStoreConfig,
        embedding_config: EmbeddingConfig,
        web_config: WebSearchConfig,
    ):
        """Initialize pipeline service."""
        self.llm_config = llm_config
        self.vector_config = vector_config
        self.embedding_config = embedding_config
        self.web_config = web_config

        self._pipeline = None
        self._vectorstore = None
        self._context_retriever = None
        self._is_initialized = False

    def initialize(self) -> Result:
        """Initialize the pipeline service."""
        init_result = initialize_qa_pipeline(
            self.llm_config, self.vector_config, self.embedding_config, self.web_config
        )

        if init_result.is_success:
            components = init_result.value
            self._pipeline = components["rag_pipeline"]
            self._vectorstore = components["vectorstore"]
            self._context_retriever = components["context_retriever"]
            self._is_initialized = True

        return init_result

    def answer(self, question: str) -> QAResponse:
        """Answer a question."""
        if not self._is_initialized:
            return QAResponse(
                question=question,
                answer="Pipeline not initialized",
                processing_time=0.0,
            )

        answer, processing_time = answer_question_with_pipeline(
            self._pipeline, question
        )

        # Get context information for response
        context_result = create_hybrid_context(
            question, self._vectorstore, self.web_config
        )
        context = context_result.value if context_result.is_success else None

        return create_qa_response(question, answer, processing_time, context)

    def answer_stream(self, question: str) -> Iterator[str]:
        """Answer a question with streaming response."""
        if not self._is_initialized:
            yield "Pipeline not initialized"
            return

        yield from answer_question_streaming(self._pipeline, question)

    def get_search_info(self, question: str) -> Dict[str, Any]:
        """Get detailed search information for debugging."""
        if not self._is_initialized:
            return {"error": "Pipeline not initialized"}

        try:
            # Get context information
            context_result = create_hybrid_context(
                question, self._vectorstore, self.web_config
            )

            if context_result.is_failure:
                return {"error": str(context_result.error)}

            context = context_result.value

            return {
                "vector_results_count": len(context.vector_results),
                "web_results_count": len(context.web_results),
                "vector_results": [
                    {
                        "content": result.content[:200] + "...",
                        "score": result.similarity_score,
                    }
                    for result in context.vector_results[:2]
                ],
                "web_results": [
                    {"title": result.title, "relevance": result.relevance_score}
                    for result in context.web_results[:2]
                ],
                "web_search_enabled": self.web_config.enabled,
                "would_use_web_search": should_retrieve_web_context(
                    question, context.vector_results, self.web_config
                ),
            }

        except Exception as e:
            return {"error": str(e)}

    def update_web_search_config(self, enabled: bool) -> None:
        """Update web search configuration."""
        self.web_config = self.web_config.__class__(
            **{**self.web_config.__dict__, "enabled": enabled}
        )

    @property
    def is_initialized(self) -> bool:
        """Check if pipeline is initialized."""
        return self._is_initialized


# Factory functions


def create_qa_service(
    llm_config: LLMConfig,
    vector_config: VectorStoreConfig,
    embedding_config: EmbeddingConfig,
    web_config: WebSearchConfig,
) -> Result:
    """Create and initialize QA service."""
    service = QAPipelineService(llm_config, vector_config, embedding_config, web_config)
    init_result = service.initialize()

    if init_result.is_success:
        return Result.success(service)

    return init_result


def create_simple_qa_function(service: QAPipelineService):
    """Create a simple Q&A function from service."""
    return lambda question: service.answer(question).answer


def create_streaming_qa_function(service: QAPipelineService):
    """Create a streaming Q&A function from service."""
    return lambda question: service.answer_stream(question)


# Configuration validation


def validate_qa_pipeline_configs(
    llm_config: LLMConfig,
    vector_config: VectorStoreConfig,
    embedding_config: EmbeddingConfig,
    web_config: WebSearchConfig,
) -> Result:
    """Validate all pipeline configurations."""
    # Validate LLM config
    if not llm_config.model_name:
        return Result.failure(ValueError("LLM model name is required"))

    if not llm_config.api_key:
        return Result.failure(ValueError("LLM API key is required"))

    # Validate vector config
    if not vector_config.collection_name:
        return Result.failure(ValueError("Vector store collection name is required"))

    # Validate embedding config
    if not embedding_config.model_name:
        return Result.failure(ValueError("Embedding model name is required"))

    # Validate temperature range
    if not (0.0 <= llm_config.temperature <= 2.0):
        return Result.failure(ValueError("LLM temperature must be between 0.0 and 2.0"))

    return Result.success("All configurations valid")


# Monitoring and metrics


def calculate_pipeline_metrics(responses: List[QAResponse]) -> Dict[str, Any]:
    """Calculate metrics for pipeline performance."""
    if not responses:
        return {
            "total_questions": 0,
            "average_processing_time": 0.0,
            "web_search_usage": 0.0,
            "average_sources": 0.0,
        }

    total_questions = len(responses)
    total_processing_time = sum(r.processing_time for r in responses)
    web_search_used = sum(1 for r in responses if r.web_results_count > 0)
    total_sources = sum(len(r.sources) for r in responses)

    return {
        "total_questions": total_questions,
        "average_processing_time": total_processing_time / total_questions,
        "web_search_usage": web_search_used / total_questions,
        "average_sources": total_sources / total_questions,
        "processing_time_distribution": {
            "fast": sum(1 for r in responses if r.processing_time < 2.0),
            "medium": sum(1 for r in responses if 2.0 <= r.processing_time < 5.0),
            "slow": sum(1 for r in responses if r.processing_time >= 5.0),
        },
    }
