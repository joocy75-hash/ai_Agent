#!/bin/bash

# Production Deployment Script
# Server: 5.161.112.248 (Hetzner)

set -e

echo "════════════════════════════════════════════════════════════════"
echo "🚀 Production Deployment Script"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Configuration
SERVER="root@5.161.112.248"
SSH_KEY="~/.ssh/hetzner_deploy_key"
DEPLOY_DIR="/root/service_c/ai-trading-platform"

echo "Step 1: Syncing files to server..."
rsync -avz --delete \
    --exclude 'node_modules' \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.env' \
    --exclude 'trading.db' \
    --exclude 'logs/*' \
    --exclude '.scannerwork' \
    -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
    ./ $SERVER:$DEPLOY_DIR/

echo "✅ Files synced"

echo ""
echo "Step 2: Building Docker images on server..."
ssh -i $SSH_KEY -o StrictHostKeyChecking=no $SERVER << 'ENDSSH'
cd /root/service_c/ai-trading-platform

# Build images
echo "Building backend image..."
docker compose -f docker-compose.production.yml build backend

echo "Building frontend images..."
docker compose -f docker-compose.production.yml build frontend admin-frontend

echo "✅ Docker images built successfully"
ENDSSH

echo ""
echo "Step 3: Starting services..."
ssh -i $SSH_KEY -o StrictHostKeyChecking=no $SERVER << 'ENDSSH'
cd /root/service_c/ai-trading-platform

# Start services
docker compose -f docker-compose.production.yml up -d

# Wait for services to start
sleep 10

# Check status
docker ps --filter name=groupc-

echo "✅ Services started"
ENDSSH

echo ""
echo "Step 4: Running health checks..."
sleep 5

echo "Backend health check:"
curl -s http://5.161.112.248:8000/health || echo "Backend not ready yet"

echo ""
echo "Frontend check:"
curl -s -I http://5.161.112.248:3001 | head -1 || echo "Frontend not ready yet"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ Deployment Complete!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Services:"
echo "  User Frontend:   https://deepsignal.shop (Internal: http://5.161.112.248:3001)"
echo "  Admin Frontend:  https://admin.deepsignal.shop (Internal: http://5.161.112.248:4000)"
echo "  Backend API:     https://api.deepsignal.shop (Internal: http://5.161.112.248:8000)"
echo ""
echo "════════════════════════════════════════════════════════════════"
