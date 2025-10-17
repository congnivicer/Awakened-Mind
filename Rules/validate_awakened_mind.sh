#!/bin/bash

# Awakened Mind Project Validator
# Run this before starting any work

echo "========================================"
echo "AWAKENED MIND PROJECT VALIDATOR"
echo "========================================"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check directories
echo -e "\n${YELLOW}Checking project directories...${NC}"
DIRS=(
    "/Volumes/NHB_Workspace/awakened_mind"
    "/Volumes/NHB_Workspace/cosmos"
    "/Volumes/NHB_Workspace/k9-cadet-workspace"
    "/Volumes/NHB_Workspace/Awakened-Mind-Complete"
)

for dir in "${DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✓${NC} $dir exists"
    else
        echo -e "${RED}✗${NC} $dir missing"
    fi
done

# Check git status
echo -e "\n${YELLOW}Checking git status...${NC}"
for dir in "${DIRS[@]:0:3}"; do
    if [ -d "$dir/.git" ]; then
        cd "$dir"
        if git diff-index --quiet HEAD --; then
            echo -e "${GREEN}✓${NC} $(basename $dir) - clean"
        else
            echo -e "${YELLOW}⚠${NC} $(basename $dir) - has uncommitted changes"
        fi
    fi
done

# Check for the critical bug
echo -e "\n${YELLOW}Checking for double initialization bug...${NC}"
BUG_FILE="/Volumes/NHB_Workspace/awakened_mind/core/mcp_orchestrator.py"
if [ -f "$BUG_FILE" ]; then
    if grep -q "if not await self.initialize_components():" "$BUG_FILE"; then
        echo -e "${RED}✗${NC} Double initialization bug still present at line ~156"
        echo "   Fix required in: $BUG_FILE"
    else
        echo -e "${GREEN}✓${NC} Double initialization bug appears fixed or not present"
    fi
else
    echo -e "${YELLOW}⚠${NC} Cannot check - mcp_orchestrator.py not found"
fi

# Check Python environment
echo -e "\n${YELLOW}Checking Python environment...${NC}"
if command -v python3 &> /dev/null; then
    echo -e "${GREEN}✓${NC} Python3 installed: $(python3 --version)"
else
    echo -e "${RED}✗${NC} Python3 not found"
fi

# Check for required Python packages
echo -e "\n${YELLOW}Checking Python packages...${NC}"
PACKAGES=("pytest" "black" "flake8" "mypy")
for pkg in "${PACKAGES[@]}"; do
    if python3 -c "import $pkg" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $pkg installed"
    else
        echo -e "${YELLOW}⚠${NC} $pkg not installed (recommended)"
    fi
done

echo -e "\n========================================"
echo "Validation complete!"
echo "========================================"
