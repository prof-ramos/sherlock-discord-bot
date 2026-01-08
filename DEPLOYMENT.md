# Deployment Guide - Sherlock Discord Bot

This guide covers the complete deployment process for the Sherlock Discord Bot using Docker Swarm.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture Overview](#architecture-overview)
- [Build and Deploy Workflow](#build-and-deploy-workflow)
- [Database Initialization](#database-initialization)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Update Workflow](#update-workflow)
- [Troubleshooting](#troubleshooting)
- [Stack Management](#stack-management)
- [Security Best Practices](#security-best-practices)
- [Performance Optimization](#performance-optimization)
- [Backup and Disaster Recovery](#backup-and-disaster-recovery)
- [Support and Resources](#support-and-resources)
- [Summary Checklist](#summary-checklist)

---

## Prerequisites

### Local Development Machine (Mac ARM64)

- Docker Desktop installed and running
- Docker Hub account with credentials
- Access to project repository

### VPS (x86_64 Linux)

- Docker installed (version 20.10+)
- Docker Swarm initialized
- External network `ProfRamosNet` created
- SSH access with appropriate permissions
- Portainer (optional, for UI management)

### Required Services

- **Neon PostgreSQL Database**: Active database with connection string
- **Discord Bot Application**: Created at [Discord Developer Portal](https://discord.com/developers/applications)
- **OpenRouter API Key**: From [OpenRouter](https://openrouter.ai/keys)
- **OpenAI API Key**: From [OpenAI Platform](https://platform.openai.com/api-keys)

---

## Architecture Overview

```
┌──────────────────┐
│  Mac (ARM64)     │
│  Development     │
└────────┬─────────┘
         │
         │ 1. Build multi-arch image
         │    ./build-and-push.sh
         ▼
┌──────────────────┐
│  Docker Hub      │
│  Registry        │
└────────┬─────────┘
         │
         │ 2. Pull image
         ▼
┌──────────────────┐      ┌───────────────┐
│  VPS (x86_64)    │◄─────┤  Neon DB      │
│  Docker Swarm    │      │  PostgreSQL   │
└────────┬─────────┘      └───────────────┘
         │
         │ 3. Deploy stack
         │    ./deploy-swarm.sh
         ▼
┌──────────────────┐
│  Running Bot     │
│  + Healthcheck   │
│  + Auto-restart  │
└────────┬─────────┘
         │
         │ 4. Monitor via Portainer
         ▼
┌──────────────────┐
│  Discord API     │
└──────────────────┘
```

### Key Components

- **Multi-stage Docker build**: Optimized production image (~800MB-1.2GB)
- **Docker Swarm**: Orchestration with health monitoring and auto-restart
- **External network**: Integration with Traefik and Portainer
- **Environment variables**: Configuration management via .env file
- **Healthcheck**: Monitors bot process every 60 seconds

---

## Build and Deploy Workflow

### Step 1: Build on Mac (ARM64)

```bash
# Navigate to project directory
cd /path/to/sherlock-discord-bot

# Make scripts executable (first time only)
chmod +x build-and-push.sh deploy-swarm.sh logs.sh rollback-swarm.sh health-check.sh

# Login to Docker Hub
docker login

# Build and push image for linux/amd64
./build-and-push.sh

# Or build with version tag
./build-and-push.sh v1.0.0
```

**What this does:**
1. Creates/uses `docker buildx` builder for multi-architecture support
2. Builds image for `linux/amd64` platform (VPS architecture)
3. Tags image as `latest` (and optionally version tag)
4. Pushes to Docker Hub: `gabrielramosprof/sherlock-discord-bot:latest`

**Build time:** 5-15 minutes (first build), 2-5 minutes (subsequent builds with cache)

### Step 2: Prepare VPS

```bash
# SSH into VPS
ssh user@your-vps-ip

# Verify Docker Swarm is initialized
docker info | grep Swarm
# Expected: "Swarm: active"

# If not active, initialize Swarm
docker swarm init

# Verify ProfRamosNet network exists
docker network ls | grep ProfRamosNet

# If not exists, create it
docker network create --driver overlay --attachable ProfRamosNet

# Create deployment directory
mkdir -p ~/sherlock-bot
cd ~/sherlock-bot
```

### Step 3: Transfer Files to VPS

**Option A: Git Clone (Recommended)**

```bash
# On VPS
git clone https://github.com/your-username/sherlock-discord-bot.git .

# Configure environment
cp .env.production.template .env
nano .env  # Edit with your credentials
```

**Option B: SCP from Mac**

```bash
# On Mac
scp docker-compose.yml .env.production.template deploy-swarm.sh user@vps-ip:~/sherlock-bot/

# On VPS
cd ~/sherlock-bot
cp .env.production.template .env
nano .env  # Edit with your credentials
```

### Step 4: Configure Environment Variables

Edit `.env` file on VPS with your credentials:

```bash
nano .env
```

**Required variables:**
- `DISCORD_BOT_TOKEN`: From Discord Developer Portal
- `DISCORD_CLIENT_ID`: From Discord Developer Portal
- `ALLOWED_SERVER_IDS`: Discord guild IDs (comma-separated)
- `DATABASE_URL`: Neon PostgreSQL connection string
- `OPENROUTER_API_KEY`: From OpenRouter
- `OPENAI_API_KEY`: From OpenAI (for embeddings)
- `DEFAULT_MODEL`: LLM model to use (e.g., `xiaomi/mimo-v2-flash:free`)

**Optional variables:**
- `SERVER_TO_MODERATION_CHANNEL`: Moderation logging
- `NEON_PROJECT_ID`: For Neon API access
- `NEON_API_KEY`: For database branch management

### Step 5: Deploy to Swarm

```bash
# On VPS
cd ~/sherlock-bot

# Deploy stack
./deploy-swarm.sh
```

**What this does:**
1. Validates Swarm is active
2. Validates `.env` exists and contains required variables
3. Verifies `ProfRamosNet` network exists
4. Pulls latest image from Docker Hub
5. Deploys stack with `docker stack deploy`
6. Shows service status

**Expected output:**
```
✅ Stack deployed successfully!

ID                NAME                          MODE        REPLICAS
xxx...            sherlock_sherlock-discord-bot replicated  1/1
```

### Step 6: Verify Deployment

```bash
# Check service status
docker service ls

# View logs (should show "We have logged in as SherlockRamosBot")
./logs.sh

# Or use Docker command
docker service logs sherlock_sherlock-discord-bot -f

# Check health status
./health-check.sh

# Test in Discord
# Run: /chat message:"olá"
# Bot should create thread and respond
```

---

## Database Initialization

**IMPORTANT:** Database must be initialized before first deployment.

### Check if Database is Initialized

```bash
# On Mac or VPS (requires DATABASE_URL in .env)
uv run python scripts/verify_db.py
```

**Expected output (if initialized):**
```
✅ Connection established.
✅ Found table: threads
✅ Found table: messages
✅ Found table: analytics
✅ Found table: documents
```

### Initialize Database (if needed)

```bash
# On Mac or VPS
uv run python scripts/init_db.py

# Verify initialization
uv run python scripts/verify_db.py
```

**What this creates:**
- Core tables: `threads`, `messages`, `analytics`
- RAG tables: `documents` with pgvector extension
- Indexes: HNSW for vector search, GIN for full-text search

**Note:** The `init_db.py` script is idempotent (safe to run multiple times).

---

## Monitoring and Maintenance

### View Logs

```bash
# Real-time logs (last 100 lines)
./logs.sh

# Or directly
docker service logs sherlock_sherlock-discord-bot -f --tail 100

# Filter for errors
docker service logs sherlock_sherlock-discord-bot 2>&1 | grep -i error
```

### Check Service Status

```bash
# Service overview
docker service ls

# Detailed task status
docker service ps sherlock_sherlock-discord-bot

# Watch for changes
watch docker service ps sherlock_sherlock-discord-bot
```

### Health Monitoring

```bash
# Run health check script
./health-check.sh

# Manual container inspect
docker inspect $(docker ps -q -f name=sherlock_sherlock) --format='{{json .State.Health}}' | jq
```

### Resource Usage

```bash
# Current stats
docker stats $(docker ps -q -f name=sherlock_sherlock) --no-stream

# Continuous monitoring
docker stats $(docker ps -q -f name=sherlock_sherlock)
```

**Expected usage:**
- **CPU**: 5-15% (spikes during LLM calls)
- **Memory**: 600-800MB (sentence-transformers embeddings)

### Portainer Integration

Access Portainer UI to:
- View stack status and logs
- Monitor resource usage
- Manage service configuration
- View container health
- Scale replicas (keep at 1!)

---

## Update Workflow

### Update to New Version

```bash
# On Mac: Build new image
./build-and-push.sh v1.1.0

# On VPS: Redeploy stack
./deploy-swarm.sh

# Swarm performs rolling update automatically
# (start-first: new container starts before old one stops)
```

### Manual Service Update

```bash
# Update to specific image tag
docker service update \
    --image gabrielramosprof/sherlock-discord-bot:v1.1.0 \
    sherlock_sherlock-discord-bot

# Force update (pull latest even if tag unchanged)
docker service update --force sherlock_sherlock-discord-bot
```

### Rollback to Previous Version

```bash
# Quick rollback
./rollback-swarm.sh

# Or manually
docker service rollback sherlock_sherlock-discord-bot

# Monitor rollback
docker service ps sherlock_sherlock-discord-bot
```

---

## Troubleshooting

### Container Keeps Restarting

**Symptoms:** Service shows repeated restarts in `docker service ps`

**Diagnosis:**
```bash
# Check logs for errors
./logs.sh

# Look for specific errors
docker service logs sherlock_sherlock-discord-bot 2>&1 | grep -i "error\|failed\|exception"
```

**Common causes:**
1. **Missing environment variables**
   - Solution: Verify all required vars in `.env`

2. **Database unreachable**
   - Solution: Test `DATABASE_URL` connectivity

3. **Invalid Discord token**
   - Solution: Verify token at Discord Developer Portal

4. **Out of memory (OOM)**
   - Solution: Increase memory limit in `docker-compose.yml` to 2G

### Healthcheck Failing

**Symptoms:** Service marked as unhealthy

**Diagnosis:**
```bash
# Check if Python process is running
docker exec $(docker ps -q -f name=sherlock_sherlock) pgrep -f "python -m src.main"

# View health status
docker inspect $(docker ps -q -f name=sherlock_sherlock) --format='{{json .State.Health}}'
```

**Solutions:**
- If process not found: Check logs for startup errors
- If process exists but health failing: Healthcheck might be too strict
- Adjust healthcheck interval in `Dockerfile` if needed

### Database Connection Timeout

**Symptoms:** Logs show `asyncio.TimeoutError` or `cannot connect to database`

**Diagnosis:**
```bash
# Test database URL from container
docker exec $(docker ps -q -f name=sherlock_sherlock) \
    python -c "import os; print(os.getenv('DATABASE_URL'))"

# Verify Neon database accepts connections from VPS IP
```

**Solutions:**
- Check `DATABASE_URL` format: `postgresql://user:pass@host/db?sslmode=require`
- Verify Neon project allows connections from VPS IP
- Check VPS firewall rules (outbound to Neon)

### Rate Limiting / Duplicate Messages

**Symptoms:** Bot responds multiple times to same message

**Cause:** Multiple replicas running

**Solution:**
```bash
# CRITICAL: Scale to exactly 1 replica
docker service scale sherlock_sherlock-discord-bot=1

# Verify in docker-compose.yml
grep "replicas:" docker-compose.yml
# Must show: replicas: 1
```

### Image Pull Failed

**Symptoms:** Deployment fails with "image not found" or "pull access denied"

**Diagnosis:**
```bash
# Verify image exists on Docker Hub
docker manifest inspect gabrielramosprof/sherlock-discord-bot:latest

# Check Docker login
docker info | grep Username
```

**Solutions:**
- Ensure image was built and pushed: `./build-and-push.sh`
- Login to Docker Hub on VPS: `docker login`
- Verify image is public or credentials are correct

### Service Not Responding in Discord

**Symptoms:** Bot shows as online but doesn't respond to commands

**Diagnosis:**
```bash
# Check logs for Discord connection
./logs.sh | grep "logged in"

# Verify allowed server IDs
docker exec $(docker ps -q -f name=sherlock_sherlock) env | grep ALLOWED_SERVER_IDS

# Check permissions in Discord
```

**Solutions:**
- Verify bot has proper Discord permissions (Send Messages, Create Threads, etc.)
- Check `ALLOWED_SERVER_IDS` includes your server
- Ensure bot is invited with correct permissions URL
- Verify Message Content Intent is enabled in Discord Developer Portal

---

## Stack Management

### Remove Stack Completely

```bash
# Remove entire stack (preserves database data)
docker stack rm sherlock

# Verify removal
docker stack ls

# Wait for services to stop
watch docker service ls
```

### Restart Service

```bash
# Force restart (creates new task)
docker service update --force sherlock_sherlock-discord-bot

# Or scale down and up
docker service scale sherlock_sherlock-discord-bot=0
docker service scale sherlock_sherlock-discord-bot=1
```

### Access Container Shell

```bash
# Execute bash in running container
docker exec -it $(docker ps -q -f name=sherlock_sherlock) bash

# Run commands inside container
docker exec $(docker ps -q -f name=sherlock_sherlock) python --version
docker exec $(docker ps -q -f name=sherlock_sherlock) uv --version
```

---

## Security Best Practices

### Environment Variables

- ✅ **DO**: Use `.env` file on VPS (not committed to git)
- ✅ **DO**: Restrict file permissions: `chmod 600 .env`
- ❌ **DON'T**: Commit `.env` to version control
- ❌ **DON'T**: Share credentials in logs or screenshots

### Docker Secrets (Alternative)

For enhanced security, use Docker Secrets instead of environment variables:

```bash
# Create secrets
echo "your-discord-token" | docker secret create discord_token -
echo "your-database-url" | docker secret create database_url -

# Update docker-compose.yml to use secrets
# (requires app code modification to read from /run/secrets/)
```

### Network Security

- Ensure VPS firewall blocks Docker API port (2376)
- Use Traefik for HTTPS if exposing any web endpoints
- Regularly update Docker and host OS

---

## Performance Optimization

### Resource Tuning

Monitor resource usage and adjust limits in `docker-compose.yml`:

```yaml
resources:
  limits:
    cpus: '1.0'    # Increase if CPU-bound
    memory: 2G     # Increase if OOM occurs
  reservations:
    cpus: '0.25'
    memory: 512M
```

### Image Size Optimization

Current image size: ~800MB-1.2GB

To reduce:
- Use `python:3.13-alpine` instead of `slim` (saves ~100MB)
- Remove unused dependencies
- Use `.dockerignore` aggressively

### Log Rotation

Current settings: 3 files × 10MB = 30MB total

Adjust in `docker-compose.yml`:

```yaml
logging:
  driver: json-file
  options:
    max-size: "5m"   # Smaller files
    max-file: "5"    # More files
```

---

## Backup and Disaster Recovery

### Database Backups

Neon provides automatic backups. Configure retention in Neon Console.

**Manual backup:**
```bash
# Export database schema and data
pg_dump "$DATABASE_URL" > backup_$(date +%Y%m%d).sql
```

### Configuration Backup

```bash
# Backup critical files
tar -czf sherlock-backup-$(date +%Y%m%d).tar.gz \
    docker-compose.yml \
    .env \
    build-and-push.sh \
    deploy-swarm.sh
```

### Disaster Recovery

1. Restore database from Neon backup
2. Deploy stack on new VPS
3. Restore `.env` configuration
4. Run `./deploy-swarm.sh`

---

## Support and Resources

### Documentation

- **Project README**: `README.md`
- **VPS Deployment Guide** (Portuguese): `docs/vps-deployment.md`
- **Architecture**: `docs/architecture.md`
- **RAG Pipeline**: `docs/rag-pipeline.md`

### Logs and Debugging

- View logs: `./logs.sh`
- Health check: `./health-check.sh`
- Service status: `docker service ps sherlock_sherlock-discord-bot`

### Community

- GitHub Issues: Report bugs and feature requests
- Discord: Test bot behavior in your server

---

## Summary Checklist

**Pre-deployment:**
- [ ] Docker Swarm initialized on VPS
- [ ] ProfRamosNet network created
- [ ] Database initialized (`scripts/init_db.py`)
- [ ] `.env` configured with all required variables
- [ ] Image built and pushed to Docker Hub

**Deployment:**
- [ ] `./deploy-swarm.sh` executed successfully
- [ ] Service shows 1/1 replicas
- [ ] Logs show "We have logged in as SherlockRamosBot"
- [ ] Healthcheck passing
- [ ] Bot responds to `/chat` in Discord

**Post-deployment:**
- [ ] Monitor logs for 24 hours
- [ ] Test all bot commands
- [ ] Verify RAG queries work
- [ ] Configure log rotation if needed
- [ ] Set up database backups

---

**Last Updated:** 2026-01-05
**Version:** 1.0.0
