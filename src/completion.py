from dataclasses import dataclass
from enum import Enum
from typing import Optional

import discord
import openai
from openai import APIConnectionError, APIStatusError, AsyncOpenAI, RateLimitError

from src.base import Conversation, Message, Prompt, ThreadConfig
from src.cache import response_cache
from src.constants import (
    BOT_INSTRUCTIONS,
    BOT_NAME,
    EXAMPLE_CONVOS,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MAX_RETRIES,
    OPENROUTER_TIMEOUT,
)
from src.moderation import (
    send_moderation_blocked_message,
    send_moderation_flagged_message,
)
from src.profiling import timed
from src.utils import close_thread, logger, split_into_shorter_messages

client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL,
    max_retries=OPENROUTER_MAX_RETRIES,
    timeout=OPENROUTER_TIMEOUT,
)

MY_BOT_NAME = BOT_NAME
MY_BOT_EXAMPLE_CONVOS = EXAMPLE_CONVOS


class CompletionResult(Enum):
    OK = 0
    TOO_LONG = 1
    INVALID_REQUEST = 2
    OTHER_ERROR = 3
    MODERATION_FLAGGED = 4
    MODERATION_BLOCKED = 5
    RATE_LIMIT = 6


@dataclass
class CompletionData:
    status: CompletionResult
    reply_text: Optional[str]
    status_text: Optional[str]



@timed
async def generate_completion_response(
    messages: list[Message], user: str, thread_config: ThreadConfig
) -> CompletionData:
    # Verificar cache primeiro
    cached = response_cache.get(
        messages,
        thread_config.model,
        temperature=thread_config.temperature,
        max_tokens=thread_config.max_tokens
    )
    if cached is not None:
        logger.info("🎯 Cache HIT for model %s (temp=%.1f)", thread_config.model, thread_config.temperature)
        return cached

    try:
        # RAG Context Injection
        rag_context = ""
        try:
            # Extract last user message for query
            last_user_msg = next((m.text for m in reversed(messages) if m.user == user), None)
            if last_user_msg:
                from src.rag_service import rag_service
                docs = rag_service.query(last_user_msg)
                if docs:
                    rag_context = "\n\nRELEVANT LEGAL CONTEXT:\n" + "\n---\n".join(docs) + "\n\nUse the above context to answer the user's question if relevant."
                    logger.info("📚 RAG: Injected %d documents into context", len(docs))
        except Exception as e:
            logger.error("RAG injection failed: %s", e)

        system_instruction = f"Instructions for {MY_BOT_NAME}: {BOT_INSTRUCTIONS}{rag_context}"

        prompt = Prompt(
            header=Message("system", system_instruction),
            examples=MY_BOT_EXAMPLE_CONVOS,
            convo=Conversation(messages),
        )
        rendered = prompt.full_render(MY_BOT_NAME)
        response = await client.chat.completions.create(
            model=thread_config.model,
            messages=rendered,
            temperature=thread_config.temperature,
            top_p=1.0,
            max_tokens=thread_config.max_tokens,
            stop=["<|endoftext|>"],
            extra_headers={
                "HTTP-Referer": "https://github.com/prof-ramos/sherlock-discord-bot",
                "X-Title": "Discord Bot Client",
            },
        )
        reply = response.choices[0].message.content.strip()

        # Note: API-based moderation is disabled for OpenRouter
        # OpenRouter applies native filtering on many models
        # Custom moderation logic can be added here if needed in the future

        result = CompletionData(status=CompletionResult.OK, reply_text=reply, status_text=None)
        # Armazenar resultado bem-sucedido em cache
        response_cache.set(
            messages,
            thread_config.model,
            result,
            temperature=thread_config.temperature,
            max_tokens=thread_config.max_tokens
        )
        return result
    except openai.BadRequestError as e:
        if "This model's maximum context length" in str(e):
            return CompletionData(
                status=CompletionResult.TOO_LONG, reply_text=None, status_text=str(e)
            )
        else:
            logger.exception(e)
            return CompletionData(
                status=CompletionResult.INVALID_REQUEST,
                reply_text=None,
                status_text=str(e),
            )
    except APIConnectionError as e:
        logger.error("OpenRouter API connection failed: %s", e.__cause__)
        return CompletionData(
            status=CompletionResult.OTHER_ERROR,
            reply_text=None,
            status_text="Could not connect to the AI service. Please try again later.",
        )
    except RateLimitError as e:
        logger.warning("OpenRouter rate limit hit: %s", e.status_code)
        return CompletionData(
            status=CompletionResult.RATE_LIMIT,
            reply_text=None,
            status_text="The AI service is currently busy. Please wait a moment and try again.",
        )
    except APIStatusError as e:
        # Sanitize log: avoid dumping e.response headers/body
        logger.error(
            "OpenRouter API error (status %d): %s",
            e.status_code,
            str(e)
        )
        return CompletionData(
            status=CompletionResult.OTHER_ERROR,
            reply_text=None,
            status_text=f"AI service error (code: {e.status_code}). Please try again.",
        )
    except Exception as e:
        logger.exception(e)
        return CompletionData(
            status=CompletionResult.OTHER_ERROR, reply_text=None, status_text=str(e)
        )


async def process_response(user: str, thread: discord.Thread, response_data: CompletionData):
    status = response_data.status
    reply_text = response_data.reply_text
    status_text = response_data.status_text
    if status is CompletionResult.OK or status is CompletionResult.MODERATION_FLAGGED:
        sent_message = None
        if not reply_text:
            sent_message = await thread.send(
                embed=discord.Embed(
                    description="**Invalid response** - empty response",
                    color=discord.Color.yellow(),
                )
            )
        else:
            shorter_response = split_into_shorter_messages(reply_text)
            for r in shorter_response:
                sent_message = await thread.send(r)
        if status is CompletionResult.MODERATION_FLAGGED:
            await send_moderation_flagged_message(
                guild=thread.guild,
                user=user,
                flagged_str=status_text,
                message=reply_text,
                url=sent_message.jump_url if sent_message else "no url",
            )

            await thread.send(
                embed=discord.Embed(
                    description="⚠️ **This conversation has been flagged by moderation.**",
                    color=discord.Color.yellow(),
                )
            )
    elif status is CompletionResult.MODERATION_BLOCKED:
        await send_moderation_blocked_message(
            guild=thread.guild,
            user=user,
            blocked_str=status_text,
            message=reply_text,
        )

        await thread.send(
            embed=discord.Embed(
                description="❌ **The response has been blocked by moderation.**",
                color=discord.Color.red(),
            )
        )
    elif status is CompletionResult.RATE_LIMIT:
        await thread.send(
            embed=discord.Embed(
                description=f"⏳ **{status_text}**",
                color=discord.Color.orange(),
            )
        )
    elif status is CompletionResult.TOO_LONG:
        await close_thread(thread)
    elif status is CompletionResult.INVALID_REQUEST:
        await thread.send(
            embed=discord.Embed(
                description=f"**Invalid request** - {status_text}",
                color=discord.Color.yellow(),
            )
        )
    else:
        await thread.send(
            embed=discord.Embed(
                description=f"**Error** - {status_text}",
                color=discord.Color.yellow(),
            )
        )
