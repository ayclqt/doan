# Hướng dẫn sử dụng LangChain & Qdrant

Tài liệu này hướng dẫn chi tiết cách sử dụng và mở rộng hệ thống LangChain kết hợp với Qdrant đã được triển khai.

## 1. Cài đặt & Khởi động

### Cài đặt dependencies

```bash
# Cài đặt các package cần thiết
pip install -r requirements.txt
```

### Khởi động Qdrant

Để khởi động Qdrant sử dụng Docker:

```bash
# Khởi động Qdrant container
docker-compose up -d

# Kiểm tra trạng thái
docker ps
```

Qdrant có giao diện web truy cập qua: http://localhost:6333/dashboard

## 2. Nạp dữ liệu

### Nạp dữ liệu sản phẩm vào vector database

```bash
# Nạp dữ liệu từ file mặc định (cleaned_data.json)
python ingest.py

# Hoặc chỉ định đường dẫn file dữ liệu khác
python ingest.py --data-path /path/to/your/data.json
```

### Tham số tùy chọn

- `--recreate`: Tạo lại collection (xóa dữ liệu cũ nếu có)
- `--data-path`: Đường dẫn đến file JSON chứa dữ liệu sản phẩm

## 3. Sử dụng CLI để truy vấn

### Chế độ tương tác

```bash
# Khởi động chế độ tương tác
python query_cli.py --interactive
```

Ví dụ sử dụng:
```
===== Hệ thống hỏi đáp sản phẩm =====
Gõ 'exit' để thoát

Câu hỏi của bạn: iPhone 15 Pro có những tính năng gì nổi bật?

Đang xử lý câu hỏi...

Trả lời: iPhone 15 Pro có nhiều tính năng nổi bật như: chip A17 Pro, camera chính 48MP với khả năng zoom quang học 3x, khung viền titanium bền bỉ, nút Action mới có thể tùy chỉnh, cổng USB-C...
```

### Truy vấn đơn

```bash
# Thực hiện một truy vấn đơn
python query_cli.py --query "So sánh MacBook Air M2 và MacBook Pro M2"
```

## 4. Sử dụng trong mã Python

### Import và khởi tạo

```python
from langchain_integration.pipeline import LangchainPipeline
from langchain_integration.vectorstore import VectorStore

# Khởi tạo vector store
vector_store = VectorStore()

# Khởi tạo pipeline
qa_pipeline = LangchainPipeline(vector_store=vector_store)

# Đặt câu hỏi
answer = qa_pipeline.answer_question("So sánh iPhone 15 Pro và Samsung Galaxy S23 Ultra")
print(answer)
```

### Tùy chỉnh cấu hình

```python
from langchain_integration.config import LLM_MODEL_NAME, LLM_TEMPERATURE

# Tùy chỉnh mô hình và tham số
qa_pipeline = LangchainPipeline(
    model_name="gpt-4-turbo",  # Thay đổi mô hình
    temperature=0.2,  # Điều chỉnh độ sáng tạo
    max_tokens=2000,  # Tăng độ dài câu trả lời
)
```

## 5. Tùy chỉnh và mở rộng

### Thay đổi embedding model

Để thay đổi mô hình embedding, chỉnh sửa file `.env`:

```
EMBEDDING_MODEL_NAME=all-mpnet-base-v2
```

Hoặc trong mã:

```python
from langchain_integration.vectorstore import VectorStore

# Thay đổi mô hình embedding
vector_store = VectorStore(embedding_model="all-mpnet-base-v2")
```

### Điều chỉnh chunk size

Để tối ưu kích thước chunk, chỉnh sửa trong `.env`:

```
CHUNK_SIZE=500
CHUNK_OVERLAP=100
```

Hoặc trong mã:

```python
from langchain_integration.text_processor import TextProcessor

# Tùy chỉnh kích thước chunk
processor = TextProcessor(chunk_size=500, chunk_overlap=100)
```

### Thêm bộ nhớ hội thoại

Mở rộng `pipeline.py` để thêm conversation memory:

```python
from langchain.memory import ConversationBufferMemory

memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
qa_pipeline.add_conversation_memory(memory)
```

## 6. Các tình huống sử dụng phổ biến

### Tìm kiếm sản phẩm tương tự

```python
from langchain_integration.vectorstore import VectorStore

# Khởi tạo vector store
vector_store = VectorStore()
vectorstore = vector_store.get_vectorstore()

# Tìm kiếm sản phẩm tương tự
results = vectorstore.similarity_search("laptop gaming giá rẻ", k=5)
for doc in results:
    print(f"- {doc.metadata.get('product_name', 'Unknown')}")
```

### Filter theo danh mục sản phẩm

```python
# Filter theo metadata
results = vectorstore.similarity_search(
    "smartphone tầm trung",
    filter={"metadata_field": "Điện thoại"}
)
```

### So sánh sản phẩm

```python
query = """So sánh chi tiết giữa:
1. iPhone 15 Pro
2. Samsung Galaxy S23 Ultra
Về: camera, pin, hiệu năng, màn hình"""

answer = qa_pipeline.answer_question(query)
```

## 7. Debug và xử lý lỗi

### Kiểm tra kết nối Qdrant

```python
from qdrant_client import QdrantClient

client = QdrantClient(url="localhost", port=6333)
collections = client.get_collections().collections
print(f"Available collections: {[c.name for c in collections]}")
```

### Xem logs

```bash
# Xem logs của Qdrant container
docker logs qdrant
```

### Các lỗi thường gặp

1. **"Failed to connect to Qdrant"**: Kiểm tra Qdrant đã chạy chưa và cổng 6333 đã mở
2. **"Collection not found"**: Chạy lại `ingest.py` để tạo và nạp dữ liệu
3. **"Invalid API key"**: Kiểm tra lại OpenAI API key trong file `.env`

## 8. Best Practices

1. **Chunking hợp lý**: Điều chỉnh kích thước chunk phù hợp với loại dữ liệu
2. **Prompt Engineering**: Tối ưu prompt để nhận câu trả lời chính xác hơn
3. **Metadata phong phú**: Thêm nhiều metadata giúp filtering hiệu quả hơn
4. **Điều chỉnh k**: Số lượng kết quả trả về từ vector search ảnh hưởng đến chất lượng câu trả lời
