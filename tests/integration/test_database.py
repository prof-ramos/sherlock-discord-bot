import pytest
from src.base import ThreadConfig


@pytest.mark.asyncio
async def test_save_and_get_thread(database_service, unique_ids):
    """Test saving and retrieving thread configuration."""
    thread_id, guild_id, user_id = unique_ids
    config = ThreadConfig(model="gpt-4", temperature=0.7, max_tokens=100)

    await database_service.save_thread(thread_id, guild_id, user_id, config)

    retrieved = await database_service.get_thread_config(thread_id)
    assert retrieved is not None
    assert retrieved.model == "gpt-4"
    assert retrieved.temperature == 0.7
    assert retrieved.max_tokens == 100


@pytest.mark.asyncio
async def test_log_and_get_messages(database_service, unique_ids):
    """Test logging messages and retrieving history."""
    thread_id, guild_id, user_id = unique_ids
    await database_service.save_thread(
        thread_id=thread_id,
        guild_id=guild_id,
        user_id=user_id,
        config=ThreadConfig(model="test", temperature=0.5, max_tokens=50),
    )

    await database_service.log_message(thread_id, "user", "Hello bot")
    await database_service.log_message(thread_id, "assistant", "Hello human")

    messages = await database_service.get_messages(thread_id)
    assert len(messages) == 2
    assert messages[0].user == "user"
    assert messages[0].text == "Hello bot"
    assert messages[1].user == "assistant"
    assert messages[1].text == "Hello human"


@pytest.mark.asyncio
async def test_log_analytics(database_service, unique_ids):
    """Test logging analytics events."""
    thread_id, guild_id, user_id = unique_ids
    await database_service.save_thread(
        thread_id=thread_id,
        guild_id=guild_id,
        user_id=user_id,
        config=ThreadConfig(model="test", temperature=0.5, max_tokens=50),
    )

    await database_service.log_analytics(
        thread_id=thread_id,
        guild_id=guild_id,
        user_id=user_id,
        model="gpt-4",
        prompt_tokens=10,
        completion_tokens=20,
        response_time_ms=500,
    )

    # Use public method for verification
    count = await database_service.get_analytics_count(thread_id)
    assert count == 1
