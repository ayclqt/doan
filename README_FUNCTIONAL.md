# Hệ thống hỏi đáp sản phẩm điện tử - Functional Programming Architecture

## 🚀 Tổng quan

Đây là phiên bản 2.0 được refactor hoàn toàn theo **Functional Programming** patterns, tối ưu hiệu năng và dễ bảo trì. Hệ thống sử dụng **msgspec** thay thế Pydantic cho data structures để đạt hiệu năng cao hơn, trong khi vẫn giữ **Pydantic Settings** cho configuration management.

## 🏗️ Kiến trúc mới

### Cấu trúc thư mục

```
src/
├── core/                 # Core functional utilities
│   ├── __init__.py
│   └── types.py         # Result, Maybe, functional utilities
├── domain/               # Domain models với msgspec
│   ├── __init__.py
│   └── models.py        # Product, TextChunk, SearchResult, etc.
├── infrastructure/       # Configuration & external services
│   ├── __init__.py
│   └── config.py        # Pydantic Settings cho config
├── services/             # Business logic services
│   ├── __init__.py
│   ├── qa_pipeline.py   # Q&A pipeline service
│   ├── vector_store.py  # Vector store operations
│   └── web_search.py    # Web search service
├── utils/               # Utility functions
│   ├── __init__.py
│   └── text_processing.py # Text processing utilities
└── main.py              # Main application entry point
```

## 🎯 Tính năng chính

### 1. **Functional Programming Patterns**
- **Immutable data structures** với `msgspec.Struct`
- **Pure functions** không có side effects
- **Function composition** với `pipe` và `compose`
- **Error handling** với `Result` type
- **Null safety** với `Maybe` type

### 2. **High Performance**
- **msgspec** cho serialization/deserialization nhanh hơn Pydantic
- **Zero-copy operations** khi có thể
- **Memoization** cho expensive operations
- **Streaming responses** để giảm latency

### 3. **Maintainability**
- **Separation of concerns** rõ ràng
- **Dependency injection** qua function parameters
- **Configuration as code** với validation
- **Comprehensive error handling**

## 🛠️ Technologies Stack

- **Core**: Python 3.12+
- **Data Structures**: msgspec (thay thế Pydantic cho models)
- **Configuration**: Pydantic Settings (giữ nguyên)
- **Vector DB**: Qdrant
- **LLM**: LangChain + OpenAI/Groq
- **Web Search**: DuckDuckGo
- **CLI**: Typer + Rich
- **Logging**: structlog

## 📋 Prerequisites

- Python 3.12+
- Qdrant server
- OpenAI API key hoặc compatible API (Groq, etc.)

## 🚀 Installation

```bash
# Clone repository
git clone <repository-url>
cd DoAn

# Install dependencies
pip install -r requirements.txt
# hoặc sử dụng uv
uv sync

# Setup environment
cp .env.example .env
# Edit .env with your configuration
```

## ⚙️ Configuration

Configuration được quản lý bởi `Pydantic Settings` trong `src/infrastructure/config.py`:

```python
# Các biến environment chính
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.x.ai/v1  # hoặc OpenAI URL
LLM_MODEL_NAME=grok-3-mini
QDRANT_URL=localhost
QDRANT_PORT=6333
EMBEDDING_MODEL_NAME=AITeamVN/Vietnamese_Embedding
WEB_SEARCH_ENABLED=true
```

## 🏃‍♂️ Usage

### 1. Data Ingestion (Functional Architecture)

```bash
# Ingest data với functional architecture
python ingest.py --data-path cleaned_data.json --verbose

# Hoặc sử dụng main app
python -m src.main ingest --data-path cleaned_data.json
```

### 2. Query CLI (Enhanced)

```bash
# Interactive mode với functional features
python query_cli.py interactive

# Single question với streaming
python query_cli.py ask "iPhone 15 có những tính năng gì?" --stream

# Debug mode để xem chi tiết
python query_cli.py debug "So sánh iPhone 15 và Samsung Galaxy S24"

# JSON output
python query_cli.py ask "Laptop gaming tốt nhất" --format json
```

### 3. Programmatic Usage

```python
from src import create_application, Result

# Tạo application
app_result = create_application()
if app_result.is_success:
    app = app_result.value
    
    # Hỏi đáp đơn giản
    response = app.ask_question("iPhone 15 Pro có những tính năng gì?")
    if response.is_success:
        qa_response = response.value
        print(f"Answer: {qa_response.answer}")
        print(f"Processing time: {qa_response.processing_time:.2f}s")
    
    # Streaming response
    for chunk in app.ask_question_stream("So sánh laptop gaming"):
        print(chunk, end="", flush=True)
```

## 🔧 Functional Programming Features

### 1. Result Type cho Error Handling

```python
from src.core.types import Result, safe_call

@safe_call
def risky_operation(data):
    if not data:
        raise ValueError("Data is empty")
    return process_data(data)

result = risky_operation(some_data)
if result.is_success:
    print(result.value)
else:
    print(f"Error: {result.error}")
```

### 2. Function Composition

```python
from src.core.types import pipe, compose

# Pipe data through functions
result = pipe(
    raw_data,
    load_and_parse_products,
    lambda products: process_products_to_chunks(products, config),
    lambda chunks: index_chunks_to_vector_store(chunks, vectorstore)
)
```

### 3. Immutable Data Structures

```python
from src.domain.models import Product, TextChunk

# Tất cả models đều immutable
product = Product(
    name="iPhone 15",
    price="25,000,000 VND",
    brand="Apple"
)

# Không thể modify
# product.name = "iPhone 16"  # Error!

# Tạo bản copy với thay đổi (nếu cần)
updated_product = Product(**{**product.__dict__, "price": "24,000,000 VND"})
```

### 4. Maybe Type cho Null Safety

```python
from src.core.types import Maybe

maybe_value = Maybe.of(some_nullable_value)
result = (maybe_value
    .map(lambda x: x.upper())
    .filter(lambda x: len(x) > 5)
    .or_else("default_value"))
```

## 📊 Performance Improvements

### msgspec vs Pydantic Performance

```python
# Benchmark results (ví dụ)
# Serialization: msgspec ~3-5x faster than Pydantic
# Deserialization: msgspec ~2-3x faster than Pydantic
# Memory usage: msgspec ~30-50% less memory
```

### Functional Benefits

- **Immutability**: Tránh accidental mutations, dễ debug
- **Pure functions**: Dễ test, dễ cache, thread-safe
- **Composition**: Code reuse cao, flexible
- **Error handling**: Explicit error handling, không có exceptions ẩn

## 🧪 Testing

```bash
# Run tests
python -m pytest tests/

# Test specific functionality
python test.py  # Basic functionality test
```

## 🔍 Debugging & Monitoring

### Debug Mode

```bash
# Chi tiết search process
python query_cli.py debug "iPhone 15 giá bao nhiêu?"
```

### Status Monitoring

```bash
# Trong interactive mode
> status  # Xem trạng thái hệ thống
> toggle  # Bật/tắt web search
```

### Logging

Sử dụng `structlog` cho structured logging:

```python
from src.infrastructure.config import get_logger

logger = get_logger()
logger.info("Processing query", query=query, user_id=user_id)
```

## 🚦 Migration Guide

### Từ version 1.0 (OOP) sang 2.0 (Functional)

#### Old way:
```python
from src.langchain_integration import LangchainPipeline, VectorStore

vector_store = VectorStore()
pipeline = LangchainPipeline(vector_store=vector_store)
answer = pipeline.answer_question("question")
```

#### New way:
```python
from src import create_application

app_result = create_application()
if app_result.is_success:
    app = app_result.value
    response = app.ask_question("question")
    if response.is_success:
        answer = response.value.answer
```

## 🤝 Contributing

1. Follow functional programming principles
2. Use `msgspec.Struct` cho data models
3. Use `Result` type cho error handling
4. Write pure functions khi có thể
5. Add comprehensive tests
6. Update documentation

## 📝 Changelog

### Version 2.0.0 (Functional Refactor)

**Added:**
- Functional programming architecture
- msgspec data structures
- Result/Maybe types
- Function composition utilities
- Streaming responses
- Enhanced error handling
- Performance optimizations

**Changed:**
- Complete codebase refactor
- Improved CLI with more features
- Better configuration management
- Enhanced debugging capabilities

**Maintained:**
- Pydantic Settings for configuration
- All existing functionality
- Backward compatibility for basic usage

## 📚 Documentation

- [Functional Programming Guide](docs/functional-programming.md)
- [Performance Benchmarks](docs/performance.md)
- [API Reference](docs/api-reference.md)
- [Migration Guide](docs/migration.md)

## 🐛 Troubleshooting

### Common Issues

1. **Import errors**: Đảm bảo `src` trong Python path
2. **Configuration errors**: Kiểm tra `.env` file
3. **Vector store connection**: Đảm bảo Qdrant server đang chạy
4. **API key issues**: Kiểm tra OpenAI/Groq API key

### Performance Issues

1. **Slow responses**: Kiểm tra embedding model và vector store
2. **Memory usage**: Sử dụng streaming cho large responses
3. **Web search timeout**: Adjust timeout settings

## 📄 License

MIT License - see LICENSE file for details.

## 👨‍💻 Author

**Lâm Quang Trí**
- Email: quangtri.lam.9@gmail.com
- Project: Electronic Product Q&A System v2.0 (Functional Architecture)

---

**Note**: Đây là phiên bản refactor hoàn toàn theo functional programming patterns nhằm cải thiện hiệu năng, maintainability và developer experience. Tất cả tính năng cũ vẫn được hỗ trợ với API tương thích ngược.