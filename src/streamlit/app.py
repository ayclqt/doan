#!/usr/bin/env python3
"""
Ứng dụng Streamlit đơn giản cho Chatbot giới thiệu sản phẩm
Phiên bản sạch với token validation
"""

import asyncio
import json
import os
import time
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Dict, Optional

import aiohttp

import streamlit as st

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"

# ================== CONFIGURATION ==================
load_dotenv()  # Tải biến môi trường từ file .env nếu có
API_BASE_URL = os.getenv("API_KEY_URL", "http://localhost:8000")
API_TIMEOUT = os.getenv("API_TIMEOUT", 300)
MAX_MESSAGE_LENGTH = os.getenv("MAX_MESSAGE_LENGTH", 1000)
SESSION_TIMEOUT_MINUTES = os.getenv("SESSION_TIMEOUT_MINUTES", 30)

# ================== STREAMLIT CONFIG ==================
st.set_page_config(
    page_title="Chatbot Giới Thiệu Sản Phẩm",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ================== CSS STYLES ==================
st.markdown(
    """
<style>
.stApp > header {
    background-color: transparent;
}

.stApp {
    margin-top: -80px;
}

.stButton > button {
    width: 100%;
    margin-bottom: 0.5rem;
}

.typing-indicator {
    opacity: 0.7;
    font-style: italic;
    animation: pulse 1.5s infinite;
}

@keyframes pulse {
    0% { opacity: 0.7; }
    50% { opacity: 1; }
    100% { opacity: 0.7; }
}
</style>
""",
    unsafe_allow_html=True,
)


# ================== UTILITY FUNCTIONS ==================
def run_async(coro):
    """Helper để chạy async functions trong Streamlit"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def init_session_state():
    """Khởi tạo session state"""
    default_values = {
        "authenticated": False,
        "user_info": None,
        "access_token": None,
        "token_expires": None,
        "current_conversation_id": None,
        "messages": [],
        "conversations": [],
        "last_activity": datetime.now(),
        "api_status": "unknown",
    }

    for key, value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = value


def is_session_valid() -> bool:
    """Kiểm tra session có hợp lệ không"""
    if not st.session_state.get("authenticated", False):
        return False

    if not st.session_state.get("access_token"):
        return False

    last_activity = st.session_state.get("last_activity")
    if not last_activity:
        return False

    # Kiểm tra timeout
    if datetime.now() - last_activity > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
        return False

    return True


def update_activity():
    """Cập nhật thời gian hoạt động cuối"""
    st.session_state.last_activity = datetime.now()


def clear_session():
    """Xóa session state"""
    keys_to_clear = [
        "authenticated",
        "user_info",
        "access_token",
        "token_expires",
        "current_conversation_id",
        "messages",
        "conversations",
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    init_session_state()


def handle_token_error():
    """Xử lý lỗi token"""
    st.error("❌ Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.")
    clear_session()
    st.rerun()


def format_timestamp(timestamp: str) -> str:
    """Format timestamp"""
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime("%H:%M:%S")
    except Exception:
        return ""


def safe_format_title(title: str, max_length: int = 25) -> str:
    """Safely format title"""
    if not title:
        return "Cuộc trò chuyện"
    if len(title) > max_length:
        return title[:max_length] + "..."
    return title


# ================== API CLIENT ==================
class APIClient:
    """Client để gọi API"""

    @staticmethod
    async def make_request(
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        token: Optional[str] = None,
        timeout: int = API_TIMEOUT,
    ) -> tuple[bool, Optional[Dict], str]:
        """Thực hiện API request"""
        url = f"{API_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {"Content-Type": "application/json"}

        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as session:
                async with session.request(
                    method, url, json=data, headers=headers
                ) as response:
                    if response.content_type == "application/json":
                        response_data = await response.json()
                    else:
                        response_data = {"message": await response.text()}

                    if response.status < 400:
                        return True, response_data, ""
                    else:
                        error_msg = response_data.get(
                            "detail", f"HTTP {response.status}"
                        )

                        # Check for token errors
                        if (
                            response.status in [401, 403]
                            or "token" in str(error_msg).lower()
                        ):
                            return False, response_data, "INVALID_TOKEN"

                        return False, response_data, error_msg

        except asyncio.TimeoutError:
            return False, None, "Request timeout"
        except aiohttp.ClientConnectorError:
            return False, None, "Không thể kết nối đến API server"
        except Exception as e:
            return False, None, f"Lỗi kết nối: {str(e)}"

    @staticmethod
    async def stream_request(
        endpoint: str, data: Dict, token: str, timeout: int = API_TIMEOUT
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Thực hiện streaming request"""
        url = f"{API_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as session:
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status == 200:
                        async for line in response.content:
                            line = line.decode("utf-8").strip()
                            if line.startswith("data: "):
                                try:
                                    chunk_data = json.loads(line[6:])
                                    yield chunk_data
                                except json.JSONDecodeError:
                                    continue
                    else:
                        error_text = await response.text()
                        if response.status in [401, 403]:
                            yield {"type": "error", "content": "INVALID_TOKEN"}
                        else:
                            yield {
                                "type": "error",
                                "content": f"HTTP {response.status}: {error_text}",
                            }

        except Exception as e:
            yield {"type": "error", "content": f"Stream error: {str(e)}"}


# ================== SERVICES ==================
class AuthService:
    """Service xử lý authentication"""

    @staticmethod
    async def login(username: str, password: str) -> tuple[bool, Optional[Dict], str]:
        """Đăng nhập"""
        if not username or len(username) < 3:
            return False, None, "Tên đăng nhập phải có ít nhất 3 ký tự"

        if not password or len(password) < 6:
            return False, None, "Mật khẩu phải có ít nhất 6 ký tự"

        data = {"username": username, "password": password}
        success, response, error = await APIClient.make_request(
            "POST", "/auth/login", data
        )

        if success and response:
            return True, response, ""
        else:
            return False, None, error or "Đăng nhập thất bại"

    @staticmethod
    async def register(
        username: str, password: str
    ) -> tuple[bool, Optional[Dict], str]:
        """Đăng ký"""
        if not username or len(username) < 3:
            return False, None, "Tên đăng nhập phải có ít nhất 3 ký tự"

        if not password or len(password) < 6:
            return False, None, "Mật khẩu phải có ít nhất 6 ký tự"

        data = {"username": username, "password": password}
        success, response, error = await APIClient.make_request(
            "POST", "/auth/register", data
        )

        if success and response:
            return True, response, ""
        else:
            return False, None, error or "Đăng ký thất bại"


class ChatService:
    """Service xử lý chat"""

    @staticmethod
    async def send_message_stream(
        message: str,
        token: str,
        conversation_id: Optional[str] = None,
        include_search_info: bool = False,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Gửi tin nhắn và nhận streaming response"""
        if not message or len(message.strip()) == 0:
            yield {"type": "error", "content": "Tin nhắn không được để trống"}
            return

        if len(message) > MAX_MESSAGE_LENGTH:
            yield {
                "type": "error",
                "content": f"Tin nhắn không được quá {MAX_MESSAGE_LENGTH} ký tự",
            }
            return

        data = {
            "message": message.strip(),
            "conversation_id": conversation_id,
            "stream": True,
            "include_search_info": include_search_info,
        }

        async for chunk in APIClient.stream_request("/chat/", data, token):
            yield chunk

    @staticmethod
    async def get_conversations(token: str) -> tuple[bool, Optional[list], str]:
        """Lấy danh sách cuộc trò chuyện"""
        success, data, error = await APIClient.make_request(
            "GET", "/chat/conversations", token=token
        )

        if success and isinstance(data, list):
            return True, data, ""
        elif error == "INVALID_TOKEN":
            return False, None, "INVALID_TOKEN"
        else:
            return False, None, error or "Không thể tải danh sách cuộc trò chuyện"

    @staticmethod
    async def get_conversation_history(
        token: str, conversation_id: str
    ) -> tuple[bool, Optional[Dict], str]:
        """Lấy lịch sử cuộc trò chuyện"""
        endpoint = f"/chat/conversations/{conversation_id}"
        success, data, error = await APIClient.make_request(
            "GET", endpoint, token=token
        )

        if success and data:
            return True, data, ""
        elif error == "INVALID_TOKEN":
            return False, None, "INVALID_TOKEN"
        else:
            return False, None, error or "Không thể tải lịch sử cuộc trò chuyện"


# ================== UI FUNCTIONS ==================
def add_message(role: str, content: str):
    """Thêm tin nhắn vào session"""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.session_state.messages.append(
        {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
    )


def clear_conversation():
    """Xóa cuộc trò chuyện hiện tại"""
    st.session_state.messages = []
    st.session_state.current_conversation_id = None


def login_page():
    """Trang đăng nhập"""
    st.title("🤖 Chatbot Giới Thiệu Sản Phẩm")
    st.markdown("---")

    tab1, tab2 = st.tabs(["Đăng Nhập", "Đăng Ký"])

    with tab1:
        st.header("Đăng Nhập")
        with st.form("login_form"):
            username = st.text_input(
                "Tên đăng nhập", placeholder="Nhập tên đăng nhập..."
            )
            password = st.text_input(
                "Mật khẩu", type="password", placeholder="Nhập mật khẩu..."
            )
            submit_button = st.form_submit_button("🔐 Đăng Nhập", type="primary")

            if submit_button:
                if username and password:
                    with st.spinner("🔐 Đang đăng nhập..."):
                        success, result, error = run_async(
                            AuthService.login(username, password)
                        )

                        if success and result:
                            st.session_state.authenticated = True
                            st.session_state.access_token = result["access_token"]
                            st.session_state.user_info = {
                                "user_id": result["user_id"],
                                "username": result["username"],
                            }
                            update_activity()
                            st.success("✅ Đăng nhập thành công!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ {error}")
                else:
                    st.error("❌ Vui lòng nhập đầy đủ thông tin!")

    with tab2:
        st.header("Đăng Ký")
        with st.form("register_form"):
            reg_username = st.text_input("Tên đăng nhập", key="reg_username")
            reg_password = st.text_input(
                "Mật khẩu", type="password", key="reg_password"
            )
            reg_confirm_password = st.text_input("Xác nhận mật khẩu", type="password")
            register_button = st.form_submit_button("📝 Đăng Ký", type="secondary")

            if register_button:
                if reg_username and reg_password and reg_confirm_password:
                    if reg_password != reg_confirm_password:
                        st.error("❌ Mật khẩu xác nhận không khớp!")
                    else:
                        with st.spinner("📝 Đang đăng ký..."):
                            success, result, error = run_async(
                                AuthService.register(reg_username, reg_password)
                            )

                            if success:
                                st.success("✅ Đăng ký thành công! Vui lòng đăng nhập.")
                            else:
                                st.error(f"❌ {error}")
                else:
                    st.error("❌ Vui lòng nhập đầy đủ thông tin!")


def sidebar():
    """Sidebar với thông tin user và cuộc trò chuyện"""
    with st.sidebar:
        # User info
        user_info = st.session_state.get("user_info", {})
        st.header(f"👋 Xin chào, {user_info.get('username', 'User')}")

        # Logout button
        if st.button("🚪 Đăng xuất", type="secondary"):
            clear_session()
            st.success("👋 Đã đăng xuất thành công!")
            time.sleep(1)
            st.rerun()

        st.markdown("---")

        # New conversation
        if st.button("💬 Cuộc trò chuyện mới", type="primary"):
            clear_conversation()
            st.rerun()

        # Conversations
        st.subheader("📝 Lịch sử trò chuyện")

        # Refresh conversations
        if st.button("🔄 Tải lại"):
            token = st.session_state.get("access_token")
            if token and is_session_valid():
                with st.spinner("📝 Đang tải danh sách cuộc trò chuyện..."):
                    success, conversations, error = run_async(
                        ChatService.get_conversations(token)
                    )

                    if success and conversations is not None:
                        # Filter valid conversations
                        valid_conversations = [
                            conv
                            for conv in conversations
                            if isinstance(conv, dict) and conv.get("id")
                        ]
                        st.session_state.conversations = valid_conversations
                        st.success(
                            f"✅ Đã tải {len(valid_conversations)} cuộc trò chuyện"
                        )
                    elif error == "INVALID_TOKEN":
                        handle_token_error()
                    else:
                        st.error(f"❌ Lỗi tải danh sách: {error}")
            else:
                handle_token_error()

        # Display conversations
        conversations = st.session_state.get("conversations", [])
        if conversations:
            for conv in conversations[:10]:  # Hiển thị tối đa 10 cuộc trò chuyện
                conv_title = safe_format_title(conv.get("title"), 25)
                conv_id = conv.get("id")
                message_count = conv.get("message_count", 0)

                if conv_id and st.button(
                    f"💬 {conv_title} ({message_count})", key=f"conv_{conv_id}"
                ):
                    # Load conversation history
                    token = st.session_state.get("access_token")
                    if token and is_session_valid():
                        with st.spinner("📜 Đang tải lịch sử cuộc trò chuyện..."):
                            success, history, error = run_async(
                                ChatService.get_conversation_history(token, conv_id)
                            )

                            if success and history:
                                st.session_state.current_conversation_id = conv_id
                                st.session_state.messages = []

                                messages = history.get("messages", [])
                                for msg in messages:
                                    if msg.get("message") and msg.get("response"):
                                        add_message("user", msg["message"])
                                        add_message("assistant", msg["response"])

                                st.success(
                                    f"✅ Đã tải lịch sử ({len(messages)} tin nhắn)"
                                )
                                st.rerun()
                            elif error == "INVALID_TOKEN":
                                handle_token_error()
                            else:
                                st.error(f"❌ Lỗi tải lịch sử: {error}")
                    else:
                        handle_token_error()
        else:
            st.info("Chưa có cuộc trò chuyện nào")

        # Stats
        messages = st.session_state.get("messages", [])
        if messages:
            st.markdown("---")
            st.caption(f"📊 Cuộc trò chuyện hiện tại: {len(messages)} tin nhắn")


def chat_interface():
    """Giao diện chat chính"""
    st.title("🤖 Chatbot Tư Vấn Sản Phẩm")
    st.markdown("Hỏi tôi bất cứ điều gì về sản phẩm điện tử!")

    # Check session validity
    if not is_session_valid():
        st.warning("⏰ Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.")
        clear_session()
        st.rerun()

    # Update activity
    update_activity()

    # Display messages
    messages = st.session_state.get("messages", [])
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("timestamp"):
                st.caption(f"⏰ {format_timestamp(message['timestamp'])}")

    # Chat settings
    with st.sidebar:
        st.markdown("---")
        st.subheader("⚙️ Cài đặt Chat")

        include_search = st.checkbox(
            "🔍 Hiển thị thông tin tìm kiếm",
            value=False,
            help="Hiển thị chi tiết về quá trình tìm kiếm",
        )

        if st.button("🗑️ Xóa cuộc trò chuyện"):
            clear_conversation()
            st.success("Đã xóa cuộc trò chuyện")
            st.rerun()

    # Chat input
    if prompt := st.chat_input("💬 Nhập câu hỏi của bạn..."):
        # Add user message
        add_message("user", prompt)

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get bot response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            search_info = None

            try:
                token = st.session_state.get("access_token")
                if not token or not is_session_valid():
                    st.error("❌ Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.")
                    handle_token_error()
                    return

                # Create status container for better loading UX
                status_container = st.status("🤖 Đang xử lý câu hỏi...", expanded=True)

                try:
                    # Stream response
                    async def process_stream():
                        nonlocal full_response, search_info
                        first_chunk_received = False

                        with status_container:
                            async for chunk in ChatService.send_message_stream(
                                prompt,
                                token,
                                st.session_state.get("current_conversation_id"),
                                include_search,
                            ):
                                if chunk["type"] == "start":
                                    st.session_state.current_conversation_id = (
                                        chunk.get("conversation_id")
                                    )

                                elif chunk["type"] == "chunk":
                                    content = chunk.get("content", "")
                                    full_response += content

                                    # Update status and start showing content after first chunk
                                    if not first_chunk_received:
                                        status_container.update(
                                            label="✅ Đang trả lời...",
                                            state="running",
                                            expanded=False,
                                        )
                                        first_chunk_received = True

                                    # Show typing indicator
                                    message_placeholder.markdown(full_response + " ▌")

                                elif chunk["type"] == "end":
                                    message_placeholder.markdown(full_response)
                                    status_container.update(
                                        label="✅ Hoàn thành!", state="complete"
                                    )
                                    metadata = chunk.get("metadata", {})
                                    if metadata.get("search_info"):
                                        search_info = metadata["search_info"]

                                elif chunk["type"] == "error":
                                    error_content = chunk.get(
                                        "content", "Unknown error"
                                    )
                                    status_container.update(
                                        label="❌ Có lỗi xảy ra", state="error"
                                    )
                                    if error_content == "INVALID_TOKEN":
                                        st.error("❌ Phiên đăng nhập đã hết hạn.")
                                        handle_token_error()
                                        return
                                    else:
                                        st.error(f"❌ Lỗi: {error_content}")
                                        return

                    run_async(process_stream())

                    # Add response to history
                    if full_response:
                        add_message("assistant", full_response)

                    # Show search info if enabled
                    if search_info and include_search:
                        with st.expander("🔍 Thông tin tìm kiếm", expanded=False):
                            st.json(search_info)

                except Exception as stream_error:
                    # Update status on error
                    status_container.update(label="❌ Lỗi kết nối", state="error")
                    st.error(f"❌ Lỗi khi xử lý phản hồi: {str(stream_error)}")

            except Exception as e:
                st.error(f"❌ Lỗi khi gửi tin nhắn: {str(e)}")


def main():
    """Hàm main"""
    # Initialize session state
    init_session_state()

    # Main app logic
    if not st.session_state.get("authenticated", False):
        login_page()
    else:
        # Layout with sidebar
        sidebar()

        # Main chat interface
        chat_interface()

        # Footer
        st.markdown("---")
        st.markdown(
            "<div style='text-align: center; color: #666; font-size: 0.8em;'>"
            "🤖 Chatbot Giới Thiệu Sản Phẩm - Powered by LLM & Vector Search"
            "</div>",
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()  # Cách chạy: streamlit run src/streamlit/app.py
