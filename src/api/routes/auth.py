from litestar import Controller, post
from litestar.exceptions import (
    InternalServerException,
    NotAuthorizedException,
)
from litestar.status_codes import HTTP_201_CREATED

from ...config import logger
from ..auth import AuthService
from ..schemas import LoginRequest, LoginResponse, RegisterRequest, RegisterResponse

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


class Auth(Controller):
    """Authentication router for login functionality"""

    path = "/auth"
    tags = ["Authentication"]

    @post("/login")
    async def login(self, data: LoginRequest) -> LoginResponse:
        """
        Authenticate user and return JWT token

        Args:
            data: Login credentials (username and password)

        Returns:
            LoginResponse with JWT token and user info

        Raises:
            NotAuthorizedException: If credentials are invalid
            InternalServerException: If token creation fails
        """
        logger.info("Login attempt", username=data.username)

        # Authenticate user
        user = await AuthService.authenticate_user(data.username, data.password)

        if not user:
            logger.warning("Invalid login attempt", username=data.username)
            raise NotAuthorizedException(detail="Invalid username or password")

        # Create JWT token
        try:
            token = AuthService.create_token(user)
            logger.info("Login successful", username=data.username, user_id=user.id)

            return LoginResponse(
                access_token=token,
                token_type="bearer",
                expires_in=24 * 60 * 60,  # 24 hours in seconds
                user_id=user.id,
                username=user.username,
            )

        except Exception as e:
            logger.error("Error creating token", username=data.username, error=str(e))
            raise InternalServerException(detail="Error creating authentication token")

    @post("/register", status_code=HTTP_201_CREATED)
    async def register(self, data: RegisterRequest) -> RegisterResponse:
        """
        Register a new user

        Args:
            data: Registration data (username and password)

        Returns:
            RegisterResponse with user info

        Raises:
            ConflictException: If username already exists
            InternalServerException: If user creation fails
        """
        logger.info("Registration attempt", username=data.username)

        try:
            # Create new user
            user = await AuthService.create_user(data.username, data.password)

            if not user:
                logger.warning("Username already exists", username=data.username)
                raise Exception("Username already exists")

            logger.info(
                "Registration successful", username=data.username, user_id=user.id
            )

            return RegisterResponse(
                user_id=user.id,
                username=user.username,
                message="User registered successfully",
            )

        except Exception as e:
            logger.error("Error creating user", username=data.username, error=str(e))
            raise InternalServerException(detail="Error creating user account")
