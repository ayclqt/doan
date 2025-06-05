import json
import re


__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


def clean_data(data):
    cleaned_products = []

    # Định nghĩa các giá trị "rác" cần loại bỏ trường
    # Các giá trị này sẽ không làm mất trường nếu chúng xuất hiện trong ngữ cảnh hợp lệ
    # Ví dụ: "Không" cho Đèn Flash Camera sau là hợp lệ và cần giữ lại.
    # Tuy nhiên, nếu "Không" là giá trị của "Hỗ trợ RAM tối đa" thì nên bỏ.
    # Danh sách này sẽ được sử dụng cẩn thận.
    junk_values = {
        "Đang cập nhật",
        "Đang cập nhật",
        "Hãng không công bố",
        "",  # Chuỗi rỗng
        " ",  # Khoảng trắng
        "Không hỗ trợ nâng cấp",
        "Không giới hạn",  # Có thể là rác nếu không phải danh bạ
    }

    # Các trường cần xử lý tách riêng
    special_fields = {
        "Kích thước:",  # Laptop
        "Màn hình rộng",  # Điện thoại
    }

    for product in data:
        cleaned_product = {}
        original_name = product.get("Tên")
        product_type = None

        # --- Bước 1: Xác định loại sản phẩm và tên sản phẩm ---
        # Ưu tiên trường 'Tên', nếu không có hoặc là rác thì thử từ khóa
        if original_name and original_name.strip() not in junk_values:
            cleaned_product["Tên"] = original_name.strip()
            if "Điện thoại" in cleaned_product["Tên"]:
                product_type = "Điện thoại"
            elif "Laptop" in cleaned_product["Tên"]:
                product_type = "Laptop"
        else:
            # Cố gắng lấy tên từ "Từ khóa" hoặc các trường khác nếu có logic cụ thể
            # Trong trường hợp này, dữ liệu "Từ khóa" có vẻ không đáng tin cậy cho việc tạo tên
            # nên sẽ dựa vào sự xuất hiện của các trường đặc trưng để xác định loại
            pass  # Sẽ loại bỏ nếu không có tên sau các bước dưới

        # --- Bước 2: Duyệt qua từng trường và làm sạch ---
        for key, value in product.items():
            # Chuẩn hóa tên khóa: Loại bỏ dấu hai chấm và khoảng trắng thừa
            clean_key = key.replace(":", "").strip()

            # Bỏ qua các trường "Từ khóa" hoặc các trường không cần thiết khác
            if clean_key == "Từ khóa":
                continue

            # Kiểm tra và bỏ qua giá trị "rác"
            if isinstance(value, str):
                cleaned_value = value.strip()
                if cleaned_value in junk_values:
                    # Đặc biệt xử lý "Không" cho các trường boolean như đèn flash
                    if clean_key == "Đèn Flash camera sau" and cleaned_value == "Không":
                        cleaned_product[clean_key] = "Không"
                    else:
                        continue  # Bỏ qua trường này nếu giá trị là rác
                elif not cleaned_value:  # Bỏ qua chuỗi rỗng sau khi strip
                    continue
                else:
                    processed_value = cleaned_value
            else:
                processed_value = value

            # --- Bước 3: Xử lý các trường đặc biệt và tách thông tin ---
            if clean_key == "Kích thước" and product_type == "Laptop":
                # Ví dụ: "Dài 359 mm - Rộng 241 mm - Dày 19.9 mm - 1.7 kg"
                dimensions = re.findall(r"(\w+)\s([\d.]+)\s(mm|cm|kg)", processed_value)
                for dim_name, dim_value, unit in dimensions:
                    if dim_name == "Dài":
                        cleaned_product["Dài"] = f"{dim_value} {unit}"
                    elif dim_name == "Rộng":
                        cleaned_product["Rộng"] = f"{dim_value} {unit}"
                    elif dim_name == "Dày":
                        cleaned_product["Dày"] = f"{dim_value} {unit}"
                    elif dim_name == "kg":  # Trọng lượng thường là số cuối cùng
                        cleaned_product["Trọng lượng"] = f"{dim_value} kg"

            elif clean_key == "Màn hình rộng" and product_type == "Điện thoại":
                # Ví dụ: "6.7\" - Tần số quét 120 Hz"
                screen_size_match = re.search(r'([\d.]+)"', processed_value)
                if screen_size_match:
                    cleaned_product["Kích thước màn hình"] = screen_size_match.group(
                        0
                    )  # Giữ nguyên "6.7\""

                refresh_rate_match = re.search(
                    r"Tần số quét\s*([\d.]+)\s*Hz", processed_value
                )
                if refresh_rate_match:
                    cleaned_product["Tần số quét màn hình"] = (
                        f"{refresh_rate_match.group(1)} Hz"
                    )

            elif clean_key == "Thông tin Pin" and product_type == "Laptop":
                # Giữ nguyên nếu có giá trị cụ thể, hoặc chuyển đổi nếu có thể
                cleaned_product[clean_key] = processed_value

            elif clean_key == "Cổng giao tiếp" and isinstance(processed_value, str):
                # Tách các cổng giao tiếp bằng dấu phẩy hoặc khoảng trắng lớn
                ports = [
                    p.strip()
                    for p in re.split(r"[,;]\s*|\s{2,}", processed_value)
                    if p.strip()
                ]
                cleaned_product[clean_key] = ", ".join(ports)

            elif clean_key == "Thời điểm ra mắt" and isinstance(processed_value, str):
                # Chỉ lấy năm nếu định dạng là tháng/năm
                year_match = re.search(r"(\d{4})", processed_value)
                if year_match:
                    cleaned_product[clean_key] = year_match.group(1)
                else:
                    cleaned_product[clean_key] = (
                        processed_value  # Giữ nguyên nếu không khớp
                    )

            # Thêm các trường đã làm sạch (trừ các trường đặc biệt đã xử lý ở trên)
            # Nếu tên khóa đã được xử lý qua logic đặc biệt thì không thêm lại
            elif clean_key not in special_fields:
                cleaned_product[clean_key] = processed_value

        # --- Bước 4: Kiểm tra lại tên sản phẩm và loại bỏ bản ghi nếu không có tên hợp lệ ---
        if "Tên" not in cleaned_product or not cleaned_product["Tên"]:
            continue  # Bỏ qua sản phẩm nếu không có tên hợp lệ

        # Thêm loại sản phẩm nếu xác định được
        if product_type:
            cleaned_product["Loại sản phẩm"] = product_type
        else:  # Cố gắng suy luận lại loại sản phẩm nếu chưa có
            if (
                "Chip xử lý (CPU)" in cleaned_product
                or "RAM" in cleaned_product
                and any(
                    k in cleaned_product
                    for k in ["Dung lượng lưu trữ", "Độ phân giải camera sau"]
                )
            ):
                cleaned_product["Loại sản phẩm"] = "Điện thoại"
            elif "Màn hình" in cleaned_product and "Ổ cứng" in cleaned_product:
                cleaned_product["Loại sản phẩm"] = "Laptop"
            else:
                # Nếu vẫn không xác định được loại, có thể cân nhắc loại bỏ hoặc gán loại "Không xác định"
                # Tạm thời để trống hoặc bạn có thể quyết định bỏ nếu không có loại
                pass

        cleaned_products.append(cleaned_product)

    return cleaned_products


# Đọc dữ liệu từ file JSON
try:
    with open("data.json", "r", encoding="utf-8") as f:
        raw_data = json.load(f)
except FileNotFoundError:
    print(
        "Lỗi: Không tìm thấy file 'data.json'. Hãy đảm bảo file nằm cùng thư mục với script."
    )
    raw_data = []
except json.JSONDecodeError:
    print("Lỗi: Không thể đọc file JSON. Kiểm tra định dạng file 'data.json'.")
    raw_data = []

if raw_data:
    cleaned_data = clean_data(raw_data)

    # Ghi dữ liệu đã làm sạch vào một file JSON mới
    output_filename = "cleaned_data.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

    print(f"Dữ liệu đã được làm sạch và lưu vào '{output_filename}'")
    # Bạn có thể in ra một vài bản ghi đầu tiên để kiểm tra
    # print(json.dumps(cleaned_data[:2], ensure_ascii=False, indent=2))
