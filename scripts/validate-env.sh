#!/bin/bash
# ============================================================
# Environment Variable Validation Script
# 배포 전 환경변수 검증 - 누락된 변수나 잘못된 설정 감지
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

print_header() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

check_required() {
    local var_name=$1
    local var_value=$2
    local description=$3

    if [ -z "$var_value" ] || [ "$var_value" == "your-"* ]; then
        echo -e "${RED}❌ MISSING: $var_name${NC}"
        echo -e "   ${description}"
        ((ERRORS++))
        return 1
    else
        echo -e "${GREEN}✅ $var_name${NC} = ${var_value:0:20}..."
        return 0
    fi
}

check_url() {
    local var_name=$1
    local var_value=$2
    local expected_protocol=$3

    if [ -z "$var_value" ]; then
        echo -e "${RED}❌ MISSING: $var_name${NC}"
        ((ERRORS++))
        return 1
    fi

    # Check protocol
    if [[ "$expected_protocol" == "https" ]] && [[ ! "$var_value" =~ ^https:// ]]; then
        echo -e "${YELLOW}⚠️  WARNING: $var_name should use HTTPS in production${NC}"
        echo -e "   Current: $var_value"
        ((WARNINGS++))
    fi

    # Check for localhost in production
    if [[ "$ENVIRONMENT" == "production" ]] && [[ "$var_value" =~ localhost ]]; then
        echo -e "${RED}❌ ERROR: $var_name contains 'localhost' in production!${NC}"
        echo -e "   Current: $var_value"
        ((ERRORS++))
        return 1
    fi

    echo -e "${GREEN}✅ $var_name${NC} = $var_value"
    return 0
}

check_secret_strength() {
    local var_name=$1
    local var_value=$2
    local min_length=$3

    if [ -z "$var_value" ]; then
        echo -e "${RED}❌ MISSING: $var_name${NC}"
        ((ERRORS++))
        return 1
    fi

    local length=${#var_value}
    if [ $length -lt $min_length ]; then
        echo -e "${YELLOW}⚠️  WARNING: $var_name is too short ($length chars, min $min_length)${NC}"
        ((WARNINGS++))
    else
        echo -e "${GREEN}✅ $var_name${NC} (length: $length)"
    fi
}

# ============================================================
# Main Validation
# ============================================================

print_header "🔍 Environment Variable Validation"

# Determine environment
ENV_FILE="${1:-.env}"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ Environment file not found: $ENV_FILE${NC}"
    exit 1
fi

echo -e "\n📂 Loading: $ENV_FILE"
source "$ENV_FILE"

# ============================================================
# Database & Cache
# ============================================================
print_header "🗄️  Database & Cache"

check_required "POSTGRES_PASSWORD" "$POSTGRES_PASSWORD" "Required for PostgreSQL authentication"
check_required "REDIS_PASSWORD" "$REDIS_PASSWORD" "Required for Redis authentication"

# ============================================================
# Security Keys
# ============================================================
print_header "🔐 Security Keys"

check_secret_strength "JWT_SECRET" "$JWT_SECRET" 32
check_secret_strength "ENCRYPTION_KEY" "$ENCRYPTION_KEY" 32

# ============================================================
# API URLs (Critical for Frontend)
# ============================================================
print_header "🌐 API URLs"

# Check VITE_API_URL
if [ "$ENVIRONMENT" == "production" ]; then
    check_url "VITE_API_URL" "$VITE_API_URL" "https"
else
    check_url "VITE_API_URL" "$VITE_API_URL" "http"
fi

# Verify CORS_ORIGINS includes frontend URL
if [ -n "$CORS_ORIGINS" ]; then
    echo -e "${GREEN}✅ CORS_ORIGINS${NC} = $CORS_ORIGINS"
else
    echo -e "${YELLOW}⚠️  WARNING: CORS_ORIGINS not set${NC}"
    ((WARNINGS++))
fi

# ============================================================
# Environment Consistency Check
# ============================================================
print_header "🔄 Consistency Checks"

# Check frontend/.env.production vs docker-compose VITE_API_URL
if [ -f "frontend/.env.production" ]; then
    FRONTEND_API_URL=$(grep "VITE_API_URL" frontend/.env.production | cut -d'=' -f2)
    if [ "$FRONTEND_API_URL" != "$VITE_API_URL" ]; then
        echo -e "${YELLOW}⚠️  WARNING: VITE_API_URL mismatch${NC}"
        echo -e "   .env: $VITE_API_URL"
        echo -e "   frontend/.env.production: $FRONTEND_API_URL"
        ((WARNINGS++))
    else
        echo -e "${GREEN}✅ VITE_API_URL consistent across files${NC}"
    fi
fi

# Check admin-frontend/.env.production
if [ -f "admin-frontend/.env.production" ]; then
    ADMIN_API_URL=$(grep "VITE_API_URL" admin-frontend/.env.production | cut -d'=' -f2)
    if [ "$ADMIN_API_URL" != "$VITE_API_URL" ]; then
        echo -e "${YELLOW}⚠️  WARNING: admin-frontend VITE_API_URL mismatch${NC}"
        echo -e "   .env: $VITE_API_URL"
        echo -e "   admin-frontend/.env.production: $ADMIN_API_URL"
        ((WARNINGS++))
    else
        echo -e "${GREEN}✅ admin-frontend VITE_API_URL consistent${NC}"
    fi
fi

# ============================================================
# Optional Services
# ============================================================
print_header "📦 Optional Services"

if [ -n "$DEEPSEEK_API_KEY" ] && [ "$DEEPSEEK_API_KEY" != "your-deepseek-api-key-here" ]; then
    echo -e "${GREEN}✅ DEEPSEEK_API_KEY${NC} configured"
else
    echo -e "${BLUE}ℹ️  DEEPSEEK_API_KEY not configured (AI features disabled)${NC}"
fi

if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ "$TELEGRAM_BOT_TOKEN" != "your-telegram-bot-token-here" ]; then
    echo -e "${GREEN}✅ TELEGRAM_BOT_TOKEN${NC} configured"
else
    echo -e "${BLUE}ℹ️  TELEGRAM_BOT_TOKEN not configured (Telegram notifications disabled)${NC}"
fi

# ============================================================
# Summary
# ============================================================
print_header "📊 Validation Summary"

echo -e "Environment: ${ENVIRONMENT:-development}"
echo ""

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}❌ ERRORS: $ERRORS${NC}"
    echo -e "${RED}   Fix the errors above before deploying!${NC}"
fi

if [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠️  WARNINGS: $WARNINGS${NC}"
    echo -e "${YELLOW}   Review warnings for potential issues${NC}"
fi

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
fi

echo ""

# Exit with error code if there are errors
if [ $ERRORS -gt 0 ]; then
    exit 1
fi

exit 0
