ĐỀ CƯƠNG ĐỒ ÁN TỐT NGHIỆP

A. THÔNG TIN CHUNG
* Sinh viên: Lâm Quang Trí
* Lớp: CT06N
* Người hướng dẫn: Ngô Thanh Hùng
* Đơn vị công tác: Trường Đại học Văn Lang
* Đề tài: Xây dựng chatbot hỗ trợ giới thiệu sản phẩm sử dụng mô hình ngôn ngữ lớn

B. ĐỀ CƯƠNG ĐỒ ÁN
1.  Tính cấp thiết, ý nghĩa thực tiễn của đề tài

    Trong bối cảnh thương mại điện tử và dịch vụ khách hàng ngày càng phát triển, việc cung cấp thông tin sản phẩm nhanh chóng, chính xác và thân thiện với người dùng là một yêu cầu cấp thiết. Các phương pháp truyền thống như nhân viên tư vấn hoặc tài liệu tĩnh thường không đáp ứng được nhu cầu cá nhân hóa và tốc độ phản hồi mà khách hàng mong đợi. Đặc biệt, với sự gia tăng của các doanh nghiệp vừa và nhỏ, việc duy trì đội ngũ hỗ trợ khách hàng lớn là một thách thức về chi phí và nguồn lực.

    Để giải quyết vấn đề này, việc xây dựng một chatbot sử dụng mô hình ngôn ngữ lớn (Large Language Model - LLM) là một giải pháp hiệu quả. Chatbot này có khả năng giao tiếp tự nhiên, hiểu ngữ cảnh, và cung cấp thông tin sản phẩm theo nhu cầu của khách hàng mọi lúc, mọi nơi. Hệ thống không chỉ giúp doanh nghiệp tiết kiệm chi phí vận hành mà còn nâng cao trải nghiệm người dùng, tăng tỷ lệ chuyển đổi mua hàng.

    Các chức năng chính của chatbot bao gồm: trả lời câu hỏi về sản phẩm, gợi ý sản phẩm phù hợp, hỗ trợ đa ngôn ngữ, và tích hợp với các nền tảng bán hàng trực tuyến. Mục tiêu của đồ án là phát triển một chatbot thông minh, dễ sử dụng, hỗ trợ doanh nghiệp trong việc giới thiệu sản phẩm và cải thiện tương tác với khách hàng. Hệ thống này sẽ góp phần tối ưu hóa quy trình kinh doanh, nâng cao hiệu quả tiếp thị và mang lại giá trị thực tiễn trong lĩnh vực thương mại điện tử.

2.  Nhiệm vụ đồ án

    Các nhiệm vụ đặt ra khi thực hiện đồ án bao gồm:
    * Thiết kế giao diện chatbot thân thiện, trực quan, tương thích trên nhiều thiết bị.
    * Phân tích và tích hợp mô hình ngôn ngữ lớn để xử lý ngôn ngữ tự nhiên và trả lời thông minh.
    * Đảm bảo bảo mật và quyền riêng tư
        * Bảo vệ thông tin người dùng và dữ liệu sản phẩm, không lưu trữ hội thoại trừ khi được yêu cầu rõ ràng.
        * Áp dụng mã hóa dữ liệu bằng các phương pháp như AES-256 cho lưu trữ và RSA cho truyền tải.
        * Ngăn chặn các lỗ hổng bảo mật như Injection Attack và Prompt Hacking thông qua kiểm tra đầu vào và sandboxing.
    * Xây dựng các chức năng chính: trả lời câu hỏi, gợi ý sản phẩm, tích hợp với cơ sở dữ liệu sản phẩm.
    * Đánh giá hiệu suất chatbot dựa trên các tiêu chí cụ thể như tốc độ phản hồi, độ chính xác, khả năng xử lý lỗi và khả năng mở rộng.

    Cụ thể về công nghệ sử dụng:
    * Frontend (FE): Sử dụng Streamlit để xây dựng giao diện người dùng thân thiện, nhẹ nhàng và dễ triển khai. Streamlit cho phép tạo ứng dụng web tương tác nhanh chóng, hỗ trợ hiển thị thông tin sản phẩm và tương tác với người dùng theo thời gian thực.
    * Backend (BE):
        * Gọi các mô hình ngôn ngữ lớn thông qua giao thức gRPC để đảm bảo hiệu suất cao và truyền dữ liệu nhanh chóng giữa frontend và backend.
        * Kết hợp hàng đợi worker bằng Dramatiq với message broker là RabbitMQ để xử lý các tác vụ bất đồng bộ như truy vấn dữ liệu sản phẩm, phân tích câu hỏi người dùng, và trả lời tự động. Điều này giúp hệ thống hoạt động mượt mà ngay cả khi có nhiều yêu cầu cùng lúc.
    * Tích hợp: Kết nối cơ sở dữ liệu sản phẩm (ví dụ: MySQL hoặc MongoDB) với chatbot để cung cấp thông tin theo thời gian thực.

3.  Dự kiến chương, mục

    Sau các mục “Lời mở đầu”, “Danh mục từ viết tắt và ký hiệu”, “Danh mục hình vẽ”, “Danh mục bảng”, nội dung chính của đồ án dự kiến được kết cấu như sau:
    1.  Chương I. Tổng quan về ứng dụng chatbot hỗ trợ giới thiệu sản phẩm
        1.1. Thực trạng và sự cần thiết của chatbot trong thương mại điện tử.
        1.2. Mục tiêu và phạm vi của đồ án.
        1.3. Đối tượng sử dụng hệ thống.
        1.4. Các công cụ và công nghệ liên quan
    2.  Chương II. Tổng quan công nghệ
        2.1. Tổng quan về mô hình ngôn ngữ lớn và ứng dụng trong chatbot.
        2.2. Giới thiệu framework Streamlit để xây dựng giao diện.
        2.3. Tổng quan về LangChain trong việc tích hợp LLM.
        2.4. Sử dụng LiteLLM để gọi và quản lý các mô hình ngôn ngữ.
        2.5. Giới thiệu gRPC, Dramatiq và RabbitMQ trong xử lý tác vụ backend.
    3.  Chương III. Xây dựng và triển khai hệ thống
        3.1. Cài đặt môi trường phát triển dự án.
        3.2. Thiết kế và xây dựng các chức năng chính của chatbot.
        3.3. Bảo mật và quyền riêng tư
        3.4. Kiểm thử hệ thống.
        3.5. Triển khai hệ thống.
        3.6. Thu thập và xử lý dữ liệu sản phẩm
    4.  Chương IV. Kết luận và hướng phát triển
        4.1. Kết quả đạt được.
        4.2. Khó khăn và thách thức.
        4.3. Phương hướng phát triển trong tương lai.
    5.  Chương V. Mở rộng và ứng dụng thực tế
        5.1. Ứng dụng chatbot trong hỗ trợ khách hàng (Customer Support).
        5.2. Tư vấn sản phẩm trên đa nền tảng (Facebook, Zalo, Website, App di động).

    Sau cùng là các mục “Kết luận”, “Danh mục tài liệu tham khảo” và “Phụ lục”. Phần phụ lục sẽ chứa mã nguồn của các module chính của ứng dụng.

4.  Tài liệu tham khảo để xây dựng đề cương
    1.  [1] Valentina Alto, Building LLM Powered Applications: Create intelligent apps and agents with large language models.
    2.  [2] Trang chủ chính thức của Streamlit https://streamlit.io/
    3.  [3] Trang chủ chính thức của LangChain https://www.langchain.com/
    4.  [4] Trang chủ chính thức của LiteLLM https://litellm.ai/
    5.  [5] Tài liệu gRPC https://grpc.io/
    6.  [6] Tài liệu Dramatiq https://dramatiq.io/
    7.  [7] Tài liệu RabbitMQ https://www.rabbitmq.com/
    8.  [8] OWASP, "Top 10 Web Application Security Risks https://owasp.org/www-project-top-ten/
