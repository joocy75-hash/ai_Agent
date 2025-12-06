#!/bin/bash

# 🚀 Auto Dashboard Deployment Script
# This script helps you deploy the trading bot system

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Auto Dashboard Deployment Script${NC}"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from .env.example...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ Created .env file${NC}"
        echo -e "${YELLOW}⚠️  Please edit .env and set your actual credentials!${NC}"
        echo ""
        read -p "Press Enter to continue after editing .env..."
    else
        echo -e "${RED}❌ .env.example not found!${NC}"
        exit 1
    fi
fi

# Generate encryption key if not set
if ! grep -q "ENCRYPTION_KEY=your-32-byte" .env 2>/dev/null; then
    echo -e "${GREEN}✅ Encryption key already set${NC}"
else
    echo -e "${YELLOW}⚠️  Generating new encryption key...${NC}"
    ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    sed -i.bak "s|ENCRYPTION_KEY=.*|ENCRYPTION_KEY=$ENCRYPTION_KEY|" .env
    rm -f .env.bak
    echo -e "${GREEN}✅ Generated encryption key${NC}"
fi

# Generate JWT secret if not set
if grep -q "JWT_SECRET=your-super-secret" .env 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Generating new JWT secret...${NC}"
    JWT_SECRET=$(openssl rand -hex 32)
    sed -i.bak "s|JWT_SECRET=.*|JWT_SECRET=$JWT_SECRET|" .env
    rm -f .env.bak
    echo -e "${GREEN}✅ Generated JWT secret${NC}"
fi

echo ""
echo -e "${GREEN}📋 Deployment Options:${NC}"
echo "  1. Development (SQLite, local)"
echo "  2. Production (PostgreSQL, Docker)"
echo "  3. Production with Nginx (HTTPS)"
echo ""
read -p "Select option (1-3): " OPTION

case $OPTION in
    1)
        echo -e "${GREEN}🔧 Starting development environment...${NC}"

        # Backend
        cd backend
        if [ ! -d "venv" ]; then
            echo -e "${YELLOW}Creating virtual environment...${NC}"
            python3 -m venv venv
        fi
        source venv/bin/activate
        pip install -r requirements.txt

        export DATABASE_URL="sqlite+aiosqlite:///./trading.db"
        export $(grep -v '^#' ../.env | xargs)

        echo -e "${GREEN}Starting backend...${NC}"
        uvicorn src.main:app --reload &
        BACKEND_PID=$!

        cd ../frontend
        echo -e "${GREEN}Starting frontend...${NC}"
        npm install
        npm run dev &
        FRONTEND_PID=$!

        echo ""
        echo -e "${GREEN}✅ Development environment started!${NC}"
        echo -e "Backend: http://localhost:8000"
        echo -e "Frontend: http://localhost:3000"
        echo ""
        echo "Press Ctrl+C to stop..."

        wait $BACKEND_PID $FRONTEND_PID
        ;;

    2)
        echo -e "${GREEN}🐳 Starting Docker Compose (without Nginx)...${NC}"
        docker-compose up -d postgres redis backend frontend

        echo ""
        echo -e "${GREEN}✅ Services started!${NC}"
        docker-compose ps

        echo ""
        echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
        sleep 10

        echo ""
        echo -e "${GREEN}🔍 Health checks:${NC}"
        curl -s http://localhost:8000/health | jq .

        echo ""
        echo -e "${GREEN}✅ Deployment complete!${NC}"
        echo -e "Backend API: http://localhost:8000"
        echo -e "Frontend: http://localhost:3000"
        echo -e "PostgreSQL: localhost:5432"
        echo ""
        echo -e "View logs: ${YELLOW}docker-compose logs -f${NC}"
        echo -e "Stop services: ${YELLOW}docker-compose down${NC}"
        ;;

    3)
        echo -e "${GREEN}🔒 Starting full production stack with Nginx...${NC}"

        # Check SSL certificates
        if [ ! -f nginx/ssl/fullchain.pem ] || [ ! -f nginx/ssl/privkey.pem ]; then
            echo -e "${RED}❌ SSL certificates not found in nginx/ssl/${NC}"
            echo -e "${YELLOW}Please place your SSL certificates in nginx/ssl/:${NC}"
            echo "  - fullchain.pem"
            echo "  - privkey.pem"
            echo ""
            echo -e "${YELLOW}For Let's Encrypt, use:${NC}"
            echo "  sudo certbot certonly --standalone -d yourdomain.com -d api.yourdomain.com"
            exit 1
        fi

        docker-compose --profile production up -d

        echo ""
        echo -e "${GREEN}✅ Production stack started!${NC}"
        docker-compose ps

        echo ""
        echo -e "${GREEN}✅ Deployment complete!${NC}"
        echo -e "HTTPS Frontend: https://yourdomain.com"
        echo -e "HTTPS API: https://api.yourdomain.com"
        echo ""
        echo -e "View logs: ${YELLOW}docker-compose logs -f${NC}"
        ;;

    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}🎉 Deployment successful!${NC}"
