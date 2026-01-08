#!/bin/bash
# ============================================================================
# View Sherlock Discord Bot Logs
# ============================================================================
# This script displays real-time logs from the sherlock-discord-bot service.
#
# Usage:
#   ./logs.sh
# ============================================================================

STACK_NAME="sherlock"
SERVICE_NAME="${STACK_NAME}_sherlock-discord-bot"

echo "📋 Viewing logs for: $SERVICE_NAME"
echo "Press Ctrl+C to exit"
echo ""

# Follow logs with last 100 lines
docker service logs "$SERVICE_NAME" -f --tail 100
