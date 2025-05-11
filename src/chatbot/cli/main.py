"""
Module CLI cho ứng dụng chatbot giới thiệu sản phẩm
"""

import os
from typing import Optional, List

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from ..config import settings
from ..core import ProductChatbot, VectorStore, DataIngestor

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__license__ = "MIT"
__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"

# Khởi tạo typer app
app = typer.Typer(
    name="product-chatbot",
    help="Chatbot giới thiệu sản phẩm sử dụng mô hình ngôn ngữ lớn",
)

# Khởi tạo console
console = Console()


@app.command()
def chat(
    model: str = typer.Option(
        settings.model_name,
        "--model", "-m",
        help="Model LLM sử dụng cho chatbot",
    ),
    temperature: float = typer.Option(
        settings.temperature,
        "--temperature", "-t",
        help="Nhiệt độ của model LLM",
    ),
):
    """
    Bắt đầu một phiên chat với chatbot
    """
    # Hiển thị banner
    console.print(
        Panel.fit(
            "[bold green]Chatbot Giới Thiệu Sản Phẩm[/bold green]\n"
            "[italic]Gõ /exit để thoát, /reset để xóa lịch sử trò chuyện[/italic]"
        )
    )
    
    # Khởi tạo vector store và chatbot
    try:
        vector_store = VectorStore()
        chatbot = ProductChatbot(
            vector_store=vector_store,
            model=model,
            temperature=temperature,
        )
        
        # Kiểm tra xem có dữ liệu trong vector store không
        stats = vector_store.get_collection_stats()
        if stats["count"] == 0:
            console.print(
                "[yellow]Cảnh báo: Vector store không có dữ liệu. "
                "Vui lòng sử dụng lệnh 'ingest' để thêm dữ liệu trước khi chat.[/yellow]"
            )
        
    except Exception as e:
        console.print(f"[bold red]Lỗi khi khởi tạo chatbot: {str(e)}[/bold red]")
        raise typer.Exit(code=1)
    
    # Bắt đầu vòng lặp chat
    while True:
        # Nhận input từ người dùng
        user_input = Prompt.ask("\n[bold blue]Bạn[/bold blue]")
        
        # Xử lý các lệnh đặc biệt
        if user_input.lower() == "/exit":
            console.print("[yellow]Đã thoát phiên chat.[/yellow]")
            break
        
        if user_input.lower() == "/reset":
            chatbot.reset_chat_history()
            console.print("[yellow]Đã xóa lịch sử trò chuyện.[/yellow]")
            continue
        
        # Xử lý câu hỏi
        try:
            response = chatbot.ask(user_input)
            console.print("\n[bold green]Chatbot[/bold green]")
            console.print(Markdown(response))
            
        except Exception as e:
            console.print(f"[bold red]Lỗi: {str(e)}[/bold red]")


@app.command()
def ingest(
    file_paths: Optional[List[str]] = typer.Argument(
        None,
        help="Đường dẫn đến file hoặc thư mục cần nhập",
    ),
    recursive: bool = typer.Option(
        True,
        "--recursive/--no-recursive", "-r/-nr",
        help="Có xử lý đệ quy các thư mục con hay không",
    ),
):
    """
    Nhập dữ liệu từ file hoặc thư mục vào vector store
    """
    # Khởi tạo vector store và ingestor
    try:
        vector_store = VectorStore()
        ingestor = DataIngestor(vector_store=vector_store)
        
    except Exception as e:
        console.print(f"[bold red]Lỗi khi khởi tạo: {str(e)}[/bold red]")
        raise typer.Exit(code=1)
    
    # Nếu không có file_paths, yêu cầu người dùng nhập
    if not file_paths:
        file_path = Prompt.ask(
            "Nhập đường dẫn đến file hoặc thư mục cần nhập"
        )
        file_paths = [file_path]
    
    # Xử lý từng file path
    for path in file_paths:
        if not os.path.exists(path):
            console.print(f"[bold red]Đường dẫn không tồn tại: {path}[/bold red]")
            continue
        
        try:
            if os.path.isdir(path):
                console.print(f"[yellow]Đang xử lý thư mục: {path}[/yellow]")
                ingestor.ingest_from_directory(path, recursive=recursive)
            else:
                console.print(f"[yellow]Đang xử lý file: {path}[/yellow]")
                ingestor.ingest_from_file(path)
                
        except Exception as e:
            console.print(f"[bold red]Lỗi khi xử lý {path}: {str(e)}[/bold red]")
    
    # Hiển thị thống kê
    stats = vector_store.get_collection_stats()
    console.print(
        f"[green]Đã hoàn thành. "
        f"Vector store hiện có {stats['count']} đoạn văn bản.[/green]"
    )


@app.command()
def clear(
    confirm: bool = typer.Option(
        False,
        "--yes", "-y",
        help="Xác nhận xóa dữ liệu mà không hỏi",
    ),
):
    """
    Xóa toàn bộ dữ liệu trong vector store
    """
    if not confirm:
        confirm = typer.confirm("Bạn có chắc muốn xóa toàn bộ dữ liệu?")
        if not confirm:
            console.print("[yellow]Đã hủy thao tác.[/yellow]")
            return
    
    try:
        vector_store = VectorStore()
        ingestor = DataIngestor(vector_store=vector_store)
        ingestor.reset_store()
        console.print("[green]Đã xóa toàn bộ dữ liệu.[/green]")
        
    except Exception as e:
        console.print(f"[bold red]Lỗi khi xóa dữ liệu: {str(e)}[/bold red]")
        raise typer.Exit(code=1)


@app.command("info")
def info():
    """
    Hiển thị thông tin về ứng dụng và vector store
    """
    try:
        vector_store = VectorStore()
        stats = vector_store.get_collection_stats()
        
        console.print(
            Panel.fit(
                f"[bold green]Thông tin ứng dụng[/bold green]\n\n"
                f"Tên ứng dụng: {settings.app_name}\n"
                f"Collection ChromaDB: {stats['collection_name']}\n"
                f"Số lượng đoạn văn bản: {stats['count']}\n"
                f"Thư mục lưu trữ: {settings.chroma_db_directory}\n"
                f"Model Embedding: {settings.embedding_model}\n"
                f"Model LLM mặc định: {settings.model_name}\n"
            )
        )
        
    except Exception as e:
        console.print(f"[bold red]Lỗi khi lấy thông tin: {str(e)}[/bold red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()