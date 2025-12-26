#!/bin/bash

# Production Deployment Script
# Server: 158.247.245.197

set -e

echo "════════════════════════════════════════════════════════════════"
echo "🚀 Production Deployment Script"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Configuration
SERVER="root@158.247.245.197"
PASSWORD="Vc8,xn7j_fjdnNGy"
DEPLOY_DIR="/root/auto-dashboard"

echo "Step 1: Creating production environment file on server..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER << 'ENDSSH'
cd /root/auto-dashboard

# Create .env.production file
cat > .env.production << 'EOF'
# Database Configuration
POSTGRES_PASSWORD=trading_prod_password_2025_secure
DATABASE_URL=postgresql+asyncpg://trading_user:trading_prod_password_2025_secure@postgres:5432/trading_prod

# Redis Configuration
REDIS_PASSWORD=redis_password_2025_secure
REDIS_URL=redis://default:redis_password_2025_secure@redis:6379

# Security Keys
ENCRYPTION_KEY=Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8=
JWT_SECRET=prod_jwt_secret_key_change_this_in_production_2025

# Application Settings
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=INFO

# CORS Origins (adjust for your domain)
CORS_ORIGINS=http://158.247.245.197:3000,http://158.247.245.197:4000

# DeepSeek API (optional)
DEEPSEEK_API_KEY=sk-1c9d4ea0b16a40768ccfec9c5c81adef

# Telegram (optional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
EOF

echo "✅ Environment file created"
ENDSSH

echo ""
echo "Step 2: Building Docker images on server..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER << 'ENDSSH'
cd /root/auto-dashboard

# Stop any running containers
docker compose down 2>/dev/null || true

# Build images
echo "Building backend image..."
docker compose build backend

echo "Building frontend images..."
docker compose build frontend admin-frontend

echo "✅ Docker images built successfully"
ENDSSH

echo ""
echo "Step 3: Starting services..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER << 'ENDSSH'
cd /root/auto-dashboard

# Start services with production environment
docker compose --env-file .env.production up -d

# Wait for services to start
sleep 10

# Check status
docker compose ps

echo "✅ Services started"
ENDSSH

echo ""
echo "Step 4: Running health checks..."
sleep 5

echo "Backend health check:"
curl -s http://158.247.245.197:8000/health | jq '.' || echo "Backend not ready yet"

echo ""
echo "Frontend check:"
curl -s -I http://158.247.245.197:3000 | head -1 || echo "Frontend not ready yet"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ Deployment Complete!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Services:"
echo "  User Frontend:   http://158.247.245.197:3000"
echo "  Admin Frontend:  http://158.247.245.197:4000"
echo "  Backend API:     http://158.247.245.197:8000"
echo "  API Docs:        http://158.247.245.197:8000/docs"
echo ""
echo "Useful commands:"
echo "  View logs:    ssh root@158.247.245.197 'cd /root/auto-dashboard && docker compose logs -f'"
echo "  Restart:      ssh root@158.247.245.197 'cd /root/auto-dashboard && docker compose restart'"
echo "  Stop:         ssh root@158.247.245.197 'cd /root/auto-dashboard && docker compose down'"
echo ""
echo "════════════════════════════════════════════════════════════════"
