#!/bin/bash
# ============================================================================
# Docker Swarm Stack Deployment Script
# ============================================================================
# This script deploys the sherlock-discord-bot stack to Docker Swarm.
# It performs validation checks before deployment and provides helpful
# post-deployment information.
#
# Usage:
#   ./deploy-swarm.sh
#
# Prerequisites:
#   - Docker Swarm initialized (docker swarm init)
#   - .env file configured with all required variables
#   - ProfRamosNet network created
# ============================================================================

set -euo pipefail  # Exit on error, undefined vars, and pipe failures

# Configuration
STACK_NAME="sherlock"
SERVICE_NAME="${STACK_NAME}_sherlock-discord-bot"
COMPOSE_FILE="docker-compose.yml"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ============================================================================
# Function: Safe .env file parser
# ============================================================================
# Securely loads environment variables from .env file without executing
# arbitrary code. Only exports whitelisted variables with valid KEY=VALUE format.
load_env_safe() {
    local env_file="${1:-.env}"

    if [ ! -f "$env_file" ]; then
        echo -e "${RED}❌ .env file not found: $env_file${NC}"
        exit 1
    fi

    # Whitelist of allowed environment variables
    local ALLOWED_VARS=(
        "DISCORD_BOT_TOKEN"
        "DISCORD_CLIENT_ID"
        "ALLOWED_SERVER_IDS"
        "SERVER_TO_MODERATION_CHANNEL"
        "OPENROUTER_API_KEY"
        "OPENROUTER_BASE_URL"
        "OPENAI_API_KEY"
        "DATABASE_URL"
        "NEON_PROJECT_ID"
        "NEON_API_KEY"
        "DEFAULT_MODEL"
    )

    # Read and parse .env file line by line
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments (lines starting with #)
        [[ "$line" =~ ^[[:space:]]*# ]] && continue

        # Skip empty lines
        [[ -z "${line// }" ]] && continue

        # Match KEY=VALUE pattern (KEY must start with letter/underscore)
        if [[ "$line" =~ ^([A-Z_][A-Z0-9_]*)=(.*)$ ]]; then
            local key="${BASH_REMATCH[1]}"
            local value="${BASH_REMATCH[2]}"

            # Check if variable is in whitelist
            if [[ " ${ALLOWED_VARS[@]} " =~ " ${key} " ]]; then
                export "$key=$value"
            fi
        fi
    done < "$env_file"
}

# ============================================================================
# Function: Wait for service to be ready
# ============================================================================
# Polls service status until it's running or timeout is reached
wait_for_service() {
    local service_name="$1"
    local max_wait=60  # seconds
    local interval=2
    local elapsed=0

    echo -e "${YELLOW}⏳ Waiting for service to be ready...${NC}"

    while [ $elapsed -lt $max_wait ]; do
        # Check if service has running replicas
        local running=$(docker service ps "$service_name" \
            --filter "desired-state=running" \
            --format "{{.CurrentState}}" 2>/dev/null | grep -c "Running" || echo "0")

        if [ "$running" -ge 1 ]; then
            echo -e "${GREEN}✅ Service is running${NC}"
            return 0
        fi

        sleep $interval
        elapsed=$((elapsed + interval))
    done

    echo -e "${RED}❌ Service failed to start within ${max_wait}s${NC}"
    return 1
}

echo -e "${BLUE}======================================"
echo "🚀 Docker Swarm Stack Deployment"
echo "======================================"
echo -e "Stack:   ${GREEN}$STACK_NAME${NC}"
echo -e "Compose: ${GREEN}$COMPOSE_FILE${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# ============================================================================
# Step 1: Verify Docker Swarm is active
# ============================================================================
echo -e "${BLUE}[1/6]${NC} Checking Docker Swarm status..."

if ! docker info 2>/dev/null | grep -q "Swarm: active"; then
    echo -e "${RED}❌ Docker Swarm is not active on this node.${NC}"
    echo ""
    echo "Initialize Swarm with:"
    echo -e "  ${GREEN}docker swarm init${NC}"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ Docker Swarm is active${NC}"
echo ""

# ============================================================================
# Step 2: Verify .env file exists
# ============================================================================
echo -e "${BLUE}[2/6]${NC} Checking .env file..."

if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo ""
    echo "Create .env file from template:"
    echo -e "  ${GREEN}cp .env.production.template .env${NC}"
    echo -e "  ${GREEN}nano .env${NC}  # Edit with your credentials"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ .env file found${NC}"
echo ""

# ============================================================================
# Step 3: Load and validate environment variables
# ============================================================================
echo -e "${BLUE}[3/6]${NC} Validating environment variables..."

# Load environment variables securely (whitelist-based, no code execution)
load_env_safe .env

# Define required variables
REQUIRED_VARS=(
    "DISCORD_BOT_TOKEN"
    "DATABASE_URL"
    "OPENROUTER_API_KEY"
    "DISCORD_CLIENT_ID"
    "ALLOWED_SERVER_IDS"
)

# Check each required variable
MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

# Report missing variables
if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "${RED}❌ Missing required environment variables:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo -e "  ${RED}- $var${NC}"
    done
    echo ""
    echo "Please configure these variables in .env file"
    exit 1
fi

echo -e "${GREEN}✅ All required environment variables are set${NC}"
echo ""

# ============================================================================
# Step 4: Verify network exists
# ============================================================================
echo -e "${BLUE}[4/6]${NC} Checking ProfRamosNet network..."

if ! docker network ls --format "{{.Name}}" | grep -xF "ProfRamosNet" > /dev/null; then
    echo -e "${YELLOW}⚠️  ProfRamosNet network not found${NC}"
    echo ""
    echo "Create the network with:"
    echo -e "  ${GREEN}docker network create --driver overlay --attachable ProfRamosNet${NC}"
    echo ""
    read -p "Create network now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker network create --driver overlay --attachable ProfRamosNet
        echo -e "${GREEN}✅ Network created${NC}"
    else
        echo -e "${RED}❌ Deployment cancelled${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ ProfRamosNet network exists${NC}"
fi

echo ""

# ============================================================================
# Step 5: Pull latest image from Docker Hub
# ============================================================================
echo -e "${BLUE}[5/6]${NC} Pulling latest image from Docker Hub..."

IMAGE="gabrielramosprof/sherlock-discord-bot:latest"

if docker pull "$IMAGE"; then
    echo -e "${GREEN}✅ Image pulled successfully${NC}"
else
    echo -e "${RED}❌ Failed to pull image${NC}"
    echo ""
    echo "Make sure:"
    echo "  1. Image has been built and pushed: ./build-and-push.sh"
    echo "  2. You are logged in to Docker Hub: docker login"
    echo ""
    exit 1
fi

echo ""

# ============================================================================
# Step 6: Deploy stack to Swarm
# ============================================================================
echo -e "${BLUE}[6/6]${NC} Deploying stack to Swarm..."

# Deploy with registry authentication (allows workers to pull private images)
docker stack deploy \
    --compose-file "$COMPOSE_FILE" \
    --with-registry-auth \
    "$STACK_NAME"

echo ""
echo -e "${GREEN}✅ Stack deployed successfully!${NC}"
echo ""

# ============================================================================
# Post-deployment information
# ============================================================================
echo -e "${BLUE}======================================"
echo "📊 Deployment Information"
echo "======================================"
echo -e "${NC}"

# Wait for service to be ready (with timeout and retries)
wait_for_service "$SERVICE_NAME" || {
    echo -e "${RED}❌ Service failed to start. Check logs:${NC}"
    echo -e "  ${YELLOW}docker service logs $SERVICE_NAME${NC}"
    exit 1
}

# Show stack services
echo -e "${YELLOW}Stack Services:${NC}"
docker stack services "$STACK_NAME"

echo ""
echo -e "${BLUE}======================================"
echo "🔍 Next Steps"
echo "======================================"
echo -e "${NC}"
echo -e "${YELLOW}1.${NC} View logs (real-time):"
echo -e "   ${GREEN}docker service logs ${STACK_NAME}_sherlock-discord-bot -f${NC}"
echo -e "   ${GREEN}# or use: ./logs.sh${NC}"
echo ""
echo -e "${YELLOW}2.${NC} Check service status:"
echo -e "   ${GREEN}docker service ps ${STACK_NAME}_sherlock-discord-bot${NC}"
echo ""
echo -e "${YELLOW}3.${NC} Monitor container health:"
echo -e "   ${GREEN}watch docker service ps ${STACK_NAME}_sherlock-discord-bot${NC}"
echo -e "   ${GREEN}# or use: ./health-check.sh${NC}"
echo ""
echo -e "${YELLOW}4.${NC} Access Portainer:"
echo -e "   Navigate to your Portainer UI and find stack '${GREEN}$STACK_NAME${NC}'"
echo ""
echo -e "${YELLOW}5.${NC} Test bot in Discord:"
echo -e "   Run: ${GREEN}/chat message:\"olá\"${NC}"
echo ""
echo -e "${BLUE}======================================"
echo "📝 Useful Commands"
echo "======================================"
echo -e "${NC}"
echo -e "${YELLOW}Update service:${NC}"
echo -e "   ${GREEN}docker service update --image gabrielramosprof/sherlock-discord-bot:latest ${STACK_NAME}_sherlock-discord-bot${NC}"
echo ""
echo -e "${YELLOW}Rollback service:${NC}"
echo -e "   ${GREEN}./rollback-swarm.sh${NC}"
echo ""
echo -e "${YELLOW}Remove stack:${NC}"
echo -e "   ${GREEN}docker stack rm $STACK_NAME${NC}"
echo ""
echo -e "${YELLOW}Scale service (keep at 1):${NC}"
echo -e "   ${GREEN}docker service scale ${STACK_NAME}_sherlock-discord-bot=1${NC}"
echo ""
