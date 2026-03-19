#!/bin/bash
# ============================================================================
# GHL Sales Assistant - Deployment Script (Linux/macOS)
# Usage: ./deploy.sh [--build] [--restart] [--logs] [--stop]
#
# Flags:
#   --build    Force rebuild Docker images
#   --restart  Restart containers
#   --logs     Follow container logs
#   --stop     Stop all containers
#   (no flag)  Build + start (default)
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

PROJECT_NAME="GHL Sales Assistant"
COMPOSE_FILE="docker-compose.yml"
ENV_FILE="backend/.env"
ENV_EXAMPLE="backend/.env.example"

# ── Helper functions ───────────────────────────────────────────────

log_info()  { echo -e "${CYAN}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_err()   { echo -e "${RED}[ERROR]${NC} $1"; }

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_err "$1 is not installed. Please install $1 first."
        exit 1
    fi
}

# ── Preflight checks ──────────────────────────────────────────────

preflight() {
    log_info "Running preflight checks..."

    # Check Docker
    check_command "docker"
    log_ok "Docker found: $(docker --version)"

    # Check Docker Compose (v2 plugin or standalone)
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
        log_ok "Docker Compose found: $(docker compose version --short)"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
        log_ok "Docker Compose found: $(docker-compose --version)"
    else
        log_err "Docker Compose is not installed. Please install Docker Compose."
        exit 1
    fi

    # Check .env file
    if [ ! -f "$ENV_FILE" ]; then
        log_warn ".env file not found at $ENV_FILE"
        if [ -f "$ENV_EXAMPLE" ]; then
            cp "$ENV_EXAMPLE" "$ENV_FILE"
            log_warn "Copied $ENV_EXAMPLE → $ENV_FILE"
            log_warn ">>> EDIT $ENV_FILE with your actual credentials before proceeding! <<<"
            echo ""
            read -p "Press Enter after editing .env, or Ctrl+C to abort..."
        else
            log_err "No .env.example found either. Create $ENV_FILE manually."
            exit 1
        fi
    else
        log_ok ".env file exists at $ENV_FILE"
    fi

    log_ok "Preflight checks passed."
    echo ""
}

# ── Actions ────────────────────────────────────────────────────────

do_build() {
    log_info "Building Docker images..."
    $COMPOSE_CMD -f "$COMPOSE_FILE" build --no-cache
    log_ok "Build complete."
}

do_start() {
    log_info "Starting $PROJECT_NAME..."
    $COMPOSE_CMD -f "$COMPOSE_FILE" up -d
    echo ""
    log_ok "$PROJECT_NAME is starting."
    echo ""
    show_status
}

do_build_and_start() {
    log_info "Building and starting $PROJECT_NAME..."
    $COMPOSE_CMD -f "$COMPOSE_FILE" up -d --build
    echo ""
    log_ok "$PROJECT_NAME is running."
    echo ""
    show_status
}

do_restart() {
    log_info "Restarting $PROJECT_NAME..."
    $COMPOSE_CMD -f "$COMPOSE_FILE" restart
    log_ok "Restart complete."
    echo ""
    show_status
}

do_stop() {
    log_info "Stopping $PROJECT_NAME..."
    $COMPOSE_CMD -f "$COMPOSE_FILE" down
    log_ok "All containers stopped."
}

do_logs() {
    log_info "Showing logs (Ctrl+C to exit)..."
    $COMPOSE_CMD -f "$COMPOSE_FILE" logs -f
}

show_status() {
    log_info "Container status:"
    $COMPOSE_CMD -f "$COMPOSE_FILE" ps
    echo ""

    # Extract host port
    PORT=$(grep -oP '^\s*-\s*"\K[0-9]+' "$COMPOSE_FILE" | head -1 2>/dev/null || echo "8000")
    log_info "Access URL: http://localhost:${PORT}"
    log_info "Health check: http://localhost:${PORT}/health"
    log_info "API docs: http://localhost:${PORT}/docs"
}

# ── Main ───────────────────────────────────────────────────────────

echo ""
echo "=========================================="
echo "  $PROJECT_NAME — Deploy"
echo "=========================================="
echo ""

case "${1:-}" in
    --build)
        preflight
        do_build
        do_start
        ;;
    --restart)
        do_restart
        ;;
    --logs)
        do_logs
        ;;
    --stop)
        do_stop
        ;;
    "")
        preflight
        do_build_and_start
        ;;
    *)
        echo "Usage: $0 [--build] [--restart] [--logs] [--stop]"
        echo ""
        echo "  --build    Force rebuild images (no cache)"
        echo "  --restart  Restart running containers"
        echo "  --logs     Follow container logs"
        echo "  --stop     Stop all containers"
        echo "  (no flag)  Build + start (default)"
        exit 1
        ;;
esac
