import os
import uuid
from pathlib import Path

import asyncpg
import pytest
from dotenv import load_dotenv

load_dotenv()


def generate_unique_ids() -> tuple[int, int, int]:
    """Generate unique IDs for test isolation."""
    return uuid.uuid4().int % (10**18), uuid.uuid4().int % (10**18), uuid.uuid4().int % (10**18)


@pytest.fixture(scope="function")
async def database_pool():
    """
    Creates a database pool for integration tests.
    Skips if DATABASE_URL is not set.
    """
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        pytest.skip("DATABASE_URL not set, skipping integration tests")

    pool = None
    try:
        pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)

        # Initialize Schema
        schema_path = Path(__file__).parent.parent / "scripts" / "init_schema.sql"
        if schema_path.exists():
            with open(schema_path) as f:
                sql = f.read()
                async with pool.acquire() as conn:
                    await conn.execute(sql)

        yield pool

    except Exception as e:
        pytest.fail(f"Failed to initialize test database pool: {e}")

    finally:
        if pool:
            await pool.close()


@pytest.fixture(scope="function")
async def clean_db(database_pool):
    """
    Yields the pool, ensuring tables are truncated after the test.
    """
    # Truncate before usage to ensure a clean start
    try:
        async with database_pool.acquire() as conn:
            await conn.execute("TRUNCATE TABLE messages, analytics, threads CASCADE;")
    except Exception as e:
        pytest.fail(f"Failed to truncate tables before test: {e}")

    yield database_pool

    # Cleanup after test
    try:
        async with database_pool.acquire() as conn:
            await conn.execute("TRUNCATE TABLE messages, analytics, threads CASCADE;")
    except Exception as e:
        # Log but don't fail - test already passed/failed
        import logging

        logging.warning("Failed to truncate tables after test: %s", e)


@pytest.fixture(scope="function")
def unique_ids() -> tuple[int, int, int]:
    """Provides unique thread_id, guild_id, user_id for each test."""
    return generate_unique_ids()


@pytest.fixture(scope="function")
async def database_service(clean_db):
    """
    Yields an initialized DatabaseService, ensuring it is closed after use.
    Depends on clean_db to ensure database is ready.
    """
    from src.database import DatabaseService

    service = DatabaseService()
    try:
        await service.connect()
    except Exception as e:
        pytest.fail(f"Failed to connect DatabaseService: {e}")

    try:
        yield service
    finally:
        try:
            await service.close()
        except Exception as e:
            import logging

            logging.warning("Failed to close DatabaseService: %s", e)
