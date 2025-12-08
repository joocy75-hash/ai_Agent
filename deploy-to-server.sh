#!/bin/bash
# Deployment script for Vultr server
# Server IP: 158.247.245.197

set -e  # Exit on error

SERVER_IP="158.247.245.197"
SERVER_USER="root"
PROJECT_DIR="/root/auto-dashboard"

echo "🚀 Starting deployment to $SERVER_IP..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Copy files to server
echo -e "${YELLOW}📦 Step 1: Copying files to server...${NC}"
rsync -avz --exclude 'node_modules' \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude 'dist' \
  --exclude 'build' \
  --exclude '.env' \
  ./ ${SERVER_USER}@${SERVER_IP}:${PROJECT_DIR}/

# Step 2: Run deployment on server
echo -e "${YELLOW}📦 Step 2: Running deployment on server...${NC}"
ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
cd /root/auto-dashboard

# Create .env.production if not exists
if [ ! -f .env.production ]; then
  echo "Creating .env.production..."
  cat > .env.production << 'EOF'
# PostgreSQL
POSTGRES_PASSWORD=TradingBot2024!SecurePassword

# Redis
REDIS_PASSWORD=Redis2024!SecurePassword

# Backend Security
ENCRYPTION_KEY=Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8=
JWT_SECRET=super-secret-jwt-key-change-this-in-production-2024

# Frontend URLs
VITE_API_URL=http://158.247.245.197:8000

# CORS Origins
ALLOWED_ORIGINS=http://158.247.245.197:3000,http://158.247.245.197:4000,http://158.247.245.197

# Logging
LOG_LEVEL=INFO
EOF
fi

# Stop existing containers
echo "Stopping existing containers..."
docker-compose --env-file .env.production down

# Pull latest images
echo "Building Docker images..."
docker-compose --env-file .env.production build --no-cache

# Start containers
echo "Starting containers..."
docker-compose --env-file .env.production up -d

# Wait for services to be healthy
echo "Waiting for services to start..."
sleep 10

# Check if services are running
docker-compose --env-file .env.production ps

# Create admin account
echo "Creating admin account..."
docker exec trading-backend python -m src.scripts.create_admin_user || echo "Admin user might already exist"

echo "✅ Deployment complete!"
ENDSSH

echo -e "${GREEN}✅ Deployment to $SERVER_IP completed!${NC}"
echo ""
echo "📋 Service URLs:"
echo "  Frontend:  http://$SERVER_IP:3000"
echo "  Backend:   http://$SERVER_IP:8000"
echo "  Admin:     http://$SERVER_IP:4000"
echo ""
echo "🔐 Login credentials:"
echo "  Email:     admin@admin.com"
echo "  Password:  Admin123!"
