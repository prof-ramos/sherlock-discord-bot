import logging
from collections.abc import Iterator
from typing import Optional

import discord
from discord import Message as DiscordMessage

from src.base import Message

# Use module-level logger
logger = logging.getLogger(__name__)


def discord_message_to_message(message: DiscordMessage) -> Optional[Message]:
    """Convert a Discord Message to internal Message format."""
    if (
        message.type == discord.MessageType.thread_starter_message
        and message.reference
        and (cached := message.reference.cached_message)
        and cached.embeds
        and cached.embeds[0].fields
    ):
        field = cached.embeds[0].fields[0]
        if field.value:
            return Message(user=field.name, text=field.value)

    if message.content:
        return Message(user=message.author.name, text=message.content)

    return None


def split_into_shorter_messages(message: str) -> Iterator[str]:
    """Divide a message into chunks within Discord's character limit using a generator."""
    from src.constants import MAX_CHARS_PER_REPLY_MSG

    for i in range(0, len(message), MAX_CHARS_PER_REPLY_MSG):
        yield message[i : i + MAX_CHARS_PER_REPLY_MSG]


def is_last_message_stale(
    interaction_message: DiscordMessage, last_message: Optional[DiscordMessage], bot_id: int
) -> bool:
    """Check if the last message in a thread is from someone other than the bot and not the current interaction."""
    if not last_message:
        return False

    return (
        last_message.id != interaction_message.id
        and last_message.author is not None
        and last_message.author.id != bot_id
    )


async def close_thread(thread: discord.Thread) -> None:
    """Safely close and archive a Discord thread."""
    from src.constants import INACTIVATE_THREAD_PREFIX

    try:
        await thread.edit(name=INACTIVATE_THREAD_PREFIX)
        await thread.send(
            embed=discord.Embed(
                description="**Thread closed** - Context limit reached, closing...",
                color=discord.Color.blue(),
            )
        )
        await thread.edit(archived=True, locked=True)
    except discord.HTTPException as e:
        logger.error("Failed to close thread %s: %s", thread.id, e)


def should_block(guild: Optional[discord.Guild]) -> bool:
    """Determine if a message should be blocked based on guild allowlist."""
    from src.constants import ALLOWED_SERVER_IDS

    if guild is None:
        logger.info("Access denied: Private messages (DMs) are not supported.")
        return True

    if guild.id not in ALLOWED_SERVER_IDS:
        logger.info(
            "Access denied: Guild %s (ID: %s) is not in the allowed list.", guild.name, guild.id
        )
        return True

    return False
