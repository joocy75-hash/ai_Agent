#!/bin/bash
#
# ML Model Quick Training Script
# 원클릭으로 ML 모델 학습 실행 (인증 불필요)
#
# Usage:
#   ./scripts/quick_train.sh              # 기본: ETH 60일 데이터
#   ./scripts/quick_train.sh --quick      # 빠른 테스트: 7일
#   ./scripts/quick_train.sh --symbol BTCUSDT --days 90
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Project paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Find Python
if [ -f "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11" ]; then
    PYTHON="/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11"
else
    PYTHON="python3"
fi

echo -e "${BLUE}"
echo "=========================================="
echo "   ML Model Training Pipeline"
echo "=========================================="
echo -e "${NC}"

# Check dependencies
echo -e "${YELLOW}Checking dependencies...${NC}"
$PYTHON -c "import lightgbm; print(f'  LightGBM: {lightgbm.__version__}')" 2>/dev/null || {
    echo -e "${RED}LightGBM not installed. Installing...${NC}"
    pip3 install lightgbm
}
$PYTHON -c "import aiohttp; print(f'  aiohttp: {aiohttp.__version__}')" 2>/dev/null || {
    echo -e "${RED}aiohttp not installed. Installing...${NC}"
    pip3 install aiohttp
}
$PYTHON -c "import pandas; print(f'  pandas: {pandas.__version__}')" 2>/dev/null
echo ""

# Create directories
mkdir -p "$PROJECT_ROOT/src/ml/saved_models"
mkdir -p "$PROJECT_ROOT/src/ml/data"
mkdir -p "$PROJECT_ROOT/logs"

# Run training
echo -e "${YELLOW}Starting ML training...${NC}"
echo ""

cd "$PROJECT_ROOT"
$PYTHON scripts/train_ml_pipeline.py "$@"

# Check results
echo ""
echo -e "${YELLOW}Checking saved models...${NC}"
if [ -d "$PROJECT_ROOT/src/ml/saved_models" ]; then
    MODEL_COUNT=$(ls -1 "$PROJECT_ROOT/src/ml/saved_models"/*.txt 2>/dev/null | wc -l | tr -d ' ')
    if [ "$MODEL_COUNT" -gt 0 ]; then
        echo -e "${GREEN}Success! $MODEL_COUNT model(s) saved${NC}"
    else
        echo -e "${RED}No models saved. Check logs.${NC}"
    fi
fi

echo ""
echo -e "${BLUE}=========================================="
echo "   Done!"
echo -e "==========================================${NC}"
