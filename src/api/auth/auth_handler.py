"""
Auth handler cho business logic và user management.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from ...config import config, logger
from .models import User, UserInDB, UserCreate, UserUpdate
from .utils import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
)


class AuthHandler:
    """Handler cho authentication business logic."""

    def __init__(self):
        """Initialize auth handler."""
        # In-memory storage cho demo - trong production sẽ dùng database
        self._users: Dict[int, UserInDB] = {}
        self._users_by_username: Dict[str, int] = {}
        self._users_by_email: Dict[str, int] = {}
        self._refresh_tokens: Dict[str, dict] = {}
        self._user_id_counter = 1

        # Tạo default admin user
        self._create_default_users()

    def _create_default_users(self):
        """Tạo default users cho testing."""
        # Admin user
        admin_user = UserCreate(
            username="admin",
            email="admin@example.com",
            password="admin123",
            full_name="Administrator",
        )
        self.create_user(admin_user, is_superuser=True)

        # Demo user
        demo_user = UserCreate(
            username="demo",
            email="demo@example.com",
            password="demo123",
            full_name="Demo User",
        )
        self.create_user(demo_user)

    def create_user(
        self, user_data: UserCreate, is_superuser: bool = False
    ) -> Optional[User]:
        """Tạo user mới."""
        try:
            # Kiểm tra username đã tồn tại
            if user_data.username in self._users_by_username:
                logger.warning(f"Username already exists: {user_data.username}")
                return None

            # Kiểm tra email đã tồn tại
            if user_data.email in self._users_by_email:
                logger.warning(f"Email already exists: {user_data.email}")
                return None

            # Tạo user mới
            user_id = self._user_id_counter
            self._user_id_counter += 1

            hashed_password = hash_password(user_data.password)

            db_user = UserInDB(
                id=user_id,
                username=user_data.username,
                email=user_data.email,
                full_name=user_data.full_name,
                hashed_password=hashed_password,
                is_active=True,
                is_superuser=is_superuser,
                created_at=datetime.now(timezone.utc),
                login_count=0,
            )

            # Lưu vào storage
            self._users[user_id] = db_user
            self._users_by_username[user_data.username] = user_id
            self._users_by_email[user_data.email] = user_id

            logger.info(f"User created successfully: {user_data.username}")

            return User(
                id=db_user.id,
                username=db_user.username,
                email=db_user.email,
                full_name=db_user.full_name,
                is_active=db_user.is_active,
                created_at=db_user.created_at,
                last_login=db_user.last_login,
            )

        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None

    def authenticate_user(self, username: str, password: str) -> Optional[UserInDB]:
        """Authenticate user với username/password."""
        try:
            user_id = self._users_by_username.get(username)
            if not user_id:
                return None

            user = self._users.get(user_id)
            if not user or not user.is_active:
                return None

            if not verify_password(password, user.hashed_password):
                return None

            # Update login info
            user.last_login = datetime.now(timezone.utc)
            user.login_count += 1

            logger.info(f"User authenticated: {username}")
            return user

        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return None

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Lấy user theo ID."""
        user = self._users.get(user_id)
        if user and user.is_active:
            return User(
                id=user.id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                created_at=user.created_at,
                last_login=user.last_login,
            )
        return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Lấy user theo username."""
        user_id = self._users_by_username.get(username)
        if user_id:
            return self.get_user_by_id(user_id)
        return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Lấy user theo email."""
        user_id = self._users_by_email.get(email)
        if user_id:
            return self.get_user_by_id(user_id)
        return None

    def update_user(self, user_id: int, user_update: UserUpdate) -> Optional[User]:
        """Cập nhật thông tin user."""
        try:
            user = self._users.get(user_id)
            if not user:
                return None

            # Update fields
            if user_update.email is not None:
                # Kiểm tra email mới không trùng
                if (
                    user_update.email in self._users_by_email
                    and self._users_by_email[user_update.email] != user_id
                ):
                    return None

                # Update email mapping
                old_email = user.email
                if old_email in self._users_by_email:
                    del self._users_by_email[old_email]
                self._users_by_email[user_update.email] = user_id
                user.email = user_update.email

            if user_update.full_name is not None:
                user.full_name = user_update.full_name

            if user_update.is_active is not None:
                user.is_active = user_update.is_active

            user.updated_at = datetime.now(timezone.utc)

            logger.info(f"User updated: {user.username}")

            return User(
                id=user.id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                created_at=user.created_at,
                last_login=user.last_login,
            )

        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return None

    def change_password(
        self, user_id: int, current_password: str, new_password: str
    ) -> bool:
        """Đổi mật khẩu user."""
        try:
            user = self._users.get(user_id)
            if not user:
                return False

            # Verify current password
            if not verify_password(current_password, user.hashed_password):
                return False

            # Update password
            user.hashed_password = hash_password(new_password)
            user.updated_at = datetime.now(timezone.utc)

            logger.info(f"Password changed for user: {user.username}")
            return True

        except Exception as e:
            logger.error(f"Error changing password: {e}")
            return False

    def create_tokens(self, user: UserInDB) -> dict:
        """Tạo access và refresh tokens."""
        try:
            token_data = {"user_id": user.id, "username": user.username}

            access_token = create_access_token(token_data)
            refresh_token = create_refresh_token(token_data)

            # Lưu refresh token
            self._refresh_tokens[refresh_token] = {
                "user_id": user.id,
                "created_at": datetime.now(timezone.utc),
                "is_active": True,
            }

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": config.access_token_expire_minutes * 60,
            }

        except Exception as e:
            logger.error(f"Error creating tokens: {e}")
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[dict]:
        """Refresh access token bằng refresh token."""
        try:
            # Verify refresh token
            payload = verify_token(refresh_token)
            if not payload or payload.get("token_type") != "refresh":
                return None

            # Kiểm tra token có trong storage không
            token_data = self._refresh_tokens.get(refresh_token)
            if not token_data or not token_data["is_active"]:
                return None

            user_id = payload.get("user_id")
            user = self._users.get(user_id)
            if not user or not user.is_active:
                return None

            # Tạo access token mới
            new_token_data = {"user_id": user.id, "username": user.username}

            access_token = create_access_token(new_token_data)

            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": config.access_token_expire_minutes * 60,
            }

        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return None

    def revoke_refresh_token(self, refresh_token: str) -> bool:
        """Revoke refresh token."""
        try:
            if refresh_token in self._refresh_tokens:
                self._refresh_tokens[refresh_token]["is_active"] = False
                return True
            return False
        except Exception as e:
            logger.error(f"Error revoking token: {e}")
            return False

    def get_current_user_from_token(self, token: str) -> Optional[User]:
        """Lấy user hiện tại từ access token."""
        try:
            payload = verify_token(token)
            if not payload or payload.get("token_type") != "access":
                return None

            user_id = payload.get("user_id")
            if not user_id:
                return None

            return self.get_user_by_id(user_id)

        except Exception as e:
            logger.error(f"Error getting user from token: {e}")
            return None

    def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Lấy danh sách users."""
        try:
            users = []
            for user_data in list(self._users.values())[skip : skip + limit]:
                if user_data.is_active:
                    users.append(
                        User(
                            id=user_data.id,
                            username=user_data.username,
                            email=user_data.email,
                            full_name=user_data.full_name,
                            is_active=user_data.is_active,
                            created_at=user_data.created_at,
                            last_login=user_data.last_login,
                        )
                    )
            return users
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []

    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate user."""
        try:
            user = self._users.get(user_id)
            if user:
                user.is_active = False
                user.updated_at = datetime.now(timezone.utc)
                logger.info(f"User deactivated: {user.username}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deactivating user: {e}")
            return False

    def activate_user(self, user_id: int) -> bool:
        """Activate user."""
        try:
            user = self._users.get(user_id)
            if user:
                user.is_active = True
                user.updated_at = datetime.now(timezone.utc)
                logger.info(f"User activated: {user.username}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error activating user: {e}")
            return False

    def get_user_stats(self) -> dict:
        """Lấy thống kê users."""
        try:
            total_users = len(self._users)
            active_users = len([u for u in self._users.values() if u.is_active])
            superusers = len([u for u in self._users.values() if u.is_superuser])

            return {
                "total_users": total_users,
                "active_users": active_users,
                "inactive_users": total_users - active_users,
                "superusers": superusers,
                "total_refresh_tokens": len(self._refresh_tokens),
                "active_refresh_tokens": len(
                    [t for t in self._refresh_tokens.values() if t["is_active"]]
                ),
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}


__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"
