# Chatbot Giới Thiệu Sản Phẩm

Ứng dụng chatbot giới thiệu sản phẩm sử dụng LangChain và ChromaDB để trả lời các câu hỏi về sản phẩm dựa trên dữ liệu được cung cấp.

## Tính năng

- Nhập dữ liệu sản phẩm từ nhiều định dạng (PDF, DOCX, TXT, CSV, Excel)
- Tạo vector embeddings và lưu trữ trong ChromaDB
- Truy vấn thông tin sản phẩm thông qua giao diện dòng lệnh
- Sử dụng LLM (OpenAI) để tạo ra câu trả lời chính xác

## Yêu cầu

- Python 3.12 trở lên
- OpenAI API key

## Cài đặt

1. Clone repository này:

```bash
git clone <repository-url>
cd DoAn
```

2. Tạo và kích hoạt môi trường ảo:

```bash
uv venv
source .venv/bin/activate  # Linux/Mac
# hoặc
.venv\Scripts\activate  # Windows
```

3. Cài đặt các thư viện phụ thuộc:

```bash
uv sync
```

4. Tạo file `.env` dựa vào file `.env.example`:

```bash
cp .env.example .env
```

5. Chỉnh sửa file `.env` và thêm OpenAI API key của bạn

## Sử dụng

### Nhập dữ liệu sản phẩm

```bash
python main.py ingest <đường_dẫn_đến_tệp_hoặc_thư_mục>
```

### Bắt đầu một phiên chat

```bash
python main.py chat
```

### Xem thông tin về vector store

```bash
python main.py info
```

### Xóa toàn bộ dữ liệu

```bash
python main.py clear
```

## Lệnh trong chế độ chat

- `/exit`: Thoát khỏi phiên chat
- `/reset`: Xóa lịch sử trò chuyện

## Cấu trúc dự án

```
DoAn/
├── .env                # File cấu hình môi trường
├── .env.example        # File mẫu cấu hình môi trường
├── main.py             # Điểm vào chính của ứng dụng
├── pyproject.toml      # Cấu hình dự án và dependencies
├── README.md           # Tài liệu dự án
└── src/                # Mã nguồn
    └── product_chatbot/
        ├── __init__.py
        ├── cli/        # Giao diện dòng lệnh
        ├── config/     # Cấu hình ứng dụng
        ├── core/       # Logic chính của ứng dụng
        └── utils/      # Các tiện ích
```

## Phát triển

### Kiến trúc hệ thống

Xem các file `.mmd` trong thư mục gốc để hiểu về kiến trúc hệ thống.

## Giấy phép

[LICENSE]