#!/bin/bash

# ============================================================
# Integrated Deployment Script
# Supports Group A, B, C and Global Proxy
# ============================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Base directory
BASE_DIR="/root"

# Function to display usage
usage() {
    echo -e "${YELLOW}Usage: $0 {proxy|group_a|group_b|group_c|all|status|logs} [command]${NC}"
    echo "Examples:"
    echo "  $0 group_c deploy    - Deploy Group C"
    echo "  $0 group_c stop      - Stop Group C"
    echo "  $0 group_c logs      - Show logs for Group C"
    echo "  $0 proxy deploy      - Deploy Global Proxy"
    echo "  $0 status            - Show status of all services"
    exit 1
}

# Create shared network if not exists
setup_network() {
    if ! docker network ls | grep -q "proxy-net"; then
        echo -e "${YELLOW}Creating shared network: proxy-net...${NC}"
        docker network create proxy-net
    fi
}

# Generic management function
manage_service() {
    local group=$1
    local action=$2
    local compose_file=${3:-docker-compose.yml}
    
    if [ ! -d "${BASE_DIR}/${group}" ]; then
        echo -e "${RED}Directory ${BASE_DIR}/${group} not found.${NC}"
        return 1
    fi

    cd ${BASE_DIR}/${group}
    case $action in
        deploy)
            echo -e "${GREEN}Deploying ${group}...${NC}"
            setup_network
            docker compose -f ${compose_file} up -d --build
            ;;
        stop)
            echo -e "${RED}Stopping ${group}...${NC}"
            docker compose -f ${compose_file} down
            ;;
        logs)
            docker compose -f ${compose_file} logs -f
            ;;
        status)
            docker compose -f ${compose_file} ps
            ;;
        *)
            docker compose -f ${compose_file} ps
            ;;
    esac
}

# Main Logic
if [ -z "$1" ]; then
    usage
fi

case $1 in
    proxy)
        manage_service "proxy" ${2:-status}
        ;;
    group_a)
        manage_service "group_a" ${2:-status}
        ;;
    group_b)
        manage_service "group_b" ${2:-status}
        ;;
    group_c)
        manage_service "group_c" ${2:-status} "docker-compose.production.yml"
        ;;
    all)
        setup_network
        manage_service "proxy" deploy
        manage_service "group_a" deploy
        manage_service "group_c" deploy "docker-compose.production.yml"
        ;;
    status)
        echo -e "${YELLOW}--- Global Proxy Status ---${NC}"
        docker ps --filter name=global-proxy
        echo -e "\n${YELLOW}--- Group A Status ---${NC}"
        docker ps --filter name=groupa-
        echo -e "\n${YELLOW}--- Group B Status ---${NC}"
        docker ps --filter name=groupb-
        echo -e "\n${YELLOW}--- Group C Status ---${NC}"
        docker ps --filter name=groupc-
        ;;
    logs)
        if [ -z "$2" ]; then
            echo "Please specify a group: proxy, group_a, group_b, group_c"
            exit 1
        fi
        case $2 in
            proxy) manage_service "proxy" logs ;;
            group_a) manage_service "group_a" logs ;;
            group_b) manage_service "group_b" logs ;;
            group_c) manage_service "group_c" logs "docker-compose.production.yml" ;;
            *) echo "Logs for $2 not supported yet" ;;
        esac
        ;;
    *)
        usage
        ;;
esac
