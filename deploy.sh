#!/bin/bash
# HyperBot Deployment & Management Script
# Usage: ./deploy.sh [install|start|stop|restart|status|logs]

set -e

BOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BOT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() { echo -e "${BLUE}ℹ${NC} $1"; }
echo_success() { echo -e "${GREEN}✓${NC} $1"; }
echo_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
echo_error() { echo -e "${RED}✗${NC} $1"; }

# Check if PM2 is installed
check_pm2() {
    if ! command -v pm2 &> /dev/null; then
        echo_warning "PM2 not found. Installing..."
        npm install -g pm2
        echo_success "PM2 installed"
    fi
}

# Install dependencies
install() {
    echo_info "Installing HyperBot dependencies..."
    
    # Check Python version
    if ! command -v python3 &> /dev/null; then
        echo_error "Python 3 not found. Please install Python 3.9+"
        exit 1
    fi
    
    # Install Python packages
    echo_info "Installing Python packages..."
    pip3 install -r requirements.txt
    
    # Install PM2 if not exists
    check_pm2
    
    # Check .env file
    if [ ! -f .env ]; then
        echo_warning ".env file not found!"
        if [ -f .env.example ]; then
            echo_info "Copying .env.example to .env"
            cp .env.example .env
            echo_warning "Please configure .env with your credentials"
        else
            echo_error "No .env or .env.example found!"
            exit 1
        fi
    fi
    
    echo_success "Installation complete!"
    echo_info "Next steps:"
    echo "  1. Configure .env with your API keys"
    echo "  2. Run: ./deploy.sh start"
}

# Start bot with PM2
start() {
    check_pm2
    
    echo_info "Starting HyperBot with PM2..."
    
    # Check if already running
    if pm2 list | grep -q "hyperbot"; then
        echo_warning "HyperBot already running. Use './deploy.sh restart' to restart."
        return 0
    fi
    
    # Start with PM2
    pm2 start ecosystem.config.js
    pm2 save
    
    echo_success "HyperBot started!"
    echo_info "View logs: ./deploy.sh logs"
    echo_info "Check status: ./deploy.sh status"
}

# Stop bot
stop() {
    echo_info "Stopping HyperBot..."
    pm2 stop hyperbot 2>/dev/null || echo_warning "HyperBot not running"
    echo_success "HyperBot stopped"
}

# Restart bot
restart() {
    echo_info "Restarting HyperBot..."
    pm2 restart hyperbot 2>/dev/null || {
        echo_warning "HyperBot not running, starting fresh..."
        start
    }
    echo_success "HyperBot restarted"
}

# Show status
status() {
    check_pm2
    echo_info "HyperBot Status:"
    pm2 list | grep -A 1 "hyperbot" || echo_warning "HyperBot not running"
    echo ""
    pm2 describe hyperbot 2>/dev/null || echo_warning "No detailed info available"
}

# Show logs
logs() {
    echo_info "Streaming HyperBot logs (Ctrl+C to exit)..."
    pm2 logs hyperbot --lines 50
}

# Show help
help() {
    echo "HyperBot Deployment Script"
    echo ""
    echo "Usage: ./deploy.sh [command]"
    echo ""
    echo "Commands:"
    echo "  install   - Install dependencies and setup"
    echo "  start     - Start HyperBot with PM2"
    echo "  stop      - Stop HyperBot"
    echo "  restart   - Restart HyperBot"
    echo "  status    - Show bot status"
    echo "  logs      - Stream bot logs"
    echo "  help      - Show this help"
    echo ""
    echo "PM2 Commands:"
    echo "  pm2 monit              - Real-time monitoring"
    echo "  pm2 logs hyperbot      - Stream logs"
    echo "  pm2 restart hyperbot   - Restart bot"
    echo "  pm2 stop hyperbot      - Stop bot"
    echo "  pm2 delete hyperbot    - Remove from PM2"
}

# Main command handler
case "${1:-help}" in
    install)
        install
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    help|*)
        help
        ;;
esac
