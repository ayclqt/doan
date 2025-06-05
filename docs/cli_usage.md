# Hướng Dẫn Sử Dụng CLI Cho Hệ Thống Hỏi Đáp Sản Phẩm Điện Tử

Tài liệu này hướng dẫn cách sử dụng công cụ dòng lệnh (CLI) để truy vấn hệ thống hỏi đáp sản phẩm điện tử.

## Cài Đặt

Đảm bảo bạn đã cài đặt tất cả các dependencies cần thiết trong môi trường ảo:

```bash
pip install -e .
```

hoặc

```bash
uv pip install -e .
```

Sau khi cài đặt, bạn có thể sử dụng lệnh `qa` trực tiếp thay vì `python query_cli.py`.

## Cách Sử Dụng

### Xem Trợ Giúp

Để xem các lệnh và tùy chọn có sẵn:

```bash
qa --help
```

Kết quả:

```
Usage: qa [OPTIONS] COMMAND [ARGS]...

  Chương trình dòng lệnh để truy vấn hệ thống hỏi đáp sản phẩm điện tử.

Options:
  --help  Show this message and exit.

Commands:
  info      Hiển thị thông tin về hệ thống hỏi đáp.
  query     Truy vấn hệ thống hỏi đáp sản phẩm.
  version   Hiển thị phiên bản của hệ thống.
```

Để xem chi tiết về các tùy chọn của lệnh `query`:

```bash
qa query --help
```

Kết quả:

```
Usage: qa query [OPTIONS]

  Truy vấn hệ thống hỏi đáp sản phẩm.

Options:
  -q, --query TEXT                 Câu hỏi cần truy vấn
  -i, --interactive                Chạy ở chế độ tương tác
  -f, --format [text|markdown|json]
                                  Định dạng hiển thị đầu ra
  -s, --sources                    Hiển thị thông tin nguồn dữ liệu (nếu có)
  --help                           Show this message and exit.
```

### Truy Vấn Đơn

Để đặt một câu hỏi đơn:

```bash
qa query --query "iPhone 15 Pro Max có giá bao nhiêu?"
```

hoặc sử dụng cú pháp ngắn:

```bash
qa query -q "iPhone 15 Pro Max có giá bao nhiêu?"
```

### Định Dạng Đầu Ra

Bạn có thể chọn một trong ba định dạng đầu ra:

```bash
qa query -q "iPhone 15 Pro Max có giá bao nhiêu?" --format text
qa query -q "iPhone 15 Pro Max có giá bao nhiêu?" --format markdown
qa query -q "iPhone 15 Pro Max có giá bao nhiêu?" --format json
```

### Chế Độ Tương Tác

Để chạy ứng dụng ở chế độ tương tác, cho phép bạn đặt nhiều câu hỏi:

```bash
qa query --interactive
```

hoặc sử dụng cú pháp ngắn:

```bash
qa query -i
```

Trong chế độ tương tác, bạn có thể sử dụng các lệnh sau:
- `exit`: Thoát khỏi ứng dụng
- `help`: Hiển thị trợ giúp
- `clear`: Xóa màn hình
- `history`: Hiển thị lịch sử các câu hỏi và trả lời

### Hiển Thị Thông Tin và Phiên Bản

Để xem thông tin về hệ thống:

```bash
qa info
```

Để xem phiên bản hiện tại:

```bash
qa version
```

## Ví Dụ Sử Dụng

### Truy vấn đơn với định dạng markdown

```bash
qa query -q "So sánh iPhone 15 và Samsung Galaxy S23" -f markdown
```

Kết quả:

```
Đang khởi tạo hệ thống hỏi đáp...

Thời gian xử lý: 2.34 giây

┌─────────────── Kết quả ───────────────┐
│ Câu hỏi:                              │
│ So sánh iPhone 15 và Samsung Galaxy S23 │
│                                      │
│ Trả lời:                              │
└──────────────────────────────────────┘

[Câu trả lời chi tiết sẽ hiển thị ở đây với định dạng markdown]
```

### Truy vấn dưới dạng JSON

```bash
qa query -q "iPhone 15 có những màu nào?" -f json
```

Kết quả hiển thị thông tin đầu ra dưới dạng JSON có cấu trúc.

### Chế độ tương tác

```bash
qa query -i -f markdown
```

Kết quả:

```
Đang khởi tạo hệ thống hỏi đáp...

┌─────────────────────────────────────────┐
│ Hệ thống hỏi đáp sản phẩm              │
│ Gõ 'exit' để thoát, 'help' để xem trợ giúp │
└─────────────────────────────────────────┘

Câu hỏi của bạn: help

┌───────── Lệnh Có Sẵn ─────────┐
│ Lệnh    │ Mô tả               │
│─────────┼─────────────────────│
│ exit    │ Thoát khỏi chương   │
│         │ trình               │
│ help    │ Hiển thị menu trợ   │
│         │ giúp này            │
│ clear   │ Xóa màn hình        │
│ history │ Hiển thị lịch sử    │
│         │ câu hỏi và trả lời  │
└─────────┴─────────────────────┘

Câu hỏi của bạn: iPhone 15 có những màu nào?

Thời gian xử lý: 1.75 giây

┌────────────── Kết quả ──────────────┐
│ Q: iPhone 15 có những màu nào?      │
│                                     │
│ A: [Câu trả lời chi tiết sẽ hiển    │
│ thị ở đây]                          │
└─────────────────────────────────────┘
```

## Tùy Chỉnh Nâng Cao

Để tùy chỉnh cấu hình của hệ thống (như mô hình LLM, nhiệt độ, v.v.), hãy chỉnh sửa các biến trong file cấu hình `.env` hoặc làm việc trực tiếp với mã nguồn.

## Xử Lý Lỗi

Nếu bạn gặp bất kỳ lỗi nào trong quá trình sử dụng CLI, hãy đảm bảo:

1. Các dịch vụ phụ thuộc (như Qdrant) đang chạy
2. Các biến môi trường được cấu hình chính xác
3. Dữ liệu đã được nhập vào hệ thống

## Hỗ Trợ

Nếu bạn gặp vấn đề hoặc có câu hỏi, vui lòng tạo issue trên repository của dự án.