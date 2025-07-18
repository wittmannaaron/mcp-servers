#!/bin/bash

# File Catalog - Automated Setup Script
# This script sets up the complete environment and verifies all prerequisites

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}🎯 File Catalog - Automated Setup${NC}"
echo "=================================================="
echo "Project root: $PROJECT_ROOT"
echo

# Function to print status messages
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}🔧 $1${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python
print_info "Checking Python installation..."
if ! command_exists python3; then
    print_error "Python 3 is not installed"
    exit 1
fi
PYTHON_VERSION=$(python3 --version 2>&1)
print_status "Found: $PYTHON_VERSION"

# Check Ollama
print_info "Checking Ollama installation..."
if ! command_exists ollama; then
    print_error "Ollama is not installed"
    echo "Please install Ollama first:"
    echo "curl -fsSL https://ollama.ai/install.sh | sh"
    exit 1
fi
OLLAMA_VERSION=$(ollama --version 2>&1)
print_status "Found: $OLLAMA_VERSION"

# Check if Ollama is running
print_info "Checking if Ollama service is running..."
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    print_error "Ollama service is not running"
    echo "Please start Ollama first:"
    echo "ollama serve"
    exit 1
fi
print_status "Ollama service is running"

# Check for required Ollama models
print_info "Checking required Ollama models..."
MODELS_OUTPUT=$(ollama list 2>/dev/null || echo "")

if ! echo "$MODELS_OUTPUT" | grep -q "llama3.2"; then
    print_error "llama3.2 model is not installed"
    echo "Please install it first:"
    echo "ollama pull llama3.2:latest"
    exit 1
fi
print_status "Found llama3.2 model"

if ! echo "$MODELS_OUTPUT" | grep -q "bge-m3"; then
    print_error "bge-m3 model is not installed"
    echo "Please install it first:"
    echo "ollama pull bge-m3"
    exit 1
fi
print_status "Found bge-m3 model"

# Check pandoc
print_info "Checking pandoc installation..."
if ! command_exists pandoc; then
    print_error "pandoc is not installed"
    echo "Please install pandoc first:"
    echo "# macOS: brew install pandoc"
    echo "# Ubuntu: sudo apt-get install pandoc"
    exit 1
fi
PANDOC_VERSION=$(pandoc --version | head -n1)
print_status "Found: $PANDOC_VERSION"

# Check exiftool (optional but recommended)
print_info "Checking exiftool installation..."
if command_exists exiftool; then
    EXIFTOOL_VERSION=$(exiftool -ver)
    print_status "Found exiftool: $EXIFTOOL_VERSION"
else
    print_warning "exiftool not found (optional - for image metadata extraction)"
fi

print_info "All prerequisites verified successfully!"
echo

# Create virtual environment
print_info "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_status "Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
print_info "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
print_status "Python dependencies installed"

# Create necessary directories
print_info "Creating necessary directories..."
for dir in "data" "logs"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        print_status "Created directory: $dir"
    else
        print_status "Directory already exists: $dir"
    fi
done

# Create .env file
print_info "Setting up environment configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_status "Created .env from .env.example"
    else
        # Create .env with default values
        cat > .env << 'EOF'
# Logging
LOG_LEVEL="INFO"
LOG_TO_FILE="true"

# Ollama Configuration
OLLAMA_HOST="http://localhost:11434"
OLLAMA_MODEL="llama3.2:latest"

# Processing Preferences
PREFER_MARKITDOWN="true"
PREFER_PANDOC="true"
USE_DOCLING_PDF_ONLY="true"

# File Processing
MAX_FILE_SIZE_MB="100"

# Database Settings
DATABASE_URL="sqlite:///./data/filecatalog.db"

# Additional Settings
DEBUG="false"
LOG_FILE_PATH="logs/filecatalog.log"
LOG_FILE_ROTATION="10 MB"
LOG_FILE_RETENTION="10 days"
LLM_REQUEST_TIMEOUT="60.0"
LLM_TEMPERATURE="0.1"
LLM_MAX_TOKENS="4000"
EOF
        print_status "Created .env with default configuration"
    fi
else
    print_status ".env file already exists"
fi

echo
print_info "Running setup verification..."
python full_ingestion_test.py --check-tools

echo
echo -e "${GREEN}🎉 File Catalog setup completed successfully!${NC}"
echo "=================================================="
echo
echo "Next steps:"
echo "1. Test the system: python full_ingestion_test.py --check-tools"
echo "2. Run ingestion test: python full_ingestion_test.py -c 5"
echo "3. Process your documents: python full_ingestion_test.py -d /path/to/your/documents"
echo
echo "Note: Virtual environment is activated. To reactivate later:"
echo "source venv/bin/activate"
