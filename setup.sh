#!/bin/bash

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Python 3.11.9 Environment Setup${NC}"
echo -e "${BLUE}  (With dlib-bin prebuilt wheel)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if Python 3.11 is installed
if ! command -v python3.11 &> /dev/null; then
    echo -e "${RED}Error: Python 3.11 is not installed!${NC}"
    echo -e "${YELLOW}Please install Python 3.11.9 first:${NC}"
    echo "  brew install python@3.11"
    exit 1
fi

# Verify Python version
PYTHON_VERSION=$(python3.11 --version)
echo -e "${GREEN}✓ Found: $PYTHON_VERSION${NC}"
echo ""

# Remove old virtual environment if it exists
if [ -d ".venv311" ]; then
    echo -e "${YELLOW}Removing existing virtual environment...${NC}"
    rm -rf .venv311
    echo -e "${GREEN}✓ Removed old virtual environment${NC}"
    echo ""
fi

if [ -d "venv" ]; then
    echo -e "${YELLOW}Removing existing 'venv' directory...${NC}"
    rm -rf venv
    echo -e "${GREEN}✓ Removed old venv directory${NC}"
    echo ""
fi

# Create new virtual environment with Python 3.11
echo -e "${BLUE}Creating new virtual environment with Python 3.11.9...${NC}"
python3.11 -m venv .venv311

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to create virtual environment!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Virtual environment created${NC}"
echo ""

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source .venv311/bin/activate

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to activate virtual environment!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Upgrade pip, setuptools, and wheel
echo -e "${BLUE}Upgrading pip, setuptools, and wheel...${NC}"
pip install --upgrade pip setuptools wheel

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to upgrade pip!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ pip, setuptools, and wheel upgraded${NC}"
echo ""

# Clear pip cache to save disk space
echo -e "${BLUE}Clearing pip cache to free disk space...${NC}"
pip cache purge
echo -e "${GREEN}✓ Cache cleared${NC}"
echo ""

# Install dlib-bin first (prebuilt wheel, avoids CMake issues)
echo -e "${BLUE}Installing dlib-bin (prebuilt wheel for macOS ARM64)...${NC}"
pip install dlib-bin==20.0.0

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to install dlib-bin!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ dlib-bin installed successfully${NC}"
echo ""

# Install face-recognition without dlib dependency (since dlib-bin is already installed)
echo -e "${BLUE}Installing face-recognition...${NC}"
pip install --no-deps face-recognition==1.3.0 face-recognition-models

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to install face-recognition!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ face-recognition installed successfully${NC}"
echo ""

# Install remaining dependencies with --no-cache-dir to prevent disk space issues
echo -e "${BLUE}Installing remaining dependencies...${NC}"
echo -e "${YELLOW}This may take several minutes. Using --no-cache-dir to save disk space...${NC}"
echo ""

pip install --no-cache-dir -r requirements.txt

if [ $? -ne 0 ]; then
    echo -e "${RED}Some dependencies failed to install!${NC}"
    echo -e "${YELLOW}Trying to install dependencies one by one...${NC}"
    
    # Try installing one by one to identify problematic packages
    while IFS= read -r line; do
        # Skip empty lines and comments
        if [[ -z "$line" || "$line" =~ ^# ]]; then
            continue
        fi
        
        echo -e "${BLUE}Installing: $line${NC}"
        pip install --no-cache-dir "$line"
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}Failed to install: $line${NC}"
            echo -e "${YELLOW}Continuing with other packages...${NC}"
        fi
    done < requirements.txt
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Installation Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}To activate the virtual environment in the future, run:${NC}"
echo -e "  ${GREEN}source .venv311/bin/activate${NC}"
echo ""
echo -e "${YELLOW}Verifying installation...${NC}"
python -c "import dlib; import face_recognition; import flask; import torch; import transformers; print('✅ All major packages imported successfully!')"
echo ""
echo -e "${GREEN}✓ Setup complete! You can now run your application.${NC}"
