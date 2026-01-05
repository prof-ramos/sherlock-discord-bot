import json
import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import discord
import httpx
import openai
from bs4 import BeautifulSoup
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

# Remove global variables that are mutated from main.py


# ============================================================================
# Tool Functions for Function Calling
# ============================================================================


async def buscar_jurisprudencia_web(query: str, tribunal: str = "todos") -> str:
    """
    Busca jurisprudência via Serper.dev.

    Args:
        query: Consulta jurídica (ex: "habeas corpus preventivo 2024")
        tribunal: "stf", "stj", "planalto", ou "todos"

    Returns:
        String formatada com top 3 resultados (título, URL, snippet)
    """
    serper_api_key = os.environ.get("SERPER_API_KEY")
    if not serper_api_key:
        logger.warning("SERPER_API_KEY not configured. Web search unavailable.")
        return "⚠️ Busca web não disponível (SERPER_API_KEY não configurada)"

    try:
        # Build site-specific query
        site_filters = {
            "stf": "site:portal.stf.jus.br OR site:stf.jus.br",
            "stj": "site:stj.jus.br",
            "planalto": "site:planalto.gov.br",
            "todos": "site:stf.jus.br OR site:stj.jus.br OR site:planalto.gov.br",
        }
        site_filter = site_filters.get(tribunal.lower(), site_filters["todos"])
        full_query = f"{query} {site_filter}"

        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": serper_api_key,
                    "Content-Type": "application/json",
                },
                json={"q": full_query, "num": 5, "gl": "br", "hl": "pt"},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

        # Format results
        results = data.get("organic", [])
        if not results:
            return f"Nenhum resultado encontrado para: {query}"

        formatted = []
        for i, result in enumerate(results[:3], 1):
            title = result.get("title", "Sem título")
            link = result.get("link", "")
            snippet = result.get("snippet", "")
            formatted.append(f"**{i}. {title}**\n🔗 {link}\n📄 {snippet}\n")

        logger.info("🔧 Web search: Found %d results for query '%s'", len(results), query)
        return "\n".join(formatted)

    except httpx.TimeoutException:
        logger.error("Serper.dev timeout for query: %s", query)
        return "⏳ Timeout ao buscar jurisprudência online"
    except Exception as e:
        logger.error("Serper.dev search failed: %s", str(e))
        return f"❌ Erro ao buscar jurisprudência: {str(e)}"


async def extrair_conteudo_url(url: str) -> str:
    """
    Extrai texto de URL de decisão judicial.

    Args:
        url: URL completa (ex: https://portal.stf.jus.br/...)

    Returns:
        Texto extraído (max 4000 chars)
    """
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(url, follow_redirects=True, timeout=30.0)
            response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove unwanted tags
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Extract text
        text = soup.get_text(separator="\n", strip=True)

        # Limit to 4000 chars
        if len(text) > 4000:
            text = text[:4000] + "\n\n[... conteúdo truncado ...]"

        logger.info("🔧 URL extraction: Extracted %d chars from %s", len(text), url)
        return text

    except httpx.TimeoutException:
        logger.error("URL extraction timeout: %s", url)
        return f"⏳ Timeout ao acessar URL: {url}"
    except Exception as e:
        logger.error("URL extraction failed for %s: %s", url, str(e))
        return f"❌ Erro ao extrair conteúdo da URL: {str(e)}"


async def consultar_base_local(query: str, num_docs: int = 3) -> str:
    """
    Consulta RAG local (já existente).

    Args:
        query: Consulta jurídica
        num_docs: Número de documentos (1-5)

    Returns:
        Documentos formatados da base local
    """
    try:
        from src.rag_service import rag_service

        # Clamp num_docs to valid range
        num_docs = max(1, min(5, num_docs))

        docs = await rag_service.query(query, n_results=num_docs)

        if not docs:
            return "📚 Nenhum documento encontrado na base local"

        # Format documents
        formatted = []
        for i, doc in enumerate(docs, 1):
            # Truncate each doc to 1000 chars
            doc_text = doc if len(doc) <= 1000 else doc[:1000] + "..."
            formatted.append(f"**Documento {i}:**\n{doc_text}\n")

        logger.info("🔧 Local RAG: Retrieved %d documents for query '%s'", len(docs), query)
        return "\n".join(formatted)

    except Exception as e:
        logger.error("Local RAG query failed: %s", str(e))
        return f"❌ Erro ao consultar base local: {str(e)}"


# Tool schemas in OpenAI format
AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "buscar_jurisprudencia_web",
            "description": (
                "Busca jurisprudência e legislação ATUALIZADA em sites oficiais brasileiros "
                "(STF, STJ, Planalto). Use quando precisar de informações RECENTES (2024-2025) "
                "ou casos específicos não disponíveis na base local."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Consulta jurídica em português (ex: 'habeas corpus preventivo "
                            "jurisprudência recente')"
                        ),
                    },
                    "tribunal": {
                        "type": "string",
                        "enum": ["stf", "stj", "planalto", "todos"],
                        "description": (
                            "Filtrar por tribunal: stf=Supremo Tribunal Federal, "
                            "stj=Superior Tribunal de Justiça, planalto=Legislação Federal, "
                            "todos=buscar em todos"
                        ),
                        "default": "todos",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "extrair_conteudo_url",
            "description": (
                "Extrai o texto completo de uma URL de decisão judicial ou legislação. "
                "Use quando o usuário fornecer um link específico para análise."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL completa (ex: https://portal.stf.jus.br/...)",
                    }
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_base_local",
            "description": (
                "Consulta a base de conhecimento local (RAG) com legislação e jurisprudência "
                "já indexada. Use para informações gerais e consolidadas."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Consulta jurídica em português",
                    },
                    "num_docs": {
                        "type": "integer",
                        "description": "Número de documentos a retornar (1-5)",
                        "default": 3,
                        "minimum": 1,
                        "maximum": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
]

# Mapping of function names to callables
TOOL_FUNCTIONS = {
    "buscar_jurisprudencia_web": buscar_jurisprudencia_web,
    "extrair_conteudo_url": extrair_conteudo_url,
    "consultar_base_local": consultar_base_local,
}


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
    messages: list[Message],
    user: str,
    thread_config: ThreadConfig,
    bot_name: str = BOT_NAME,
    example_conversations: list = EXAMPLE_CONVOS,
    enable_tools: bool = True,
) -> CompletionData:
    # Verificar cache primeiro
    cached = response_cache.get(
        messages,
        thread_config.model,
        temperature=thread_config.temperature,
        max_tokens=thread_config.max_tokens,
    )
    if cached is not None:
        logger.info(
            "🎯 Cache HIT for model %s (temp=%.1f)", thread_config.model, thread_config.temperature
        )
        return cached

    try:
        # RAG Context Injection
        rag_context = ""
        try:
            # Extract last user message for query
            last_user_msg = next((m.text for m in reversed(messages) if m.user == str(user)), None)
            if last_user_msg:
                from src.rag_service import rag_service

                docs = await rag_service.query(last_user_msg)
                if docs:
                    from html import escape as html_escape

                    # XML-structured context with escaped content
                    indented_docs = "\n".join(
                        [f"<doc index='{i + 1}'>{html_escape(d)}</doc>" for i, d in enumerate(docs)]
                    )
                    rag_text = (
                        "<relevant_context>\n"
                        f"{indented_docs}\n"
                        "</relevant_context>\n\n"
                        "Instructions:\n"
                        "1. Use the provided context to answer the user's question.\n"
                        "2. If the context contains the answer, cite the document index or content.\n"
                        "3. If the context is valid but insufficient, use your general knowledge but mention the missing details.\n"
                    )
                    rag_context = Message("system", rag_text).render()
                    logger.info("📚 RAG: Injected %d documents into context", len(docs))
        except Exception as e:
            logger.error("RAG injection failed: %s", e)

        system_instruction = f"Instructions for {bot_name}: {BOT_INSTRUCTIONS}"

        # Create example conversations with the bot's actual name
        bot_example_conversations = [
            Conversation(
                messages=[
                    Message(user=bot_name, text=msg.text) if msg.user == BOT_NAME else msg
                    for msg in convo.messages
                ]
            )
            for convo in example_conversations
        ]

        prompt = Prompt(
            header=Message("system", system_instruction),
            examples=bot_example_conversations,
            convo=Conversation(messages),
        )
        rendered = prompt.full_render(bot_name, thread_config.model, rag_context)

        # Prepare API call parameters
        call_params = {
            "model": thread_config.model,
            "messages": rendered,
            "temperature": thread_config.temperature,
            "top_p": 1.0,
            "max_tokens": thread_config.max_tokens,
            "stop": ["<|endoftext|>"],
            "extra_headers": {
                "HTTP-Referer": "https://github.com/prof-ramos/sherlock-discord-bot",
                "X-Title": "Discord Bot Client",
            },
        }

        # Add tools if enabled
        if enable_tools:
            call_params["tools"] = AVAILABLE_TOOLS
            call_params["tool_choice"] = "auto"

        # First API call
        response = await client.chat.completions.create(**call_params)
        message = response.choices[0].message
        used_tools = False

        # Check for tool calls
        if message.tool_calls:
            used_tools = True
            logger.info("🔧 LLM solicitou %d tool(s)", len(message.tool_calls))

            # Build tool messages
            tool_messages = [message.model_dump(exclude_unset=True)]

            # Execute each tool
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                logger.info("⚙️ Executando: %s(%s)", function_name, function_args)

                # Call the corresponding function
                if function_name in TOOL_FUNCTIONS:
                    try:
                        function_to_call = TOOL_FUNCTIONS[function_name]
                        function_response = await function_to_call(**function_args)
                    except Exception as e:
                        logger.error("Tool %s failed: %s", function_name, str(e))
                        function_response = f"❌ Erro ao executar {function_name}: {str(e)}"
                else:
                    logger.error("Unknown tool requested: %s", function_name)
                    function_response = f"❌ Ferramenta desconhecida: {function_name}"

                # Add tool result
                tool_messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    }
                )

            # Second API call with tool results
            logger.info("🔄 Fazendo segunda chamada ao LLM com resultados das tools")
            second_response = await client.chat.completions.create(
                model=thread_config.model,
                messages=rendered + tool_messages,
                temperature=thread_config.temperature,
                top_p=1.0,
                max_tokens=thread_config.max_tokens,
                stop=["<|endoftext|>"],
                extra_headers={
                    "HTTP-Referer": "https://github.com/prof-ramos/sherlock-discord-bot",
                    "X-Title": "Discord Bot Client",
                },
            )
            reply = second_response.choices[0].message.content.strip()
            logger.info("✅ Resposta final gerada com tools")
        else:
            reply = message.content.strip() if message.content else ""

        # Note: API-based moderation is disabled for OpenRouter
        # OpenRouter applies native filtering on many models
        # Custom moderation logic can be added here if needed in the future

        result = CompletionData(status=CompletionResult.OK, reply_text=reply, status_text=None)

        # Only cache responses that didn't use tools (to avoid caching dynamic data)
        if not used_tools:
            response_cache.set(
                messages,
                thread_config.model,
                result,
                temperature=thread_config.temperature,
                max_tokens=thread_config.max_tokens,
            )
        else:
            logger.info("⚠️ Skipping cache for tool-based response (dynamic data)")

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
        logger.error("OpenRouter API error (status %d): %s", e.status_code, str(e))
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
