from typing import Optional

import discord

from src.constants import (
    SERVER_TO_MODERATION_CHANNEL,
)


def moderate_message(message: str, user: str) -> tuple[str, str]:  # [flagged_str, blocked_str]
    # Moderação desativada: OpenRouter não possui endpoint /moderations
    # O OpenRouter já aplica filtros nativos em muitos modelos
    # Retorna strings vazias, significando "sem flag", "sem bloqueio"
    return ("", "")


async def fetch_moderation_channel(
    guild: Optional[discord.Guild],
) -> Optional[discord.abc.GuildChannel]:
    if not guild or not guild.id:
        return None
    moderation_channel = SERVER_TO_MODERATION_CHANNEL.get(guild.id, None)
    if moderation_channel:
        channel = await guild.fetch_channel(moderation_channel)
        return channel
    return None


async def send_moderation_flagged_message(
    guild: Optional[discord.Guild],
    user: str,
    flagged_str: Optional[str],
    message: Optional[str],
    url: Optional[str],
):
    if guild and flagged_str and len(flagged_str) > 0:
        moderation_channel = await fetch_moderation_channel(guild=guild)
        if moderation_channel:
            message = message[:100] if message else None
            await moderation_channel.send(f"⚠️ {user} - {flagged_str} - {message} - {url}")


async def send_moderation_blocked_message(
    guild: Optional[discord.Guild],
    user: str,
    blocked_str: Optional[str],
    message: Optional[str],
):
    if guild and blocked_str and len(blocked_str) > 0:
        moderation_channel = await fetch_moderation_channel(guild=guild)
        if moderation_channel:
            message = message[:500] if message else None
            await moderation_channel.send(f"❌ {user} - {blocked_str} - {message}")
