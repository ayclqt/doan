# Hướng dẫn Import/Export Vector Database Qdrant

Tài liệu này hướng dẫn cách chuyển dữ liệu vector database Qdrant giữa Google Colab và môi trường local.

## 1. Giới thiệu

Khi làm việc với các mô hình nhúng (embeddings) và vector database, đôi khi bạn cần chạy quá trình embedding trên Google Colab (để tận dụng GPU miễn phí) và sau đó sử dụng kết quả trong môi trường local. Hướng dẫn này mô tả quy trình chuyển đổi dữ liệu Qdrant giữa các môi trường.

## 2. Quy trình Import/Export

### 2.1 Tổng quan về quy trình

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Dữ liệu sản │     │ Colab       │     │ Export      │     │ Local       │
│ phẩm (JSON) │ --> │ Qdrant DB   │ --> │ File (pkl)  │ --> │ Qdrant DB   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

1. Upload dữ liệu sản phẩm (JSON) lên Google Colab
2. Thực hiện embedding và xây dựng vector database trên Colab
3. Export vector database từ Colab thành file (pickle format)
4. Download file export về máy local
5. Import file vào Qdrant vector database local

## 3. Quy trình chi tiết

### 3.1 Trên Google Colab

#### Bước 1: Upload notebook và dữ liệu

1. Upload file notebook `qdrant_import_export.ipynb` lên Google Colab
2. Chạy cell đầu tiên để cài đặt các thư viện cần thiết
3. Upload file dữ liệu JSON (`cleaned_data.json`) lên Colab

#### Bước 2: Xử lý dữ liệu và tạo embeddings

1. Chạy các cell để thiết lập Qdrant trong Colab
2. Chạy quá trình text processing và embedding 
3. Nạp dữ liệu vào Qdrant collection trong Colab

#### Bước 3: Export và download

1. Chạy cell export để lưu collection thành file `qdrant_export.pkl`
2. Download file xuống máy local

### 3.2 Trên môi trường Local

#### Bước 1: Chuẩn bị môi trường local

1. Đảm bảo Qdrant đã được khởi chạy:
```bash
docker-compose up -d
```

2. Cài đặt dependencies nếu chưa có:
```bash
pip install -r requirements.txt
```

#### Bước 2: Import dữ liệu vào Qdrant local

1. Sử dụng script `import_qdrant.py` để import file đã download:
```bash
python import_qdrant.py qdrant_export.pkl --host localhost --port 6333
```

2. Script sẽ tạo collection trong Qdrant local và import tất cả points với vectors và metadata

#### Bước 3: Kiểm tra dữ liệu đã import

Bạn có thể kiểm tra dữ liệu bằng cách:
1. Truy cập Qdrant dashboard: http://localhost:6333/dashboard
2. Chạy script query để kiểm tra:
```bash
python query_cli.py --query "iPhone 15 Pro có những tính năng gì nổi bật?"
```

## 4. Export dữ liệu từ Local (nếu cần)

Nếu bạn cần export dữ liệu từ môi trường local để chuyển sang môi trường khác:

```bash
python export_qdrant.py product_data --output my_export.pkl
```

Trong đó:
- `product_data` là tên collection
- `my_export.pkl` là tên file output

## 5. Tùy chỉnh Import/Export

### 5.1 Thay đổi cấu hình Qdrant

Nếu Qdrant server của bạn không chạy ở localhost:6333:

```bash
python import_qdrant.py qdrant_export.pkl --host your-qdrant-host --port your-port
```

### 5.2 Xử lý Collection lớn

Với collection lớn, quá trình export/import có thể mất thời gian. Các script được thiết kế để xử lý theo batch để tránh sử dụng quá nhiều memory.

## 6. Xử lý sự cố

### Vấn đề kết nối Qdrant

Nếu gặp lỗi kết nối:
- Kiểm tra xem Qdrant container đã chạy chưa với `docker ps`
- Đảm bảo port 6333 không bị block bởi firewall
- Kiểm tra logs của Qdrant: `docker logs qdrant`

### Vấn đề import/export

- Nếu file export quá lớn, có thể tăng batch_size trong script để tối ưu hóa
- Nếu gặp lỗi memory, giảm batch_size để giảm memory usage

## 7. Kết luận

Quy trình import/export này giúp bạn có thể tận dụng tài nguyên của Google Colab để xây dựng vector database, sau đó sử dụng kết quả trong môi trường local của mình, tiết kiệm thời gian và tài nguyên tính toán.
