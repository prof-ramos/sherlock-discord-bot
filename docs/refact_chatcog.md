# Plano de Refatoração ChatCog - SherlockRamosBot

**Data**: 2026-01-04 **Objetivo**: Refatorar ChatCog seguindo princípios SOLID e melhores práticas
do discord.py **Arquivo Final**: `docs/refact_chatcog.md`

---

## 📋 Contexto

### Problema Atual

O `ChatCog` (`src/cogs/chat.py`) apresenta o anti-pattern **"God Object"**:

- **400+ linhas** de código
- **7+ responsabilidades** distintas
- **Alta complexidade ciclomática**
- **Difícil de testar** (acoplamento alto)
- **Baixa coesão** (múltiplas preocupações misturadas)

### Melhores Práticas Identificadas (Context7)

#### Discord.py (fonte: /rapptz/discord.py)

✅ **Separação de Cogs por Responsabilidade**:

- Cada Cog deve ter uma responsabilidade clara (Moderation, Fun, Chat, etc.)
- Use `cog_check` para validações específicas do Cog
- Implemente `cog_app_command_error` para slash commands (e `cog_command_error` se houver prefix commands)
- Use `cog_before_invoke` e `cog_after_invoke` para hooks

✅ **Lifecycle Management**:

- `cog_unload()` para cleanup
- `cog_load()` para inicialização
- Event listeners com `@commands.Cog.listener()`

#### Dependency Injector (fonte: /ets-labs/python-dependency-injector)

✅ **Container Pattern**:

```python
class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    database = providers.Singleton(DatabaseService)
    rag_service = providers.Factory(RAGService, db=database)
    completion_service = providers.Factory(CompletionService)
```

✅ **Injeção via `@inject` e `Provide`**:

```python
@inject
def process_message(
    service: MessageService = Provide[Container.message_service]
):
    ...
```

---

## 🎯 Objetivos da Refatoração

### 1. Separação de Responsabilidades (SRP)

- **ChatCog**: Apenas comandos slash e event listeners
- **MessageOrchestrator**: Pipeline de processamento de mensagens
- **ThreadManager**: Gerenciamento de ciclo de vida de threads
- **StalenessChecker**: Verificação de mensagens obsoletas

### 2. Dependency Injection

- Eliminar singletons globais (`db_service`, `rag_service`, `response_cache`)
- Criar `Container` para gerenciar dependências
- Injetar serviços via construtor

### 3. Testabilidade

- Cada serviço isolado e mockável
- Interfaces claras (Protocols)
- Testes unitários para cada componente

### 4. Manutenibilidade

- Cada classe com <200 linhas
- Métodos com <50 linhas
- Documentação clara

---

## ⚠️ Ajustes de Compatibilidade (antes de codar)

- **Protocolos completos**: adicionar `log_message`, `get_messages` e `deactivate_thread` no `DatabaseProtocol`.
- **Assinaturas utilitárias**: usar `is_last_message_stale(interaction_message, last_message, bot_id)` e `split_into_shorter_messages(content)` (sem segundo argumento).
- **Moderação e status de completion**: preservar bloqueio/flag e handling de `TOO_LONG`, `RATE_LIMIT`, etc.
- **RAG e cache**: manter injeção de contexto e cache dentro do `CompletionService` (sem globals).
- **App commands**: usar `cog_app_command_error` e `@app_commands.check` para allowlist; `cog_check` não cobre slash commands.
- **Criação de thread**: manter criação via mensagem (`Message.create_thread`) e validar tipo de canal.
- **Menções**: remover menções do conteúdo, responder saudação se vazio e manter histórico por usuário/canal.

---

## 🏗️ Arquitetura Proposta

### Estrutura de Diretórios

```text
src/
├── cogs/
│   └── chat.py              # ChatCog (comandos e listeners)
├── services/
│   ├── __init__.py
│   ├── completion_service.py
│   ├── message_orchestrator.py
│   ├── moderation_service.py
│   ├── thread_manager.py
│   ├── staleness_checker.py
│   └── response_sender.py
├── protocols/
│   ├── __init__.py
│   ├── database_protocol.py
│   ├── completion_protocol.py
│   └── rag_protocol.py
├── container.py             # DI Container
└── (arquivos existentes)
```

### Hierarquia de Classes

```text
Container (DI)
  ├─► Services
  │   ├─► DatabaseService
  │   ├─► RAGService
  │   ├─► CompletionService
  │   ├─► CacheService
  │   └─► ModerationService
  │
  └─► Business Logic
      ├─► MessageOrchestrator
      ├─► ThreadManager
      ├─► StalenessChecker
      └─► ResponseSender

ChatCog (injeta via Container)
  ├─► @app_commands.command('chat')
  ├─► @Cog.listener('on_message')
  └─► Delega para MessageOrchestrator
```

---

## 📝 Implementação Detalhada

### Fase 1: Criar Protocols (Interfaces)

**Arquivo**: `src/protocols/database_protocol.py`

```python
from typing import Protocol, Optional
from src.base import ThreadConfig, Message

class DatabaseProtocol(Protocol):
    """Interface para serviços de banco de dados."""

    async def connect(self) -> None:
        """Estabelece conexão com banco."""
        ...

    async def save_thread(
        self, thread_id: int, guild_id: int,
        user_id: int, config: ThreadConfig
    ) -> None:
        ...

    async def deactivate_thread(self, thread_id: int) -> None:
        """Desativa uma thread no banco."""
        ...

    async def get_thread_config(
        self, thread_id: int
    ) -> Optional[ThreadConfig]:
        ...

    async def log_message(
        self, thread_id: int, role: str, content: str, tokens: int = 0
    ) -> None:
        ...

    async def get_messages(
        self, thread_id: int, limit: int = 10
    ) -> list[Message]:
        ...
```

**Arquivo**: `src/protocols/completion_protocol.py`

```python
from typing import Protocol
from src.completion import CompletionData
from src.base import Conversation, Message, ThreadConfig

class CompletionProtocol(Protocol):
    """Interface para serviços de completion."""

    async def generate(
        self, messages: list[Message],
        user: str,
        config: ThreadConfig,
        bot_name: str,
        examples: list[Conversation]
    ) -> CompletionData:
        ...
```

**Arquivo**: `src/protocols/rag_protocol.py`

```python
from typing import Optional, Protocol

class RAGProtocol(Protocol):
    """Interface para serviços RAG."""

    async def query(
        self,
        query_text: str,
        n_results: int = 5,
        filter_metadata: Optional[dict[str, str]] = None
    ) -> list[str]:
        ...
```

---

### Fase 2: Criar Container de DI

**Arquivo**: `src/container.py`

```python
from dependency_injector import containers, providers
from src.database import DatabaseService
from src.rag_service import RAGService
from src.cache import LRUCache
from src.services.completion_service import CompletionService
from src.services.message_orchestrator import MessageOrchestrator
from src.services.moderation_service import ModerationService
from src.services.thread_manager import ThreadManager
from src.services.staleness_checker import StalenessChecker
from src.services.response_sender import ResponseSender

class Container(containers.DeclarativeContainer):
    """Container de injeção de dependências."""

    # Configuração
    config = providers.Configuration()

    # Serviços de Infraestrutura (Singleton)
    database = providers.Singleton(DatabaseService)

    rag_service = providers.Singleton(RAGService)

    cache = providers.Singleton(
        LRUCache,
        max_size=config.cache.max_size,
        ttl_seconds=config.cache.ttl_seconds
    )

    # Serviços de Negócio (Factory)
    completion_service = providers.Factory(
        CompletionService,
        cache=cache,
        rag_service=rag_service
    )

    thread_manager = providers.Factory(
        ThreadManager,
        database=database
    )

    moderation_service = providers.Factory(
        ModerationService
    )

    staleness_checker = providers.Factory(
        StalenessChecker
    )

    response_sender = providers.Factory(
        ResponseSender
    )

    message_orchestrator = providers.Factory(
        MessageOrchestrator,
        database=database,
        completion_service=completion_service,
        thread_manager=thread_manager,
        staleness_checker=staleness_checker,
        response_sender=response_sender
    )
```

---

### Fase 3: Criar Services

#### 3.1 CompletionService

**Arquivo**: `src/services/completion_service.py`

```python
from src.base import Conversation, Message, ThreadConfig
from src.cache import LRUCache
from src.completion import CompletionData, generate_completion_response
from src.protocols.rag_protocol import RAGProtocol

class CompletionService:
    """Wrapper de completion com dependências injetáveis."""

    def __init__(self, rag_service: RAGProtocol, cache: LRUCache):
        self.rag_service = rag_service
        self.cache = cache

    async def generate(
        self,
        messages: list[Message],
        user: str,
        config: ThreadConfig,
        bot_name: str,
        examples: list[Conversation]
    ) -> CompletionData:
        # TODO: ajustar generate_completion_response para aceitar cache/rag_service
        return await generate_completion_response(
            messages=messages,
            user=user,
            thread_config=config,
            bot_name=bot_name,
            example_conversations=examples,
            rag_service=self.rag_service,
            cache=self.cache
        )
```

#### 3.2 MessageOrchestrator

**Arquivo**: `src/services/message_orchestrator.py`

```python
from typing import Optional

import discord
from src.protocols.database_protocol import DatabaseProtocol
from src.protocols.completion_protocol import CompletionProtocol
from src.services.thread_manager import ThreadManager
from src.services.staleness_checker import StalenessChecker
from src.services.response_sender import ResponseSender
from src.base import Conversation, Message, ThreadConfig

class MessageOrchestrator:
    """Orquestra o pipeline de processamento de mensagens."""

    def __init__(
        self,
        database: DatabaseProtocol,
        completion_service: CompletionProtocol,
        thread_manager: ThreadManager,
        staleness_checker: StalenessChecker,
        response_sender: ResponseSender
    ):
        self.db = database
        self.completion = completion_service
        self.thread_manager = thread_manager
        self.staleness = staleness_checker
        self.sender = response_sender

    async def process_message(
        self,
        message: discord.Message,
        thread_config: ThreadConfig,
        bot_name: str,
        examples: list[Conversation],
        bot_id: int,
        content_override: Optional[str] = None
    ) -> bool:
        """
        Processa uma mensagem e retorna True se processou com sucesso.

        Pipeline:
        1. (Thread) Esperar batch e verificar staleness
        2. Buscar histórico
        3. Gerar completion (RAG e cache no CompletionService)
        4. (Thread) Verificar staleness novamente
        5. Enviar resposta (status-aware)
        6. Persistir no banco
        """
        content = content_override or message.content
        is_thread = isinstance(message.channel, discord.Thread)

        # 1. Staleness check inicial (somente threads)
        if is_thread:
            await self.staleness.wait_for_batch()
            if await self.staleness.is_stale(message, bot_id):
                return False

        # 2. Buscar histórico
        history = await self._fetch_history(message, thread_config, content)

        # 3. Gerar completion
        completion_result = await self.completion.generate(
            messages=history,
            user=str(message.author),
            config=thread_config,
            bot_name=bot_name,
            examples=examples
        )

        # 4. Staleness check final (somente threads)
        if is_thread and await self.staleness.is_stale(message, bot_id):
            return False

        # 5. Enviar resposta
        await self.sender.send_completion(
            message=message,
            response=completion_result
        )

        # 6. Persistir
        await self._persist_messages(message, content, completion_result)

        return True

    async def _fetch_history(
        self,
        message: discord.Message,
        config: ThreadConfig,
        content: str
    ) -> list[Message]:
        """Busca histórico de mensagens."""
        # Thread: usar histórico do Discord (limitado por config)
        # Menção: usar histórico no DB com thread_id sintético (ThreadManager.get_mention_thread_id)
        # Usar `content` como texto da mensagem atual (mentions já removidas)
        pass

    async def _persist_messages(
        self, user_msg: discord.Message, content: str, response
    ) -> None:
        """Persiste mensagens no banco."""
        # Thread: usar thread.id
        # Menção: usar thread_id sintético (ThreadManager.get_mention_thread_id) e garantir save_thread
        pass
```

#### 3.3 ModerationService

**Arquivo**: `src/services/moderation_service.py`

```python
import discord
from src.moderation import (
    moderate_message,
    send_moderation_blocked_message,
    send_moderation_flagged_message
)

class ModerationService:
    """Encapsula moderação preservando o comportamento atual."""

    def check_message(self, message: str, user: discord.User) -> tuple[str, str]:
        return moderate_message(message=message, user=user)

    async def handle_blocked(
        self,
        guild: discord.Guild,
        user: discord.User,
        blocked_str: str,
        message: str
    ) -> None:
        if not blocked_str:
            return
        await send_moderation_blocked_message(
            guild=guild,
            user=user,
            blocked_str=blocked_str,
            message=message
        )

    async def handle_flagged(
        self,
        guild: discord.Guild,
        user: discord.User,
        flagged_str: str,
        message: str,
        url: str
    ) -> None:
        if not flagged_str:
            return
        await send_moderation_flagged_message(
            guild=guild,
            user=user,
            flagged_str=flagged_str,
            message=message,
            url=url
        )

    async def handle_thread_blocked(
        self,
        thread: discord.Thread,
        message: discord.Message,
        blocked_str: str
    ) -> bool:
        if not blocked_str:
            return False
        await send_moderation_blocked_message(
            guild=thread.guild,
            user=message.author,
            blocked_str=blocked_str,
            message=message.content
        )
        try:
            await message.delete()
            await thread.send(
                embed=discord.Embed(
                    description=(
                        f"❌ **{message.author}'s message has been deleted by moderation.**"
                    ),
                    color=discord.Color.red()
                )
            )
        except Exception:
            await thread.send(
                embed=discord.Embed(
                    description=(
                        "❌ **"
                        f"{message.author}'s message has been blocked by moderation but could "
                        "not be deleted. Missing Manage Messages permission in this Channel."
                        "**"
                    ),
                    color=discord.Color.red()
                )
            )
        return True

    async def handle_thread_flagged(
        self,
        thread: discord.Thread,
        message: discord.Message,
        flagged_str: str
    ) -> None:
        if not flagged_str:
            return
        await send_moderation_flagged_message(
            guild=thread.guild,
            user=message.author,
            flagged_str=flagged_str,
            message=message.content,
            url=message.jump_url
        )
        await thread.send(
            embed=discord.Embed(
                description=(
                    f"⚠️ **{message.author}'s message has been flagged by moderation.**"
                ),
                color=discord.Color.yellow()
            )
        )

    def build_embed(
        self,
        user: discord.User,
        message: str,
        model: str,
        temperature: float,
        max_tokens: int,
        flagged_str: str
    ) -> discord.Embed:
        embed = discord.Embed(
            description=f"<@{user.id}> wants to chat! 🤖💬",
            color=discord.Color.green()
        )
        embed.add_field(name="model", value=model)
        embed.add_field(name="temperature", value=temperature, inline=True)
        embed.add_field(name="max_tokens", value=max_tokens, inline=True)
        embed.add_field(name=user.name, value=message)

        if flagged_str:
            embed.color = discord.Color.yellow()
            embed.title = "⚠️ This prompt was flagged by moderation."

        return embed
```

#### 3.4 ThreadManager

**Arquivo**: `src/services/thread_manager.py`

```python
import discord
from typing import Optional
from src.protocols.database_protocol import DatabaseProtocol
from src.base import ThreadConfig
from src.constants import ACTIVATE_THREAD_PREFIX

class ThreadManager:
    """Gerencia ciclo de vida de threads do Discord."""

    def __init__(self, database: DatabaseProtocol):
        self.db = database

    async def create_thread(
        self,
        starter_message: discord.Message,
        user: discord.User,
        config: ThreadConfig,
        initial_message: str
    ) -> discord.Thread:
        """
        Cria uma nova thread e persiste configuração.

        Returns:
            Thread criada
        """
        thread = await starter_message.create_thread(
            name=f"{ACTIVATE_THREAD_PREFIX} {user.name[:20]} - {initial_message[:30]}",
            type=discord.ChannelType.public_thread,
            auto_archive_duration=60
        )

        # Persistir configuração
        await self.db.save_thread(
            thread_id=thread.id,
            guild_id=starter_message.guild.id,
            user_id=user.id,
            config=config
        )

        return thread

    async def get_thread_config(self, thread_id: int) -> Optional[ThreadConfig]:
        """Busca configuração da thread."""
        return await self.db.get_thread_config(thread_id)

    def get_mention_thread_id(self, channel_id: int, user_id: int) -> int:
        """Cria ID sintético para histórico por menção (canal + usuário)."""
        return hash(f"{channel_id}_{user_id}") % (10**18)

    async def close_thread(
        self, thread: discord.Thread, reason: str = "Max messages reached"
    ) -> None:
        """Fecha thread e atualiza banco."""
        from src.utils import close_thread
        await close_thread(thread)
        await self.db.deactivate_thread(thread.id)

    async def should_close(
        self, thread: discord.Thread, max_messages: int
    ) -> bool:
        """Verifica se thread deve ser fechada."""
        return thread.message_count >= max_messages
```

#### 3.5 StalenessChecker

**Arquivo**: `src/services/staleness_checker.py`

```python
import asyncio
import discord
from src.constants import SECONDS_DELAY_RECEIVING_MSG

class StalenessChecker:
    """Verifica se mensagens estão obsoletas (staleness)."""

    async def wait_for_batch(self) -> None:
        """Aguarda tempo para batch de mensagens rápidas."""
        if SECONDS_DELAY_RECEIVING_MSG > 0:
            await asyncio.sleep(SECONDS_DELAY_RECEIVING_MSG)

    async def is_stale(self, message: discord.Message, bot_id: int) -> bool:
        """
        Verifica se mensagem ainda é a mais recente do usuário.

        Args:
            message: Mensagem a verificar
            bot_id: ID do bot

        Returns:
            True se há mensagem mais nova do mesmo usuário
        """
        from src.utils import is_last_message_stale
        if not isinstance(message.channel, discord.Thread):
            return False
        return is_last_message_stale(
            interaction_message=message,
            last_message=message.channel.last_message,
            bot_id=bot_id
        )
```

#### 3.6 ResponseSender

**Arquivo**: `src/services/response_sender.py`

```python
import discord
from src.completion import CompletionData, CompletionResult, process_response
from src.utils import split_into_shorter_messages

class ResponseSender:
    """Envia respostas preservando o comportamento atual."""

    async def send_completion(
        self, message: discord.Message, response: CompletionData
    ) -> None:
        """
        Envia resposta com handling de status.

        - Threads: reutiliza `process_response` existente
        - Menções: responde no canal com chunks (comportamento atual)
        """
        if isinstance(message.channel, discord.Thread):
            await process_response(
                user=message.author.name,
                thread=message.channel,
                response_data=response
            )
            return

        if response.status == CompletionResult.OK and response.reply_text:
            for chunk in split_into_shorter_messages(response.reply_text):
                await message.reply(chunk)
            return

        if response.status == CompletionResult.TOO_LONG:
            await message.reply(
                "❌ A resposta ficou muito longa. Tente uma pergunta mais específica."
            )
            return

        await message.reply(
            f"❌ Erro ao gerar resposta: {response.status_text or 'Erro desconhecido'}"
        )
```

---

### Fase 4: Refatorar ChatCog

**Arquivo**: `src/cogs/chat.py` (Refatorado)

```python
import discord
from discord import app_commands
from discord.ext import commands
from dependency_injector.wiring import inject, Provide

from src.container import Container
from src.services.message_orchestrator import MessageOrchestrator
from src.services.thread_manager import ThreadManager
from src.base import ThreadConfig
from src.constants import (
    ACTIVATE_THREAD_PREFIX,
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
    MAX_THREAD_MESSAGES
)
from src.utils import should_block, logger
from src.services.moderation_service import ModerationService


async def _is_allowed(interaction: discord.Interaction) -> bool:
    """Check allowlist for app commands."""
    return not should_block(interaction.guild)


def _strip_mentions(message: discord.Message) -> str:
    """Remove bot/user mentions from message content."""
    content = message.content
    for mention in message.mentions:
        content = content.replace(f"<@{mention.id}>", "").replace(f"<@!{mention.id}>", "")
    return content.strip()


class ChatCog(commands.Cog, name='Chat'):
    """Comandos de chat e handlers de mensagem."""

    @inject
    def __init__(
        self,
        bot: commands.Bot,
        orchestrator: MessageOrchestrator = Provide[Container.message_orchestrator],
        thread_manager: ThreadManager = Provide[Container.thread_manager],
        moderation: ModerationService = Provide[Container.moderation_service]
    ):
        self.bot = bot
        self.orchestrator = orchestrator
        self.thread_manager = thread_manager
        self.moderation = moderation

    async def cog_load(self) -> None:
        """Chamado quando Cog é carregado."""
        logger.info("ChatCog loaded successfully")

    async def cog_unload(self) -> None:
        """Cleanup quando Cog é descarregado."""
        logger.info("ChatCog unloading...")

    async def cog_check(self, ctx: commands.Context) -> bool:
        """Verifica se comando pode ser executado neste contexto."""
        if ctx.guild is None:
            return False
        return not should_block(ctx.guild)

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError
    ) -> None:
        """Handler de erros centralizado para app commands deste Cog."""
        if isinstance(error, discord.app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ Você não tem permissão para usar este comando.", ephemeral=True
            )
        elif isinstance(error, discord.app_commands.BotMissingPermissions):
            await interaction.response.send_message(
                f"❌ Preciso das permissões: {', '.join(error.missing_permissions)}",
                ephemeral=True
            )
        else:
            logger.exception("Erro não tratado no ChatCog", exc_info=error)
            await interaction.response.send_message(
                "❌ Ocorreu um erro inesperado.", ephemeral=True
            )

    @app_commands.command(name="chat", description="Iniciar conversa com o bot")
    @app_commands.check(_is_allowed)
    @app_commands.checks.has_permissions(send_messages=True)
    @app_commands.checks.has_permissions(view_channel=True)
    @app_commands.checks.bot_has_permissions(send_messages=True)
    @app_commands.checks.bot_has_permissions(view_channel=True)
    @app_commands.checks.bot_has_permissions(manage_threads=True)
    @app_commands.describe(message="Primeira mensagem da conversa")
    @app_commands.describe(model="Modelo LLM a usar")
    @app_commands.describe(temperature="Criatividade (0.0 = focado, 1.0 = criativo)")
    @app_commands.describe(max_tokens="Tokens máximos na resposta")
    async def chat_command(
        self,
        interaction: discord.Interaction,
        message: str,
        model: AVAILABLE_MODELS = DEFAULT_MODEL,
        temperature: app_commands.Range[float, 0.0, 1.0] = 1.0,
        max_tokens: app_commands.Range[int, 1, 4096] = 512
    ) -> None:
        """Cria thread e processa primeira mensagem."""
        config = ThreadConfig(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )

        try:
            if not isinstance(interaction.channel, discord.TextChannel):
                return

            # Validar conteúdo
            if not message or not message.strip():
                await interaction.response.send_message(
                    "❌ A mensagem não pode estar vazia.", ephemeral=True
                )
                return

            message = message.strip()
            if len(message) > 4000:
                await interaction.response.send_message(
                    f"❌ A mensagem é muito longa ({len(message)} caracteres).",
                    ephemeral=True
                )
                return

            # Moderação
            flagged_str, blocked_str = self.moderation.check_message(
                message=message,
                user=interaction.user
            )
            await self.moderation.handle_blocked(
                guild=interaction.guild,
                user=interaction.user,
                blocked_str=blocked_str,
                message=message
            )
            if blocked_str:
                await interaction.response.send_message(
                    "❌ Seu prompt foi bloqueado por moderação.", ephemeral=True
                )
                return

            embed = self.moderation.build_embed(
                user=interaction.user,
                message=message,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                flagged_str=flagged_str
            )
            await interaction.response.send_message(embed=embed)
            response = await interaction.original_response()

            await self.moderation.handle_flagged(
                guild=interaction.guild,
                user=interaction.user,
                flagged_str=flagged_str,
                message=message,
                url=response.jump_url
            )

            # Criar thread
            thread = await self.thread_manager.create_thread(
                starter_message=response,
                user=interaction.user,
                config=config,
                initial_message=message
            )

            # Enviar mensagem inicial na thread
            user_msg = await thread.send(
                f"{interaction.user.mention}: {message}"
            )

            # Processar mensagem
            success = await self.orchestrator.process_message(
                message=user_msg,
                thread_config=config,
                bot_name=self.bot.user.name,
                examples=self.bot.example_conversations,
                bot_id=self.bot.user.id,
                content_override=message
            )

            if success:
                await interaction.followup.send(
                    f"✅ Thread criada: {thread.mention}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "⚠️ Não foi possível processar a mensagem.",
                    ephemeral=True
                )

        except Exception as e:
            logger.exception("Erro ao criar thread", exc_info=e)
            await interaction.followup.send(
                "❌ Erro ao criar thread. Tente novamente.",
                ephemeral=True
            )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """
        Processa mensagens que mencionam o bot ou em threads ativas.

        Casos:
        1. Mensagem em thread do bot
        2. Menção ao bot em qualquer canal
        """
        # Ignorar mensagens do próprio bot
        if message.author == self.bot.user:
            return

        # Ignorar DMs
        if message.guild is None:
            return

        # Verificar allowlist
        if should_block(message.guild):
            return

        # Caso 1: Mensagem em thread
        if self._is_bot_thread(message):
            await self._handle_thread_message(message)
            return

        # Caso 2: Menção ao bot
        if self.bot.user in message.mentions:
            await self._handle_mention(message)
            return

    def _is_bot_thread(self, message: discord.Message) -> bool:
        """Verifica se mensagem está em thread criada pelo bot."""
        if not isinstance(message.channel, discord.Thread):
            return False

        thread = message.channel
        return (
            thread.owner_id == self.bot.user.id and
            thread.name.startswith(ACTIVATE_THREAD_PREFIX) and
            not thread.archived and
            not thread.locked
        )

    async def _handle_thread_message(self, message: discord.Message) -> None:
        """Processa mensagem em thread do bot."""
        thread = message.channel

        # Verificar se deve fechar thread
        if await self.thread_manager.should_close(thread, MAX_THREAD_MESSAGES):
            await self.thread_manager.close_thread(
                thread, "Limite de mensagens atingido"
            )
            return

        # Moderação
        flagged_str, blocked_str = self.moderation.check_message(
            message=message.content,
            user=message.author
        )
        if await self.moderation.handle_thread_blocked(
            thread=thread,
            message=message,
            blocked_str=blocked_str
        ):
            return
        await self.moderation.handle_thread_flagged(
            thread=thread,
            message=message,
            flagged_str=flagged_str
        )

        # Buscar configuração da thread
        config = await self.thread_manager.get_thread_config(thread.id)
        if config is None:
            logger.warning(f"Config não encontrada para thread {thread.id}")
            return

        # Processar mensagem
        await self.orchestrator.process_message(
            message=message,
            thread_config=config,
            bot_name=self.bot.user.name,
            examples=self.bot.example_conversations,
            bot_id=self.bot.user.id
        )

    async def _handle_mention(self, message: discord.Message) -> None:
        """Processa mensagem que menciona o bot."""
        # Configuração padrão para menções
        from src.constants import (
            DEFAULT_MENTION_TEMPERATURE,
            DEFAULT_MENTION_MAX_TOKENS
        )

        content = _strip_mentions(message)
        if not content:
            await message.reply("👋 Olá! Sou o SherlockBot, seu assistente jurídico. Como posso ajudar?")
            return

        flagged_str, blocked_str = self.moderation.check_message(
            message=content,
            user=message.author
        )
        await self.moderation.handle_blocked(
            guild=message.guild,
            user=message.author,
            blocked_str=blocked_str,
            message=content
        )
        if blocked_str:
            await message.reply("❌ Seu prompt foi bloqueado por moderação.")
            return

        await self.moderation.handle_flagged(
            guild=message.guild,
            user=message.author,
            flagged_str=flagged_str,
            message=content,
            url=message.jump_url
        )

        config = ThreadConfig(
            model=DEFAULT_MODEL,
            temperature=DEFAULT_MENTION_TEMPERATURE,
            max_tokens=DEFAULT_MENTION_MAX_TOKENS
        )

        await self.orchestrator.process_message(
            message=message,
            thread_config=config,
            bot_name=self.bot.user.name,
            examples=self.bot.example_conversations,
            bot_id=self.bot.user.id,
            content_override=content
        )
```

---

### Fase 5: Atualizar main.py

**Arquivo**: `src/main.py` (Modificações)

```python
import logging
import discord
from discord.ext import commands

from src.base import Conversation, Message
from src.cogs.chat import ChatCog
from src.container import Container  # NOVO
from src.constants import (
    ALLOWED_SERVER_IDS,
    BOT_INVITE_URL,
    BOT_NAME,
    DISCORD_BOT_TOKEN,
    EXAMPLE_CONVOS,
    CACHE_MAX_SIZE,
    CACHE_TTL_SECONDS
)
from src.utils import logger

# ... logging setup ...

class SherlockRamosBot(commands.Bot):
    """Discord bot entry point com DI container."""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

        # Inicializar container DI
        self.container = Container()
        self.container.config.cache.max_size.from_value(CACHE_MAX_SIZE)
        self.container.config.cache.ttl_seconds.from_value(CACHE_TTL_SECONDS)

        # Wire container para injeção automática
        self.container.wire(modules=[
            "src.cogs.chat",
            "src.services.message_orchestrator"
        ])

    # ... métodos existentes (bot_name, example_conversations) ...

    async def setup_hook(self) -> None:
        """Carrega Cogs e sincroniza comandos."""
        # Adicionar ChatCog (dependências injetadas automaticamente)
        await self.add_cog(ChatCog(self))

        # Sincronizar comandos
        for guild_id in ALLOWED_SERVER_IDS:
            guild = discord.Object(id=guild_id)
            self.tree.copy_global_to(guild=guild)
            try:
                synced = await self.tree.sync(guild=guild)
                logger.info("Synced %d commands to guild %d", len(synced), guild_id)
            except Exception as exc:
                logger.error("Failed to sync commands: %s", exc)

        await self.tree.sync()
        logger.info("Global command sync complete")

    async def close(self) -> None:
        """Cleanup antes de fechar."""
        from src.profiling import log_metrics_summary_sync

        log_metrics_summary_sync()

        # Shutdown container
        await self.container.shutdown_resources()

        await super().close()

def run() -> None:
    """Entry point."""
    bot = SherlockRamosBot()
    bot.run(DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    run()
```

---

## 🧪 Fase 6: Testes

### 6.1 Testes Unitários

**Arquivo**: `tests/unit/test_message_orchestrator.py`

```python
import pytest
from unittest.mock import AsyncMock, Mock
from src.completion import CompletionData, CompletionResult
from src.services.message_orchestrator import MessageOrchestrator

@pytest.fixture
def mock_dependencies():
    """Cria mocks para todas as dependências."""
    return {
        'database': AsyncMock(),
        'completion_service': AsyncMock(),
        'thread_manager': AsyncMock(),
        'staleness_checker': AsyncMock(),
        'response_sender': AsyncMock()
    }

@pytest.fixture
def orchestrator(mock_dependencies):
    """Cria MessageOrchestrator com dependências mockadas."""
    return MessageOrchestrator(**mock_dependencies)

@pytest.mark.asyncio
async def test_process_message_success(orchestrator, mock_dependencies):
    """Testa processamento bem-sucedido de mensagem."""
    # Arrange
    mock_message = Mock()
    mock_config = Mock()

    mock_dependencies['staleness_checker'].is_stale.return_value = False
    mock_dependencies['completion_service'].generate.return_value = CompletionData(
        status=CompletionResult.OK,
        reply_text="Resposta gerada",
        status_text=None
    )

    # Act
    result = await orchestrator.process_message(
        message=mock_message,
        thread_config=mock_config,
        bot_name="TestBot",
        examples=[],
        bot_id=123
    )

    # Assert
    assert result is True
    mock_dependencies['response_sender'].send_completion.assert_called_once()
```

**Arquivo**: `tests/unit/test_thread_manager.py`

```python
import pytest
from unittest.mock import AsyncMock, Mock
from src.services.thread_manager import ThreadManager
from src.base import ThreadConfig

@pytest.fixture
def thread_manager():
    """Cria ThreadManager com database mockado."""
    mock_db = AsyncMock()
    return ThreadManager(database=mock_db)

@pytest.mark.asyncio
async def test_create_thread(thread_manager):
    """Testa criação de thread."""
    # Arrange
    mock_starter = AsyncMock()
    mock_user = Mock(name="TestUser")
    config = ThreadConfig(model="test", temperature=0.7, max_tokens=100)

    mock_thread = Mock(id=12345)
    mock_starter.create_thread.return_value = mock_thread
    mock_starter.guild.id = 67890

    # Act
    thread = await thread_manager.create_thread(
        starter_message=mock_starter,
        user=mock_user,
        config=config,
        initial_message="Test"
    )

    # Assert
    assert thread == mock_thread
    thread_manager.db.save_thread.assert_called_once()
```

### 6.2 Testes de Integração

**Arquivo**: `tests/integration/test_chat_cog_integration.py`

```python
import pytest
from unittest.mock import Mock
from src.cogs.chat import ChatCog
from src.container import Container

@pytest.fixture
def container():
    """Container configurado para testes."""
    container = Container()
    # Configurar com valores de teste
    container.config.cache.max_size.from_value(10)
    container.config.cache.ttl_seconds.from_value(60)
    return container

@pytest.mark.asyncio
async def test_chat_cog_initialization(container):
    """Testa inicialização do ChatCog com DI."""
    # Arrange
    mock_bot = Mock()
    container.wire(modules=["src.cogs.chat"])

    # Act
    cog = ChatCog(mock_bot)

    # Assert
    assert cog.orchestrator is not None
    assert cog.thread_manager is not None
```

---

## 📊 Fase 7: Migração Gradual

### Estratégia de Rollout

#### Etapa 1: Criar nova estrutura (sem quebrar existente)

- Criar `src/services/`
- Criar `src/protocols/`
- Criar `src/container.py`
- **Status**: ChatCog antigo ainda funciona

#### Etapa 2: Implementar serviços

- Implementar MessageOrchestrator
- Implementar ThreadManager
- Implementar StalenessChecker
- Implementar ResponseSender
- **Status**: Serviços testados isoladamente

#### Etapa 3: Criar ChatCog v2 (paralelo)

- Criar `src/cogs/chat_v2.py`
- Implementar com DI
- Testar em servidor de desenvolvimento
- **Status**: Duas versões coexistem

#### Etapa 4: Feature Flag

- Adicionar `USE_NEW_CHATCOG` em constants
- Carregar ChatCog v1 ou v2 baseado em flag
- Testar gradualmente em produção
- **Status**: Rollback fácil se houver problemas

#### Etapa 5: Finalizar migração

- Remover `chat.py` antigo
- Renomear `chat_v2.py` → `chat.py`
- Remover feature flag
- **Status**: Migração completa

---

## 📋 Checklist de Implementação

### Fase 1: Fundação

- [ ] Criar `src/protocols/database_protocol.py` (inclui `log_message`, `get_messages`, `deactivate_thread`)
- [ ] Criar `src/protocols/completion_protocol.py`
- [ ] Criar `src/protocols/rag_protocol.py`
- [ ] Instalar `dependency-injector`: `uv add dependency-injector`
- [ ] Criar `src/container.py`
- [ ] Atualizar `DatabaseService` com `deactivate_thread`

### Fase 2: Services

- [ ] Criar `src/services/__init__.py`
- [ ] Implementar `CompletionService` (remover `response_cache` global)
- [ ] Refatorar `generate_completion_response` para receber cache/RAG via DI
- [ ] Implementar `MessageOrchestrator`
- [ ] Implementar `ModerationService`
- [ ] Implementar `ThreadManager`
- [ ] Implementar `StalenessChecker`
- [ ] Implementar `ResponseSender`

### Fase 3: Testes

- [ ] Escrever testes unitários para cada serviço
- [ ] Cobrir moderação (blocked/flagged) e fluxo de menções
- [ ] Alcançar 80%+ cobertura em services
- [ ] Executar `uv run pytest tests/unit -v`

### Fase 4: Refatoração

- [ ] Criar `src/cogs/chat_v2.py`
- [ ] Migrar lógica de ChatCog para v2
- [ ] Preservar moderação, menções e criação de thread via mensagem
- [ ] Atualizar `main.py` com Container
- [ ] Wire modules no container

### Fase 5: Validação

- [ ] Testar localmente (3+ cenários)
- [ ] Testar em servidor dev
- [ ] Monitorar logs de erro
- [ ] Comparar performance (antes/depois)

### Fase 6: Deploy

- [ ] Adicionar feature flag `USE_NEW_CHATCOG`
- [ ] Deploy gradual (10% → 50% → 100%)
- [ ] Monitorar métricas
- [ ] Remover código legado após 1 semana estável

---

## 📈 Métricas de Sucesso

### Antes da Refatoração

- **Linhas no ChatCog**: ~400
- **Complexidade ciclomática**: Alta (>20)
- **Cobertura de testes**: <20%
- **Acoplamento**: Alto (8+ dependências diretas)

### Depois da Refatoração (Meta)

- **Linhas no ChatCog**: <150
- **Linhas por serviço**: <200
- **Complexidade ciclomática**: Baixa (<10 por método)
- **Cobertura de testes**: >80%
- **Acoplamento**: Baixo (dependências injetadas)
- **Testabilidade**: Alta (serviços mockáveis)

## 🚀 Benefícios Esperados

### Manutenibilidade

✅ Cada componente com responsabilidade única ✅ Código mais fácil de entender ✅ Mudanças isoladas
(menor risco de regressão)

### Testabilidade

✅ Mocks fáceis (dependências injetadas) ✅ Testes unitários rápidos ✅ Cobertura aumenta de 20% →
80%+

### Escalabilidade

✅ Adicionar novos Cogs sem afetar ChatCog ✅ Substituir implementações (ex: trocar cache por Redis)
✅ Paralelizar processamento (múltiplos orchestrators)

### Performance

✅ Profiling por serviço (identificar gargalos) ✅ Cache otimizado (injetável) ✅ Conexões
gerenciadas pelo container

---

## 🎯 Próximos Passos

1. **Criar documento final**: `docs/refact_chatcog.md`
2. **Validar com equipe**: Review do plano
3. **Estimar esforço**: 2-3 semanas para implementação completa
4. **Priorizar fases**: Começar por Fase 1 (fundação)

---

**Plano criado por**: Claude Sonnet 4.5 **Data**: 2026-01-04 **Baseado em**: Análise arquitetural +
Context7 best practices
