# LangChain & Qdrant Implementation Documentation

This document provides a detailed technical explanation of the LangChain and Qdrant vector database implementation for the product Q&A system.

## Tổng quan kỹ thuật

Hệ thống truy vấn sản phẩm được xây dựng dựa trên kiến trúc Retrieval Augmented Generation (RAG). RAG kết hợp khả năng truy xuất thông tin (retrieval) từ cơ sở dữ liệu vector với việc sinh câu trả lời (generation) từ mô hình ngôn ngữ lớn.

## Các thành phần chính

### 1. Vector Database (Qdrant)

[Qdrant](https://qdrant.tech/) là một vector database hiệu suất cao, tối ưu hóa cho việc tìm kiếm gần đúng (approximate nearest neighbor search). Qdrant được sử dụng để lưu trữ và truy vấn vector embeddings của dữ liệu sản phẩm.

**Cấu trúc dữ liệu trong Qdrant:**
- **Collection**: `product_data` - Lưu trữ vector embeddings của sản phẩm
- **Vector**: Mỗi vector đại diện cho thông tin của một sản phẩm (hoặc một phần của sản phẩm)
- **Metadata**: Thông tin bổ sung về sản phẩm được lưu kèm với vector để truy xuất nhanh

### 2. Sentence Embeddings

Mô hình `all-MiniLM-L6-v2` từ thư viện `sentence-transformers` được sử dụng để chuyển đổi văn bản thành vector số học. Mô hình này tạo ra vector có kích thước 384 chiều và được tối ưu hóa cho tìm kiếm ngữ nghĩa (semantic search).

**Ưu điểm của `all-MiniLM-L6-v2`:**
- Kích thước nhỏ, hiệu suất cao
- Hỗ trợ tiếng Việt
- Có thể chạy trên CPU

### 3. Text Processing

Quá trình xử lý văn bản bao gồm:

1. **Làm sạch dữ liệu**: Xử lý dữ liệu thô từ file JSON
2. **Chunking**: Chia nhỏ thông tin sản phẩm thành các đoạn có kích thước phù hợp
3. **Formatting**: Định dạng thông tin sản phẩm để tối ưu cho tìm kiếm và hỏi đáp

**Tham số chunking:**
- Chunk size: 1000 ký tự (có thể điều chỉnh)
- Chunk overlap: 200 ký tự (đảm bảo không mất ngữ cảnh giữa các chunks)

### 4. LangChain Pipeline

LangChain được sử dụng để xây dựng pipeline hỏi đáp với các thành phần:

1. **Retriever**: Tìm kiếm thông tin sản phẩm liên quan từ vector database
2. **Prompt Template**: Định dạng câu hỏi và ngữ cảnh để gửi đến LLM
3. **Language Model**: Xử lý prompt và tạo câu trả lời (mặc định: `gpt-3.5-turbo`)
4. **Output Parser**: Xử lý kết quả từ LLM và định dạng câu trả lời cuối cùng

## Quy trình hoạt động chi tiết

### 1. Quá trình nạp dữ liệu (Data Ingestion)

```
┌─────────────────┐     ┌───────────────┐     ┌─────────────────┐     ┌─────────────┐
│ JSON Product    │ --> │ Text          │ --> │ Vector          │ --> │ Qdrant      │
│ Data            │     │ Processing    │     │ Embedding       │     │ Collection   │
└─────────────────┘     └───────────────┘     └─────────────────┘     └─────────────┘
```

1. **Đọc dữ liệu**: Đọc file JSON chứa thông tin sản phẩm đã được làm sạch
2. **Xử lý văn bản**: Mỗi sản phẩm được chuyển đổi thành văn bản có cấu trúc
3. **Chunking**: Nếu sản phẩm có nhiều thông tin, chia thành nhiều chunks với overlap
4. **Tạo metadata**: Mỗi chunk được gắn metadata với thông tin sản phẩm
5. **Embedding**: Chuyển văn bản thành vector sử dụng mô hình embedding
6. **Lưu trữ**: Lưu vector và metadata vào Qdrant collection

### 2. Quá trình truy vấn (Query Process)

```
┌─────────┐     ┌────────────┐     ┌───────────┐     ┌───────────┐     ┌────────────┐
│ User    │     │ Vector     │     │ Similarity│     │ Context   │     │ LLM        │
│ Query   │ --> │ Embedding  │ --> │ Search    │ --> │ Formation │ --> │ Generation │
└─────────┘     └────────────┘     └───────────┘     └───────────┘     └────────────┘
```

1. **Chuyển đổi truy vấn**: Câu hỏi người dùng được chuyển thành vector embedding
2. **Tìm kiếm gần nhất**: Vector database trả về các sản phẩm có vector gần nhất với vector truy vấn
3. **Tạo ngữ cảnh**: Thông tin sản phẩm được định dạng thành ngữ cảnh cho prompt
4. **Tạo prompt**: Ngữ cảnh và câu hỏi được kết hợp vào prompt template
5. **Gọi LLM**: LLM xử lý prompt và tạo câu trả lời dựa trên ngữ cảnh
6. **Trả về kết quả**: Câu trả lời được định dạng và trả về cho người dùng

## Các lớp và module chính

### 1. `VectorStore` (vectorstore.py)

Class này quản lý tương tác với cơ sở dữ liệu vector Qdrant, bao gồm:
- Khởi tạo kết nối với Qdrant
- Tạo và quản lý collection
- Index dữ liệu vào collection
- Thực hiện tìm kiếm vector

```python
# Pseudocode example
vs = VectorStore()
vs.create_collection()  # Tạo collection nếu chưa tồn tại
vs.index_documents(documents)  # Index dữ liệu
results = vs.similarity_search("iPhone 15")  # Tìm kiếm vector
```

### 2. `TextProcessor` (text_processor.py)

Class này xử lý văn bản và chuẩn bị dữ liệu cho embedding:
- Đọc dữ liệu từ file JSON
- Chuyển đổi sản phẩm thành văn bản có cấu trúc
- Phân đoạn văn bản thành các chunks
- Thêm metadata cho mỗi chunk

```python
# Pseudocode example
processor = TextProcessor()
products = processor.load_data()
chunks = processor.process_all_products(products)
```

### 3. `LangchainPipeline` (pipeline.py)

Class này xây dựng pipeline RAG với LangChain:
- Khởi tạo LLM
- Tạo retriever từ vector store
- Định nghĩa prompt template 
- Kết hợp các components thành chain hoàn chỉnh

```python
# Pseudocode example
pipeline = LangchainPipeline()
answer = pipeline.answer_question("So sánh iPhone và Samsung")
```

## Cách tối ưu hóa và mở rộng

### 1. Tối ưu hóa Vector Search

- **Filtering**: Sử dụng filter để giới hạn kết quả tìm kiếm theo danh mục sản phẩm
- **Reranking**: Thêm bước reranking sau vector search để cải thiện độ chính xác
- **Hybrid search**: Kết hợp BM25 với vector search cho kết quả toàn diện hơn

### 2. Cải thiện Prompt Engineering

- **Prompt tuning**: Điều chỉnh prompt để cải thiện chất lượng câu trả lời
- **Few-shot learning**: Thêm ví dụ vào prompt để LLM hiểu rõ hơn định dạng mong muốn
- **Chain-of-thought**: Yêu cầu LLM giải thích từng bước suy luận

### 3. Mở rộng chức năng

- **Conversation memory**: Lưu trữ lịch sử hội thoại để hệ thống có thể trả lời theo ngữ cảnh
- **Document retrieval**: Mở rộng để tìm kiếm trong tài liệu hướng dẫn sử dụng
- **Feedback loop**: Thu thập phản hồi người dùng để cải thiện hệ thống
