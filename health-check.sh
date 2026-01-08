#!/bin/bash
# ============================================================================
# Health Check for Sherlock Discord Bot
# ============================================================================
# This script displays the health status of the sherlock-discord-bot service
# and its containers.
#
# Usage:
#   ./health-check.sh
#
# Requirements:
#   - jq (for JSON parsing): sudo apt install jq
# ============================================================================

STACK_NAME="sherlock"
SERVICE_NAME="${STACK_NAME}_sherlock-discord-bot"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}======================================"
echo "🏥 Service Health Status"
echo "======================================"
echo -e "${NC}"

# Show service tasks (replicas and their status)
echo -e "${YELLOW}Service Tasks:${NC}"
docker service ps "$SERVICE_NAME" \
    --format "table {{.Name}}\t{{.Image}}\t{{.CurrentState}}\t{{.Error}}" \
    --no-trunc

echo ""
echo -e "${BLUE}======================================"
echo "🐳 Container Health"
echo "======================================"
echo -e "${NC}"

# Get container ID
CONTAINER_ID=$(docker ps -q -f name="${SERVICE_NAME}" 2>/dev/null | head -1)

if [ -z "$CONTAINER_ID" ]; then
    echo -e "${YELLOW}⚠️  No running container found for service.${NC}"
    echo ""
    echo "This could mean:"
    echo "  - Service is starting up"
    echo "  - Service crashed and is restarting"
    echo "  - Service is not deployed"
    echo ""
    echo "Check service status with:"
    echo -e "  ${GREEN}docker service ps $SERVICE_NAME${NC}"
    exit 0
fi

echo -e "${GREEN}✅ Container ID: $CONTAINER_ID${NC}"
echo ""

# Check if jq is installed
if command -v jq &> /dev/null; then
    echo -e "${YELLOW}Health Check Details:${NC}"
    docker inspect --format='{{json .State.Health}}' "$CONTAINER_ID" | jq '.'
else
    echo -e "${YELLOW}⚠️  jq not installed. Showing raw health status...${NC}"
    echo ""
    docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_ID" 2>/dev/null || echo "Health status: unknown"
    echo ""
    echo "Install jq for better formatting:"
    echo -e "  ${GREEN}sudo apt install jq${NC}"
fi

echo ""
echo -e "${BLUE}======================================"
echo "📊 Resource Usage"
echo "======================================"
echo -e "${NC}"

# Show resource usage
docker stats --no-stream "$CONTAINER_ID" --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

echo ""
echo -e "${BLUE}======================================"
echo "🔍 Quick Diagnostics"
echo "======================================"
echo -e "${NC}"

# Check if process is running
PROCESS_CHECK=$(docker exec "$CONTAINER_ID" pgrep -f "python -m src.main" 2>/dev/null || echo "")
if [ -n "$PROCESS_CHECK" ]; then
    echo -e "${GREEN}✅ Python process is running (PID: $PROCESS_CHECK)${NC}"
else
    echo -e "${YELLOW}⚠️  Python process not found${NC}"
fi

# Check recent errors in logs
ERROR_COUNT=$(docker service logs "$SERVICE_NAME" --tail 100 2>/dev/null | grep -i "error" | wc -l)
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Found $ERROR_COUNT error(s) in recent logs${NC}"
    echo ""
    echo "View logs with:"
    echo -e "  ${GREEN}./logs.sh${NC}"
else
    echo -e "${GREEN}✅ No recent errors in logs${NC}"
fi

echo ""
