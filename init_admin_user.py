#!/usr/bin/env python3
"""
Script to initialize default admin user in Redis.
Run this script once to create the default admin user.
"""

import asyncio
import sys
from pathlib import Path

from src import redis_user_service
from src import config, logger

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def check_admin_user_exists():
    """Check if admin user already exists"""
    try:
        # Check if admin user exists
        existing_user = await redis_user_service.get_user_by_username(config.api_user)
        if existing_user:
            logger.warning(
                "Admin user already exists",
                username=existing_user.username,
                user_id=existing_user.id,
            )

            # Verify authentication still works
            auth_user = await redis_user_service.authenticate_user(
                config.api_user, config.api_pass
            )

            if auth_user:
                logger.info("✅ Admin user authentication verified")
                return True
            else:
                logger.warning("⚠️  Admin user exists but authentication failed")
                return True

        return False

    except Exception as e:
        logger.error("❌ Error checking admin user", error=str(e))
        return False


async def init_admin_user():
    """Initialize default admin user in Redis"""
    try:
        logger.info("Initializing admin user...")

        # Check if admin user already exists
        if await check_admin_user_exists():
            logger.info("✅ Admin user initialization skipped - user already exists")
            return

        logger.info("🔄 Creating new admin user...")

        # Create admin user
        admin_user = await redis_user_service.create_user(
            username=config.api_user, password=config.api_pass
        )

        if admin_user:
            logger.info(
                "Admin user created successfully",
                username=admin_user.username,
                user_id=admin_user.id,
            )
            logger.info(
                "✅ Admin user created", username=admin_user.username, id=admin_user.id
            )
        else:
            logger.error("❌ Failed to create admin user")
            sys.exit(1)

        # Verify the user can be authenticated
        auth_user = await redis_user_service.authenticate_user(
            config.api_user, config.api_pass
        )

        if auth_user:
            logger.info("✅ Admin user authentication verified")
        else:
            logger.error("❌ Admin user authentication failed")
            sys.exit(1)

    except Exception as e:
        logger.error("❌ Error initializing admin user", error=str(e))
        sys.exit(1)
    finally:
        # Close Redis connection
        await redis_user_service.close()


async def check_redis_connection():
    """Check if Redis is available"""
    try:
        redis_client = await redis_user_service.get_redis_client()
        await redis_client.ping()
        logger.info("✅ Redis connection successful")
        return True
    except Exception as e:
        logger.error(
            "❌ Redis connection failed! Please make sure Redis is running and accessible",
            redis=config.redis_url,
            error=str(e),
        )
        return False


async def main():
    """Main function"""
    logger.info(
        "🚀 Initializing admin user for JWT authentication...",
        redis=config.redis_url,
        username=config.api_user,
    )

    # Check Redis connection first
    if not await check_redis_connection():
        sys.exit(1)

    # Initialize admin user
    await init_admin_user()

    logger.info("✅ Admin user initialization completed!")


if __name__ == "__main__":
    asyncio.run(main())
