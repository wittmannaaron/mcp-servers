#!/bin/bash
# Document Search System - Stop Script
# Version: 2.1 Native macOS App

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}🛑 Document Search System - Shutdown${NC}"
echo -e "${BLUE}============================================================${NC}"

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -i :$port > /dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to gracefully stop processes
stop_processes() {
    local stopped=0
    
    echo -e "${YELLOW}Stopping Document Search System components...${NC}"
    
    # Stop native app processes
    if pgrep -f "python.*native_app.py" > /dev/null 2>&1; then
        echo -e "${BLUE}• Stopping native macOS app...${NC}"
        pkill -f "python.*native_app.py" 2>/dev/null || true
        sleep 2
        stopped=1
    fi
    
    # Stop Flask processes on port 5001
    if check_port 5001; then
        echo -e "${BLUE}• Stopping Flask backend (port 5001)...${NC}"
        lsof -ti :5001 | xargs kill -TERM 2>/dev/null || true
        sleep 3
        
        # Force kill if still running
        if check_port 5001; then
            lsof -ti :5001 | xargs kill -9 2>/dev/null || true
            sleep 1
        fi
        stopped=1
    fi
    
    # Stop React processes on port 3000
    if check_port 3000; then
        echo -e "${BLUE}• Stopping React frontend (port 3000)...${NC}"
        lsof -ti :3000 | xargs kill -TERM 2>/dev/null || true
        sleep 3
        
        # Force kill if still running
        if check_port 3000; then
            lsof -ti :3000 | xargs kill -9 2>/dev/null || true
            sleep 1
        fi
        stopped=1
    fi
    
    # Stop any remaining Flask app processes
    if pgrep -f "python.*app.py" > /dev/null 2>&1; then
        echo -e "${BLUE}• Stopping remaining Flask processes...${NC}"
        pkill -f "python.*app.py" 2>/dev/null || true
        sleep 1
        stopped=1
    fi
    
    # Stop any remaining node processes related to our app
    if pgrep -f "node.*react-scripts" > /dev/null 2>&1; then
        echo -e "${BLUE}• Stopping remaining React processes...${NC}"
        pkill -f "node.*react-scripts" 2>/dev/null || true
        sleep 1
        stopped=1
    fi
    
    if [ $stopped -eq 1 ]; then
        echo -e "${GREEN}✓ All processes stopped${NC}"
    else
        echo -e "${YELLOW}• No running processes found${NC}"
    fi
}

# Function to verify cleanup
verify_cleanup() {
    echo -e "${BLUE}Verifying cleanup...${NC}"
    
    local issues=0
    
    # Check ports
    if check_port 5001; then
        echo -e "${RED}✗ Port 5001 still in use${NC}"
        issues=1
    else
        echo -e "${GREEN}✓ Port 5001 is free${NC}"
    fi
    
    if check_port 3000; then
        echo -e "${RED}✗ Port 3000 still in use${NC}"
        issues=1
    else
        echo -e "${GREEN}✓ Port 3000 is free${NC}"
    fi
    
    # Check processes
    if pgrep -f "python.*native_app.py" > /dev/null 2>&1; then
        echo -e "${RED}✗ Native app processes still running${NC}"
        issues=1
    else
        echo -e "${GREEN}✓ No native app processes${NC}"
    fi
    
    if pgrep -f "python.*app.py" > /dev/null 2>&1; then
        echo -e "${RED}✗ Flask processes still running${NC}"
        issues=1
    else
        echo -e "${GREEN}✓ No Flask processes${NC}"
    fi
    
    if pgrep -f "node.*react-scripts" > /dev/null 2>&1; then
        echo -e "${RED}✗ React processes still running${NC}"
        issues=1
    else
        echo -e "${GREEN}✓ No React processes${NC}"
    fi
    
    return $issues
}

# Function to force cleanup
force_cleanup() {
    echo -e "${YELLOW}Performing force cleanup...${NC}"
    
    # Kill all processes more aggressively
    pkill -9 -f "python.*native_app.py" 2>/dev/null || true
    pkill -9 -f "python.*app.py" 2>/dev/null || true  
    pkill -9 -f "node.*react-scripts" 2>/dev/null || true
    
    # Force kill processes on ports
    lsof -ti :5001 | xargs kill -9 2>/dev/null || true
    lsof -ti :3000 | xargs kill -9 2>/dev/null || true
    
    sleep 2
    echo -e "${GREEN}✓ Force cleanup completed${NC}"
}

# Function to show running processes
show_status() {
    echo -e "${BLUE}Current system status:${NC}"
    echo ""
    
    echo -e "${BLUE}Ports in use:${NC}"
    if check_port 5001; then
        echo -e "${YELLOW}• Port 5001: $(lsof -i :5001 | tail -n +2 | awk '{print $1}')${NC}"
    else
        echo -e "${GREEN}• Port 5001: Free${NC}"
    fi
    
    if check_port 3000; then
        echo -e "${YELLOW}• Port 3000: $(lsof -i :3000 | tail -n +2 | awk '{print $1}')${NC}"
    else
        echo -e "${GREEN}• Port 3000: Free${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}Related processes:${NC}"
    
    if pgrep -f "python.*native_app.py" > /dev/null 2>&1; then
        echo -e "${YELLOW}• Native app: Running (PID: $(pgrep -f 'python.*native_app.py'))${NC}"
    else
        echo -e "${GREEN}• Native app: Not running${NC}"
    fi
    
    if pgrep -f "python.*app.py" > /dev/null 2>&1; then
        echo -e "${YELLOW}• Flask backend: Running (PID: $(pgrep -f 'python.*app.py'))${NC}"
    else
        echo -e "${GREEN}• Flask backend: Not running${NC}"
    fi
    
    if pgrep -f "node.*react-scripts" > /dev/null 2>&1; then
        echo -e "${YELLOW}• React frontend: Running (PID: $(pgrep -f 'node.*react-scripts'))${NC}"
    else
        echo -e "${GREEN}• React frontend: Not running${NC}"
    fi
}

# Main execution
main() {
    case "${1:-}" in
        --force)
            echo -e "${YELLOW}Force stop mode enabled${NC}"
            force_cleanup
            ;;
        --status)
            show_status
            exit 0
            ;;
        --help|-h)
            echo "Usage: $0 [--force] [--status] [--help]"
            echo ""
            echo "Options:"
            echo "  --force          Force kill all processes immediately"
            echo "  --status         Show current status without stopping"
            echo "  --help, -h       Show this help message"  
            echo ""
            echo "Examples:"
            echo "  ./stop.sh                # Graceful shutdown"
            echo "  ./stop.sh --force        # Force kill all processes"
            echo "  ./stop.sh --status       # Check current status"
            exit 0
            ;;
        "")
            # Normal graceful shutdown
            stop_processes
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information."
            exit 1
            ;;
    esac
    
    # Verify cleanup unless force mode was used
    if [ "${1:-}" != "--force" ]; then
        echo ""
        if verify_cleanup; then
            echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${GREEN}✅ Document Search System stopped successfully${NC}"
            echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        else
            echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${YELLOW}⚠️  Some processes may still be running${NC}"
            echo -e "${YELLOW}   Run './stop.sh --force' for aggressive cleanup${NC}"
            echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}✅ Force cleanup completed${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    fi
}

# Run main function
main "$@"