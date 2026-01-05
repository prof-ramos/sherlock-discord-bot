import asyncio

import discord
from discord import Message as DiscordMessage
from discord import app_commands
from discord.ext import commands

from src import completion
from src.base import Message, ThreadConfig
from src.completion import generate_completion_response, process_response
from src.constants import (
    ACTIVATE_THREAD_PREFIX,
    AVAILABLE_MODELS,
    DEFAULT_MENTION_MAX_TOKENS,
    DEFAULT_MENTION_TEMPERATURE,
    DEFAULT_MODEL,
    DEFAULT_THREAD_MAX_TOKENS,
    DEFAULT_THREAD_TEMPERATURE,
    MAX_THREAD_MESSAGES,
    OPTIMIZED_HISTORY_LIMIT,
    SECONDS_DELAY_RECEIVING_MSG,
)
from src.database import DatabaseService
from src.moderation import (
    moderate_message,
    send_moderation_blocked_message,
    send_moderation_flagged_message,
)
from src.profiling import timed
from src.utils import (
    close_thread,
    discord_message_to_message,
    is_last_message_stale,
    logger,
    should_block,
    split_into_shorter_messages,
)


class ChatCog(commands.Cog):
    """Chat command and message handlers for the bot."""

    def __init__(self, bot: commands.Bot, db_service: DatabaseService) -> None:
        self.bot = bot
        self.db_service = db_service

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError
    ) -> None:
        """Handle app command errors for this cog."""
        if isinstance(error, discord.app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.", ephemeral=True
            )
        elif isinstance(error, discord.app_commands.BotMissingPermissions):
            await interaction.response.send_message(
                f"❌ I'm missing required permissions: {', '.join(error.missing_permissions)}",
                ephemeral=True,
            )
        elif isinstance(error, discord.app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ Command on cooldown. Try again in {error.retry_after:.1f}s.",
                ephemeral=True,
            )
        else:
            logger.exception("Unhandled app command error: %s", error)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An unexpected error occurred. Please try again.", ephemeral=True
                )

    @app_commands.command(name="chat", description="Create a new thread for conversation")
    @app_commands.checks.has_permissions(send_messages=True)
    @app_commands.checks.has_permissions(view_channel=True)
    @app_commands.checks.bot_has_permissions(send_messages=True)
    @app_commands.checks.bot_has_permissions(view_channel=True)
    @app_commands.checks.bot_has_permissions(manage_threads=True)
    @app_commands.describe(message="The first prompt to start the chat with")
    @app_commands.describe(model="The model to use for the chat")
    @app_commands.describe(temperature="Controls randomness. Higher values mean more randomness.")
    @app_commands.describe(
        max_tokens="How many tokens the model should output at max for each message."
    )
    async def chat_command(
        self,
        interaction: discord.Interaction,
        message: str,
        model: AVAILABLE_MODELS = DEFAULT_MODEL,
        temperature: app_commands.Range[float, 0.0, 1.0] = 1.0,
        max_tokens: app_commands.Range[int, 1, 4096] = 512,
    ) -> None:
        """Create a new chat thread and process the first user message."""
        logger.info(
            "Chat command invoked",
            extra={
                "user_id": interaction.user.id,
                "user_name": interaction.user.name,
                "guild_id": interaction.guild_id,
                "channel_id": interaction.channel_id,
                "command": "chat",
            },
        )
        try:
            if not isinstance(interaction.channel, discord.TextChannel):
                return

            if should_block(guild=interaction.guild):
                return

            # Validate message parameter
            if not message or not message.strip():
                await interaction.response.send_message(
                    "❌ A mensagem não pode estar vazia.", ephemeral=True
                )
                return

            message = message.strip()
            if len(message) > 4000:  # Discord's message limit is 4000 chars for slash commands
                await interaction.response.send_message(
                    f"❌ A mensagem é muito longa ({len(message)} caracteres). Máximo permitido: 4000 caracteres.",
                    ephemeral=True,
                )
                return

            user = interaction.user
            logger.info(
                "Processing chat command",
                extra={
                    "user_id": user.id,
                    "user_name": user.name,
                    "message_length": len(message),
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )

            if interaction.response.is_done():
                return

            # temperature and max_tokens validation handled by Discord UI via app_commands.Range

            try:
                flagged_str, blocked_str = moderate_message(message=message, user=user)
                await send_moderation_blocked_message(
                    guild=interaction.guild,
                    user=user,
                    blocked_str=blocked_str,
                    message=message,
                )
                if len(blocked_str) > 0:
                    await interaction.response.send_message(
                        f"Your prompt has been blocked by moderation.\n{message}",
                        ephemeral=True,
                    )
                    return

                embed = discord.Embed(
                    description=f"<@{user.id}> wants to chat! 🤖💬",
                    color=discord.Color.green(),
                )
                embed.add_field(name="model", value=model)
                embed.add_field(name="temperature", value=temperature, inline=True)
                embed.add_field(name="max_tokens", value=max_tokens, inline=True)
                embed.add_field(name=user.name, value=message)

                if len(flagged_str) > 0:
                    embed.color = discord.Color.yellow()
                    embed.title = "⚠️ This prompt was flagged by moderation."

                await interaction.response.send_message(embed=embed)
                response = await interaction.original_response()

                await send_moderation_flagged_message(
                    guild=interaction.guild,
                    user=user,
                    flagged_str=flagged_str,
                    message=message,
                    url=response.jump_url,
                )
            except Exception as exc:
                logger.exception("Failed to start chat via moderation/embed block")
                await interaction.response.send_message(
                    f"Failed to start chat: {exc}", ephemeral=True
                )
                return

            thread = await response.create_thread(
                name=f"{ACTIVATE_THREAD_PREFIX} {user.name[:20]} - {message[:30]}",
                slowmode_delay=1,
                reason="gpt-bot",
                auto_archive_duration=60,
            )

            thread_config = ThreadConfig(
                model=model, max_tokens=max_tokens, temperature=temperature
            )
            await self.db_service.save_thread(
                thread_id=thread.id,
                guild_id=interaction.guild_id,
                user_id=user.id,
                config=thread_config,
            )
            await self.db_service.log_message(thread_id=thread.id, role="user", content=message)

            async with thread.typing():
                messages = [Message(user=user.name, text=message)]
                response_data = await generate_completion_response(
                    messages=messages,
                    user=user,
                    thread_config=thread_config,
                    bot_name=self.bot.bot_name,
                    example_conversations=self.bot.example_conversations,
                )
                if response_data.reply_text:
                    await self.db_service.log_message(
                        thread_id=thread.id,
                        role="assistant",
                        content=response_data.reply_text,
                    )
                await process_response(user=user, thread=thread, response_data=response_data)
        except Exception as exc:
            logger.exception("Failed to start chat: %s", exc)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"Failed to start chat: {str(exc)}", ephemeral=True
                )
            else:
                await interaction.followup.send(f"Failed to start chat: {str(exc)}", ephemeral=True)

    async def handle_mention(self, message: DiscordMessage) -> None:
        """Handle when the bot is mentioned directly in a channel."""
        content = message.content
        for mention in message.mentions:
            content = content.replace(f"<@{mention.id}>", "").replace(f"<@!{mention.id}>", "")
        content = content.strip()

        # Per-user thread ID for isolated conversation history
        # Combining channel and user ensures each user has their own history
        thread_id = hash(f"{message.channel.id}_{message.author.id}") % (10**18)
        if not content:
            history = await self.db_service.get_messages(thread_id=thread_id, limit=1)
            if history:
                await message.reply("Oi! Em que posso ajudar agora? ⚖️")
            else:
                await message.reply(
                    "👋 Olá! Sou o SherlockBot, seu assistente jurídico. Como posso ajudar?"
                )
            return

        logger.info(
            "Bot mention received",
            extra={
                "user_id": message.author.id,
                "user_name": message.author.name,
                "guild_id": message.guild.id if message.guild else None,
                "channel_id": message.channel.id,
                "message_length": len(content),
            },
        )

        flagged_str, blocked_str = moderate_message(message=content, user=message.author)
        if len(blocked_str) > 0:
            await message.reply("❌ Seu prompt foi bloqueado por moderação.")
            return

        if len(flagged_str) > 0:
            logger.warning("Flagged mention from %s: %s", message.author, flagged_str)

        thread_config = ThreadConfig(
            model=DEFAULT_MODEL,
            max_tokens=DEFAULT_MENTION_MAX_TOKENS,
            temperature=DEFAULT_MENTION_TEMPERATURE,
        )

        guild_id = message.guild.id if message.guild else 0
        user_id = message.author.id

        async with message.channel.typing():
            # 1. Ensure thread entry for history tracking
            await self.db_service.save_thread(
                thread_id=thread_id,
                guild_id=guild_id,
                user_id=user_id,
                config=thread_config,
            )

            # 2. Log current message
            await self.db_service.log_message(
                thread_id=thread_id,
                role="user",
                content=content,
            )

            # 3. Retrieve history (last 10 messages)
            messages = await self.db_service.get_messages(thread_id=thread_id, limit=10)

            response_data = await generate_completion_response(
                messages=messages,
                user=message.author.name,
                thread_config=thread_config,
                bot_name=self.bot.bot_name,
                example_conversations=self.bot.example_conversations,
            )

        if response_data.status == completion.CompletionResult.OK and response_data.reply_text:
            # 4. Log bot reply
            await self.db_service.log_message(
                thread_id=thread_id,
                role="assistant",
                content=response_data.reply_text,
            )

            for chunk in split_into_shorter_messages(response_data.reply_text):
                await message.reply(chunk)
        elif response_data.status == completion.CompletionResult.TOO_LONG:
            await message.reply(
                "❌ A resposta ficou muito longa. Tente uma pergunta mais específica."
            )
        else:
            await message.reply(
                f"❌ Erro ao gerar resposta: {response_data.status_text or 'Erro desconhecido'}"
            )

    @commands.Cog.listener()
    @timed
    async def on_message(self, message: DiscordMessage) -> None:
        """Handle incoming messages for mentions and bot threads."""
        try:
            if should_block(guild=message.guild):
                return

            if self.bot.user is None or message.author == self.bot.user:
                return

            if self.bot.user in message.mentions:
                await self.handle_mention(message)
                return

            channel = message.channel
            if not isinstance(channel, discord.Thread):
                return

            thread = channel
            if thread.owner_id != self.bot.user.id:
                return

            if (
                thread.archived
                or thread.locked
                or not thread.name.startswith(ACTIVATE_THREAD_PREFIX)
            ):
                return

            if thread.message_count > MAX_THREAD_MESSAGES:
                await close_thread(thread=thread)
                return

            flagged_str, blocked_str = moderate_message(
                message=message.content, user=message.author
            )
            await send_moderation_blocked_message(
                guild=message.guild,
                user=message.author,
                blocked_str=blocked_str,
                message=message.content,
            )
            if len(blocked_str) > 0:
                try:
                    await message.delete()
                    await thread.send(
                        embed=discord.Embed(
                            description=(
                                f"❌ **{message.author}'s message has been deleted by moderation.**"
                            ),
                            color=discord.Color.red(),
                        )
                    )
                    return
                except Exception:
                    await thread.send(
                        embed=discord.Embed(
                            description=(
                                "❌ **"
                                f"{message.author}'s message has been blocked by moderation but could "
                                "not be deleted. Missing Manage Messages permission in this Channel."
                                "**"
                            ),
                            color=discord.Color.red(),
                        )
                    )
                    return
            await send_moderation_flagged_message(
                guild=message.guild,
                user=message.author,
                flagged_str=flagged_str,
                message=message.content,
                url=message.jump_url,
            )
            if len(flagged_str) > 0:
                await thread.send(
                    embed=discord.Embed(
                        description=(
                            f"⚠️ **{message.author}'s message has been flagged by moderation.**"
                        ),
                        color=discord.Color.yellow(),
                    )
                )

            if SECONDS_DELAY_RECEIVING_MSG > 0:
                await asyncio.sleep(SECONDS_DELAY_RECEIVING_MSG)
                if is_last_message_stale(
                    interaction_message=message,
                    last_message=thread.last_message,
                    bot_id=self.bot.user.id,
                ):
                    return

            logger.info(
                "Processing thread message",
                extra={
                    "user_id": message.author.id,
                    "user_name": message.author.name,
                    "guild_id": message.guild.id if message.guild else None,
                    "channel_id": message.channel.id,
                    "thread_id": thread.id,
                    "thread_name": thread.name,
                    "message_length": len(message.content),
                    "thread_message_count": thread.message_count,
                },
            )

            await self.db_service.log_message(
                thread_id=thread.id, role="user", content=message.content
            )

            history_limit = min(OPTIMIZED_HISTORY_LIMIT, MAX_THREAD_MESSAGES)
            channel_messages = []
            async for msg in thread.history(limit=history_limit):
                converted = discord_message_to_message(msg)
                if converted:
                    channel_messages.append(converted)
            channel_messages.reverse()

            thread_config = await self.db_service.get_thread_config(thread.id)
            if not thread_config:
                thread_config = ThreadConfig(
                    model=DEFAULT_MODEL,
                    max_tokens=DEFAULT_THREAD_MAX_TOKENS,
                    temperature=DEFAULT_THREAD_TEMPERATURE,
                )

            async with thread.typing():
                response_data = await generate_completion_response(
                    messages=channel_messages,
                    user=message.author.name,
                    thread_config=thread_config,
                    bot_name=self.bot.bot_name,
                    example_conversations=self.bot.example_conversations,
                )
                if response_data.reply_text:
                    await self.db_service.log_message(
                        thread_id=thread.id,
                        role="assistant",
                        content=response_data.reply_text,
                    )

            if is_last_message_stale(
                interaction_message=message,
                last_message=thread.last_message,
                bot_id=self.bot.user.id,
            ):
                return

            await process_response(user=message.author, thread=thread, response_data=response_data)
        except Exception as e:
            # Safely determine thread_id for logging
            try:
                thread_id = thread.id
            except (NameError, AttributeError):
                thread_id = message.channel.id
            logger.exception("Error processing message in thread (ID: %s): %s", thread_id, str(e))
