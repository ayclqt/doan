# Hệ Thống Hỏi Đáp Sản Phẩm Điện Tử Thông Minh

Dự án này xây dựng một hệ thống trợ lý AI thông minh sử dụng LangChain và Vector Database Qdrant để tìm kiếm, so sánh và trả lời câu hỏi liên quan đến thông tin sản phẩm điện tử. Hệ thống có khả năng hiểu ngữ cảnh câu hỏi bằng tiếng Việt, tìm kiếm thông tin chính xác và cung cấp câu trả lời chi tiết dựa trên cơ sở dữ liệu sản phẩm được thu thập.

**🆕 Tính năng mới**: Hệ thống đã được tích hợp **DuckDuckGo Web Search** để tự động bổ sung thông tin mới nhất từ internet khi cơ sở dữ liệu nội bộ không đủ thông tin hoặc thiếu dữ liệu cập nhật.

## Kiến trúc hệ thống

Hệ thống bao gồm các thành phần chính:

- **Vector Database (Qdrant)**: Lưu trữ vector embeddings của dữ liệu sản phẩm, hỗ trợ tìm kiếm ngữ nghĩa hiệu quả
- **LangChain Pipeline**: Xử lý câu hỏi và tạo câu trả lời thông minh dựa trên thông tin sản phẩm có liên quan
- **Text Processor**: Xử lý và chuẩn bị dữ liệu cho vector embeddings, tách và chuẩn hóa thông tin sản phẩm
- **Embedding Model**: Chuyển đổi văn bản thành vector embeddings sử dụng AITeamVN/Vietnamese_Embedding hỗ trợ tốt cho tiếng Việt
- **Retrieval & Generation**: Kết hợp tìm kiếm ngữ nghĩa và tạo câu trả lời với bối cảnh chính xác sử dụng mô hình LLM
- **🆕 Web Search Integration**: Tích hợp DuckDuckGo search để tự động bổ sung thông tin mới nhất từ internet
- **🆕 Hybrid Search**: Kết hợp tìm kiếm vector database và web search để cung cấp thông tin toàn diện nhất

## Yêu cầu hệ thống

- Python 3.12+
- Docker và Docker Compose (cho Qdrant)
- OpenAI API key (hoặc API key của mô hình LLM được cấu hình)
- RAM: Tối thiểu 4GB (khuyến nghị 8GB+)
- Ổ cứng: Tối thiểu 1GB dung lượng trống

## Cài đặt

1. Clone repository:
```bash
git clone https://gitlab.com/ayclqt/doan.git
cd doan
```

2. Cài đặt dependencies từ pyproject.toml:
```bash
pip install -e .
```
hoặc nếu dùng uv:
```bash
uv sync
```

3. Tạo file `.env` từ file mẫu:
```bash
cp .env.example .env
```

4. Chỉnh sửa file `.env` và thêm các cấu hình cần thiết:
```
# LLM API Credentials
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_API_BASE=https://api.openai.com/v1

# Vector Database Configuration
QDRANT_URL=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=product_data

# Embedding Model
EMBEDDING_MODEL_NAME=AITeamVN/Vietnamese_Embedding

# LLM Configuration
LLM_MODEL_NAME=grok-3-mini
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=1024

# Text Processing
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Web Search Configuration
WEB_SEARCH_ENABLED=true
WEB_SEARCH_MAX_RESULTS=5
WEB_SEARCH_REGION=vn-vi
WEB_SEARCH_TIMELIMIT=
WEB_SEARCH_BACKEND=auto
WEB_SEARCH_SIMILARITY_THRESHOLD=0.7

# Data Paths
CLEANED_DATA_PATH=cleaned_data.json
```

5. Khởi chạy Qdrant với Docker Compose:
```bash
docker compose up -d
```

6. Kiểm tra cài đặt:
```bash
python check_setup.py
```

## Sử dụng

### 1. Nạp dữ liệu vào vector database

```bash
# Nạp dữ liệu với cấu hình mặc định
python ingest.py --data-path cleaned_data.json

# Nạp dữ liệu với tùy chọn nâng cao
python ingest.py --data-path cleaned_data.json --chunk-size 1000 --chunk-overlap 200
```

Các thông số này đã được cấu hình sẵn trong file `.env` và có thể điều chỉnh theo nhu cầu.

### 2. Truy vấn hệ thống

Sử dụng lệnh truy vấn đơn:
```bash
python query_cli.py --query "So sánh iPhone 15 Pro và Samsung Galaxy S23 Ultra"
```

Hoặc sử dụng chế độ tương tác:
```bash
python query_cli.py --interactive
```

### 3. Các ví dụ câu hỏi

- "Điện thoại nào có camera tốt nhất trong tầm giá 15 triệu?"
- "So sánh pin của iPhone 15 Pro Max và Samsung Galaxy S23 Ultra"
- "Laptop nào phù hợp cho thiết kế đồ họa dưới 30 triệu?"
- "Giới thiệu cho tôi các tablet có bút cảm ứng tốt"

## Cấu trúc mã nguồn

```
.
├── src/
│   └── langchain_integration/
│       ├── __init__.py
│       ├── config.py         # Cấu hình hệ thống
│       ├── pipeline.py       # LangChain Q&A pipeline 
│       ├── text_processor.py # Xử lý và chuẩn bị dữ liệu
│       ├── vectorstore.py    # Tích hợp với Qdrant
│       └── web_search.py     # 🆕 Tích hợp DuckDuckGo web search
├── notebooks/               # Notebooks cho phân tích và thử nghiệm
├── docs/                    # Tài liệu hướng dẫn
├── cleaned_data.json        # Dữ liệu sản phẩm đã làm sạch
├── data.json                # Dữ liệu sản phẩm gốc
├── docker-compose.yml       # Cấu hình Docker cho Qdrant
├── ingest.py                # Script nạp dữ liệu
├── query_cli.py             # CLI tool để truy vấn


├── export_qdrant.py         # Công cụ export Qdrant collection
├── import_qdrant.py         # Công cụ import Qdrant collection
├── check_setup.py           # Công cụ kiểm tra cài đặt
├── test.py                  # Script kiểm thử
├── test_web_search.py       # 🆕 Script test tích hợp web search
├── demo_web_search.py       # 🆕 Demo tính năng web search
├── pyproject.toml           # Cấu hình project và dependencies
├── LICENSE                  # Thông tin giấy phép
└── .env.example             # File cấu hình mẫu
```

## Quy trình hoạt động

1. **Thu thập & Tiền xử lý dữ liệu**: 
   - Thu thập thông tin sản phẩm từ nhiều nguồn
   - Làm sạch và chuẩn hóa dữ liệu

2. **Xử lý dữ liệu**:
   - Dữ liệu sản phẩm được phân tích và chia thành các chunks có ý nghĩa
   - Sử dụng kỹ thuật chunking thông minh để bảo toàn ngữ cảnh thông tin

3. **Tạo Vector Embedding**:
   - Mỗi chunk văn bản được chuyển đổi thành vector đa chiều
   - Sử dụng mô hình AITeamVN/Vietnamese_Embedding để tạo embeddings tối ưu cho tiếng Việt
   - Mô hình được cấu hình trong file `.env` và có thể thay đổi

4. **Lưu trữ Vector Database**:
   - Vectors được lưu trữ trong Qdrant cùng với metadata chi tiết
   - Tổ chức theo collection riêng biệt cho từng danh mục sản phẩm

5. **Xử lý câu hỏi**:
   - Phân tích ngữ cảnh và ý định của câu hỏi người dùng
   - Chuyển đổi câu hỏi thành vector query

6. **Tìm kiếm ngữ nghĩa**:
   - Thực hiện tìm kiếm vector similarity với Qdrant
   - Truy xuất các thông tin sản phẩm liên quan nhất với câu hỏi

7. **🆕 Hybrid Search Decision**:
   - Hệ thống đánh giá chất lượng kết quả từ vector database
   - Nếu không đủ thông tin hoặc cần dữ liệu mới nhất, tự động kích hoạt web search
   - Kết hợp thông tin từ cả vector database và web search

8. **Tạo câu trả lời**:
   - LLM kết hợp thông tin từ vector database và web search để tạo câu trả lời
   - Ưu tiên thông tin từ vector database, bổ sung thông tin từ web search
   - Đảm bảo câu trả lời chính xác, đầy đủ và ghi rõ nguồn tham khảo

## Import/Export Vector Database

Hệ thống hỗ trợ chuyển dữ liệu vector database giữa môi trường khác nhau (ví dụ: từ Google Colab về local):

### Export từ Google Colab

Sử dụng notebook `notebooks/qdrant_import_export.ipynb` để:
1. Nạp dữ liệu và tạo embeddings trên Colab
2. Export database thành file pickle
3. Download file về máy local

### Import vào local

```bash
# Import file đã export vào Qdrant local
python import_qdrant.py qdrant_export.pkl

# Import với tùy chọn nâng cao
python import_qdrant.py qdrant_export.pkl --collection-name new_collection --recreate-collection
```

### Export từ local

```bash
# Export collection từ Qdrant local
python export_qdrant.py product_data --output my_export.pkl

# Export với tùy chọn lọc theo metadata
python export_qdrant.py product_data --output my_export.pkl --filter-by-category "smartphone"
```

Chi tiết hơn có thể xem tại [docs/import_export_guide.md](docs/import_export_guide.md).

## Tính năng chính

### Tính năng cơ bản
- Tìm kiếm sản phẩm thông minh dựa trên ngữ nghĩa
- So sánh thông số kỹ thuật chi tiết giữa nhiều sản phẩm
- Gợi ý sản phẩm dựa trên nhu cầu người dùng
- Trả lời chính xác các câu hỏi về thông số kỹ thuật

### 🆕 Tính năng Web Search tích hợp
- **Tìm kiếm tự động**: Tự động tìm kiếm web khi vector database không đủ thông tin
- **Thông tin cập nhật**: Bổ sung thông tin giá cả, khuyến mãi mới nhất từ internet
- **Hybrid Search**: Kết hợp kết quả từ cơ sở dữ liệu nội bộ và tìm kiếm web
- **Cấu hình linh hoạt**: Có thể bật/tắt web search và điều chỉnh các tham số
- **Nguồn đáng tin cậy**: Sử dụng DuckDuckGo để đảm bảo quyền riêng tư và kết quả chất lượng

## Công cụ kiểm tra cài đặt

Hệ thống cung cấp công cụ kiểm tra cài đặt để đảm bảo mọi thứ hoạt động đúng:

```bash
# Kiểm tra cấu hình và kết nối
python check_setup.py

# Kiểm tra và chạy thử truy vấn mẫu
python check_setup.py --test-query

# Kiểm tra với câu hỏi tùy chỉnh
python check_setup.py --test-query --query "Điện thoại nào có camera tốt nhất?"
```

### 🆕 Kiểm tra tính năng Web Search

```bash
# Test tích hợp web search
python test_web_search.py

# Demo đầy đủ tính năng web search
python demo_web_search.py
```

Công cụ này sẽ kiểm tra:
- Các biến môi trường trong file `.env`
- Kết nối đến Qdrant và tình trạng collection
- Các dependencies đã được cài đặt đầy đủ
- Tập dữ liệu sản phẩm
- Các thành phần LangChain hoạt động đúng
- **🆕 Tình trạng DuckDuckGo web search**
- **🆕 Hybrid search pipeline**

## Chức năng tiếp theo

### Cải tiến Web Search
- **Multi-source search**: Tích hợp thêm các nguồn tìm kiếm khác (Google, Bing)
- **Search result caching**: Cache kết quả tìm kiếm để tăng tốc độ
- **Smart search triggers**: Cải thiện thuật toán quyết định khi nào sử dụng web search
- **Content filtering**: Lọc và xếp hạng kết quả web search chính xác hơn

### Tính năng khác
- **Cập nhật dữ liệu định kỳ**: Hệ thống tự động cập nhật thông tin sản phẩm mới
- **Tích hợp API (RESTful)**: Xây dựng API cho phép tích hợp vào các ứng dụng khác
- **Xây dựng giao diện web**: Giao diện người dùng trực quan với Streamlit hoặc Flask
- **Bộ nhớ hội thoại**: Ghi nhớ ngữ cảnh hội thoại để cải thiện trải nghiệm người dùng
- **Cá nhân hóa**: Điều chỉnh kết quả dựa trên lịch sử và sở thích người dùng
- **Triển khai bảo mật**: Xác thực người dùng và phân quyền truy cập
- **Phân tích feedback**: Cải thiện hệ thống dựa trên phản hồi người dùng

## Đóng góp

Chúng tôi rất hoan nghênh mọi đóng góp cho dự án! Vui lòng tạo một merge request hoặc mở issue để thảo luận về các tính năng, báo lỗi hoặc cải tiến bạn muốn đóng góp.

Tác giả chính: Lâm Quang Trí (quangtri.lam.9@gmail.com)

## Lưu ý về tập dữ liệu

Dữ liệu sản phẩm được thu thập từ các nguồn công khai trên internet và được xử lý làm sạch để sử dụng cho mục đích học tập và nghiên cứu. Đảm bảo bạn tuân thủ quy định và điều khoản sử dụng của các nguồn dữ liệu khi triển khai ứng dụng này.

## Giấy phép

Dự án được phát hành theo giấy phép MIT. Xem file [LICENSE](LICENSE) để biết thêm chi tiết.
