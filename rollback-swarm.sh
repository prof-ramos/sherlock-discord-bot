#!/bin/bash
# ============================================================================
# Rollback Sherlock Discord Bot Service
# ============================================================================
# This script rolls back the sherlock-discord-bot service to its previous
# version. Useful when an update causes issues.
#
# Usage:
#   ./rollback-swarm.sh
# ============================================================================

set -e

STACK_NAME="sherlock"
SERVICE_NAME="${STACK_NAME}_sherlock-discord-bot"

# Colors
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${YELLOW}⚠️  Rolling back service: $SERVICE_NAME${NC}"
echo ""

# Confirm rollback
read -p "Are you sure you want to rollback to the previous version? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Rollback cancelled."
    exit 0
fi

# Execute rollback
echo -e "${BLUE}Initiating rollback...${NC}"
docker service rollback "$SERVICE_NAME"

echo ""
echo -e "${GREEN}✅ Rollback initiated${NC}"
echo ""
echo "Monitor rollback progress with:"
echo -e "  ${GREEN}docker service ps $SERVICE_NAME${NC}"
echo -e "  ${GREEN}./logs.sh${NC}"
echo ""
