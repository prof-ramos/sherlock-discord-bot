import asyncio
import logging
import os

from dotenv import load_dotenv

load_dotenv()

from src.base import ThreadConfig  # noqa: E402
from src.database import db_service  # noqa: E402
from src.utils import logger  # noqa: E402

# Configure logging to show output, only if not already configured
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


async def verify_db():
    try:
        logger.info("Starting database verification...")
        # Check connection string
        if not os.environ.get("DATABASE_URL"):
            logger.error("DATABASE_URL not found in environment!")
            return

        # Test save_thread and get_thread_config
        test_thread_id = 999999
        test_guild_id = 888888
        test_user_id = 777777
        test_config = ThreadConfig(model="gpt-4", temperature=0.5, max_tokens=100)

        logger.info("Testing save_thread...")
        await db_service.save_thread(test_thread_id, test_guild_id, test_user_id, test_config)

        logger.info("Testing get_thread_config...")
        retrieved = await db_service.get_thread_config(test_thread_id)

        if retrieved and retrieved.model == "gpt-4" and retrieved.temperature == 0.5:
            logger.info("✅ Database verification successful!")
        else:
            logger.error(f"❌ Database verification failed! Retrieved: {retrieved}")

        # Cleanup
        await db_service.close()
    except Exception as e:
        logger.error(f"❌ An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(verify_db())
