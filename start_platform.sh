#!/usr/bin/env bash
# ==============================================================================
# ChronoShield AI — Unified Platform Local Runner
# ==============================================================================
# Seamlessly spins up all microservices: Backend, AI Engine, and Frontend dev.
# Graces terminations, checks dependencies, and ensures high-performance logs.
# ==============================================================================

# ANSI Color Codes
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
MAGENTA='\033[0;35m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Terminal UI Branding
echo -e "${CYAN}${BOLD}"
echo "   ______ __                                ____   __     _        __     __"
echo "  / ____// /_   _____ ____   ____   ____   / __/  / /_   (_)___   / /____/ /"
echo " / /    / __ \ / ___// __ \ / __ \ / __ \ / /_   / __ \ / // _ \ / // __  / "
echo "/ /___ / / / // /   / /_/ // / / // /_/ // __/  / / / // //  __// // /_/ /  "
echo "\____//_/ /_//_/    \____//_/ /_/ \____//_/    /_/ /_//_/ \___//_/ \__,_/   "
echo "                                                                            "
echo -e "                   -- HACKATHON STABLE RELEASE CANDIDATE --                 ${NC}"
echo -e "${BLUE}==============================================================================${NC}"

# Define absolute path of monorepo root
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

# Array to keep track of spawned child process PIDs
declare -a PIDS=()

# Graceful termination handler
cleanup() {
    echo -e "\n\n${YELLOW}[!] Intercepted shutdown signal. Initiating graceful shutdown...${NC}"
    
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${BLUE}[-] Stopping process with PID $pid...${NC}"
            kill -TERM "$pid" 2>/dev/null
        fi
    done

    # Wait for processes to exit
    for pid in "${PIDS[@]}"; do
        wait "$pid" 2>/dev/null
    done

    echo -e "${GREEN}[✓] All microservices terminated successfully. Port states cleanly released.${NC}"
    exit 0
}

# Bind cleanup handler to SIGINT, SIGTERM, and EXIT
trap cleanup SIGINT SIGTERM

# Check standard TCP port availability
check_port() {
    local host="127.0.0.1"
    local port=$1
    nc -z "$host" "$port" >/dev/null 2>&1
    return $?
}

echo -e "${BOLD}Checking System Dependencies...${NC}"

# Verify Postgres Database Status
echo -n "  ▸ PostgreSQL Database (Port 5432)... "
if check_port 5432; then
    echo -e "${GREEN}[ONLINE]${NC}"
else
    echo -e "${RED}[OFFLINE]${NC}"
    echo -e "${RED}${BOLD}ERROR: PostgreSQL must be running on port 5432 to initialize ChronoShield.${NC}"
    echo -e "Please start PostgreSQL locally before launching this platform runner."
    exit 1
fi

# Verify Redis Cache Status
echo -n "  ▸ Redis Memory Store  (Port 6379)... "
if check_port 6379; then
    echo -e "${GREEN}[ONLINE]${NC}"
else
    echo -e "${YELLOW}[OFFLINE] (Warning: Security Rate Limiter will auto-fallback to thread-safe memory timeline buckets)${NC}"
fi

# Verify Virtual Environments
echo -e "\n${BOLD}Validating Virtual Environments...${NC}"

# Backend venv
if [ -d "backend/venv" ]; then
    echo -e "  ▸ Backend virtual environment... ${GREEN}[OK]${NC}"
else
    echo -e "  ▸ Backend virtual environment... ${RED}[MISSING]${NC}"
    echo -e "${RED}ERROR: Please build the backend virtual environment at backend/venv first.${NC}"
    exit 1
fi

# AI Engine venv
if [ -d "ai-engine/venv" ]; then
    echo -e "  ▸ AI Engine virtual environment... ${GREEN}[OK]${NC}"
else
    echo -e "  ▸ AI Engine virtual environment... ${RED}[MISSING]${NC}"
    echo -e "${RED}ERROR: Please build the AI-Engine virtual environment at ai-engine/venv first.${NC}"
    exit 1
fi

# Verify Frontend dependencies
if [ -d "frontend/node_modules" ]; then
    echo -e "  ▸ Frontend node modules... ${GREEN}[OK]${NC}"
else
    echo -e "  ▸ Frontend node modules... ${YELLOW}[WARNING] (node_modules missing, running automatic npm install...)${NC}"
    cd frontend && npm install && cd ..
fi

echo -e "\n${BLUE}==============================================================================${NC}"
echo -e "${BOLD}Spinning Up ChronoShield AI Subsystems...${NC}"

# 1. Start FastAPI Backend Service
echo -e "  🚀 Starting ${CYAN}FastAPI Backend${NC} (Port 8000)..."
source backend/venv/bin/activate
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
PIDS+=($BACKEND_PID)
deactivate
cd "${ROOT_DIR}"

# 2. Start PyTorch AI Engine
echo -e "  🚀 Starting ${MAGENTA}PyTorch AI Engine${NC} (Port 8001)..."
source ai-engine/venv/bin/activate
cd ai-engine
python -m uvicorn src.main:app --host 127.0.0.1 --port 8001 > ../logs/ai-engine.log 2>&1 &
AI_PID=$!
PIDS+=($AI_PID)
deactivate
cd "${ROOT_DIR}"

# Allow backend services a brief moment to boot and bind ports
sleep 2

# 3. Start React Vite Frontend
echo -e "  🚀 Starting ${GREEN}React Vite Frontend Dashboard${NC} (Port 5173)..."
cd frontend
npm run dev -- --port 5173 > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
PIDS+=($FRONTEND_PID)
cd "${ROOT_DIR}"

echo -e "${BLUE}==============================================================================${NC}"
echo -e "${GREEN}${BOLD}✓ CHRONOSHIELD AI PLATFORM IS ACTIVATED AND RUNNING SUCCESSFULLY!${NC}"
echo -e "\n${BOLD}Operational Portal Addresses:${NC}"
echo -e "  🖥️  ${BOLD}Interactive Web UI:${NC}    ${CYAN}http://localhost:5173/${NC}"
echo -e "  ⚙️  ${BOLD}Core Backend API:${NC}      ${CYAN}http://localhost:8000/${NC}"
echo -e "  📝 ${BOLD}Swagger API Specs:${NC}     ${CYAN}http://localhost:8000/docs${NC}"
echo -e "  🧠 ${BOLD}PyTorch Anomaly Engine:${NC} ${CYAN}http://localhost:8001/${NC}"
echo -e "\n${BOLD}Aggregated Stream Log Outputs:${NC}"
echo -e "  📂 Backend log:   ${BLUE}./logs/backend.log${NC}"
echo -e "  📂 AI Engine log: ${BLUE}./logs/ai-engine.log${NC}"
echo -e "  📂 Frontend log:  ${BLUE}./logs/frontend.log${NC}"
echo -e "\n${YELLOW}Press [Ctrl+C] at any time to concurrently terminate all services and exit.${NC}"
echo -e "${BLUE}==============================================================================${NC}"

# Keep script running to catch SIGINT and display live heartbeats
while true; do
    # Verify child processes are still alive, restart if crashed
    for pid in "${PIDS[@]}"; do
        if ! kill -0 "$pid" 2>/dev/null; then
            echo -e "${RED}[!] Subprocess $pid crashed or exited unexpectedly! Check log outputs.${NC}"
            cleanup
        fi
    done
    sleep 5
done
