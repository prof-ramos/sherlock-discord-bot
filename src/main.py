import asyncio
import logging
from typing import Optional

import discord
from discord import Message as DiscordMessage
from discord import app_commands

from src import completion
from src.base import Conversation, Message, ThreadConfig
from src.completion import generate_completion_response, process_response
from src.constants import (
    ACTIVATE_THREAD_PREFIX,
    ALLOWED_SERVER_IDS,
    AVAILABLE_MODELS,
    BOT_INVITE_URL,
    BOT_NAME,
    DEFAULT_MODEL,
    DISCORD_BOT_TOKEN,
    EXAMPLE_CONVOS,
    MAX_THREAD_MESSAGES,
    OPTIMIZED_HISTORY_LIMIT,
    SECONDS_DELAY_RECEIVING_MSG,
)
from src.database import db_service
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

logging.basicConfig(
    format="[%(asctime)s] [%(filename)s:%(lineno)d] %(levelname)s: %(message)s", level=logging.INFO
)
# Reduce verbosity of external libraries
logging.getLogger("discord").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)


@tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: discord.app_commands.AppCommandError
) -> None:
    """Global error handler for all app commands."""
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


@client.event
async def on_ready():
    logger.info("We have logged in as %s. Invite URL: %s", client.user, BOT_INVITE_URL)

    # Log all connected guilds
    logger.info("Connected to %d guilds:", len(client.guilds))
    for guild in client.guilds:
        logger.info("  - %s (ID: %d)", guild.name, guild.id)

    completion.MY_BOT_NAME = client.user.name
    completion.MY_BOT_EXAMPLE_CONVOS = []
    for c in EXAMPLE_CONVOS:
        messages = []
        for m in c.messages:
            if m.user == BOT_NAME:
                messages.append(Message(user=client.user.name, text=m.text))
            else:
                messages.append(m)
        completion.MY_BOT_EXAMPLE_CONVOS.append(Conversation(messages=messages))

    # Sync commands to specific guilds for instant update
    for guild_id in ALLOWED_SERVER_IDS:
        guild = discord.Object(id=guild_id)
        tree.copy_global_to(guild=guild)
        try:
            synced = await tree.sync(guild=guild)
            logger.info("Synced %d commands to guild %d", len(synced), guild_id)
        except Exception as e:
            logger.error("Failed to sync commands to guild %d: %s", guild_id, e)

    # Also sync globally (takes up to 1 hour to propagate)
    await tree.sync()
    logger.info("Global command sync complete")


# /chat message:
@tree.command(name="chat", description="Create a new thread for conversation")
@discord.app_commands.checks.has_permissions(send_messages=True)
@discord.app_commands.checks.has_permissions(view_channel=True)
@discord.app_commands.checks.bot_has_permissions(send_messages=True)
@discord.app_commands.checks.bot_has_permissions(view_channel=True)
@discord.app_commands.checks.bot_has_permissions(manage_threads=True)
@app_commands.describe(message="The first prompt to start the chat with")
@app_commands.describe(model="The model to use for the chat")
@app_commands.describe(
    temperature="Controls randomness. Higher values mean more randomness. Between 0 and 1"
)
@app_commands.describe(
    max_tokens="How many tokens the model should output at max for each message."
)
async def chat_command(
    int: discord.Interaction,
    message: str,
    model: AVAILABLE_MODELS = DEFAULT_MODEL,
    temperature: Optional[float] = 1.0,
    max_tokens: Optional[int] = 512,
):
    logger.info(
        "Chat command invoked by %s in guild %s channel %s",
        int.user, int.guild_id, int.channel_id
    )
    try:
        # only support creating thread in text channel
        if not isinstance(int.channel, discord.TextChannel):
            return

        # block servers not in allow list
        if should_block(guild=int.guild):
            return

        user = int.user
        logger.info("Chat command by %s %s", user, message[:20])

        if int.response.is_done():
            # In case some previous check sent a message
            return

        # Check for valid temperature
        if temperature is not None and (temperature < 0 or temperature > 1):
            await int.response.send_message(
                f"You supplied an invalid temperature: {temperature}. Temperature must be between 0 and 1.",
                ephemeral=True,
            )
            return

        # Check for valid max_tokens
        if max_tokens is not None and (max_tokens < 1 or max_tokens > 4096):
            await int.response.send_message(
                f"You supplied an invalid max_tokens: {max_tokens}. Max tokens must be between 1 and 4096.",
                ephemeral=True,
            )
            return

        try:
            # moderate the message
            flagged_str, blocked_str = moderate_message(message=message, user=user)
            await send_moderation_blocked_message(
                guild=int.guild,
                user=user,
                blocked_str=blocked_str,
                message=message,
            )
            if len(blocked_str) > 0:
                # message was blocked
                await int.response.send_message(
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
                # message was flagged
                embed.color = discord.Color.yellow()
                embed.title = "⚠️ This prompt was flagged by moderation."

            await int.response.send_message(embed=embed)
            response = await int.original_response()

            await send_moderation_flagged_message(
                guild=int.guild,
                user=user,
                flagged_str=flagged_str,
                message=message,
                url=response.jump_url,
            )
        except Exception as e:
            logger.exception(e)
            await int.response.send_message(f"Failed to start chat {str(e)}", ephemeral=True)
            return

        # create the thread
        thread = await response.create_thread(
            name=f"{ACTIVATE_THREAD_PREFIX} {user.name[:20]} - {message[:30]}",
            slowmode_delay=1,
            reason="gpt-bot",
            auto_archive_duration=60,
        )

        # Persistent storage
        thread_config = ThreadConfig(
            model=model, max_tokens=max_tokens, temperature=temperature
        )
        await db_service.save_thread(
            thread_id=thread.id,
            guild_id=int.guild_id,
            user_id=user.id,
            config=thread_config
        )
        # Log initials message
        await db_service.log_message(thread_id=thread.id, role="user", content=message)

        async with thread.typing():
            # fetch completion
            messages = [Message(user=user.name, text=message)]
            response_data = await generate_completion_response(
                messages=messages, user=user, thread_config=thread_config
            )
            # Log assistant response
            if response_data.reply_text:
                await db_service.log_message(
                    thread_id=thread.id,
                    role="assistant",
                    content=response_data.reply_text
                )
            # send the result
            await process_response(user=user, thread=thread, response_data=response_data)
    except Exception as e:
        logger.exception("Failed to start chat: %s", e)
        if not int.response.is_done():
            await int.response.send_message(f"Failed to start chat: {str(e)}", ephemeral=True)
        else:
            await int.followup.send(f"Failed to start chat: {str(e)}", ephemeral=True)


async def handle_mention(message: DiscordMessage):
    """Handle when the bot is mentioned directly in a channel."""
    # Remove the bot mention from the message to get the actual question
    content = message.content
    for mention in message.mentions:
        content = content.replace(f"<@{mention.id}>", "").replace(f"<@!{mention.id}>", "")
    content = content.strip()

    if not content:
        await message.reply(
            "👋 Olá! Sou o SherlockBot, seu assistente jurídico. Como posso ajudar?"
        )
        return

    logger.info("Mention from %s: %s...", message.author, content[:50])

    # moderate the message
    flagged_str, blocked_str = moderate_message(message=content, user=message.author)
    if len(blocked_str) > 0:
        await message.reply("❌ Seu prompt foi bloqueado por moderação.")
        return

    if len(flagged_str) > 0:
        # Just log and proceed or notify? Chosing to proceed but log for safety.
        logger.warning("Flagged mention from %s: %s", message.author, flagged_str)

    # Use default thread config for mentions
    thread_config = ThreadConfig(model=DEFAULT_MODEL, max_tokens=1024, temperature=0.7)

    async with message.channel.typing():
        # Generate response
        messages = [Message(user=message.author.name, text=content)]
        response_data = await generate_completion_response(
            messages=messages,
            user=message.author,
            thread_config=thread_config,
        )

    # Send the response
    if response_data.status == completion.CompletionResult.OK and response_data.reply_text:
        # Split into shorter messages if needed
        for chunk in split_into_shorter_messages(response_data.reply_text):
            await message.reply(chunk)
    elif response_data.status == completion.CompletionResult.TOO_LONG:
        await message.reply("❌ A resposta ficou muito longa. Tente uma pergunta mais específica.")
    else:
        await message.reply(
            f"❌ Erro ao gerar resposta: {response_data.status_text or 'Erro desconhecido'}"
        )


# calls for each message
@client.event
@timed
async def on_message(message: DiscordMessage):
    try:
        # block servers not in allow list
        if should_block(guild=message.guild):
            return

        # ignore messages from the bot
        if message.author == client.user:
            return

        # Check if bot was mentioned (e.g., "@SherlockBot, qual a jurisprudência...")
        if client.user in message.mentions:
            await handle_mention(message)
            return

        # ignore messages not in a thread
        channel = message.channel
        if not isinstance(channel, discord.Thread):
            return

        # ignore threads not created by the bot
        thread = channel
        if thread.owner_id != client.user.id:
            return

        # ignore threads that are archived locked or title is not what we want
        if thread.archived or thread.locked or not thread.name.startswith(ACTIVATE_THREAD_PREFIX):
            # ignore this thread
            return

        if thread.message_count > MAX_THREAD_MESSAGES:
            # too many messages, no longer going to reply
            await close_thread(thread=thread)
            return

        # moderate the message
        flagged_str, blocked_str = moderate_message(message=message.content, user=message.author)
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
                        description=f"❌ **{message.author}'s message has been deleted by moderation.**",
                        color=discord.Color.red(),
                    )
                )
                return
            except Exception:
                await thread.send(
                    embed=discord.Embed(
                        description=f"❌ **{message.author}'s message has been blocked by moderation but could not be deleted. Missing Manage Messages permission in this Channel.**",
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
                    description=f"⚠️ **{message.author}'s message has been flagged by moderation.**",
                    color=discord.Color.yellow(),
                )
            )

        # wait a bit in case user has more messages
        if SECONDS_DELAY_RECEIVING_MSG > 0:
            await asyncio.sleep(SECONDS_DELAY_RECEIVING_MSG)
            if is_last_message_stale(
                interaction_message=message,
                last_message=thread.last_message,
                bot_id=client.user.id,
            ):
                # there is another message, so ignore this one
                return

        logger.info(
            "Thread message to process - %s: %s - %s %s",
            message.author, message.content[:50], thread.name, thread.jump_url
        )

        # Log user message
        await db_service.log_message(thread_id=thread.id, role="user", content=message.content)

        # Search history with limit
        history_limit = min(OPTIMIZED_HISTORY_LIMIT, MAX_THREAD_MESSAGES)
        channel_messages = []
        async for msg in thread.history(limit=history_limit):
            converted = discord_message_to_message(msg)
            if converted:
                channel_messages.append(converted)
        channel_messages.reverse()

        # Get persistent config
        thread_config = await db_service.get_thread_config(thread.id)
        if not thread_config:
            # Fallback for old or untracked threads
            thread_config = ThreadConfig(model=DEFAULT_MODEL, max_tokens=512, temperature=1.0)

        # generate the response
        async with thread.typing():
            response_data = await generate_completion_response(
                messages=channel_messages,
                user=message.author,
                thread_config=thread_config,
            )
            # Log assistant response
            if response_data.reply_text:
                await db_service.log_message(
                    thread_id=thread.id,
                    role="assistant",
                    content=response_data.reply_text
                )

        if is_last_message_stale(
            interaction_message=message,
            last_message=thread.last_message,
            bot_id=client.user.id,
        ):
            # there is another message and its not from us, so ignore this response
            return

        # send response
        await process_response(user=message.author, thread=thread, response_data=response_data)
    except Exception as e:
        logger.exception(e)


def run() -> None:
    """Entry point for the bot."""
    client.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    run()
