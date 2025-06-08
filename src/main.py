"""
Main application entry point with functional composition.
"""

from typing import Optional
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.core.types import Result
from src.infrastructure.config import create_config_manager, get_logger
from src.services.qa_pipeline import create_qa_service
from src.utils.text_processing import load_and_process_data
from src.services.vector_store import index_chunks_to_vector_store

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class Application:
    """Main application class with functional composition."""

    def __init__(self):
        self.config_manager = None
        self.qa_service = None
        self.logger = None
        self.is_initialized = False

    def initialize(self) -> Result:
        """Initialize the application."""
        self.logger = get_logger()
        self.logger.info("Initializing application...")

        # Initialize configuration
        config_result = create_config_manager()
        if config_result.is_failure:
            self.logger.error(
                "Failed to initialize configuration", error=config_result.error
            )
            return config_result

        self.config_manager = config_result.value
        self.logger = self.config_manager.logger

        # Initialize Q&A service
        qa_service_result = create_qa_service(
            self.config_manager.llm_config,
            self.config_manager.vector_store_config,
            self.config_manager.embedding_config,
            self.config_manager.web_search_config,
        )

        if qa_service_result.is_failure:
            self.logger.error(
                "Failed to initialize Q&A service", error=qa_service_result.error
            )
            return qa_service_result

        self.qa_service = qa_service_result.value
        self.is_initialized = True

        self.logger.info("Application initialized successfully")
        return Result.success(self)

    def ingest_data(self, data_path: Optional[str] = None) -> Result:
        """Ingest data into the vector store."""
        if not self.is_initialized:
            return Result.failure(RuntimeError("Application not initialized"))

        data_path = data_path or self.config_manager.settings.cleaned_data_path

        self.logger.info("Starting data ingestion", data_path=data_path)

        # Load and process data
        chunks_result = load_and_process_data(
            data_path, self.config_manager.embedding_config, self.logger
        )

        if chunks_result.is_failure:
            self.logger.error(
                "Failed to load and process data", error=chunks_result.error
            )
            return chunks_result

        chunks = chunks_result.value

        # Index chunks to vector store
        vectorstore = self.qa_service._vectorstore
        index_result = index_chunks_to_vector_store(chunks, vectorstore)

        if index_result.is_failure:
            self.logger.error("Failed to index chunks", error=index_result.error)
            return index_result

        indexed_count = index_result.value
        self.logger.info(
            "Data ingestion completed",
            chunks_count=len(chunks),
            indexed_count=indexed_count,
        )

        return Result.success(indexed_count)

    def ask_question(self, question: str) -> Result:
        """Ask a question and get response."""
        if not self.is_initialized:
            return Result.failure(RuntimeError("Application not initialized"))

        if not question or not question.strip():
            return Result.failure(ValueError("Question cannot be empty"))

        try:
            response = self.qa_service.answer(question)
            return Result.success(response)
        except Exception as e:
            self.logger.error("Failed to answer question", question=question, error=e)
            return Result.failure(e)

    def ask_question_stream(self, question: str):
        """Ask a question and get streaming response."""
        if not self.is_initialized:
            yield "Application not initialized"
            return

        if not question or not question.strip():
            yield "Question cannot be empty"
            return

        try:
            yield from self.qa_service.answer_stream(question)
        except Exception as e:
            self.logger.error("Failed to stream answer", question=question, error=e)
            yield f"Error: {e}"

    def get_search_info(self, question: str) -> dict:
        """Get search information for debugging."""
        if not self.is_initialized:
            return {"error": "Application not initialized"}

        return self.qa_service.get_search_info(question)

    def toggle_web_search(self, enabled: bool) -> None:
        """Toggle web search functionality."""
        if not self.is_initialized:
            return

        self.config_manager.update_web_search_enabled(enabled)
        self.qa_service.update_web_search_config(enabled)

        self.logger.info("Web search toggled", enabled=enabled)

    def get_status(self) -> dict:
        """Get application status."""
        return {
            "initialized": self.is_initialized,
            "config_summary": self.config_manager.get_config_summary()
            if self.config_manager
            else {},
            "qa_service_ready": self.qa_service.is_initialized
            if self.qa_service
            else False,
        }


# Factory functions
def create_application() -> Result:
    """Create and initialize application."""
    app = Application()
    return app.initialize()


def create_simple_qa_function():
    """Create a simple Q&A function."""
    app_result = create_application()

    if app_result.is_failure:

        def error_qa(question: str) -> str:
            return f"Application initialization failed: {app_result.error}"

        return error_qa

    app = app_result.value

    def qa_function(question: str) -> str:
        result = app.ask_question(question)
        if result.is_success:
            return result.value.answer
        return f"Error: {result.error}"

    return qa_function


# CLI interface functions
def run_interactive_mode():
    """Run interactive Q&A mode."""
    print("Initializing application...")

    app_result = create_application()
    if app_result.is_failure:
        print(f"Failed to initialize application: {app_result.error}")
        return

    app = app_result.value
    print("Application initialized successfully!")
    print("Type 'exit' to quit, 'status' for status, 'toggle' to toggle web search")
    print("-" * 50)

    while True:
        try:
            question = input("\nQuestion: ").strip()

            if question.lower() == "exit":
                break
            elif question.lower() == "status":
                status = app.get_status()
                print(f"Status: {status}")
                continue
            elif question.lower() == "toggle":
                current_enabled = app.config_manager.web_search_config.enabled
                app.toggle_web_search(not current_enabled)
                print(f"Web search {'enabled' if not current_enabled else 'disabled'}")
                continue
            elif not question:
                continue

            print("\nAnswer: ", end="", flush=True)

            # Use streaming response
            for chunk in app.ask_question_stream(question):
                print(chunk, end="", flush=True)
            print()  # New line after streaming

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


def run_single_question(question: str, stream: bool = False):
    """Run single question mode."""
    app_result = create_application()
    if app_result.is_failure:
        print(f"Failed to initialize application: {app_result.error}")
        return

    app = app_result.value

    if stream:
        print("Answer: ", end="", flush=True)
        for chunk in app.ask_question_stream(question):
            print(chunk, end="", flush=True)
        print()
    else:
        result = app.ask_question(question)
        if result.is_success:
            response = result.value
            print(f"Question: {response.question}")
            print(f"Answer: {response.answer}")
            print(f"Processing time: {response.processing_time:.2f}s")
            print(f"Vector results: {response.vector_results_count}")
            print(f"Web results: {response.web_results_count}")
        else:
            print(f"Error: {result.error}")


def run_data_ingestion(data_path: Optional[str] = None):
    """Run data ingestion."""
    print("Initializing application for data ingestion...")

    app_result = create_application()
    if app_result.is_failure:
        print(f"Failed to initialize application: {app_result.error}")
        return

    app = app_result.value

    print("Starting data ingestion...")
    ingest_result = app.ingest_data(data_path)

    if ingest_result.is_success:
        print(
            f"Data ingestion completed successfully. Indexed {ingest_result.value} documents."
        )
    else:
        print(f"Data ingestion failed: {ingest_result.error}")


# Main entry point
def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Q&A System for Electronic Products")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Interactive mode
    interactive_parser = subparsers.add_parser(
        "interactive", help="Run interactive Q&A mode"
    )

    # Single question mode
    question_parser = subparsers.add_parser("ask", help="Ask a single question")
    question_parser.add_argument("question", help="Question to ask")
    question_parser.add_argument(
        "--stream", action="store_true", help="Use streaming response"
    )

    # Data ingestion mode
    ingest_parser = subparsers.add_parser(
        "ingest", help="Ingest data into vector store"
    )
    ingest_parser.add_argument("--data-path", help="Path to data file")

    args = parser.parse_args()

    if args.command == "interactive":
        run_interactive_mode()
    elif args.command == "ask":
        run_single_question(args.question, args.stream)
    elif args.command == "ingest":
        run_data_ingestion(args.data_path)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
