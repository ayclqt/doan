#!/bin/bash

# Hiển thị banner
echo "===================================="
echo "Thiết lập chatbot giới thiệu sản phẩm"
echo "===================================="

# Kiểm tra Python
echo "Kiểm tra cài đặt Python..."
if command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
else
    echo "Không tìm thấy Python. Vui lòng cài đặt Python phiên bản 3.9 trở lên."
    exit 1
fi

PYTHON_VERSION=$($PYTHON --version | cut -d " " -f 2)
echo "Phiên bản Python: $PYTHON_VERSION"

# Kiểm tra uv
echo "Kiểm tra cài đặt uv..."
if ! command -v uv &>/dev/null; then
    echo "Không tìm thấy uv. Bạn có muốn cài đặt không? (y/n)"
    read INSTALL_UV
    if [ "$INSTALL_UV" == "y" ] || [ "$INSTALL_UV" == "Y" ]; then
        curl -sSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
    else
        echo "Vui lòng cài đặt uv trước khi tiếp tục: https://github.com/astral-sh/uv"
        exit 1
    fi
fi

# Tạo môi trường ảo
echo "Tạo môi trường ảo..."
uv venv
if [ ! -d ".venv" ]; then
    echo "Không thể tạo môi trường ảo. Vui lòng kiểm tra lại."
    exit 1
fi

# Kích hoạt môi trường ảo
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source .venv/Scripts/activate
else
    source .venv/bin/activate
fi

# Cài đặt dependencies
echo "Cài đặt thư viện phụ thuộc..."
uv sync

# Tạo file .env nếu chưa tồn tại
if [ ! -f ".env" ]; then
    echo "Tạo file .env từ mẫu..."
    cp .env.example .env
    echo "Vui lòng chỉnh sửa file .env và thêm API key của bạn."
fi

# Tạo thư mục chroma_db nếu chưa tồn tại
if [ ! -d ".chroma_db" ]; then
    echo "Tạo thư mục lưu trữ ChromaDB..."
    mkdir -p .chroma_db
fi

echo "===================================="
echo "Thiết lập hoàn tất!"
echo "Để chạy chatbot, sử dụng lệnh: python main.py chat"
echo "Để thêm dữ liệu, sử dụng lệnh: python main.py ingest <đường_dẫn>"
echo "===================================="