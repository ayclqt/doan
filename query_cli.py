"""
CLI tool để truy vấn hệ thống hỏi đáp sản phẩm sử dụng Typer và Rich.
"""

import os
import time
import typer
from typing import Optional
from enum import Enum
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich import print as rprint
from rich.table import Table

from src import LangchainPipeline, VectorStore


__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


# Khởi tạo Typer và Rich Console
app = typer.Typer(
    help="Hệ thống hỏi đáp sản phẩm điện tử",
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


def get_qa_pipeline():
    """Khởi tạo pipeline hỏi đáp."""
    with console.status("[bold green]Đang khởi tạo hệ thống hỏi đáp..."):
        vector_store = VectorStore()
        qa_pipeline = LangchainPipeline(vector_store=vector_store)
        return qa_pipeline


def interactive_mode(
    qa_pipeline: LangchainPipeline,
    output_format: OutputFormat = OutputFormat.TEXT,
    show_sources: bool = False,
    mode: Mode = Mode.STREAM,
) -> None:
    """Chạy chế độ tương tác để nhập nhiều câu hỏi."""
    rprint(
        Panel.fit(
            "[bold cyan]Hệ thống hỏi đáp sản phẩm[/bold cyan]\n"
            "[italic]Gõ 'exit' để thoát, 'help' để xem trợ giúp[/italic]",
            border_style="blue",
        )
    )

    history = []

    while True:
        query = Prompt.ask("\n[bold green]Câu hỏi của bạn")

        if query.lower() == "exit":
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

        if not query.strip():
            continue

        start_time = time.time()

        if mode == Mode.STREAM:
            # Hiển thị kết quả theo chế độ streaming
            answer = display_streaming_answer(query, qa_pipeline, output_format)
        else:
            # Hiển thị kết quả theo chế độ block
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold green]Đang xử lý câu hỏi..."),
                transient=True,
            ) as progress:
                progress.add_task("processing", total=None)
                answer = qa_pipeline.answer_question(query)

        end_time = time.time()
        history.append({"question": query, "answer": answer})

        # Hiển thị thời gian xử lý
        console.print(
            f"\n[bold]Thời gian xử lý:[/bold] {end_time - start_time:.2f} giây"
        )

        # Nếu không phải streaming, hiển thị kết quả
        if mode != Mode.STREAM:
            display_answer(query, answer, output_format, end_time - start_time)


def show_help():
    """Hiển thị trợ giúp cho chế độ tương tác."""
    help_table = Table(title="Lệnh Có Sẵn")
    help_table.add_column("Lệnh", style="cyan")
    help_table.add_column("Mô tả", style="green")

    help_table.add_row("exit", "Thoát khỏi chương trình")
    help_table.add_row("help", "Hiển thị menu trợ giúp này")
    help_table.add_row("clear", "Xóa màn hình")
    help_table.add_row("history", "Hiển thị lịch sử câu hỏi và trả lời")

    console.print(help_table)


def show_history(history):
    """Hiển thị lịch sử câu hỏi và trả lời."""
    if not history:
        rprint("[italic yellow]Chưa có lịch sử câu hỏi.[/italic yellow]")
        return

    history_table = Table(title="Lịch Sử Hỏi Đáp")
    history_table.add_column("STT", style="cyan", no_wrap=True)
    history_table.add_column("Câu Hỏi", style="green")
    history_table.add_column("Trả Lời", style="blue")

    for i, item in enumerate(history, 1):
        history_table.add_row(
            str(i),
            item["question"][:50] + ("..." if len(item["question"]) > 50 else ""),
            item["answer"][:50] + ("..." if len(item["answer"]) > 50 else ""),
        )

    console.print(history_table)


def display_streaming_answer(query, qa_pipeline, output_format):
    """Hiển thị câu trả lời theo chế độ streaming."""
    console.print(f"\n[bold green]Q:[/bold green] {query}")
    console.print("\n[bold blue]A:[/bold blue] ", end="")

    # Lưu câu trả lời đầy đủ để trả về
    full_answer = ""

    try:
        # Phục vụ stream từng phần
        for chunk in qa_pipeline.answer_question_stream(query):
            console.print(chunk, end="", highlight=False)
            full_answer += chunk
    except Exception as e:
        error_msg = f"Lỗi khi xử lý streaming: {e}"
        console.print(f"\n[bold red]{error_msg}[/bold red]")
        return error_msg

    console.print()  # Xuống dòng sau khi hoàn thành
    return full_answer


def display_answer(query, answer, output_format, time_taken=None):
    """Hiển thị câu trả lời theo định dạng được chọn."""

    if output_format == OutputFormat.TEXT:
        rprint(
            Panel(
                f"[bold green]Q:[/bold green] {query}\n\n[bold blue]A:[/bold blue] {answer}",
                title="Kết quả",
                border_style="green",
            )
        )
    elif output_format == OutputFormat.MARKDOWN:
        rprint(
            Panel(
                f"[bold green]Câu hỏi:[/bold green]\n{query}\n\n[bold blue]Trả lời:[/bold blue]",
                title="Kết quả",
                border_style="green",
            )
        )
        console.print(Markdown(answer))
    elif output_format == OutputFormat.JSON:
        import json

        result = {
            "question": query,
            "answer": answer,
            "time_taken": f"{time_taken:.2f}s" if time_taken else "N/A",
        }
        rprint(
            Panel(
                json.dumps(result, ensure_ascii=False, indent=2),
                title="JSON Result",
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
    """Truy vấn hệ thống hỏi đáp sản phẩm."""
    # Khởi tạo pipeline
    qa_pipeline = get_qa_pipeline()

    if interactive:
        interactive_mode(qa_pipeline, output_format, show_sources, mode)
    elif query:
        start_time = time.time()

        if mode == Mode.STREAM:
            # Hiển thị kết quả theo chế độ streaming
            answer = display_streaming_answer(query, qa_pipeline, output_format)
        else:
            # Hiển thị kết quả theo chế độ block
            answer = qa_pipeline.answer_question(query)
            end_time = time.time()
            time_taken = end_time - start_time
            display_answer(query, answer, output_format, time_taken)

        end_time = time.time()
        console.print(
            f"\n[bold]Thời gian xử lý:[/bold] {end_time - start_time:.2f} giây"
        )
    else:
        typer.echo("Vui lòng cung cấp một câu hỏi hoặc sử dụng chế độ tương tác.")
        raise typer.Exit(1)


@app.command()
def info():
    """Hiển thị thông tin về hệ thống hỏi đáp."""
    rprint(
        Panel.fit(
            "[bold cyan]Thông tin hệ thống hỏi đáp sản phẩm điện tử[/bold cyan]\n\n"
            "Hệ thống sử dụng [bold]LangChain[/bold] và [bold]Qdrant[/bold] để cung cấp câu trả lời "
            "chính xác dựa trên dữ liệu sản phẩm.\n\n"
            "[italic]Được phát triển như một dự án cuối kỳ.[/italic]",
            border_style="blue",
            title="Thông tin",
        )
    )


@app.command()
def version():
    """Hiển thị phiên bản của hệ thống."""
    console.print("[bold cyan]Hệ thống hỏi đáp sản phẩm[/bold cyan] v1.0.0")


@app.callback()
def main():
    """Chương trình dòng lệnh để truy vấn hệ thống hỏi đáp sản phẩm điện tử."""
    pass


if __name__ == "__main__":
    app()
