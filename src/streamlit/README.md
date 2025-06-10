# Streamlit Chatbot Application

Ứng dụng Streamlit cho chatbot giới thiệu sản phẩm sử dụng mô hình ngôn ngữ lớn (LLM).

## 🚀 Tính năng

- **Đăng nhập/Đăng ký**: Xác thực người dùng qua API
- **Chat thời gian thực**: Streaming response từ LLM
- **Quản lý cuộc trò chuyện**: Lưu trữ và tải lại lịch sử chat
- **Tìm kiếm thông minh**: Tích hợp vector search và web search
- **Giao diện thân thiện**: UI responsive với Streamlit
- **Session management**: Quản lý phiên đăng nhập tự động

## 📋 Yêu cầu hệ thống

- Python 3.8+
- API server đang chạy (mặc định: http://localhost:8000)
- Các package Python theo `requirements.txt`

## 🛠 Cài đặt

1. **Cài đặt dependencies:**
```bash
pip install -r requirements.txt
```

2. **Kiểm tra cài đặt:**
```bash
python run.py --check-only
```

## 🎯 Sử dụng

### Chạy ứng dụng cơ bản

```bash
python run.py
```

Ứng dụng sẽ chạy tại: http://localhost:8501

### Các tùy chọn khác

```bash
# Chạy trên tất cả interfaces
python run.py --host 0.0.0.0 --port 8502

# Chạy với debug mode
python run.py --debug

# Chỉ định URL API khác
python run.py --api-url http://api.example.com:8000

# Xem tất cả tùy chọn
python run.py --help
```

### Chạy trực tiếp với Streamlit

```bash
streamlit run main.py --server.port 8501
```

## 🔧 Cấu hình

### Biến môi trường

Tạo file `.env` hoặc thiết lập biến môi trường:

```bash
# API Configuration
API_BASE_URL=http://localhost:8000
API_TIMEOUT=30

# UI Configuration
PAGE_TITLE=Chatbot Giới Thiệu Sản Phẩm
SIDEBAR_EXPANDED=true
SHOW_SEARCH_INFO=false

# Chat Configuration
MAX_MESSAGE_LENGTH=1000
MAX_CONVERSATION_HISTORY=50

# Session Configuration
SESSION_TIMEOUT_MINUTES=30
AUTO_SAVE_CONVERSATIONS=true

# Debug
DEBUG_MODE=false
LOG_LEVEL=INFO
```

### Cấu hình Streamlit

File `.streamlit/config.toml` (tùy chọn):

```toml
[server]
port = 8501
headless = false

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
```

## 📱 Hướng dẫn sử dụng

### 1. Đăng nhập

- Mở ứng dụng tại http://localhost:8501
- Chọn tab "Đăng Nhập" hoặc "Đăng Ký"
- Nhập thông tin tài khoản
- Nhấn nút đăng nhập/đăng ký

### 2. Chat với bot

- Sau khi đăng nhập, nhập câu hỏi vào ô chat
- Bot sẽ trả lời theo thời gian thực (streaming)
- Có thể bật "Bao gồm thông tin tìm kiếm" để xem chi tiết

### 3. Quản lý cuộc trò chuyện

- **Cuộc trò chuyện mới**: Nhấn nút "💬 Cuộc trò chuyện mới"
- **Xem lịch sử**: Chọn từ danh sách trong sidebar
- **Tải lại**: Nhấn nút "🔄 Tải lại" để cập nhật danh sách
- **Xóa**: Nhấn nút "🗑️ Xóa cuộc trò chuyện"

## 📁 Cấu trúc thư mục

```
src/streamlit/
├── main.py              # Ứng dụng Streamlit chính
├── config.py            # Cấu hình ứng dụng
├── utils.py             # Utility functions
├── run.py               # Script chạy ứng dụng
├── requirements.txt     # Dependencies
└── README.md           # Tài liệu này
```

## 🔌 API Endpoints

Ứng dụng sử dụng các API endpoints sau:

- `POST /auth/login` - Đăng nhập
- `POST /auth/register` - Đăng ký
- `POST /chat/` - Chat với streaming
- `GET /chat/conversations` - Lấy danh sách cuộc trò chuyện
- `GET /chat/conversations/{id}/history` - Lấy lịch sử cuộc trò chuyện

## 🔍 Tính năng chi tiết

### Authentication Service
- Validate input tự động
- Session management với timeout
- Token-based authentication

### Chat Service
- Streaming response real-time
- Message validation và sanitization
- Conversation history caching
- Search info integration

### UI Components
- Responsive chat interface
- Sidebar navigation
- Message formatting
- Error handling
- Loading states

### Utilities
- Session state management
- API client với retry logic
- Message formatters
- Validation helpers
- Cache management

## 🛡️ Bảo mật

- Token-based authentication
- Input validation và sanitization
- Session timeout tự động
- HTTPS ready (với reverse proxy)
- No hardcoded credentials

## 🚨 Xử lý lỗi

### Lỗi thường gặp

1. **"Connection error"**
   - Kiểm tra API server có đang chạy không
   - Xác nhận URL API đúng trong config

2. **"Request timeout"**
   - Tăng `API_TIMEOUT` trong config
   - Kiểm tra kết nối mạng

3. **"Session expired"**
   - Đăng nhập lại
   - Kiểm tra `SESSION_TIMEOUT_MINUTES`

4. **"Invalid credentials"**
   - Kiểm tra username/password
   - Đảm bảo tài khoản đã được tạo

### Debug Mode

Bật debug để xem thông tin chi tiết:

```bash
python run.py --debug
```

Hoặc set biến môi trường:

```bash
DEBUG_MODE=true streamlit run main.py
```

## 📊 Monitoring

### Session Stats
- Thời gian hoạt động cuối
- Số tin nhắn trong conversation
- Thống kê tìm kiếm

### Performance
- API response time
- Cache hit rate
- Stream processing time

## 🔄 Cập nhật

### Cập nhật dependencies

```bash
pip install -r requirements.txt --upgrade
```

### Cập nhật cache

```bash
# Cache sẽ tự động clear khi restart app
# Hoặc dùng nút "Tải lại" trong UI
```

## 🤝 Đóng góp

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## 📝 License

[Your License Here]

## 📞 Hỗ trợ

- Email: quangtri.lam.9@gmail.com
- GitHub Issues: [Repository URL]

## 🔖 Changelog

### v1.0.0
- Initial release
- Basic chat functionality
- Authentication system
- Conversation management
- Streaming responses
- Search integration

---

**Lưu ý**: Đảm bảo API server đang chạy trước khi khởi động Streamlit app.