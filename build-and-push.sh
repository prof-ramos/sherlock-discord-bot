#!/bin/bash
# ============================================================================
# Docker Multi-Architecture Build and Push Script
# ============================================================================
# This script builds a Docker image for linux/amd64 architecture from an
# ARM64 Mac and pushes it to Docker Hub.
#
# Usage:
#   ./build-and-push.sh           # Build and push with 'latest' tag
#   ./build-and-push.sh v1.0.0   # Build and push with version tag + latest
# ============================================================================

set -e  # Exit on error

# Configuration
IMAGE_NAME="gabrielramosprof/sherlock-discord-bot"
VERSION_TAG="${1:-latest}"  # Use first argument or default to 'latest'
PLATFORM="linux/amd64"      # Target VPS architecture (x86_64)

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================"
echo "🐳 Docker Multi-Arch Build & Push"
echo "======================================"
echo -e "Image:    ${GREEN}$IMAGE_NAME${NC}"
echo -e "Tag:      ${GREEN}$VERSION_TAG${NC}"
echo -e "Platform: ${GREEN}$PLATFORM${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# ============================================================================
# Step 1: Verify buildx is available
# ============================================================================
echo -e "${BLUE}[1/5]${NC} Checking docker buildx availability..."

if ! docker buildx version &> /dev/null; then
    echo -e "${RED}❌ docker buildx not found.${NC}"
    echo -e "${YELLOW}Installing buildx...${NC}"
    docker buildx install
fi

echo -e "${GREEN}✅ docker buildx available${NC}"
echo ""

# ============================================================================
# Step 2: Create or use existing buildx builder
# ============================================================================
echo -e "${BLUE}[2/5]${NC} Setting up buildx builder..."

BUILDER_NAME="sherlock-builder"

if ! docker buildx inspect $BUILDER_NAME &> /dev/null; then
    echo -e "${YELLOW}🔧 Creating buildx builder: $BUILDER_NAME${NC}"
    docker buildx create --name $BUILDER_NAME --driver docker-container --use
    echo -e "${GREEN}✅ Builder created${NC}"
else
    echo -e "${YELLOW}✅ Using existing builder: $BUILDER_NAME${NC}"
    docker buildx use $BUILDER_NAME
fi

# Bootstrap the builder (start the buildkit container)
echo -e "${YELLOW}Starting builder...${NC}"
docker buildx inspect --bootstrap

echo ""

# ============================================================================
# Step 3: Login to Docker Hub
# ============================================================================
echo -e "${BLUE}[3/5]${NC} Docker Hub authentication..."

# Check if already logged in
if ! docker info 2>/dev/null | grep -q "Username:"; then
    echo -e "${YELLOW}🔐 Please login to Docker Hub:${NC}"
    docker login
else
    echo -e "${GREEN}✅ Already logged in to Docker Hub${NC}"
fi

echo ""

# ============================================================================
# Step 4: Build and push image
# ============================================================================
echo -e "${BLUE}[4/5]${NC} Building image for ${PLATFORM}..."
echo -e "${YELLOW}This may take several minutes on first build...${NC}"
echo ""

# Build arguments
BUILD_TAGS=""
if [ "$VERSION_TAG" != "latest" ]; then
    BUILD_TAGS="--tag $IMAGE_NAME:$VERSION_TAG --tag $IMAGE_NAME:latest"
else
    BUILD_TAGS="--tag $IMAGE_NAME:latest"
fi

# Execute build
docker buildx build \
    --platform $PLATFORM \
    $BUILD_TAGS \
    --push \
    --progress=plain \
    --provenance=false \
    .

echo ""
echo -e "${GREEN}✅ Build complete!${NC}"
echo ""

# ============================================================================
# Step 5: Verify pushed image
# ============================================================================
echo -e "${BLUE}[5/5]${NC} Verifying pushed image..."

if docker manifest inspect $IMAGE_NAME:latest &> /dev/null; then
    echo -e "${GREEN}✅ Image successfully pushed to Docker Hub${NC}"
    echo ""
    echo -e "${BLUE}📦 Pushed tags:${NC}"
    if [ "$VERSION_TAG" != "latest" ]; then
        echo -e "  - ${GREEN}$IMAGE_NAME:$VERSION_TAG${NC}"
    fi
    echo -e "  - ${GREEN}$IMAGE_NAME:latest${NC}"
else
    echo -e "${RED}❌ Failed to verify image on Docker Hub${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}======================================"
echo "✅ Build and Push Complete!"
echo "======================================"
echo -e "${NC}"
echo "Next steps:"
echo ""
echo -e "  ${YELLOW}1.${NC} Deploy to VPS:"
echo "     ${GREEN}./deploy-swarm.sh${NC}"
echo ""
echo -e "  ${YELLOW}2.${NC} Check logs (after deploy):"
echo "     ${GREEN}docker service logs sherlock_sherlock-discord-bot -f${NC}"
echo ""
echo -e "  ${YELLOW}3.${NC} Verify service status:"
echo "     ${GREEN}docker service ps sherlock_sherlock-discord-bot${NC}"
echo ""
