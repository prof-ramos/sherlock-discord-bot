# Manual de Deploy VPS - Sherlock Discord Bot

Guia completo em português para deploy do Sherlock Discord Bot em VPS usando Docker Swarm.

## Índice

- [Visão Geral](#visão-geral)
- [Pré-requisitos](#pré-requisitos)
- [Preparação do Ambiente](#preparação-do-ambiente)
- [Build e Push da Imagem](#build-e-push-da-imagem)
- [Deploy no Swarm](#deploy-no-swarm)
- [Monitoramento e Manutenção](#monitoramento-e-manutenção)
- [Atualização e Rollback](#atualização-e-rollback)
- [Troubleshooting](#troubleshooting)
- [Referência Rápida de Comandos](#referência-rápida-de-comandos)

---

## Visão Geral

### Arquitetura do Deploy

```
┌────────────────────┐
│  Mac M3 (ARM64)    │  ← Máquina de desenvolvimento
│  Desenvolvimento   │
└──────────┬─────────┘
           │
           │ 1. Build multi-arch (ARM64 → AMD64)
           │    ./build-and-push.sh
           ▼
┌────────────────────┐
│  Docker Hub        │  ← Registry de imagens
│  gabrielramosprof/ │
│  sherlock-...      │
└──────────┬─────────┘
           │
           │ 2. Pull da imagem
           ▼
┌────────────────────┐      ┌─────────────────┐
│  VPS Linux         │◄─────┤  Neon Postgres  │
│  (x86_64)          │      │  Database       │
│  Docker Swarm      │      └─────────────────┘
└──────────┬─────────┘
           │
           │ 3. Deploy stack
           │    ./deploy-swarm.sh
           ▼
┌────────────────────┐
│  Bot Rodando       │  ← Com healthcheck e auto-restart
│  Rede: ProfRamosNet│
│  Portainer         │
└──────────┬─────────┘
           │
           │ 4. Conexão Discord
           ▼
┌────────────────────┐
│  Discord API       │
└────────────────────┘
```

### Fluxo de Build

**Mac ARM64 → Docker Hub → VPS x86_64**

O processo utiliza **Docker Buildx** para compilar uma imagem compatível com a arquitetura x86_64 do servidor a partir de um Mac com chip ARM64 (M1/M2/M3).

### Infraestrutura Existente

- **Portainer**: Interface web para gerenciar Docker
- **Traefik**: Reverse proxy (não usado pelo bot)
- **Rede ProfRamosNet**: Rede overlay compartilhada (external)

---

## Pré-requisitos

### No Mac (Desenvolvimento)

✅ **Docker Desktop** instalado e rodando
✅ **Conta no Docker Hub** configurada
✅ **Acesso ao repositório** do projeto
✅ **uv** instalado (gerenciador de pacotes Python)

### Na VPS (Produção)

✅ **Sistema**: Linux 24.04.5 LTS (Kernel 5.10, Debian)
✅ **Docker** versão 20.10+ instalado
✅ **Docker Swarm** inicializado
✅ **Rede ProfRamosNet** criada
✅ **Acesso SSH** configurado
✅ **Portainer** rodando (opcional, mas recomendado)

### Serviços Externos

✅ **Banco de Dados**: Neon PostgreSQL ativo e inicializado
✅ **Discord Bot**: Aplicação criada no [Discord Developer Portal](https://discord.com/developers/applications)
✅ **OpenRouter API**: Chave obtida em [OpenRouter](https://openrouter.ai/keys)
✅ **OpenAI API**: Chave para embeddings obtida em [OpenAI](https://platform.openai.com/api-keys)

---

## Preparação do Ambiente

### 1. Configuração Inicial da VPS

```bash
# Conectar via SSH
ssh usuario@ip-da-vps

# Atualizar sistema (recomendado)
sudo apt update && sudo apt upgrade -y

# Verificar Docker instalado
docker --version
# Esperado: Docker version 20.10.x ou superior

# Verificar se Swarm está ativo
docker info | grep Swarm
# Esperado: "Swarm: active"
```

**Se Swarm não estiver ativo:**

```bash
# Inicializar Docker Swarm
docker swarm init

# Salvar o token de join (caso queira adicionar workers depois)
docker swarm join-token worker
```

### 2. Criar Rede Externa (se não existir)

```bash
# Verificar se rede existe
docker network ls | grep ProfRamosNet

# Se não existir, criar
docker network create --driver overlay --attachable ProfRamosNet

# Confirmar criação
docker network inspect ProfRamosNet
```

### 3. Criar Diretório de Deploy

```bash
# Criar pasta para o projeto
mkdir -p ~/sherlock-bot
cd ~/sherlock-bot

# Verificar caminho atual
pwd
# Esperado: /home/usuario/sherlock-bot
```

### 4. Configurar Arquivo .env

**Opção A: Clonar repositório (Recomendado)**

```bash
# Clonar projeto
git clone https://github.com/seu-usuario/sherlock-discord-bot.git .

# Copiar template
cp .env.production.template .env

# Editar com suas credenciais
nano .env
```

**Opção B: Copiar arquivos manualmente**

```bash
# No Mac (sua máquina local)
scp docker-compose.yml usuario@ip-vps:~/sherlock-bot/
scp .env.production.template usuario@ip-vps:~/sherlock-bot/
scp deploy-swarm.sh usuario@ip-vps:~/sherlock-bot/

# Na VPS
cd ~/sherlock-bot
cp .env.production.template .env
nano .env
```

### 5. Preencher Variáveis de Ambiente

Edite o arquivo `.env` com suas credenciais reais:

```bash
nano .env
```

**Variáveis OBRIGATÓRIAS:**

```bash
# ⚠️ ATENÇÃO: EXEMPLOS ABAIXO - SUBSTITUA COM SEUS VALORES REAIS
# NÃO use os valores de exemplo, eles não funcionarão!

# Discord Bot
DISCORD_BOT_TOKEN=your-discord-bot-token-here
DISCORD_CLIENT_ID=your-discord-client-id-here
ALLOWED_SERVER_IDS=your-server-id-here

# OpenRouter (LLM)
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-api-key-here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# OpenAI (Embeddings para RAG)
OPENAI_API_KEY=sk-proj-your-openai-api-key-here

# Banco de Dados Neon
DATABASE_URL=postgresql://user:password@host.neon.tech/dbname?sslmode=require

# Modelo Padrão
DEFAULT_MODEL=xiaomi/mimo-v2-flash:free
```

**Variáveis OPCIONAIS:**

```bash
# Neon API (para gerenciamento de branches)
NEON_PROJECT_ID=your-neon-project-id-here
NEON_API_KEY=napi_your-neon-api-key-here

# Canal de moderação (formato: server_id:channel_id)
SERVER_TO_MODERATION_CHANNEL=server-id:channel-id
```

**Salvar e sair**: `Ctrl+O` → `Enter` → `Ctrl+X`

### 6. Inicializar Banco de Dados

⚠️ **IMPORTANTE**: Este passo deve ser executado ANTES do primeiro deploy.

**Opção A: Executar no Mac (Desenvolvimento)**

```bash
# No Mac, no diretório do projeto
cd /caminho/para/sherlock-discord-bot

# Criar .env local com DATABASE_URL da VPS
nano .env
# Adicionar: DATABASE_URL=postgresql://...

# Inicializar banco
uv run python scripts/init_db.py

# Verificar inicialização
uv run python scripts/verify_db.py
```

**Opção B: Executar na VPS**

```bash
# Na VPS, instalar uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# Clonar projeto (se ainda não fez)
git clone https://github.com/seu-usuario/sherlock-discord-bot.git ~/sherlock-bot-temp
cd ~/sherlock-bot-temp

# Copiar .env da pasta de deploy
cp ~/sherlock-bot/.env .

# Inicializar banco
uv run python scripts/init_db.py

# Verificar
uv run python scripts/verify_db.py

# Limpar
cd ~ && rm -rf ~/sherlock-bot-temp
```

**Saída esperada:**

```
✅ Connection established.
🏗️ Applying schema...
✅ Schema applied successfully
✅ Found table: threads
✅ Found table: messages
✅ Found table: analytics
✅ Found table: documents
```

---

## Build e Push da Imagem

Este passo é executado no **Mac** (máquina de desenvolvimento).

### 1. Preparar Build Multi-Arquitetura

```bash
# No Mac, no diretório do projeto
cd /caminho/para/sherlock-discord-bot

# Tornar scripts executáveis (apenas primeira vez)
chmod +x build-and-push.sh deploy-swarm.sh logs.sh rollback-swarm.sh health-check.sh

# Verificar Docker Desktop rodando
docker ps
```

### 2. Login no Docker Hub

```bash
# Fazer login (uma vez)
docker login

# Inserir:
# Username: gabrielramosprof
# Password: [seu-token-ou-senha]
```

### 3. Executar Build

```bash
# Build e push com tag 'latest'
./build-and-push.sh

# Ou com tag de versão específica
./build-and-push.sh v1.0.0
```

**O que o script faz:**

1. ✅ Verifica se `docker buildx` está disponível
2. ✅ Cria/usa builder `sherlock-builder` para multi-arch
3. ✅ Autentica no Docker Hub
4. ✅ Compila imagem para `linux/amd64` (arquitetura da VPS)
5. ✅ Faz push para `gabrielramosprof/sherlock-discord-bot:latest`

**Tempo estimado:**
- Primeiro build: 5-15 minutos
- Builds subsequentes: 2-5 minutos (usa cache)

**Saída esperada:**

```
======================================
🐳 Docker Multi-Arch Build & Push
======================================
Image:    gabrielramosprof/sherlock-discord-bot
Tag:      latest
Platform: linux/amd64
======================================

[1/5] Checking docker buildx availability...
✅ docker buildx available

[2/5] Setting up buildx builder...
✅ Using existing builder: sherlock-builder

[3/5] Docker Hub authentication...
✅ Already logged in to Docker Hub

[4/5] Building image for linux/amd64...
...
✅ Build complete!

[5/5] Verifying pushed image...
✅ Image successfully pushed to Docker Hub

📦 Pushed tags:
  - gabrielramosprof/sherlock-discord-bot:latest
```

### 4. Verificar Imagem no Docker Hub

Acesse: https://hub.docker.com/r/gabrielramosprof/sherlock-discord-bot

Confirme que:
- ✅ Tag `latest` está presente
- ✅ Arquitetura é `linux/amd64`
- ✅ Tamanho da imagem: ~800MB-1.2GB

---

## Deploy no Swarm

Este passo é executado na **VPS**.

### 1. Copiar Arquivos Necessários

Se ainda não fez, copie os arquivos do Mac para a VPS:

```bash
# No Mac
cd /caminho/para/sherlock-discord-bot

scp docker-compose.yml usuario@ip-vps:~/sherlock-bot/
scp deploy-swarm.sh usuario@ip-vps:~/sherlock-bot/
scp logs.sh rollback-swarm.sh health-check.sh usuario@ip-vps:~/sherlock-bot/

# Tornar executáveis na VPS
ssh usuario@ip-vps "chmod +x ~/sherlock-bot/*.sh"
```

### 2. Executar Deploy

```bash
# Na VPS
cd ~/sherlock-bot

# Executar script de deploy
./deploy-swarm.sh
```

**O que o script faz:**

1. ✅ Valida que Docker Swarm está ativo
2. ✅ Verifica se `.env` existe
3. ✅ Valida variáveis obrigatórias (DISCORD_BOT_TOKEN, DATABASE_URL, etc.)
4. ✅ Verifica se rede `ProfRamosNet` existe
5. ✅ Faz pull da imagem do Docker Hub
6. ✅ Deploya stack com `docker stack deploy`

**Saída esperada:**

```
======================================
🚀 Docker Swarm Stack Deployment
======================================
Stack:   sherlock
Compose: docker-compose.yml
======================================

[1/6] Checking Docker Swarm status...
✅ Docker Swarm is active

[2/6] Checking .env file...
✅ .env file found

[3/6] Validating environment variables...
✅ All required environment variables are set

[4/6] Checking ProfRamosNet network...
✅ ProfRamosNet network exists

[5/6] Pulling latest image from Docker Hub...
✅ Image pulled successfully

[6/6] Deploying stack to Swarm...

✅ Stack deployed successfully!

======================================
📊 Deployment Information
======================================

Stack Services:
ID            NAME                          MODE        REPLICAS
abc123...     sherlock_sherlock-discord-bot replicated  1/1
```

### 3. Verificar Serviços

```bash
# Listar todos os serviços do stack
docker stack services sherlock

# Ver status detalhado
docker service ps sherlock_sherlock-discord-bot

# Deve mostrar: Running (health: starting) → Running (healthy)
```

### 4. Visualizar Logs

```bash
# Usar script auxiliar
./logs.sh

# Ou diretamente
docker service logs sherlock_sherlock-discord-bot -f --tail 100
```

**Logs esperados:**

```
sherlock_sherlock-discord-bot.1.xxx | [2026-01-05 12:00:00] INFO: Starting Sherlock Discord Bot...
sherlock_sherlock-discord-bot.1.xxx | [2026-01-05 12:00:01] INFO: 🔌 Connecting to database...
sherlock_sherlock-discord-bot.1.xxx | [2026-01-05 12:00:02] INFO: ✅ Connection established.
sherlock_sherlock-discord-bot.1.xxx | [2026-01-05 12:00:03] INFO: We have logged in as SherlockRamosBot. Invite URL: https://discord.com/...
sherlock_sherlock-discord-bot.1.xxx | [2026-01-05 12:00:04] INFO: Ready to receive commands!
```

### 5. Testar no Discord

1. Abra o Discord no servidor permitido (ALLOWED_SERVER_IDS)
2. Execute o comando: `/chat message:"olá"`
3. Bot deve:
   - ✅ Criar uma thread com prefixo `💬✅`
   - ✅ Responder com mensagem gerada pelo LLM
   - ✅ Armazenar conversa no banco de dados

---

## Monitoramento e Manutenção

### Ver Logs em Tempo Real

```bash
# Script auxiliar (recomendado)
./logs.sh

# Comando direto
docker service logs sherlock_sherlock-discord-bot -f

# Filtrar por erro
docker service logs sherlock_sherlock-discord-bot | grep -i error

# Últimas 50 linhas
docker service logs sherlock_sherlock-discord-bot --tail 50
```

### Verificar Health Status

```bash
# Script auxiliar (recomendado)
./health-check.sh

# Saída esperada:
# ✅ Service Tasks: Running (healthy)
# ✅ Container ID: abc123...
# ✅ Python process is running (PID: 1)
# ✅ No recent errors in logs
```

### Monitorar Recursos

```bash
# Uso de CPU e memória
docker stats $(docker ps -q -f name=sherlock_sherlock) --no-stream

# Esperado:
# CPU:    5-15% (picos durante chamadas ao LLM)
# Memória: 600-800MB (embeddings do sentence-transformers)
```

### Acessar via Portainer

1. Abra Portainer: `https://seu-dominio-portainer.com`
2. Navegue para: **Stacks** → `sherlock`
3. Visualize:
   - Status dos serviços
   - Logs em tempo real
   - Métricas de CPU/memória
   - Configuração do stack

---

## Atualização e Rollback

### Atualizar para Nova Versão

#### 1. Build nova imagem (no Mac)

```bash
# No Mac
cd /caminho/para/sherlock-discord-bot

# Fazer alterações no código...
git add .
git commit -m "feat: adicionar nova funcionalidade"

# Build e push com nova tag
./build-and-push.sh v1.1.0
```

#### 2. Atualizar na VPS

```bash
# Na VPS
cd ~/sherlock-bot

# Atualizar stack (puxa imagem latest automaticamente)
./deploy-swarm.sh

# OU atualizar serviço diretamente
docker service update --image gabrielramosprof/sherlock-discord-bot:latest sherlock_sherlock-discord-bot
```

**Comportamento do update:**
- ✅ Swarm inicia novo container com imagem atualizada
- ✅ Aguarda novo container ficar healthy
- ✅ Encerra container antigo (zero-downtime)
- ✅ Se novo container falhar, Swarm faz rollback automático

### Rollback para Versão Anterior

```bash
# Rollback rápido usando script
./rollback-swarm.sh

# Confirmar: y

# OU rollback manual
docker service rollback sherlock_sherlock-discord-bot
```

**Monitorar rollback:**

```bash
# Ver progresso
watch docker service ps sherlock_sherlock-discord-bot

# Verificar logs
./logs.sh
```

### Atualizar para Tag Específica

```bash
# Atualizar para versão específica
docker service update \
    --image gabrielramosprof/sherlock-discord-bot:v1.0.0 \
    sherlock_sherlock-discord-bot

# Verificar
docker service inspect sherlock_sherlock-discord-bot --format '{{.Spec.TaskTemplate.ContainerSpec.Image}}'
```

---

## Troubleshooting

### 🔴 Problema: Container Reiniciando Constantemente

**Sintomas:**
```bash
docker service ps sherlock_sherlock-discord-bot
# Mostra múltiplas tentativas de restart
```

**Diagnóstico:**

```bash
# Ver logs detalhados
./logs.sh

# Procurar erros
docker service logs sherlock_sherlock-discord-bot | grep -i "error\|failed\|exception"
```

**Causas comuns:**

1. **Variável de ambiente faltando**
   ```bash
   # Verificar .env
   cat .env | grep DISCORD_BOT_TOKEN
   cat .env | grep DATABASE_URL

   # Redeployar após corrigir
   ./deploy-swarm.sh
   ```

2. **Banco de dados inacessível**
   ```bash
   # Testar conexão do container
   docker exec $(docker ps -q -f name=sherlock_sherlock) \
       python -c "import asyncpg; print('OK')"

   # Verificar URL
   echo $DATABASE_URL
   ```

3. **Token do Discord inválido**
   - Verificar token no Discord Developer Portal
   - Atualizar `.env` com token correto
   - Redeployar: `./deploy-swarm.sh`

4. **Out of Memory (OOM)**
   ```bash
   # Verificar logs do sistema
   dmesg | grep -i oom

   # Solução: Aumentar memory limit em docker-compose.yml
   nano docker-compose.yml
   # Alterar: memory: 2G
   ./deploy-swarm.sh
   ```

### 🔴 Problema: Healthcheck Falhando

**Sintomas:**
```bash
docker service ps sherlock_sherlock-discord-bot
# Mostra: unhealthy
```

**Diagnóstico:**

```bash
# Verificar se processo Python está rodando
docker exec $(docker ps -q -f name=sherlock_sherlock) pgrep -f "python -m src.main"

# Ver status de saúde detalhado
docker inspect $(docker ps -q -f name=sherlock_sherlock) --format='{{json .State.Health}}' | jq
```

**Soluções:**

1. **Processo não está rodando**
   - Ver logs para entender por que falhou
   - Corrigir erro e redesenhar

2. **Healthcheck muito rigoroso**
   - Ajustar intervalo no Dockerfile (rebuild necessário)

### 🔴 Problema: Bot Não Responde no Discord

**Sintomas:**
- Bot aparece online no Discord
- Não responde a comandos `/chat` ou menções

**Diagnóstico:**

```bash
# Verificar logs de conexão
./logs.sh | grep "logged in"

# Verificar ALLOWED_SERVER_IDS
docker exec $(docker ps -q -f name=sherlock_sherlock) env | grep ALLOWED_SERVER_IDS

# Ver ID do servidor Discord
# No Discord: Settings → Advanced → Enable Developer Mode
# Right-click no servidor → Copy Server ID
```

**Soluções:**

1. **Server ID não está em ALLOWED_SERVER_IDS**
   ```bash
   # Editar .env
   nano .env
   # Adicionar ID do servidor em ALLOWED_SERVER_IDS

   # Redesenhar
   ./deploy-swarm.sh
   ```

2. **Permissões faltando no Discord**
   - Bot precisa de: Send Messages, Create Threads, Read Message History
   - Verificar no Discord Developer Portal → OAuth2 → URL Generator
   - Reinvite o bot com permissões corretas

3. **Message Content Intent desabilitado**
   - Discord Developer Portal → Bot → Privileged Gateway Intents
   - Ativar "Message Content Intent"
   - Reiniciar bot: `docker service update --force sherlock_sherlock-discord-bot`

### 🔴 Problema: Mensagens Duplicadas

**Sintomas:**
- Bot responde 2x ou mais à mesma mensagem

**Causa:**
- Múltiplas réplicas rodando (CRÍTICO para bots Discord)

**Solução:**

```bash
# Verificar réplicas
docker service ls | grep sherlock

# DEVE mostrar: 1/1

# Se mostrar mais de 1, escalar para 1
docker service scale sherlock_sherlock-discord-bot=1

# Verificar docker-compose.yml
grep "replicas:" docker-compose.yml
# DEVE ser: replicas: 1
```

### 🔴 Problema: Erro ao Puxar Imagem

**Sintomas:**
```
Failed to pull image: unauthorized
```

**Soluções:**

1. **Fazer login no Docker Hub na VPS**
   ```bash
   docker login
   # Username: gabrielramosprof
   # Password: [seu-token]
   ```

2. **Verificar imagem existe**
   ```bash
   docker manifest inspect gabrielramosprof/sherlock-discord-bot:latest
   ```

3. **Rebuild e push novamente**
   ```bash
   # No Mac
   ./build-and-push.sh
   ```

### 🔴 Problema: Erro de Conexão com Banco de Dados

**Sintomas:**
```
asyncio.TimeoutError: Database connection timeout
```

**Diagnóstico:**

```bash
# Testar DATABASE_URL
echo $DATABASE_URL

# Verificar formato correto
# postgresql://user:pass@host/db?sslmode=require&channel_binding=require
```

**Soluções:**

1. **Verificar Neon aceita conexões**
   - Acessar Neon Console
   - Verificar se projeto está ativo
   - Verificar se IP da VPS está permitido

2. **Testar conexão manual**
   ```bash
   # Instalar psql (opcional)
   sudo apt install postgresql-client

   # Testar conexão
   psql "$DATABASE_URL" -c "SELECT 1;"
   ```

3. **Verificar firewall da VPS**
   ```bash
   # Permitir conexões HTTPS outbound (porta 5432)
   sudo ufw allow out 5432
   ```

---

## Referência Rápida de Comandos

### Gerenciamento do Stack

```bash
# Deploy/atualizar stack
./deploy-swarm.sh

# Ver serviços do stack
docker stack services sherlock

# Ver todos os containers do stack
docker stack ps sherlock

# Remover stack completo
docker stack rm sherlock
```

### Gerenciamento de Serviço

```bash
# Ver status
docker service ls
docker service ps sherlock_sherlock-discord-bot

# Ver logs
./logs.sh
docker service logs sherlock_sherlock-discord-bot -f

# Atualizar serviço
docker service update --image gabrielramosprof/sherlock-discord-bot:latest sherlock_sherlock-discord-bot

# Forçar restart
docker service update --force sherlock_sherlock-discord-bot

# Rollback
./rollback-swarm.sh
docker service rollback sherlock_sherlock-discord-bot

# Escalar (manter em 1!)
docker service scale sherlock_sherlock-discord-bot=1
```

### Gerenciamento de Container

```bash
# Ver containers rodando
docker ps -f name=sherlock_sherlock

# Acessar shell do container
docker exec -it $(docker ps -q -f name=sherlock_sherlock) bash

# Ver variáveis de ambiente
docker exec $(docker ps -q -f name=sherlock_sherlock) env

# Ver uso de recursos
docker stats $(docker ps -q -f name=sherlock_sherlock) --no-stream
```

### Monitoramento

```bash
# Logs em tempo real
./logs.sh

# Health check
./health-check.sh

# Métricas de recursos
docker stats $(docker ps -q -f name=sherlock_sherlock)

# Ver tasks do serviço
docker service ps sherlock_sherlock-discord-bot
```

### Debug

```bash
# Inspecionar serviço
docker service inspect sherlock_sherlock-discord-bot

# Inspecionar container
docker inspect $(docker ps -q -f name=sherlock_sherlock)

# Ver logs de erro
docker service logs sherlock_sherlock-discord-bot | grep -i error

# Ver eventos do Swarm
docker events --filter 'type=service'
```

---

## Checklist de Deploy

### Pré-Deploy

- [ ] Docker Swarm inicializado na VPS
- [ ] Rede `ProfRamosNet` criada
- [ ] Conta Docker Hub configurada
- [ ] Banco de dados Neon ativo
- [ ] Banco de dados inicializado (`scripts/init_db.py`)
- [ ] Arquivo `.env` configurado na VPS
- [ ] Todas as variáveis obrigatórias preenchidas

### Deploy

- [ ] Imagem built e pushed para Docker Hub (Mac)
- [ ] `./deploy-swarm.sh` executado com sucesso (VPS)
- [ ] Serviço mostra `1/1` réplicas
- [ ] Logs mostram "We have logged in as SherlockRamosBot"
- [ ] Healthcheck passando (status: healthy)
- [ ] Bot responde a `/chat` no Discord

### Pós-Deploy

- [ ] Monitorar logs por 24h
- [ ] Testar comandos: `/chat`, menções, threads
- [ ] Verificar RAG funcionando (perguntas jurídicas)
- [ ] Confirmar uso de recursos (CPU, memória)
- [ ] Configurar rotação de logs (se necessário)
- [ ] Documentar qualquer issue encontrado

---

## Suporte e Recursos

### Documentação

- **README Principal**: `/README.md`
- **Deployment Guide (EN)**: `/DEPLOYMENT.md`
- **Arquitetura**: `/docs/architecture.md`
- **RAG Pipeline**: `/docs/rag-pipeline.md`
- **Este Guia**: `/docs/vps-deployment.md`

### Scripts Disponíveis

- `./build-and-push.sh` - Build multi-arch e push (Mac)
- `./deploy-swarm.sh` - Deploy no Swarm (VPS)
- `./logs.sh` - Ver logs em tempo real (VPS)
- `./health-check.sh` - Verificar saúde do serviço (VPS)
- `./rollback-swarm.sh` - Rollback rápido (VPS)

### Comandos Úteis

```bash
# Ver versão da imagem rodando
docker service inspect sherlock_sherlock-discord-bot \
    --format '{{.Spec.TaskTemplate.ContainerSpec.Image}}'

# Ver quando serviço foi atualizado
docker service inspect sherlock_sherlock-discord-bot \
    --format '{{.UpdatedAt}}'

# Ver histórico de tasks
docker service ps sherlock_sherlock-discord-bot --no-trunc
```

---

**Última Atualização:** 2026-01-05
**Versão:** 1.0.0
**Autor:** Gabriel Ramos
