#!/bin/bash
# Document Search System - Start Script
# Version: 2.1 Native macOS App

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}🔍 Document Search System - Startup${NC}"
echo -e "${BLUE}============================================================${NC}"

# Check if we're in the right directory
if [ ! -f "native_app.py" ]; then
    echo -e "${RED}Error: native_app.py not found!${NC}"
    echo -e "${RED}Please run this script from the project root directory.${NC}"
    exit 1
fi

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -i :$port > /dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to stop existing processes
stop_existing() {
    echo -e "${YELLOW}Checking for existing processes...${NC}"
    
    # Stop any existing Flask processes on port 5001
    if check_port 5001; then
        echo -e "${YELLOW}Stopping existing Flask server on port 5001...${NC}"
        lsof -ti :5001 | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
    
    # Stop any existing React processes on port 3000
    if check_port 3000; then
        echo -e "${YELLOW}Stopping existing React server on port 3000...${NC}"
        lsof -ti :3000 | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
    
    # Stop any existing native app processes
    pkill -f "python.*native_app.py" 2>/dev/null || true
    sleep 1
    
    echo -e "${GREEN}✓ Cleaned up existing processes${NC}"
}

# Check Python virtual environment
check_venv() {
    echo -e "${BLUE}Checking Python virtual environment...${NC}"
    
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Creating Python virtual environment...${NC}"
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Check if PyWebView is installed
    if ! python -c "import webview" 2>/dev/null; then
        echo -e "${YELLOW}Installing Python dependencies...${NC}"
        pip install -q pywebview requests flask flask-cors ollama
    fi
    
    echo -e "${GREEN}✓ Python environment ready${NC}"
}

# Check React dependencies
check_react() {
    echo -e "${BLUE}Checking React dependencies...${NC}"
    
    cd file-search-client/frontend
    
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}Installing npm dependencies...${NC}"
        npm install --silent
    fi
    
    cd ../..
    echo -e "${GREEN}✓ React dependencies ready${NC}"
}

# Check database connection
check_database() {
    echo -e "${BLUE}Checking database connection...${NC}"
    
    # Check if database exists (from SPECIFICATION.md path)
    DB_PATH="/Users/aaron/Projects/mcp-servers/file-search-server-v3/data/filebrowser.db"
    if [ ! -f "$DB_PATH" ]; then
        echo -e "${RED}Warning: Database not found at $DB_PATH${NC}"
        echo -e "${YELLOW}Please ensure the database is available for full functionality.${NC}"
    else
        echo -e "${GREEN}✓ Database found${NC}"
    fi
}

# Check Ollama service
check_ollama() {
    echo -e "${BLUE}Checking Ollama service...${NC}"
    
    if ! command -v ollama &> /dev/null; then
        echo -e "${RED}Warning: Ollama not found in PATH${NC}"
        echo -e "${YELLOW}Please install Ollama for LLM functionality.${NC}"
        return
    fi
    
    # Check if Ollama is running
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${YELLOW}Starting Ollama service...${NC}"
        ollama serve > /dev/null 2>&1 &
        sleep 3
    fi
    
    # Check if catalog-browser model exists
    if ollama list | grep -q "catalog-browser"; then
        echo -e "${GREEN}✓ Ollama and catalog-browser model ready${NC}"
    else
        echo -e "${YELLOW}Warning: catalog-browser model not found${NC}"
        echo -e "${YELLOW}LLM features may not work properly.${NC}"
    fi
}

# Start the application
start_app() {
    echo -e "${BLUE}Starting Document Search System...${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🚀 Launching native macOS app...${NC}"
    echo -e "${GREEN}   • Flask Backend will start on http://localhost:5001${NC}"
    echo -e "${GREEN}   • React Frontend will start on http://localhost:3000${NC}"
    echo -e "${GREEN}   • Native app window will open automatically${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}Note: It may take 10-15 seconds for all components to start.${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop the application.${NC}"
    echo ""
    
    # Activate virtual environment and start
    source venv/bin/activate
    python native_app.py
}

# Main execution
main() {
    # Parse command line arguments
    case "${1:-}" in
        --force-clean)
            echo -e "${YELLOW}Force cleaning enabled${NC}"
            stop_existing
            ;;
        --help|-h)
            echo "Usage: $0 [--force-clean] [--help]"
            echo ""
            echo "Options:"
            echo "  --force-clean    Force stop all existing processes first"
            echo "  --help, -h       Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./start.sh                # Normal startup"  
            echo "  ./start.sh --force-clean  # Clean restart"
            exit 0
            ;;
        "")
            # Normal startup - only clean if ports are in use
            if check_port 5001 || check_port 3000; then
                stop_existing
            fi
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information."
            exit 1
            ;;
    esac
    
    # Run all checks
    check_venv
    check_react  
    check_database
    check_ollama
    
    echo ""
    # Start the application
    start_app
}

# Make sure script can be interrupted cleanly
trap 'echo -e "\n${YELLOW}Stopping application...${NC}"; pkill -f "python.*native_app.py" 2>/dev/null || true; exit 0' INT TERM

# Run main function
main "$@"