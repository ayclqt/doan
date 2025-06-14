#!/usr/bin/env python3
"""
Ứng dụng Streamlit cho Chatbot giới thiệu sản phẩm
Phiên bản refactored với auto-load conversations và pagination
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Dict, List, Optional

import aiohttp
import streamlit as st
from dotenv import load_dotenv

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"

# ================== CONFIGURATION ==================
load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", 300))
MAX_MESSAGE_LENGTH = int(os.getenv("MAX_MESSAGE_LENGTH", 1000))
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", 30))
CONVERSATIONS_PER_PAGE = 8

# ================== STREAMLIT CONFIG ==================
st.set_page_config(
    page_title="Chatbot Giới Thiệu Sản Phẩm",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ================== CSS STYLES ==================
st.write(
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

.conversation-item {
    margin-bottom: 0.5rem;
    padding: 0.5rem;
    border-radius: 0.25rem;
    border: 1px solid #e0e0e0;
}

.error-message {
    color: #ff4444;
    background-color: #ffe6e6;
    padding: 0.5rem;
    border-radius: 0.25rem;
    margin: 0.5rem 0;
}

.success-message {
    color: #00aa00;
    background-color: #e6ffe6;
    padding: 0.5rem;
    border-radius: 0.25rem;
    margin: 0.5rem 0;
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


def format_timestamp(timestamp: str) -> str:
    """Format timestamp cho hiển thị"""
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime("%H:%M:%S")
    except Exception:
        return ""


def safe_format_title(title: str, max_length: int = 25) -> str:
    """Format title an toàn"""
    if not title:
        return "Cuộc trò chuyện"
    if len(title) > max_length:
        return title[:max_length] + "..."
    return title


def get_friendly_error_message(error: str) -> str:
    """Chuyển đổi error message thành thông báo thân thiện"""
    error_mappings = {
        "INVALID_TOKEN": "❌ Thông tin đăng nhập không hợp lệ",
        "Invalid username or password": "❌ Tên đăng nhập hoặc mật khẩu không chính xác",
        "Request timeout": "⏳ Kết nối bị timeout, vui lòng thử lại",
        "Không thể kết nối đến API server": "🌐 Không thể kết nối đến server",
        "Username already exists": "❌ Tên đăng nhập đã tồn tại",
    }

    for key, friendly_msg in error_mappings.items():
        if key.lower() in error.lower():
            return friendly_msg

    return f"❌ {error}"


# ================== STATE MANAGEMENT ==================
class SessionState:
    """Quản lý session state"""

    @staticmethod
    def init():
        """Khởi tạo session state"""
        default_values = {
            "authenticated": False,
            "user_info": None,
            "access_token": None,
            "current_conversation_id": None,
            "messages": [],
            "conversations": [],
            "conversations_page": 1,
            "has_more_conversations": True,
            "last_activity": datetime.now(),
            "loading_conversations": False,
        }

        for key, value in default_values.items():
            if key not in st.session_state:
                st.session_state[key] = value

    @staticmethod
    def is_valid() -> bool:
        """Kiểm tra session có hợp lệ không"""
        if not st.session_state.get("authenticated", False):
            return False

        if not st.session_state.get("access_token"):
            return False

        last_activity = st.session_state.get("last_activity")
        if not last_activity:
            return False

        if datetime.now() - last_activity > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
            return False

        return True

    @staticmethod
    def update_activity():
        """Cập nhật thời gian hoạt động cuối"""
        st.session_state.last_activity = datetime.now()

    @staticmethod
    def clear():
        """Xóa session state"""
        keys_to_clear = [
            "authenticated",
            "user_info",
            "access_token",
            "current_conversation_id",
            "messages",
            "conversations",
            "conversations_page",
            "has_more_conversations",
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        SessionState.init()


# ================== API CLIENT ==================
class APIClient:
    """Client để gọi API với error handling tốt hơn"""

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


class ConversationService:
    """Service xử lý conversations với pagination"""

    @staticmethod
    async def get_conversations(
        token: str, page: int = 1, limit: int = CONVERSATIONS_PER_PAGE
    ) -> tuple[bool, Optional[List], str]:
        """Lấy danh sách cuộc trò chuyện với pagination"""
        offset = (page - 1) * limit
        endpoint = f"/chat/conversations?limit={limit}&offset={offset}"

        success, data, error = await APIClient.make_request(
            "GET", endpoint, token=token
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


class ChatService:
    """Service xử lý chat - đã loại bỏ include_search_info"""

    @staticmethod
    async def send_message_stream(
        message: str,
        token: str,
        conversation_id: Optional[str] = None,
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

        # API sẽ tự động sử dụng include_search_info=False theo default
        data = {
            "message": message.strip(),
            "conversation_id": conversation_id,
            "stream": True,
        }

        async for chunk in APIClient.stream_request("/chat/", data, token):
            yield chunk


# ================== UI COMPONENTS ==================
class ConversationManager:
    """Quản lý conversations với pagination"""

    @staticmethod
    async def load_conversations(page: int = 1) -> bool:
        """Load conversations cho trang chỉ định"""
        token = st.session_state.get("access_token")
        if not token or not SessionState.is_valid():
            return False

        st.session_state.loading_conversations = True

        try:
            success, conversations, error = await ConversationService.get_conversations(
                token, page, CONVERSATIONS_PER_PAGE
            )

            if success and conversations is not None:
                valid_conversations = [
                    conv
                    for conv in conversations
                    if isinstance(conv, dict) and conv.get("id")
                ]

                st.session_state.conversations = valid_conversations
                st.session_state.conversations_page = page
                st.session_state.has_more_conversations = (
                    len(valid_conversations) >= CONVERSATIONS_PER_PAGE
                )

                return True
            elif error == "INVALID_TOKEN":
                AuthHandler.handle_token_error()
                return False
            else:
                st.toast(f"Lỗi tải conversations: {error}", icon="❌")
                return False

        except Exception as e:
            st.toast(f"Lỗi không mong muốn: {str(e)}", icon="❌")
            return False
        finally:
            st.session_state.loading_conversations = False

    @staticmethod
    def render_pagination():
        """Render pagination controls"""
        current_page = st.session_state.get("conversations_page", 1)
        has_more = st.session_state.get("has_more_conversations", False)

        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button("◀", disabled=(current_page <= 1), key="prev_page"):
                if run_async(ConversationManager.load_conversations(current_page - 1)):
                    st.rerun()

        with col2:
            if st.button("▶", disabled=not has_more, key="next_page"):
                if run_async(ConversationManager.load_conversations(current_page + 1)):
                    st.rerun()

    @staticmethod
    def render_conversation_list():
        """Render danh sách conversations"""
        conversations = st.session_state.get("conversations", [])

        if not conversations:
            st.toast("Chưa có cuộc trò chuyện nào", icon="ℹ️")
            return

        for conv in conversations:
            conv_title = safe_format_title(conv.get("title"), 25)
            conv_id = conv.get("id")
            message_count = conv.get("message_count", 0)

            if conv_id and st.button(
                f"💬 {conv_title} ({message_count})", key=f"conv_{conv_id}"
            ):
                ConversationManager.load_conversation_history(conv_id)

    @staticmethod
    def load_conversation_history(conv_id: str):
        """Load lịch sử cuộc trò chuyện"""
        token = st.session_state.get("access_token")
        if not token or not SessionState.is_valid():
            AuthHandler.handle_token_error()
            return

        with st.spinner("📜 Đang tải lịch sử cuộc trò chuyện..."):
            success, history, error = run_async(
                ConversationService.get_conversation_history(token, conv_id)
            )

            if success and history:
                st.session_state.current_conversation_id = conv_id
                st.session_state.messages = []

                messages = history.get("messages", [])
                for msg in messages:
                    if msg.get("message") and msg.get("response"):
                        MessageHandler.add_message("user", msg["message"])
                        MessageHandler.add_message("assistant", msg["response"])

                st.toast(f"Đã tải lịch sử ({len(messages)} tin nhắn)", icon="✅")
                st.rerun()
            elif error == "INVALID_TOKEN":
                AuthHandler.handle_token_error()
            else:
                st.toast("Lỗi tải lịch sử: " + error, icon="❌")


class MessageHandler:
    """Xử lý messages"""

    @staticmethod
    def add_message(role: str, content: str):
        """Thêm tin nhắn vào session"""
        if "messages" not in st.session_state:
            st.session_state.messages = []

        st.session_state.messages.append(
            {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
        )

    @staticmethod
    def clear_conversation():
        """Xóa cuộc trò chuyện hiện tại"""
        st.session_state.messages = []
        st.session_state.current_conversation_id = None

    @staticmethod
    def render_messages():
        """Render danh sách messages"""
        messages = st.session_state.get("messages", [])
        for message in messages:
            with st.chat_message(message["role"]):
                st.write(message["content"], unsafe_allow_html=True)
                if message.get("timestamp"):
                    st.caption(f"⏰ {format_timestamp(message['timestamp'])}")


class AuthHandler:
    """Xử lý authentication"""

    @staticmethod
    def handle_token_error():
        """Xử lý lỗi token"""
        st.toast("Phiên đăng nhập đã hết hạn", icon="❌")
        st.toast("Bạn sẽ được chuyển về trang đăng nhập", icon="ℹ️")

        for i in range(3, 0, -1):
            st.toast(f"Chuyển hướng sau {i} giây...", icon="⏳")
            time.sleep(1)

        SessionState.clear()
        st.rerun()

    @staticmethod
    async def auto_load_conversations_on_login():
        """Tự động load conversations sau khi đăng nhập"""
        if st.session_state.get("authenticated") and not st.session_state.get(
            "conversations"
        ):
            await ConversationManager.load_conversations(1)


# ================== UI PAGES ==================
def login_page():
    """Trang đăng nhập"""
    st.title("🤖 Chatbot Giới Thiệu Sản Phẩm")
    st.write("---")

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
                        SessionState.update_activity()
                        st.toast("Đăng nhập thành công!", icon="✅")

                        # Auto-load conversations
                        run_async(AuthHandler.auto_load_conversations_on_login())

                        time.sleep(1)
                        st.rerun()
                    else:
                        friendly_error = get_friendly_error_message(error)
                        # Remove duplicate icon from error message
                        clean_error = (
                            friendly_error.replace("❌ ", "")
                            if friendly_error.startswith("❌ ")
                            else friendly_error
                        )
                        st.toast(clean_error, icon="❌")
                        if (
                            "timeout" in error.lower()
                            or "kết nối" in friendly_error.lower()
                        ):
                            if st.button("🔄 Thử lại", key="login_retry"):
                                st.rerun()
                else:
                    st.toast("Vui lòng nhập đầy đủ thông tin!", icon="❌")

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
                        st.toast("Mật khẩu xác nhận không khớp!", icon="❌")
                    else:
                        with st.spinner("📝 Đang đăng ký..."):
                            success, result, error = run_async(
                                AuthService.register(reg_username, reg_password)
                            )

                            if success:
                                st.toast(
                                    "Đăng ký thành công! Vui lòng đăng nhập.", icon="✅"
                                )
                            else:
                                friendly_error = get_friendly_error_message(error)
                                clean_error = (
                                    friendly_error.replace("❌ ", "")
                                    if friendly_error.startswith("❌ ")
                                    else friendly_error
                                )
                                st.toast(clean_error, icon="❌")
                                if (
                                    "timeout" in error.lower()
                                    or "kết nối" in friendly_error.lower()
                                ):
                                    if st.button("🔄 Thử lại", key="register_retry"):
                                        st.rerun()
                else:
                    st.toast("Vui lòng nhập đầy đủ thông tin!", icon="❌")


def sidebar():
    """Sidebar với thông tin user và conversations"""
    with st.sidebar:
        # User info
        user_info = st.session_state.get("user_info", {})
        st.header(f"👋 Xin chào, {user_info.get('username', 'User')}")

        # Logout button
        if st.button("🚪 Đăng xuất", type="secondary"):
            SessionState.clear()
            st.toast("👋 Đã đăng xuất thành công!", icon="✅")
            time.sleep(1)
            st.rerun()

        st.write("---")

        # New conversation
        if st.button("💬 Cuộc trò chuyện mới", type="primary"):
            MessageHandler.clear_conversation()
            st.toast("Đã tạo cuộc trò chuyện mới!", icon="✅")
            st.rerun()

        # Conversations section
        st.subheader("📝 Lịch sử trò chuyện")

        # Conversations list
        if st.session_state.get("loading_conversations", False):
            st.toast("⏳ Đang tải danh sách cuộc trò chuyện...", icon="⏳")
        else:
            ConversationManager.render_conversation_list()

        # Pagination controls (moved below conversation list)
        ConversationManager.render_pagination()

        # Delete conversation button (moved outside of settings)
        if st.button("🗑️ Xóa cuộc trò chuyện", type="secondary"):
            MessageHandler.clear_conversation()
            st.toast("Đã xóa cuộc trò chuyện", icon="✅")
            st.rerun()

        # Stats
        messages = st.session_state.get("messages", [])
        if messages:
            st.caption(f"📊 Cuộc trò chuyện hiện tại: {len(messages)} tin nhắn")


def chat_interface():
    """Giao diện chat chính - đã loại bỏ search settings"""
    st.title("🤖 Chatbot Tư Vấn Sản Phẩm")
    st.write("Hỏi tôi bất cứ điều gì về sản phẩm điện tử!")

    # Check session validity
    if not SessionState.is_valid():
        st.toast("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.", icon="⚠️")
        SessionState.clear()
        st.rerun()

    # Update activity
    SessionState.update_activity()

    # Display messages
    MessageHandler.render_messages()

    # Chat input
    if prompt := st.chat_input("💬 Nhập câu hỏi của bạn..."):
        # Add user message
        MessageHandler.add_message("user", prompt)

        # Display user message
        with st.chat_message("user"):
            st.write(prompt)

        # Get bot response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            try:
                token = st.session_state.get("access_token")
                if not token or not SessionState.is_valid():
                    st.toast(
                        "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.", icon="❌"
                    )
                    AuthHandler.handle_token_error()
                    return

                status_container = st.status(
                    "🤔 Đang phân tích câu hỏi...", expanded=True
                )

                try:

                    async def process_stream():
                        nonlocal full_response
                        first_chunk_received = False

                        with status_container:
                            async for chunk in ChatService.send_message_stream(
                                prompt,
                                token,
                                st.session_state.get("current_conversation_id"),
                            ):
                                if chunk["type"] == "start":
                                    st.session_state.current_conversation_id = (
                                        chunk.get("conversation_id")
                                    )

                                elif chunk["type"] == "chunk":
                                    content = chunk.get("content", "")
                                    full_response += content

                                    if not first_chunk_received:
                                        status_container.update(
                                            label="💭 Đang xử lý...",
                                            state="running",
                                            expanded=False,
                                        )
                                        first_chunk_received = True

                                    message_placeholder.write(full_response + " ▌")

                                elif chunk["type"] == "end":
                                    message_placeholder.write(full_response)
                                    status_container.update(
                                        label="✅ Hoàn thành!", state="complete"
                                    )

                                elif chunk["type"] == "error":
                                    error_content = chunk.get(
                                        "content", "Unknown error"
                                    )
                                    status_container.update(
                                        label="❌ Có lỗi xảy ra", state="error"
                                    )
                                    if error_content == "INVALID_TOKEN":
                                        st.toast(
                                            "Phiên đăng nhập đã hết hạn.", icon="❌"
                                        )
                                        AuthHandler.handle_token_error()
                                        return
                                    else:
                                        st.toast(f"Lỗi: {error_content}", icon="❌")
                                        return

                    run_async(process_stream())

                    # Add response to history
                    if full_response:
                        MessageHandler.add_message("assistant", full_response)

                except Exception as stream_error:
                    status_container.update(label="❌ Lỗi kết nối", state="error")
                    st.toast(f"Lỗi khi xử lý phản hồi: {str(stream_error)}", icon="❌")

            except Exception as e:
                st.toast(f"Lỗi khi gửi tin nhắn: {str(e)}", icon="❌")


def main():
    """Hàm main"""
    # Initialize session state
    SessionState.init()

    # Main app logic
    if not st.session_state.get("authenticated", False):
        login_page()
    else:
        # Layout with sidebar
        sidebar()

        # Main chat interface
        chat_interface()

        # Footer
        st.write("---")
        st.write(
            "<div style='text-align: center; color: #666; font-size: 0.8em;'>"
            "🤖 Chatbot Giới Thiệu Sản Phẩm - Powered by LLM & Vector Search"
            "</div>",
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
