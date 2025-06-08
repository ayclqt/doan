"""
CLI tool để truy vấn hệ thống hỏi đáp sản phẩm sử dụng functional architecture.
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional
from enum import Enum

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich import print as rprint
from rich.table import Table

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src import create_application, get_logger, QAResponse

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


# Khởi tạo Typer và Rich Console
app = typer.Typer(
    help="Hệ thống hỏi đáp sản phẩm điện tử với functional programming",
    add_completion=False,
)
console = Console()


class OutputFormat(str, Enum):
    """Định dạng hiển thị kết quả."""

    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"


class Mode(str, Enum):
    """Chế độ hiển thị kết quả."""

    BLOCK = "block"
    STREAM = "stream"  # Chế độ mặc định


def get_qa_application():
    """Khởi tạo ứng dụng hỏi đáp với functional architecture."""
    with console.status(
        "[bold green]Đang khởi tạo hệ thống hỏi đáp với functional architecture..."
    ):
        app_result = create_application()

        if app_result.is_failure:
            console.print(f"[bold red]❌ Lỗi khởi tạo: {app_result.error}[/bold red]")
            raise typer.Exit(1)

        return app_result.value


def interactive_mode(
    output_format: OutputFormat = OutputFormat.TEXT,
    show_sources: bool = False,
    mode: Mode = Mode.STREAM,
) -> None:
    """Chạy chế độ tương tác để nhập nhiều câu hỏi."""
    # Initialize application
    try:
        qa_app = get_qa_application()
        logger = get_logger()
    except typer.Exit:
        return

    rprint(
        Panel.fit(
            "[bold cyan]🤖 Hệ thống hỏi đáp sản phẩm (Functional Architecture)[/bold cyan]\n"
            "[italic]Gõ 'exit' để thoát, 'help' để xem trợ giúp[/italic]\n"
            "[dim]Powered by functional programming & msgspec[/dim]",
            border_style="blue",
        )
    )

    history = []

    # Show initial status
    status = qa_app.get_status()
    if status["initialized"]:
        console.print("✅ [green]Hệ thống đã sẵn sàng![/green]")
    else:
        console.print("⚠️ [yellow]Hệ thống chưa hoàn toàn sẵn sàng[/yellow]")

    while True:
        try:
            query = Prompt.ask("\n[bold green]❓ Câu hỏi của bạn")

            if query.lower() == "exit":
                console.print("👋 [cyan]Tạm biệt![/cyan]")
                break

            if query.lower() == "help":
                show_help()
                continue

            if query.lower() == "clear":
                os.system("cls" if os.name == "nt" else "clear")
                continue

            if query.lower() == "history":
                show_history(history)
                continue

            if query.lower() == "status":
                show_status(qa_app)
                continue

            if query.lower() == "toggle":
                toggle_web_search(qa_app)
                continue

            if not query.strip():
                continue

            start_time = time.time()

            if mode == Mode.STREAM:
                # Hiển thị kết quả theo chế độ streaming
                answer = display_streaming_answer(query, qa_app, output_format)
                end_time = time.time()

                # Create response object for history
                response = QAResponse(
                    question=query, answer=answer, processing_time=end_time - start_time
                )
            else:
                # Hiển thị kết quả theo chế độ block
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[bold green]🔄 Đang xử lý câu hỏi..."),
                    transient=True,
                ) as progress:
                    progress.add_task("processing", total=None)

                    result = qa_app.ask_question(query)
                    end_time = time.time()

                    if result.is_success:
                        response = result.value
                        display_answer(response, output_format, show_sources)
                    else:
                        console.print(f"[bold red]❌ Lỗi: {result.error}[/bold red]")
                        continue

            history.append(
                {
                    "question": response.question,
                    "answer": response.answer,
                    "processing_time": response.processing_time,
                    "vector_results": response.vector_results_count,
                    "web_results": response.web_results_count,
                }
            )

            # Hiển thị thông tin xử lý
            processing_time = response.processing_time
            console.print(
                f"\n[bold]⏱️  Thời gian xử lý:[/bold] {processing_time:.2f} giây"
            )

            if show_sources and response.sources:
                console.print(
                    f"[bold]📚 Nguồn tham khảo:[/bold] {len(response.sources)} nguồn"
                )

        except KeyboardInterrupt:
            console.print("\n👋 [cyan]Tạm biệt![/cyan]")
            break
        except Exception as e:
            console.print(f"[bold red]❌ Lỗi không mong muốn: {e}[/bold red]")
            logger.error("Unexpected error in interactive mode", error=e)


def show_help():
    """Hiển thị trợ giúp cho chế độ tương tác."""
    help_table = Table(title="🔧 Lệnh Có Sẵn")
    help_table.add_column("Lệnh", style="cyan", no_wrap=True)
    help_table.add_column("Mô tả", style="green")

    help_table.add_row("exit", "Thoát khỏi chương trình")
    help_table.add_row("help", "Hiển thị menu trợ giúp này")
    help_table.add_row("clear", "Xóa màn hình")
    help_table.add_row("history", "Hiển thị lịch sử câu hỏi và trả lời")
    help_table.add_row("status", "Hiển thị trạng thái hệ thống")
    help_table.add_row("toggle", "Bật/tắt tìm kiếm web")

    console.print(help_table)


def show_history(history):
    """Hiển thị lịch sử câu hỏi và trả lời."""
    if not history:
        rprint("[italic yellow]📝 Chưa có lịch sử câu hỏi.[/italic yellow]")
        return

    history_table = Table(title="📚 Lịch Sử Hỏi Đáp")
    history_table.add_column("STT", style="cyan", no_wrap=True)
    history_table.add_column("Câu Hỏi", style="green")
    history_table.add_column("Trả Lời", style="blue")
    history_table.add_column("Thời gian", style="yellow")
    history_table.add_column("Vector", style="magenta")
    history_table.add_column("Web", style="red")

    for i, item in enumerate(history, 1):
        history_table.add_row(
            str(i),
            item["question"][:50] + ("..." if len(item["question"]) > 50 else ""),
            item["answer"][:50] + ("..." if len(item["answer"]) > 50 else ""),
            f"{item.get('processing_time', 0):.2f}s",
            str(item.get("vector_results", 0)),
            str(item.get("web_results", 0)),
        )

    console.print(history_table)


def show_status(qa_app):
    """Hiển thị trạng thái hệ thống."""
    status = qa_app.get_status()

    status_table = Table(title="🔍 Trạng Thái Hệ Thống")
    status_table.add_column("Thành phần", style="cyan")
    status_table.add_column("Trạng thái", style="green")

    status_table.add_row(
        "Ứng dụng", "✅ Hoạt động" if status["initialized"] else "❌ Chưa khởi tạo"
    )
    status_table.add_row(
        "Q&A Service",
        "✅ Hoạt động" if status["qa_service_ready"] else "❌ Chưa sẵn sàng",
    )

    config_summary = status.get("config_summary", {})
    if config_summary:
        status_table.add_row("LLM Model", config_summary.get("llm_model", "N/A"))
        status_table.add_row(
            "Embedding Model", config_summary.get("embedding_model", "N/A")
        )
        status_table.add_row(
            "Web Search",
            "✅ Bật" if config_summary.get("web_search_enabled") else "❌ Tắt",
        )

        vector_store = config_summary.get("vector_store", {})
        if vector_store:
            status_table.add_row(
                "Vector Store", f"{vector_store.get('url')}:{vector_store.get('port')}"
            )

    console.print(status_table)


def toggle_web_search(qa_app):
    """Bật/tắt tìm kiếm web."""
    status = qa_app.get_status()
    config_summary = status.get("config_summary", {})
    current_enabled = config_summary.get("web_search_enabled", False)

    qa_app.toggle_web_search(not current_enabled)

    new_status = "bật" if not current_enabled else "tắt"
    console.print(f"🔄 [cyan]Đã {new_status} tìm kiếm web[/cyan]")


def display_streaming_answer(query, qa_app, output_format):
    """Hiển thị câu trả lời theo chế độ streaming."""
    console.print(f"\n[bold green]❓ Q:[/bold green] {query}")
    console.print("\n[bold blue]🤖 A:[/bold blue] ", end="")

    # Lưu câu trả lời đầy đủ để trả về
    full_answer = ""

    try:
        # Phục vụ stream từng phần
        for chunk in qa_app.ask_question_stream(query):
            console.print(chunk, end="", highlight=False)
            full_answer += chunk
    except Exception as e:
        error_msg = f"Lỗi khi xử lý streaming: {e}"
        console.print(f"\n[bold red]❌ {error_msg}[/bold red]")
        return error_msg

    console.print()  # Xuống dòng sau khi hoàn thành
    return full_answer


def display_answer(
    response: QAResponse, output_format: OutputFormat, show_sources: bool = False
):
    """Hiển thị câu trả lời theo định dạng được chọn."""
    if output_format == OutputFormat.TEXT:
        content = f"[bold green]❓ Q:[/bold green] {response.question}\n\n[bold blue]🤖 A:[/bold blue] {response.answer}"

        if show_sources and response.sources:
            content += "\n\n[bold yellow]📚 Nguồn:[/bold yellow]\n" + "\n".join(
                f"• {source}" for source in response.sources[:3]
            )

        rprint(Panel(content, title="💬 Kết quả", border_style="green"))

    elif output_format == OutputFormat.MARKDOWN:
        rprint(
            Panel(
                f"[bold green]❓ Câu hỏi:[/bold green]\n{response.question}\n\n[bold blue]🤖 Trả lời:[/bold blue]",
                title="💬 Kết quả",
                border_style="green",
            )
        )
        console.print(Markdown(response.answer))

        if show_sources and response.sources:
            console.print("\n[bold yellow]📚 Nguồn tham khảo:[/bold yellow]")
            for source in response.sources[:3]:
                console.print(f"• {source}")

    elif output_format == OutputFormat.JSON:
        import json

        result = response.to_dict()

        rprint(
            Panel(
                json.dumps(result, ensure_ascii=False, indent=2),
                title="📄 JSON Result",
                border_style="green",
            )
        )


@app.command()
def query(
    query: Optional[str] = typer.Option(
        None, "--query", "-q", help="Câu hỏi cần truy vấn"
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Chạy ở chế độ tương tác"
    ),
    output_format: OutputFormat = typer.Option(
        OutputFormat.TEXT, "--format", "-f", help="Định dạng hiển thị đầu ra"
    ),
    show_sources: bool = typer.Option(
        False, "--sources", "-s", help="Hiển thị thông tin nguồn dữ liệu (nếu có)"
    ),
    mode: Mode = typer.Option(
        Mode.STREAM,
        "--mode",
        "-m",
        help="Chế độ hiển thị: stream (mặc định) hoặc block",
    ),
):
    """Truy vấn hệ thống hỏi đáp sản phẩm với functional architecture."""
    if interactive:
        interactive_mode(output_format, show_sources, mode)
    elif query:
        # Khởi tạo ứng dụng
        try:
            qa_app = get_qa_application()
        except typer.Exit:
            return

        start_time = time.time()

        if mode == Mode.STREAM:
            # Hiển thị kết quả theo chế độ streaming
            answer = display_streaming_answer(query, qa_app, output_format)
            end_time = time.time()

            console.print(
                f"\n[bold]⏱️  Thời gian xử lý:[/bold] {end_time - start_time:.2f} giây"
            )
        else:
            # Hiển thị kết quả theo chế độ block
            result = qa_app.ask_question(query)
            end_time = time.time()

            if result.is_success:
                response = result.value
                display_answer(response, output_format, show_sources)

                console.print(
                    f"\n[bold]⏱️  Thời gian xử lý:[/bold] {response.processing_time:.2f} giây"
                )
                console.print(
                    f"[bold]📊 Thống kê:[/bold] Vector: {response.vector_results_count}, Web: {response.web_results_count}"
                )
            else:
                console.print(f"[bold red]❌ Lỗi: {result.error}[/bold red]")
                raise typer.Exit(1)
    else:
        console.print(
            "[yellow]⚠️  Vui lòng cung cấp một câu hỏi hoặc sử dụng chế độ tương tác.[/yellow]"
        )
        console.print(
            "Sử dụng: [cyan]python query_cli.py --help[/cyan] để xem hướng dẫn"
        )
        raise typer.Exit(1)


@app.command()
def info():
    """Hiển thị thông tin về hệ thống hỏi đáp."""
    rprint(
        Panel.fit(
            "[bold cyan]🤖 Hệ thống hỏi đáp sản phẩm điện tử (v2.0)[/bold cyan]\n\n"
            "[bold]🔧 Công nghệ:[/bold]\n"
            "• [green]Functional Programming[/green] - Tối ưu hiệu năng và bảo trì\n"
            "• [blue]msgspec[/blue] - Serialization nhanh thay thế Pydantic\n"
            "• [yellow]LangChain[/yellow] - Framework AI/LLM\n"
            "• [magenta]Qdrant[/magenta] - Vector database\n"
            "• [red]DuckDuckGo[/red] - Web search integration\n\n"
            "[bold]✨ Tính năng:[/bold]\n"
            "• Immutable data structures\n"
            "• Streaming responses\n"
            "• Hybrid search (Vector + Web)\n"
            "• Error handling với Result types\n"
            "• High performance với zero-copy serialization\n\n"
            "[italic]🎓 Được phát triển như một dự án cuối kỳ với modern architecture.[/italic]",
            border_style="blue",
            title="ℹ️  Thông tin",
        )
    )


@app.command()
def version():
    """Hiển thị phiên bản của hệ thống."""
    console.print(
        "[bold cyan]🤖 Hệ thống hỏi đáp sản phẩm[/bold cyan] [green]v2.0.0[/green] [yellow](Functional)[/yellow]"
    )


@app.command()
def debug(
    query: str = typer.Argument(..., help="Câu hỏi để debug"),
):
    """Debug thông tin chi tiết về quá trình tìm kiếm."""
    try:
        qa_app = get_qa_application()
    except typer.Exit:
        return

    console.print(f"🔍 [cyan]Debugging query:[/cyan] {query}")

    # Get detailed search info
    search_info = qa_app.get_search_info(query)

    debug_table = Table(title="🐛 Debug Information")
    debug_table.add_column("Metric", style="cyan")
    debug_table.add_column("Value", style="green")

    for key, value in search_info.items():
        if isinstance(value, (list, dict)):
            debug_table.add_row(
                key, str(len(value)) if isinstance(value, list) else str(value)
            )
        else:
            debug_table.add_row(key, str(value))

    console.print(debug_table)

    # Show detailed results if available
    if "vector_results" in search_info and search_info["vector_results"]:
        console.print("\n📊 [yellow]Vector Results:[/yellow]")
        for i, result in enumerate(search_info["vector_results"], 1):
            console.print(
                f"{i}. Score: {result.get('score', 'N/A'):.3f} - {result.get('content', 'N/A')}"
            )

    if "web_results" in search_info and search_info["web_results"]:
        console.print("\n🌐 [yellow]Web Results:[/yellow]")
        for i, result in enumerate(search_info["web_results"], 1):
            console.print(
                f"{i}. Relevance: {result.get('relevance', 'N/A'):.3f} - {result.get('title', 'N/A')}"
            )


@app.callback()
def main():
    """
    🤖 Chương trình dòng lệnh để truy vấn hệ thống hỏi đáp sản phẩm điện tử.

    Sử dụng functional programming architecture với msgspec để tối ưu hiệu năng.
    """
    pass


if __name__ == "__main__":
    app()
