import uuid
from datetime import datetime, timezone
from typing import Optional

import bcrypt
import redis.asyncio as redis

from ...config import config
from ..schemas.auth import User

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class RedisUserService:
    """Redis-based user management service"""

    def __init__(self):
        self.redis_client = None

    async def get_redis_client(self) -> redis.Redis:
        """Get or create Redis client"""
        if self.redis_client is None:
            self.redis_client = redis.from_url(config.redis_url, decode_responses=True)
        return self.redis_client

    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def _verify_password(password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))

    async def create_user(self, username: str, password: str) -> Optional[User]:
        """
        Create a new user with hashed password

        Args:
            username: Username
            password: Plain text password

        Returns:
            User object if created successfully, None if username exists
        """
        redis_client = await self.get_redis_client()

        # Check if user already exists
        if await redis_client.exists(f"index:{username}"):
            return None

        # Generate unique user ID
        user_id = str(uuid.uuid4())

        # Hash password
        hashed_password = self._hash_password(password)

        # Create user data as hash
        user_data = {
            "id": user_id,
            "username": username,
            "password": hashed_password,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_active": "1",  # Store as string for Redis compatibility
        }

        # Store user data in Redis as hash
        await redis_client.hset(f"user:{user_id}", mapping=user_data)
        await redis_client.set(f"index:{username}", user_id)

        return User(
            id=user_id,
            username=username,
            hashed_password=hashed_password,
            created_at=datetime.now(timezone.utc),
            is_active=True,
        )

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username

        Args:
            username: Username

        Returns:
            User object if found, None otherwise
        """
        redis_client = await self.get_redis_client()

        user_id = await redis_client.get(f"index:{username}")
        if not user_id:
            return None

        user_data = await redis_client.hgetall(f"user:{user_id}")
        if not user_data:
            return None

        return User(
            id=user_data["id"],
            username=user_data["username"],
            hashed_password=user_data["password"],
            created_at=datetime.fromisoformat(user_data["created_at"]),
            is_active=user_data["is_active"] == "1",
        )

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID

        Args:
            user_id: User ID

        Returns:
            User object if found, None otherwise
        """
        redis_client = await self.get_redis_client()

        user_data = await redis_client.hgetall(f"user:{user_id}")
        if not user_data:
            return None

        return User(
            id=user_data["id"],
            username=user_data["username"],
            hashed_password=user_data["password"],
            created_at=datetime.fromisoformat(user_data["created_at"]),
            is_active=user_data["is_active"] == "1",
        )

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate user with username and password

        Args:
            username: Username
            password: Plain text password

        Returns:
            User object if authentication successful, None otherwise
        """
        user = await self.get_user_by_username(username)
        if not user or not user.is_active:
            return None

        if not self._verify_password(password, user.hashed_password):
            return None

        return user

    async def update_user_last_login(self, username: str):
        """
        Update user's last login time

        Args:
            username: Username
        """
        redis_client = await self.get_redis_client()

        user_id = await redis_client.get(f"index:{username}")
        if user_id:
            await redis_client.hset(
                f"user:{user_id}", "last_login", datetime.now(timezone.utc).isoformat()
            )

    async def deactivate_user(self, username: str) -> bool:
        """
        Deactivate user account

        Args:
            username: Username

        Returns:
            True if user was deactivated, False if user not found
        """
        redis_client = await self.get_redis_client()

        user_id = await redis_client.get(f"index:{username}")
        if not user_id:
            return False

        await redis_client.hset(f"user:{user_id}", "is_active", "0")
        return True


# Global instance
redis_user_service = RedisUserService()
