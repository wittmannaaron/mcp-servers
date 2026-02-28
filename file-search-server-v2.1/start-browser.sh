#!/bin/bash
# Document Search System - Browser Fallback
# Startet das System im Browser statt PyWebView

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}🌐 Document Search System - Browser Mode${NC}"
echo -e "${BLUE}============================================================${NC}"

# Check if we're in the right directory
if [ ! -f "native_app.py" ]; then
    echo -e "${RED}Error: Please run from project root directory.${NC}"
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

# Stop existing processes
if check_port 5001 || check_port 3000; then
    echo -e "${YELLOW}Stopping existing processes...${NC}"
    lsof -ti :5001 | xargs kill -9 2>/dev/null || true
    lsof -ti :3000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Start Flask backend
echo -e "${BLUE}Starting Flask backend...${NC}"
cd file-search-client/backend
source ../../venv/bin/activate
python app.py > backend.log 2>&1 &
FLASK_PID=$!
cd ../..

# Wait for Flask to start
echo -e "${YELLOW}Waiting for Flask to start...${NC}"
sleep 3
if ! check_port 5001; then
    echo -e "${RED}Flask failed to start!${NC}"
    kill $FLASK_PID 2>/dev/null || true
    exit 1
fi

# Start React frontend
echo -e "${BLUE}Starting React frontend...${NC}"
cd file-search-client/frontend
BROWSER=none npm start > react.log 2>&1 &
REACT_PID=$!
cd ../..

# Wait for React to start
echo -e "${YELLOW}Waiting for React to start...${NC}"
sleep 10
if ! check_port 3000; then
    echo -e "${RED}React failed to start!${NC}"
    kill $FLASK_PID $REACT_PID 2>/dev/null || true
    exit 1
fi

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Document Search System ready!${NC}"
echo -e "${GREEN}   • Flask Backend: http://localhost:5001${NC}"
echo -e "${GREEN}   • React Frontend: http://localhost:3000${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}Opening browser...${NC}"

# Open browser
open "http://localhost:3000"

echo ""
echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}"

# Wait for interrupt
trap 'echo -e "\n${YELLOW}Stopping servers...${NC}"; kill $FLASK_PID $REACT_PID 2>/dev/null || true; echo -e "${GREEN}✓ Stopped${NC}"; exit 0' INT TERM

# Keep script running
wait