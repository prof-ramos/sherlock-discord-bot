# SherlockRamosBot 🕵️‍♂️⚖️

![Python](https://img.shields.io/badge/Python-3.13%2B-blue?logo=python&logoColor=white)
![Discord](https://img.shields.io/badge/Discord-Bot-5865F2?logo=discord&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Code Style](https://img.shields.io/badge/code%20style-ruff-000000.svg)

**SherlockRamosBot** é um chatbot especializado para Discord, desenvolvido para auxiliar estudantes de Direito ("concurseiros") e profissionais jurídicos brasileiros. Utilizando Modelos de Linguagem de Grande Escala (LLMs) via OpenRouter e Geração Aumentada por Recuperação (RAG), ele oferece orientações jurídicas precisas e contextualizadas, além de capacidades de conversação casual.

## 📖 Sumário

- [Funcionalidades](#-funcionalidades)
- [Arquitetura](#-arquitetura)
- [Pré-requisitos](#-pré-requisitos)
- [Instalação](#-instalação)
- [Configuração](#-configuração)
- [Uso](#-uso)
- [Desenvolvimento](#-desenvolvimento)
- [Testes](#-testes)
- [Contribuição](#-contribuição)
- [Licença](#-licença)

## 🚀 Funcionalidades

- **Modos de Interação Duais**:
  - **Modo Geral**: Conversa casual e amigável para tópicos do dia a dia.
  - **Modo Jurídico**: Ativa-se automaticamente ao detectar contextos legais. Oferece respostas detalhadas e estruturadas com citações (Artigos, Leis, Súmulas).
- **RAG (Geração Aumentada por Recuperação)**: Utiliza ChromaDB para recuperar e referenciar documentos jurídicos brasileiros relevantes, garantindo precisão e reduzindo alucinações.
- **Conversas baseadas em Threads**: Gerencia o contexto de forma eficiente usando threads do Discord, permitindo discussões organizadas e persistentes.
- **Parâmetros de LLM Customizáveis**: Usuários podem ajustar modelos, temperatura e limites de tokens para consultas específicas via comandos de barra (slash commands).
- **Persistência Robusta**: Armazena histórico de conversas e métricas em um banco de dados Neon (PostgreSQL Serverless).
- **Moderação**: Verificações de segurança integradas para sinalizar ou bloquear conteúdo inapropriado.
- **Function Calling**: Busca automatizada de jurisprudência web através da API Serper.dev quando o LLM detecta necessidade de informações atualizadas.

## 🔧 Function Calling (Tools)

O bot implementa **function calling** para permitir que o LLM acesse automaticamente informações jurídicas atualizadas quando necessário. Existem 3 ferramentas (tools) disponíveis:

### Ferramentas Disponíveis

1. **`buscar_jurisprudencia_web`**
   - **Descrição**: Busca jurisprudência e legislação atualizada em sites oficiais brasileiros (STF, STJ, Planalto)
   - **Quando usar**: Quando o LLM precisa de informações RECENTES (2024-2025) ou casos específicos não disponíveis na base local
   - **Parâmetros**:
     - `query` (obrigatório): Consulta jurídica em português
     - `tribunal` (opcional): Filtrar por "stf", "stj", "planalto" ou "todos" (padrão)

2. **`extrair_conteudo_url`**
   - **Descrição**: Extrai texto completo de uma URL de decisão judicial ou legislação
   - **Quando usar**: Quando o usuário fornece um link específico para análise
   - **Parâmetros**:
     - `url` (obrigatório): URL completa do documento

3. **`consultar_base_local`**
   - **Descrição**: Consulta a base de conhecimento local (RAG) com legislação e jurisprudência já indexada
   - **Quando usar**: Para informações gerais e consolidadas
   - **Parâmetros**:
     - `query` (obrigatório): Consulta jurídica em português
     - `num_docs` (opcional): Número de documentos a retornar (1-5, padrão: 3)

### Configuração

Para habilitar a busca web, você precisa de uma chave da API Serper.dev:

1. **Obter chave**: Cadastre-se em [https://serper.dev/](https://serper.dev/)
   - Plano gratuito: 2.500 queries/mês
2. **Configurar**: Adicione ao seu `.env`:
   ```ini
   SERPER_API_KEY=sua_chave_serper_aqui
   ```

**Nota**: Se a `SERPER_API_KEY` não estiver configurada, o bot continuará funcionando normalmente, mas as buscas web não estarão disponíveis (o LLM usará apenas a base local e conhecimento geral).

### Como Funciona

Quando você faz uma pergunta que requer informações atualizadas, o LLM automaticamente:
1. Detecta a necessidade de usar uma ferramenta
2. Executa a busca apropriada (web, URL ou base local)
3. Recebe os resultados
4. Gera uma resposta integrada com as informações obtidas

**Exemplo**:
```
Usuário: Quais foram as decisões do STF sobre LGPD em 2025?
Bot: 🔧 [busca automaticamente via Serper.dev]
      ✅ [responde com jurisprudência recente]
```

## 🏗 Arquitetura

O bot foi construído com uma stack Python moderna focada em performance e manutenibilidade:

- **Core**: `discord.py` para interação com o Discord.
- **Interface de LLM**: OpenRouter API (acesso a Claude, GPT-4, Gemini, etc.).
- **Banco de Dados**: Neon (Postgres) para dados estruturados (threads, mensagens, analytics).
- **Busca Vetorial**: ChromaDB para busca semântica em textos legais.
- **Gerenciamento de Pacotes**: `uv` para gerenciamento de dependências extremamente rápido.

## 📋 Pré-requisitos

- **Python 3.9+** (O projeto gerencia a versão do Python via `uv`)
- **uv**: Um instalador e resolvedor de pacotes Python ultra-rápido. [Instalar uv](https://github.com/astral-sh/uv).
- **Banco de Dados PostgreSQL**: Recomenda-se o Neon, mas qualquer instância Postgres funciona.
- **Token de Bot do Discord**: Obtido no [Portal de Desenvolvedores do Discord](https://discord.com/developers/applications).
- **Chave de API do OpenRouter**: Para acesso aos modelos de linguagem.

## 🛠 Instalação

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/gabrielramos/sherlock-discord-bot.git
    cd sherlock-discord-bot
    ```

2.  **Instale as dependências:**
    O uso do `uv` garante um ambiente reproduzível.
    ```bash
    uv sync
    ```

3.  **Configure o banco de dados:**
    Inicialize o esquema (certifique-se de que seu `.env` esteja configurado antes).
    ```bash
    uv run python scripts/init_db.py
    ```

## ⚙️ Configuração

Crie um arquivo `.env` na raiz do projeto. Você pode usar o `.env.example` como modelo:

```ini
# Core
DISCORD_TOKEN=seu_token_do_bot
DISCORD_GUILD_ID=seu_id_da_guilda (opcional, para sincronização rápida de comandos)

# AI / LLM
OPENROUTER_API_KEY=sua_chave_openrouter
DEFAULT_MODEL=google/gemini-2.0-flash-exp

# Banco de Dados
DATABASE_URL=postgres://usuario:senha@host/dbname?sslmode=require

# RAG / Vector DB
CHROMA_PERSIST_DIRECTORY=src/data/chroma_db

# Function Calling - Web Search (Opcional)
SERPER_API_KEY=sua_chave_serper  # Obter em https://serper.dev/
```

A persona do bot e as instruções de sistema são configuradas em `src/config.yaml`.

## 🎮 Uso

### Executando o Bot
Para iniciar o bot em produção:
```bash
uv run sherlock-bot
```
Ou via caminho direto do módulo:
```bash
uv run python -m src.main
```

### Comandos

#### 1. Iniciar uma Thread de Chat
Use o comando `/chat` para iniciar um novo tópico de conversa organizado.
```
/chat message:"Explique o princípio da legalidade" model:"gpt-4" temperature:0.7
```
- **message**: O prompt inicial.
- **model** (opcional): Selecione LLMs específicos.
- **temperature** (opcional): Nível de criatividade (0.0 a 1.0).

#### 2. Menção Direta
Basta mencionar o bot em qualquer canal para uma resposta rápida. O bot criará uma thread se a conversa continuar.
```
@SherlockRamosBot O que é Habeas Corpus?
```

## 💻 Desenvolvimento

### Setup
Certifique-se de que seu ambiente está sincronizado:
```bash
uv sync
```

### Linting & Formatação
Este projeto utiliza `ruff` para linting e formatação.
```bash
# Executa verificações e corrige problemas automáticos
uv run ruff check . --fix

# Formata o código
uv run ruff format .
```

### Verificação de Tipos
A verificação estática de tipos é feita pelo `mypy`.
```bash
uv run mypy .
```

## 🧪 Testes

O projeto utiliza `pytest` para testes unitários e de integração.

```bash
# Executa todos os testes
uv run pytest

# Executa com relatório de cobertura
uv run pytest --cov=src
```

## 🤝 Contribuição

Contribuições são bem-vindas! Siga estes passos:

1.  Faça um Fork do repositório.
2.  Crie uma branch para sua feature (`git checkout -b feature/minha-feature`).
3.  Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`).
4.  Dê um Push na branch (`git push origin feature/minha-feature`).
5.  Abra um Pull Request.

Certifique-se de que todos os testes passem e o código esteja formatado antes de enviar.

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 👥 Autores & Agradecimentos

- **Gabriel Ramos** - *Trabalho Inicial*

Agradecimentos especiais à comunidade open-source pelas ferramentas que tornam este bot possível: `discord.py`, `langchain`, `chromadb` e `asyncpg`.
