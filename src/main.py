import logging

import discord
from discord.ext import commands

from src.base import Conversation, Message
from src.cogs.chat import ChatCog
from src.constants import (
    ALLOWED_SERVER_IDS,
    BOT_INVITE_URL,
    BOT_NAME,
    DISCORD_BOT_TOKEN,
    EXAMPLE_CONVOS,
)
from src.database import db_service
from src.utils import logger

logging.basicConfig(
    format="[%(asctime)s] [%(filename)s:%(lineno)d] %(levelname)s: %(message)s", level=logging.INFO
)
logging.getLogger("discord").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


class SherlockRamosBot(commands.Bot):
    """Discord bot entry point with Cog setup and lifecycle hooks."""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.db_service = db_service

    @property
    def bot_name(self) -> str:
        """Get the bot's name, favoring the actual Discord username if connected."""
        return self.user.name if self.user else BOT_NAME

    @property
    def example_conversations(self) -> list[Conversation]:
        """Get example conversations with the actual bot name injected."""
        if not self.user:
            return EXAMPLE_CONVOS

        # Cache the processed conversations to avoid rebuilding them
        if (
            hasattr(self, "_cached_examples")
            and getattr(self, "_cached_user", None) == self.user.id
        ):
            return self._cached_examples

        processed = [
            Conversation(
                messages=[
                    Message(user=self.user.name, text=msg.text) if msg.user == BOT_NAME else msg
                    for msg in convo.messages
                ]
            )
            for convo in EXAMPLE_CONVOS
        ]
        self._cached_examples = processed
        self._cached_user = self.user.id
        return processed

    async def setup_hook(self) -> None:
        """Load cogs and sync application commands."""
        await self.add_cog(ChatCog(self, self.db_service))

        for guild_id in ALLOWED_SERVER_IDS:
            guild = discord.Object(id=guild_id)
            self.tree.copy_global_to(guild=guild)
            try:
                synced = await self.tree.sync(guild=guild)
                logger.info("Synced %d commands to guild %d", len(synced), guild_id)
            except Exception as exc:
                logger.error("Failed to sync commands to guild %d: %s", guild_id, exc)

        await self.tree.sync()
        logger.info("Global command sync complete")

    async def on_ready(self) -> None:
        """Initialize runtime data once the bot is connected."""
        if self.user is None:
            return

        logger.info("We have logged in as %s. Invite URL: %s", self.user, BOT_INVITE_URL)
        logger.info("Connected to %d guilds:", len(self.guilds))
        for guild in self.guilds:
            logger.info("  - %s (ID: %d)", guild.name, guild.id)

    async def close(self) -> None:
        """Log performance metrics before closing the bot."""
        from src.profiling import log_metrics_summary_sync

        log_metrics_summary_sync()
        await super().close()


def run() -> None:
    """Entry point for the bot."""
    bot = SherlockRamosBot()
    bot.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    run()
