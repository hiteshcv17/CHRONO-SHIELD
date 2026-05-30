#!/usr/bin/env bash

# ==============================================================================
# ChronoShield AI Monorepo Bootstrapping Script
# ==============================================================================
# Configures local directories, python virtual environments, compiles settings,
# and installs npm modules for development.

set -euo pipefail

# ANSI color codes for rich logging outputs
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
NC='\033[0;3m' # No Color

log_info() {
    echo -e "${BLUE}[INFO] $(date +'%Y-%m-%dT%H:%M:%S') - $1${NC}"
}

log_success() {
    echo -e "${GREEN}[SUCCESS] $(date +'%Y-%m-%dT%H:%M:%S') - $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}[WARN] $(date +'%Y-%m-%dT%H:%M:%S') - $1${NC}"
}

log_error() {
    echo -e "${RED}[ERROR] $(date +'%Y-%m-%dT%H:%M:%S') - $1${NC}"
}

# 1. Check current directory
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

log_info "Initializing ChronoShield AI Monorepo foundations..."

# 2. Check System Prerequisites
log_info "Checking system requirements..."
for cmd in docker python3 node npm; do
    if ! command -v "$cmd" &> /dev/null; then
        log_warn "Command '$cmd' is not available on this system. Some local tasks may be disabled."
    else
        log_success "Found utility: $cmd ($(which "$cmd"))"
    fi
done

# 3. Create Local Folders
log_info "Creating local monorepo cache and logging structures..."
mkdir -p logs configs datasets tests docs

# 4. Copy Environment Variable Template
if [ ! -f .env ]; then
    log_info "Creating local development environment '.env' file from '.env.example'..."
    cp .env.example .env
    log_success ".env file successfully created. Please configure secrets prior to launching."
else
    log_info "Local '.env' configuration already exists. Skipping."
fi

# 5. Initialize Python virtual environment for Backend
log_info "Setting up Python virtual environment for Backend Microservice..."
if [ -d backend ]; then
    cd backend
    python3 -m venv venv || python -m venv venv
    log_success "Backend virtualenv configured in: backend/venv/"
    
    # Optional local dependency installs
    log_info "To install backend dependencies, execute: source venv/bin/activate && pip install -r requirements.txt"
    cd "${ROOT_DIR}"
else
    log_warn "Backend directory not found. Skipping virtual environment creation."
fi

# 6. Initialize Python virtual environment for AI Engine
log_info "Setting up Python virtual environment for AI Engine Microservice..."
if [ -d ai-engine ]; then
    cd ai-engine
    python3 -m venv venv || python -m venv venv
    log_success "AI Engine virtualenv configured in: ai-engine/venv/"
    
    log_info "To install AI dependencies, execute: source venv/bin/activate && pip install -r requirements.txt"
    cd "${ROOT_DIR}"
else
    log_warn "AI Engine directory not found. Skipping virtual environment creation."
fi

# 7. Frontend Dependency Reminders
if [ -d frontend ]; then
    log_info "Found Frontend React service. To install npm modules: cd frontend && npm install"
fi

log_success "ChronoShield AI Monorepo successfully bootstrapped!"
log_info "To spin up all services via docker: docker compose -f infrastructure/docker-compose.yml up --build"
log_info "Have a productive session coding!"
