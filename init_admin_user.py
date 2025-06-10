#!/usr/bin/env python3
"""
Script to initialize default admin user in Redis.
Run this script once to create the default admin user.
"""

import asyncio
import sys
from pathlib import Path

from src.api.auth.redis_service import redis_user_service
from src.config import config, logger

__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def init_admin_user():
    """Initialize default admin user in Redis"""
    try:
        logger.info("Initializing admin user...")

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
            print(
                f"✅ Admin user '{admin_user.username}' created with ID: {admin_user.id}"
            )
        else:
            logger.info("Admin user already exists")
            print(f"ℹ️  Admin user '{config.api_user}' already exists")

        # Verify the user can be authenticated
        auth_user = await redis_user_service.authenticate_user(
            config.api_user, config.api_pass
        )

        if auth_user:
            logger.info("Admin user authentication verified")
            print("✅ Admin user authentication verified")
        else:
            logger.error("Admin user authentication failed")
            print("❌ Admin user authentication failed")

    except Exception as e:
        logger.error("Error initializing admin user", error=str(e))
        print(f"❌ Error initializing admin user: {e}")
        sys.exit(1)
    finally:
        # Close Redis connection
        await redis_user_service.close()


async def check_redis_connection():
    """Check if Redis is available"""
    try:
        redis_client = await redis_user_service.get_redis_client()
        await redis_client.ping()
        logger.info("Redis connection successful")
        print("✅ Redis connection successful")
        return True
    except Exception as e:
        logger.error("Redis connection failed", error=str(e))
        print(f"❌ Redis connection failed: {e}")
        print("Please make sure Redis is running and accessible at:", config.redis_url)
        return False


async def main():
    """Main function"""
    print("🚀 Initializing admin user for JWT authentication...")
    print(f"Redis URL: {config.redis_url}")
    print(f"Admin username: {config.api_user}")
    print("-" * 50)

    # Check Redis connection first
    if not await check_redis_connection():
        sys.exit(1)

    # Initialize admin user
    await init_admin_user()

    print("-" * 50)
    print("✅ Admin user initialization completed!")
    print("\nYou can now:")
    print("1. Start the API server: python start_api.py")
    print("2. Login with admin credentials via POST /auth/login")
    print("3. Register new users via POST /auth/register")


if __name__ == "__main__":
    asyncio.run(main())
