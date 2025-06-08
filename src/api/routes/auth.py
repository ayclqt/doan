"""
Auth routes cho authentication endpoints.
"""

from litestar import Router, post, get, put, delete
from litestar.di import Provide
from litestar.exceptions import HTTPException
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from ...config import logger
from ..auth import get_auth_handler, require_auth, require_admin, AuthHandler
from ..auth.models import User
from ..schemas import (
    LoginRequest,
    LoginResponse,
    UserCreate,
    UserResponse,
    TokenResponse,
    RefreshTokenRequest,
    ChangePasswordRequest,
    SuccessResponse,
)


@post(
    "/auth/login",
    status_code=HTTP_200_OK,
    dependencies={"auth_handler": Provide(get_auth_handler)},
)
async def login(data: LoginRequest, auth_handler: AuthHandler) -> LoginResponse:
    """Login endpoint."""
    try:
        # Authenticate user
        user_in_db = auth_handler.authenticate_user(data.username, data.password)
        if not user_in_db:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )

        # Create tokens
        tokens = auth_handler.create_tokens(user_in_db)
        if not tokens:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create tokens",
            )

        # Create user response
        user_response = UserResponse(
            id=user_in_db.id,
            username=user_in_db.username,
            email=user_in_db.email,
            full_name=user_in_db.full_name,
            is_active=user_in_db.is_active,
            created_at=user_in_db.created_at.isoformat(),
        )

        token_response = TokenResponse(
            access_token=tokens["access_token"],
            token_type=tokens["token_type"],
            expires_in=tokens["expires_in"],
        )

        logger.info(f"User logged in: {data.username}")

        return LoginResponse(user=user_response, token=token_response)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login",
        )


@post(
    "/auth/register",
    status_code=HTTP_201_CREATED,
    dependencies={"auth_handler": Provide(get_auth_handler)},
)
async def register(data: UserCreate, auth_handler: AuthHandler) -> UserResponse:
    """Register new user endpoint."""
    try:
        # Create user
        user = auth_handler.create_user(data)
        if not user:
            raise HTTPException(
                status_code=HTTP_409_CONFLICT, detail="Username or email already exists"
            )

        logger.info(f"New user registered: {data.username}")

        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration",
        )


@post(
    "/auth/refresh",
    status_code=HTTP_200_OK,
    dependencies={"auth_handler": Provide(get_auth_handler)},
)
async def refresh_token(
    data: RefreshTokenRequest, auth_handler: AuthHandler
) -> TokenResponse:
    """Refresh access token endpoint."""
    try:
        # Refresh token
        new_tokens = auth_handler.refresh_access_token(data.refresh_token)
        if not new_tokens:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        return TokenResponse(
            access_token=new_tokens["access_token"],
            token_type=new_tokens["token_type"],
            expires_in=new_tokens["expires_in"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during token refresh",
        )


@post(
    "/auth/logout",
    status_code=HTTP_200_OK,
    dependencies={"user": Provide(require_auth)},
)
async def logout(
    data: RefreshTokenRequest, user: User, auth_handler: AuthHandler
) -> SuccessResponse:
    """Logout endpoint."""
    try:
        # Revoke refresh token
        success = auth_handler.revoke_refresh_token(data.refresh_token)

        logger.info(f"User logged out: {user.username}")

        return SuccessResponse(message="Successfully logged out")

    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during logout",
        )


@get("/auth/me", status_code=HTTP_200_OK, dependencies={"user": Provide(require_auth)})
async def get_current_user(user: User) -> UserResponse:
    """Get current user profile endpoint."""
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


@put("/auth/me", status_code=HTTP_200_OK, dependencies={"user": Provide(require_auth)})
async def update_profile(
    data: dict, user: User, auth_handler: AuthHandler
) -> UserResponse:
    """Update user profile endpoint."""
    try:
        from ..auth.models import UserUpdate

        # Create update object
        user_update = UserUpdate(
            email=data.get("email"), full_name=data.get("full_name")
        )

        # Update user
        updated_user = auth_handler.update_user(user.id, user_update)
        if not updated_user:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, detail="Could not update user profile"
            )

        logger.info(f"User profile updated: {user.username}")

        return UserResponse(
            id=updated_user.id,
            username=updated_user.username,
            email=updated_user.email,
            full_name=updated_user.full_name,
            is_active=updated_user.is_active,
            created_at=updated_user.created_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during profile update",
        )


@post(
    "/auth/change-password",
    status_code=HTTP_200_OK,
    dependencies={"user": Provide(require_auth)},
)
async def change_password(
    data: ChangePasswordRequest, user: User, auth_handler: AuthHandler
) -> SuccessResponse:
    """Change password endpoint."""
    try:
        # Validate new password confirmation
        if data.new_password != data.confirm_password:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="New password and confirmation do not match",
            )

        # Change password
        success = auth_handler.change_password(
            user.id, data.current_password, data.new_password
        )

        if not success:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
            )

        logger.info(f"Password changed for user: {user.username}")

        return SuccessResponse(message="Password changed successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during password change",
        )


@get(
    "/auth/users",
    status_code=HTTP_200_OK,
    dependencies={
        "user": Provide(require_admin),
        "auth_handler": Provide(get_auth_handler),
    },
)
async def list_users(
    user: User,
    skip: int = 0,
    limit: int = 100,
    auth_handler: AuthHandler = get_auth_handler(),
) -> list[UserResponse]:
    """List all users endpoint (admin only)."""
    try:
        users = auth_handler.list_users(skip=skip, limit=limit)

        return [
            UserResponse(
                id=u.id,
                username=u.username,
                email=u.email,
                full_name=u.full_name,
                is_active=u.is_active,
                created_at=u.created_at.isoformat(),
            )
            for u in users
        ]

    except Exception as e:
        logger.error(f"List users error: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while listing users",
        )


@get(
    "/auth/users/{user_id:int}",
    status_code=HTTP_200_OK,
    dependencies={"user": Provide(require_admin)},
)
async def get_user(user_id: int, user: User, auth_handler: AuthHandler) -> UserResponse:
    """Get user by ID endpoint (admin only)."""
    try:
        target_user = auth_handler.get_user_by_id(user_id)
        if not target_user:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")

        return UserResponse(
            id=target_user.id,
            username=target_user.username,
            email=target_user.email,
            full_name=target_user.full_name,
            is_active=target_user.is_active,
            created_at=target_user.created_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while getting user",
        )


@delete(
    "/auth/users/{user_id:int}",
    status_code=HTTP_200_OK,
    dependencies={"user": Provide(require_admin)},
)
async def deactivate_user(
    user_id: int, user: User, auth_handler: AuthHandler
) -> SuccessResponse:
    """Deactivate user endpoint (admin only)."""
    try:
        # Prevent self-deactivation
        if user_id == user.id:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account",
            )

        success = auth_handler.deactivate_user(user_id)
        if not success:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="User not found")

        logger.info(f"User deactivated by admin: {user_id}")

        return SuccessResponse(message="User deactivated successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Deactivate user error: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while deactivating user",
        )


@get(
    "/auth/stats",
    status_code=HTTP_200_OK,
    dependencies={"user": Provide(require_admin)},
)
async def get_auth_stats(user: User, auth_handler: AuthHandler) -> dict:
    """Get authentication statistics endpoint (admin only)."""
    try:
        stats = auth_handler.get_user_stats()
        return {"success": True, "data": stats}

    except Exception as e:
        logger.error(f"Get auth stats error: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while getting auth stats",
        )


# Router
auth_router = Router(
    path="/api/v1",
    route_handlers=[
        login,
        register,
        refresh_token,
        logout,
        get_current_user,
        update_profile,
        change_password,
        list_users,
        get_user,
        deactivate_user,
        get_auth_stats,
    ],
    tags=["Authentication"],
)


__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"
