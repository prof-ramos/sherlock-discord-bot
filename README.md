# SherlockRamosBot

[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![discord.py](https://img.shields.io/badge/discord-py-blue.svg)](https://github.com/Rapptz/discord.py)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Um chatbot sofisticado para Discord, projetado para auxiliar estudantes de direito e concurseiros no
Brasil, tudo com o poder de LLMs via OpenRouter.

## 📜 Descrição

SherlockRamosBot é um assistente de IA para Discord, focado em fornecer respostas rápidas e precisas
sobre uma vasta gama de tópicos jurídicos. Ele foi criado para resolver a necessidade de acesso
rápido a informações legais complexas e materiais de estudo para estudantes e profissionais que se
preparam para concursos públicos no Brasil.

### ✨ Principais Características

- **Consultas em Linguagem Natural**: Faça perguntas jurídicas complexas em português e receba
  respostas claras e contextualizadas.
- **Memória Persistente (Neon/PostgreSQL)**: Armazena histórico de conversas e analytics em um banco
  de dados PostgreSQL serverless (Neon), garantindo continuidade e análise de dados.
- **Geração Aumentada por Recuperação (RAG)**: Utiliza o `chromadb` para consultar uma base de
  conhecimento especializada, garantindo respostas mais precisas e fundamentadas.
- **Otimização de Custos (Prompt Caching)**: Suporte automático a cache de prompt para modelos
  Anthropic e Google Gemini, reduzindo custos de inferência.
- **Suporte a Múltiplos LLMs**: Integrado com a API da OpenRouter, permitindo flexibilidade na
  escolha do modelo de linguagem.
- **Personalidade Customizável**: O comportamento e o tom do bot podem ser facilmente ajustados
  através de um arquivo de configuração (`config.yaml`).
- **Moderação Integrada**: Ferramentas para monitorar e moderar as interações, garantindo um
  ambiente seguro.

## 📚 Tabela de Conteúdos

1. [Descrição](#-descrição)
2. [Instalação](#-instalação)
3. [Uso Rápido](#️-uso-rápido)
4. [Configuração](#️-configuração)
5. [Desenvolvimento](#-desenvolvimento)
6. [Testes](#testes)
7. [Contribuição](#-contribuição)
8. [Licença](#-licença)
9. [Autores e Agradecimentos](#-autores-e-agradecimentos)
10. [Suporte](#-suporte)

## 🚀 Instalação

Siga os passos abaixo para configurar e executar o SherlockRamosBot em seu próprio servidor.

### Pré-requisitos

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (um instalador e resolvedor de pacotes Python rápido)

### Passos de Instalação

1. **Clone o repositório:**

   ```bash
   git clone https://github.com/prof-ramos/sherlock-discord-bot.git
   cd sherlock-discord-bot
   ```

2. **Instale as dependências:** Use `uv` para sincronizar o ambiente virtual e instalar todos os
   pacotes necessários.

   ```bash
   uv sync
   ```

3. **Configure as variáveis de ambiente:** Copie o arquivo de exemplo e preencha com suas próprias
   chaves de API e IDs.

   ```bash
   cp .env.example .env
   ```

   Edite o arquivo `.env` com suas credenciais do Discord e da OpenRouter.

## ⚡️ Uso Rápido

Após a instalação e configuração, você pode iniciar o bot.

1. **Execute o bot:**

   ```bash
   uv run sherlock-bot
   ```

   Alternativa:

   ```bash
   uv run python -m src.main
   ```

   Se tudo estiver configurado corretamente, o bot ficará online no seu servidor do Discord.

2. **Interaja com o Bot:** Para fazer uma pergunta, simplesmente mencione o bot no início da sua
   mensagem em qualquer canal que ele tenha permissão para ler.

   **Exemplo de Interação:**

   > **Usuário:** @SherlockRamosBot qual a diferença entre dolo e culpa no direito penal?
   >
   > **SherlockRamosBot:** A diferença fundamental entre dolo e culpa reside na intenção do agente.
   > No dolo, o agente tem a intenção de produzir o resultado... Na culpa, o agente não deseja o
   > resultado, mas o causa por imprudência, negligência ou imperícia...

## ⚙️ Configuração

A configuração principal do bot é feita através de variáveis de ambiente e um arquivo de
configuração YAML.

### Variáveis de Ambiente

O arquivo `.env` armazena as chaves e configurações sensíveis. Consulte `.env.example` para ver
todas as opções disponíveis.

- `OPENROUTER_API_KEY`: Sua chave de API da OpenRouter.
- `DISCORD_BOT_TOKEN`: O token do seu bot do Discord.
- `DISCORD_CLIENT_ID`: O ID do cliente do seu aplicativo Discord.
- `ALLOWED_SERVER_IDS`: IDs dos servidores do Discord onde o bot pode operar.
- `DEFAULT_MODEL`: O modelo de LLM padrão a ser usado (ex: `openai/gpt-3.5-turbo`).
- `DATABASE_URL`: String de conexão para o banco de dados PostgreSQL (Neon).

### Personalidade do Bot

O arquivo `src/config.yaml` controla a persona do bot, incluindo o prompt do sistema e exemplos de
poucas interações (few-shot examples) que guiam seu tom e estilo de resposta. Você pode editar este
arquivo para ajustar o comportamento do bot.

## 🧱 Estrutura do Código (Cogs)

- `src/main.py`: Entry point com `commands.Bot`, `setup_hook` para carregar cogs e sincronizar
  comandos.
- `src/cogs/chat.py`: Slash command `/chat`, handler de menções e mensagens em threads.
- `src/completion.py`: Integração com OpenRouter e montagem de respostas.
- `src/database.py`: Persistencia de threads, mensagens e analytics.

Para adicionar novos comandos, crie um novo Cog em `src/cogs/` e carregue-o no `setup_hook`. Mais
detalhes em `docs/architecture.md` e `docs/commands.md`.

## 🔐 Permissões e Segurança

- Comandos de configuracao devem ser restritos a administradores (ex: `administrator=True`).
- O bot aplica allowlist de servidores via `ALLOWED_SERVER_IDS`.

## 🗄️ Configuração do Banco de Dados (Neon)

O projeto utiliza **Neon** (PostgreSQL Serverless) para armazenar estados, histórico e métricas.

1. Crie um projeto no [Neon Console](https://console.neon.tech).
2. Obtenha a string de conexão (Pooled connection é recomendada para serverless/lambdas, mas direct
   work para containers persistentes).
3. Adicione ao seu `.env`:

```env
DATABASE_URL=postgres://user:password@host/neondb?sslmode=require
```

O bot gerenciará as conexões automaticamente usando `asyncpg`.

## 📚 Configuração da Base de Conhecimento (RAG)

O bot utiliza o **próprio banco de dados Neon** com a extensão `pgvector` para armazenar a base de
conhecimento (RAG), unificando toda a persistência.

### 1. Pré-requisitos

Certifique-se de que a variável `OPENAI_API_KEY` está definida no `.env` para a geração de
embeddings (por padrão usa `text-embedding-3-small`).

```env
OPENAI_API_KEY=sk-...
```

### 2. Formato dos Documentos

Coloque seus documentos (artigos, leis, doutrinas) na pasta `data/`. Formatos suportados: `.txt`,
`.md`, `.pdf`.

### 3. Ingestão de Dados

Para processar e indexar os documentos no Neon:

```bash
uv run python scripts/ingest_docs.py arquivo.pdf
```

Este script irá:

1. Ler o arquivo
2. Gerar embeddings via OpenAI
3. Salvar os vetores na tabela `documents` do seu banco Neon.

### 4. Verificação

Você pode verificar se os documentos foram inseridos conectando no banco e rodando:

```sql
SELECT count(*) FROM documents;
```

## 👨‍💻 Desenvolvimento

O ambiente de desenvolvimento usa as mesmas etapas da instalação. Certifique-se de instalar as
dependências de desenvolvimento.

### Configurando o Ambiente de Desenvolvimento

Para instalar as ferramentas de desenvolvimento (como `ruff`, `mypy` e `pytest`), use:

```bash
uv sync --dev
```

### Verificação de Qualidade (Ordem Recomendada)

1. **Linting e Formatação (Ruff):**

   ```bash
   uv run ruff check . --fix
   uv run ruff format .
   ```

2. **Verificação de Tipos (Mypy):**

   ```bash
   uv run mypy src
   ```

3. **Testes Automatizados (Pytest):**

   ```bash
   uv run pytest -v
   ```

   Exemplo de saída esperada:

   ```text
   tests/test_basic.py::test_example PASSED [100%]
   ```

## 🤝 Contribuição

Contribuições são muito bem-vindas! Se você deseja melhorar o SherlockRamosBot, siga estes passos:

1. Faça um Fork do repositório.
2. Crie uma nova branch (`git checkout -b feature/sua-feature`).
3. Faça suas alterações e commit (`git commit -m 'Adiciona nova feature'`).
4. Execute os testes e as ferramentas de lint para garantir a qualidade do código.
5. Envie um Pull Request.

Por favor, siga as convenções de código e estilo já presentes no projeto.

## 📄 Licença

Este projeto está licenciado sob a Licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais
detalhes.

Copyright (c) 2024-2026 Gabriel Ramos.

## 🙏 Autores e Agradecimentos

- **Autor Principal**: [Gabriel Ramos](https://github.com/prof-ramos)

Agradecimentos a toda a comunidade de código aberto e aos criadores das bibliotecas que tornaram
este projeto possível.

## 💬 Suporte

Se encontrar algum bug ou tiver alguma sugestão, por favor, abra uma **issue** no
[rastreador de issues do GitHub](https://github.com/prof-ramos/sherlock-discord-bot/issues).
