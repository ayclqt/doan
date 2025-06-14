import asyncio
import json
import redis.asyncio as redis
import sys
from datetime import datetime, timezone
from pathlib import Path

from config import config

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


__author__ = "Lâm Quang Trí"
__copyright__ = "Copyright 2025, Lâm Quang Trí"
__credits__ = ["Lâm Quang Trí"]

__maintainer__ = "Lâm Quang Trí"
__email__ = "quangtri.lam.9@gmail.com"
__status__ = "Development"


async def migrate_user_data():
    """
    Migrate user data from old JSON format to new Hash format in Redis.
    Old format: user:{username} (JSON) and user_id:{user_id} (username)
    New format: user:{user_id} (Hash) and index:{username} (user_id)
    """
    redis_client = redis.from_url(config.redis_url, decode_responses=True)
    print("Starting user data migration...")

    # Get all keys matching user:* pattern (old format)
    cursor = "0"
    user_keys = []
    while cursor != 0:
        cursor, keys = await redis_client.scan(cursor, match="user:*", count=100)
        user_keys.extend(keys)

    migrated_count = 0
    failed_count = 0

    for user_key in user_keys:
        try:
            # Extract username from key (user:{username})
            username = user_key.split(":", 1)[1]

            # Get old JSON data
            user_data_str = await redis_client.get(user_key)
            if not user_data_str:
                print(f"Warning: No data found for key {user_key}")
                failed_count += 1
                continue

            user_data = json.loads(user_data_str)
            user_id = user_data.get("id")
            if not user_id:
                print(f"Warning: No ID found in data for {user_key}")
                failed_count += 1
                continue

            # Prepare data for new Hash format
            new_user_data = {
                "id": user_id,
                "username": username,
                "password": user_data.get("hashed_password", ""),
                "created_at": user_data.get(
                    "created_at", datetime.now(timezone.utc).isoformat()
                ),
                "is_active": "1" if user_data.get("is_active", True) else "0",
            }
            if "last_login" in user_data:
                new_user_data["last_login"] = user_data["last_login"]

            # Store in new format: user:{user_id} as Hash
            await redis_client.hset(f"user:{user_id}", mapping=new_user_data)
            # Store username index: index:{username} -> user_id
            await redis_client.set(f"index:{username}", user_id)

            # Optionally, delete old keys after successful migration
            await redis_client.delete(user_key)
            old_id_key = f"user_id:{user_id}"
            if await redis_client.exists(old_id_key):
                await redis_client.delete(old_id_key)

            migrated_count += 1
            print(f"Migrated user: {username} (ID: {user_id})")

        except Exception as e:
            print(f"Error migrating user {user_key}: {str(e)}")
            failed_count += 1

    print(
        f"Migration complete. Successfully migrated: {migrated_count}, Failed: {failed_count}"
    )
    await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(migrate_user_data())
