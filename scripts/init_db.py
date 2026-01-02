import asyncio
import logging
import os
import sys

import asyncpg
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

async def init_db():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        logger.error("❌ DATABASE_URL not set in environment")
        sys.exit(1)

    logger.info("🔌 Connecting to database...")
    conn = None
    try:
        # Wrap connection in a timeout to prevent hanging
        conn = await asyncio.wait_for(asyncpg.connect(dsn), timeout=10.0)

        # Simple health check
        await conn.fetchval("SELECT 1")
        logger.info("✅ Connection established.")

        schema_path = os.path.join(os.path.dirname(__file__), "init_schema.sql")
        with open(schema_path, "r") as f:
            schema = f.read()

        logger.info("🏗️ Applying schema...")

        # Execute schema application within a transaction for safety
        async with conn.transaction():
            # asyncpg execute can handle multiple statements in a simple script block usually,
            # but explicit transaction ensures atomicity.
            await conn.execute(schema)

        logger.info("✅ Schema applied successfully.")

    except asyncio.TimeoutError:
        logger.error("❌ Connection timed out after 10 seconds.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Failed to init DB: {e}")
        sys.exit(1)
    finally:
        if conn:
            await conn.close()
            logger.info("🔌 Connection closed.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(init_db())
    except KeyboardInterrupt:
        logger.info("🛑 Operation cancelled by user.")
        sys.exit(130)
