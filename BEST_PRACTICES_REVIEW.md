# Revisão de Boas Práticas de Código: SherlockRamosBot

### Sumário Executivo

A análise da codebase do SherlockRamosBot revela uma base sólida com uso de ferramentas modernas e
uma arquitetura de banco de dados bem pensada. No entanto, o projeto sofre de um problema
arquitetônico significativo centrado no arquivo `src/main.py`, que atua como um "objeto deus",
concentrando excessiva responsabilidade. Este padrão anti-arquitetural compromete a
manutenibilidade, testabilidade e escalabilidade do projeto.

As recomendações focam na modularização de `src/main.py`, na adoção de injeção de dependência e na
automação da garantia de qualidade de código via CI/CD.

---

### 1. Problemas Críticos (Must-fix)

#### 1.1. `src/main.py`: O "Objeto Deus"

- **Problema**: O arquivo `src/main.py` acumula responsabilidades demais. Ele gerencia a
  inicialização do cliente Discord, o registro de comandos (slash commands), o tratamento de eventos
  (`on_message`), a lógica de moderação, a interação com o serviço de banco de dados e as chamadas
  para o serviço de completude da IA. Isso o torna um "objeto deus" (god object).
- **Por que é Ineficiente**:
  - **Violação do SRP (Princípio da Responsabilidade Única)**: Uma única classe/módulo tem múltiplas
    razões para mudar. Qualquer alteração em comandos, eventos ou lógica de negócios afeta
    `main.py`.
  - **Baixa Testabilidade**: É extremamente difícil escrever testes unitários para as funções em
    `main.py` sem mockar uma vasta quantidade de dependências do Discord e de serviços internos.
  - **Baixa Manutenibilidade**: O arquivo é extenso e complexo, dificultando a compreensão,
    depuração e modificação.
  - **Escalabilidade Limitada**: Adicionar novos comandos ou funcionalidades de eventos torna
    `main.py` ainda maior e mais intratável.
- **Impacto no Desempenho (Indireto)**: Embora não seja uma questão de desempenho direto de
  CPU/memória, a complexidade introduzida pode levar a bugs e dificultar otimizações futuras.
- **Como Otimizar**: Refatorar `src/main.py` utilizando o conceito de "Cogs" (ou Extensions) do
  `discord.py`. Cada Cog seria responsável por um conjunto específico de comandos ou eventos,
  aderindo ao SRP.
- **Nota de `discord.py` (Context7)**: Cogs herdam de `commands.Cog` e são adicionados de forma
  assíncrona com `await bot.add_cog(...)`. Para listeners de eventos, use
  `@commands.Cog.listener()`. Se quiser agrupar app commands, considere `commands.GroupCog`, que
  expõe `cog.app_command` como grupo.

- **Exemplo de Código (Alternativa Otimizada)**:

  **Antes (simplificado de `main.py`)**:

  ```python
  # src/main.py (antes)
  import discord
  from discord.ext import commands # Nova importação
  # ... outras importações ...

  class MyBot(commands.Bot):
      def __init__(self):
          super().__init__(command_prefix='!', intents=discord.Intents.default())
          # ... setup de intents ...

      async def on_ready(self):
          print(f'{self.user} has connected to Discord!')
          # ... lógica on_ready ...

      async def on_message(self, message):
          # ... lógica on_message ...
          pass # Chamar processamento em Cog

  # ... slash commands como @tree.command ...
  ```

  **Depois (estrutura proposta com Cogs)**:

  Crie um novo diretório `src/cogs`.

  **`src/cogs/chat.py`**:

  ```python
  # src/cogs/chat.py
  from typing import Optional

  import discord
  from discord import app_commands
  from discord.ext import commands

  from src.completion import generate_completion_response, process_response
  from src.database import DatabaseService, db_service
  from src.moderation import moderate_message, send_moderation_blocked_message, send_moderation_flagged_message
  from src.constants import ACTIVATE_THREAD_PREFIX, AVAILABLE_MODELS, DEFAULT_MODEL
  from src.base import ThreadConfig
  from src.utils import logger, should_block

  class ChatCog(commands.Cog):
      def __init__(self, bot: commands.Bot, db_service_instance: DatabaseService) -> None:
          self.bot = bot
          self.db_service = db_service_instance # Injeção de dependência

      @app_commands.command(name="chat", description="Create a new thread for conversation")
      @app_commands.checks.has_permissions(send_messages=True)
      # ... outras permissões ...
      @app_commands.describe(message="The first prompt to start the chat with")
      # ... outros argumentos ...
      async def chat_command(
          self,
          interaction: discord.Interaction,
          message: str,
          model: AVAILABLE_MODELS = DEFAULT_MODEL,
          temperature: Optional[float] = 1.0,
          max_tokens: Optional[int] = 512,
      ) -> None:
          # Lógica do comando /chat move-se para cá
          # Utiliza self.db_service para interagir com o DB
          logger.info("Chat command invoked by %s", interaction.user)
          # ... validações, moderação, criação de thread, etc. ...

          thread_config = ThreadConfig(model=model, max_tokens=max_tokens, temperature=temperature)
          await self.db_service.save_thread( # Acessa db_service injetado
              thread_id=thread.id,
              guild_id=interaction.guild_id,
              user_id=interaction.user.id,
              config=thread_config
          )
          # ... restante da lógica do comando ...

      @commands.Cog.listener()
      async def on_message(self, message: discord.Message) -> None:
          # Use listeners para eventos específicos antes espalhados em main.py
          pass

  async def setup(bot: commands.Bot) -> None:
      # db_service global ainda precisaria ser passado, ou usar uma abordagem de DI mais robusta
      await bot.add_cog(ChatCog(bot, db_service))
  ```

  **`src/main.py` (depois)**:

  ```python
  # src/main.py (depois)
  import asyncio
  import logging
  import discord
  from discord.ext import commands # Nova importação

  from src.constants import DISCORD_BOT_TOKEN, BOT_INVITE_URL, ALLOWED_SERVER_IDS
  from src.database import db_service # Ainda como global, será abordado na próxima seção
  from src.cogs.chat import ChatCog # Importa o novo Cog
  from src.profiling import log_metrics_summary_sync # Importa a função sync para atexit
  import atexit # Importa atexit

  logger = logging.getLogger(__name__)
  logging.basicConfig(...) # ... configuração de logging ...

  class SherlockRamosBot(commands.Bot):
      def __init__(self):
          intents = discord.Intents.default()
          intents.message_content = True # Certifique-se de que isso está habilitado no portal do desenvolvedor
          super().__init__(command_prefix='!', intents=intents) # Prefixo de comando pode ser inútil se usar apenas slash commands
          self.db_service = db_service # Passa o serviço de DB para o bot, para que os Cogs possam acessá-lo

      async def setup_hook(self):
          # Carrega Cogs aqui
          await self.add_cog(ChatCog(self, self.db_service)) # Instancia e adiciona o Cog
          # ... outros Cogs ...

          # Sincroniza comandos globais e por guild
          for guild_id in ALLOWED_SERVER_IDS:
              guild = discord.Object(id=guild_id)
              self.tree.copy_global_to(guild=guild)
              await self.tree.sync(guild=guild)
              logger.info(f"Synced commands to guild {guild_id}")
          await self.tree.sync()
          logger.info("Global command sync complete")


      async def on_ready(self):
          logger.info(f"We have logged in as {self.user}. Invite URL: {BOT_INVITE_URL}")
          # ... lógica de on_ready restante ...

      async def on_message(self, message: discord.Message):
          if message.author == self.user:
              return
          # Se for uma thread de conversa do bot ou menção, encaminha
          # A lógica de on_message se torna um 'dispatcher'
          # Cogs podem ter listeners para eventos específicos

          # Exemplo simplificado:
          if self.user in message.mentions:
              # Chame uma função no Cog que lida com menções
              pass
          elif isinstance(message.channel, discord.Thread) and message.channel.owner_id == self.user.id:
              # Chame uma função no Cog que lida com mensagens em threads do bot
              pass

          # Permite que os comandos base do bot (se houver) ainda funcionem
          await self.process_commands(message)

  def run_bot() -> None:
      bot = SherlockRamosBot()
      bot.run(DISCORD_BOT_TOKEN)

  if __name__ == "__main__":
      atexit.register(log_metrics_summary_sync)
      run_bot()
  ```

- **Benefícios**: Aumenta drasticamente a manutenibilidade e testabilidade. Permite que
  desenvolvedores trabalhem em funcionalidades isoladas sem afetar outras partes do bot.

---

### 2. Prioridade Alta (Important improvements)

#### 2.1. Injeção de Dependência para Serviços

- **Problema**: Serviços como `db_service` e `rag_service` são importados e usados diretamente como
  singletons globais em vários módulos (ex: `main.py`, `completion.py`).
- **Por que Viola Boas Práticas**:
  - **Violação do DIP (Princípio da Inversão de Dependência)**: Módulos de alto nível (como
    `main.py`) dependem diretamente de implementações de baixo nível (singletons globais).
  - **Dificulta a Testabilidade**: Para testar um módulo que usa um singleton global, é necessário
    mockar o singleton, o que pode ser complicado e propenso a erros.
  - **Flexibilidade Reduzida**: Trocar a implementação de um serviço (ex: mudar de `chromadb` para
    outro DB vetorial) exigiria modificar múltiplos arquivos.
- **Como Otimizar**: Utilizar Injeção de Dependência (DI). Em vez de importar o singleton global, os
  serviços são "injetados" (passados como argumentos) para as classes ou funções que precisam deles.

- **Exemplo de Código (Alternativa Otimizada)**:

  **Antes (em `completion.py`)**:

  ```python
  # src/completion.py (antes, simplificado)
  from src.database import db_service # Importação direta
  from src.rag_service import rag_service # Importação direta
  # ...

  async def generate_completion_response(...):
      # ...
      await db_service.log_message(...) # Uso direto
      relevant_docs = rag_service.query(...) # Uso direto
      # ...
  ```

  **Depois (estrutura proposta)**:

  ```python
  # src/completion.py (depois, simplificado)
  # Remove importações diretas de singletons de serviço
  # from src.database import db_service # REMOVER
  # from src.rag_service import rag_service # REMOVER

  from src.base import DatabaseService, RAGService # Importar interfaces/classes dos serviços

  class CompletionService:
      def __init__(self, db_service: DatabaseService, rag_service: RAGService):
          self.db_service = db_service
          self.rag_service = rag_service

      async def generate_completion_response(
          self, messages: List[Message], user: discord.Member, thread_config: ThreadConfig
      ) -> CompletionResponse:
          # ...
          await self.db_service.log_message(...) # Usa o serviço injetado
          relevant_docs = self.rag_service.query(...) # Usa o serviço injetado
          # ...

  # Onde este serviço for instanciado (ex: no setup_hook do bot ou no Cog):
  # completion_service = CompletionService(db_service_instance, rag_service_instance)
  ```

- **Benefícios**: Melhora a testabilidade (pode-se injetar mocks), aumenta a flexibilidade para
  trocar implementações e reduz o acoplamento entre módulos.

#### 2.2. Automação da Garantia de Qualidade de Código via CI/CD

- **Problema**: O projeto tem `ruff` (linting/formatação) e `mypy` (verificação de tipos)
  configurados em `pyproject.toml`, o que é excelente. No entanto, não há um processo automatizado
  para garantir que essas ferramentas sejam executadas em cada Pull Request ou commit. Isso permite
  que código que não segue as melhores práticas ou tem erros de tipo seja mesclado.
- **Por que Viola Boas Práticas**: Introduz technical debt, reduz a consistência do código, pode
  introduzir bugs e dificulta a revisão de código manual.
- **Como Otimizar**: Implementar um pipeline de CI/CD (Integração Contínua/Entrega Contínua) usando
  GitHub Actions (dado que o repositório está no GitHub).

- **Exemplo de Código (GitHub Actions Workflow - `.github/workflows/ci.yml`)**:

  ```yaml
  # .github/workflows/ci.yml
  name: CI/CD SherlockRamosBot

  on:
    push:
      branches:
        - main
    pull_request:
      branches:
        - main

  jobs:
    build:
      runs-on: ubuntu-latest

      steps:
        - name: Checkout code
          uses: actions/checkout@v4

        - name: Set up Python
          uses: actions/setup-python@v5
          with:
            python-version: '3.13' # Alinhar com a versão do projeto

        - name: Install uv
          run: |
            pip install uv

        - name: Install dependencies
          run: uv sync --dev

        - name: Run Ruff (Linting and Formatting)
          run: uv run ruff check .
          # Opcional: uv run ruff format . --check para verificar formatação

        - name: Run Mypy (Type Checking)
          run: uv run mypy src

        - name: Run Pytest (Unit Tests)
          run: uv run pytest
  ```

- **Benefícios**: Garante a consistência do código, captura erros precocemente, melhora a qualidade
  geral do software e acelera o processo de revisão de código.

---

### 3. Prioridade Média (Recommended changes)

#### 3.1. Modularização do `CompletionService`

- **Problema**: A função `generate_completion_response` em `src/completion.py` ainda concentra
  várias responsabilidades: verificação de cache, consulta ao serviço RAG e chamada à API da LLM.
- **Por que Viola Boas Práticas**: Viola o SRP, tornando a função mais complexa do que o necessário
  e dificultando a alteração de uma parte da lógica sem impactar as outras.
- **Como Otimizar**: Decompor `generate_completion_response` em funções ou métodos menores e mais
  focados.

- **Exemplo de Código (Alternativa Otimizada)**:

  **Antes (simplificado de `completion.py`)**:

  ```python
  # src/completion.py (antes, simplificado)
  async def generate_completion_response(...):
      cached_response = response_cache.get(...)
      if cached_response:
          return cached_response

      relevant_docs = rag_service.query(...)
      # ... construir prompt ...
      llm_response = await client.chat.completions.create(...)

      response_cache.set(...)
      return CompletionResponse(...)
  ```

  **Depois (estrutura proposta)**:

  ```python
  # src/completion.py (depois, simplificado)
  class CompletionService:
      def __init__(self, cache_service, rag_service, llm_client):
          self.cache = cache_service
          self.rag = rag_service
          self.llm_client = llm_client

      async def _get_cached_response(self, messages, model, temperature, max_tokens):
          return self.cache.get(messages, model, temperature, max_tokens)

      async def _get_rag_context(self, query_text):
          return self.rag.query(query_text)

      async def _call_llm_api(self, messages_with_context, model, temperature, max_tokens):
          # ... lógica de chamada da API LLM ...
          pass

      async def generate_completion_response(
          self, messages: List[Message], user: discord.Member, thread_config: ThreadConfig
      ) -> CompletionResponse:
          cached_response = await self._get_cached_response(
              messages, thread_config.model, thread_config.temperature, thread_config.max_tokens
          )
          if cached_response:
              return cached_response

          query_text = messages[-1].text # Exemplo: última mensagem para consulta RAG
          relevant_docs = await self._get_rag_context(query_text)

          # ... construir prompt com contexto RAG ...
          llm_response = await self._call_llm_api(
              messages_with_context, thread_config.model, thread_config.temperature, thread_config.max_tokens
          )

          self.cache.set(
              messages, thread_config.model, llm_response,
              thread_config.temperature, thread_config.max_tokens
          )
          return CompletionResponse(...)
  ```

- **Benefícios**: Aumenta a clareza do código, facilita a manutenção, permite testar cada etapa
  (cache, RAG, LLM) isoladamente e torna a função `generate_completion_response` mais enxuta e
  legível.

#### 3.2. Logging das Estatísticas do Cache

- **Problema**: O módulo `src/cache.py` inclui um método `log_stats()` que fornece métricas valiosas
  sobre a eficácia do cache (hits, misses, taxa de acertos). No entanto, este método não é chamado
  em nenhum lugar do código.
- **Por que Viola Boas Práticas**: Ignora uma ferramenta de observabilidade já implementada, o que
  dificulta o monitoramento do desempenho do cache e a identificação de problemas (ex: baixa taxa de
  acertos, cache expirando rapidamente).
- **Como Otimizar**: Registrar as estatísticas do cache periodicamente (se possível) ou, no mínimo,
  no encerramento da aplicação.

- **Exemplo de Código (Alternativa Otimizada)**:

  Dado que já implementamos o `atexit.register(log_metrics_summary_sync)` em `src/main.py`, podemos
  estender isso para incluir as estatísticas do cache.

  **Em `src/profiling.py` (adicionar `cache_stats` ao summary)**:

  ```python
  # src/profiling.py
  # ...
  from src.cache import response_cache # Importar o cache global

  # ... na função log_metrics_summary_sync() ...
  def log_metrics_summary_sync() -> None:
      # ... (código existente para métricas de performance) ...

      # Adicionar estatísticas do cache
      cache_s = response_cache.stats
      print(
          f"📦 Cache Stats: size={cache_s['size']}/{cache_s['max_size']}, "
          f"hits={cache_s['hits']}, misses={cache_s['misses']}, "
          f"hit_rate={cache_s['hit_rate']}"
      )
  ```

- **Benefícios**: Fornece insights sobre a eficácia do cache, permitindo ajustes nos parâmetros
  (`max_size`, `ttl_seconds`) para otimizar o uso e reduzir chamadas desnecessárias à LLM e ao
  serviço RAG.

---

### 4. Prioridade Baixa (Nice-to-have enhancements)

#### 4.1. Hash Mais Rápido para Chaves de Cache

- **Problema**: A função `_hash_key` em `src/cache.py` utiliza `hashlib.sha256` para gerar chaves de
  cache. Embora seguro, SHA-256 é um algoritmo criptográfico projetado para segurança, não para
  velocidade.
- **Por que Viola Boas Práticas**: Uso de um algoritmo mais pesado do que o necessário para uma
  tarefa não-criptográfica, podendo introduzir uma pequena latência.
- **Como Otimizar**: Para hashing de chaves de cache onde a segurança criptográfica não é
  primordial, um algoritmo de hashing não-criptográfico mais rápido (como `xxhash` ou o `hash()`
  embutido do Python, embora com ressalvas sobre consistência entre execuções) seria mais eficiente.

- **Exemplo de Código (Alternativa Otimizada)**:

  ```python
  # src/cache.py (simplificado)
  import hashlib
  # import xxhash # Se for instalar uma biblioteca externa

  class LRUCache:
      # ...
      def _hash_key(...):
          # ...
          content = f"{model}:{temperature}:{max_tokens}:{convo_str}"
          content = f"{model}:{temperature}:{max_tokens}:{convo_str}"
          # return xxhash.xxh64(content.encode()).hexdigest() # Exemplo com xxhash (rápido, não criptográfico)
          return hashlib.sha256(content.encode()).hexdigest() # SHA-256 (seguro, padrão)
          # Nota: Evite MD5/SHA1 a menos que compatibilidade legada seja estritamente necessária.

  ```

- **Benefícios**: Ganhos marginais de desempenho na geração de chaves de cache, especialmente para
  sistemas com altíssima taxa de requisições.

---

Esta revisão visa guiar o desenvolvimento futuro do SherlockRamosBot, priorizando a estabilidade,
manutenibilidade e escalabilidade do projeto.
