#!/bin/bash

# ==============================================================
# 보안 헤더 검증 스크립트
# ==============================================================
# 모든 OWASP 권장 보안 헤더가 제대로 적용되는지 테스트
# ==============================================================

set -e

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 테스트 대상 서버
API_URL="${API_URL:-http://localhost:8000}"

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}  🔒 보안 헤더 검증 테스트${NC}"
echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}테스트 대상: $API_URL${NC}"
echo ""

# 헬스 체크
echo -e "${YELLOW}1. 헬스 체크...${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" "$API_URL/health")
HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
    echo -e "${RED}❌ 서버가 응답하지 않습니다 (HTTP $HTTP_CODE)${NC}"
    echo -e "${RED}서버를 먼저 시작해주세요: uvicorn src.main:app --reload${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 서버 정상 (HTTP $HTTP_CODE)${NC}"
echo ""

# 보안 헤더 체크
echo -e "${YELLOW}2. 보안 헤더 검증...${NC}"
HEADERS=$(curl -s -I "$API_URL/health")

# 필수 보안 헤더 목록
declare -A REQUIRED_HEADERS=(
    ["X-Content-Type-Options"]="nosniff"
    ["X-Frame-Options"]="DENY"
    ["X-XSS-Protection"]="1; mode=block"
    ["Referrer-Policy"]="strict-origin-when-cross-origin"
    ["Permissions-Policy"]="camera=(), microphone=()"
    ["Content-Security-Policy"]="default-src"
    ["Cache-Control"]="no-store"  # API 응답은 캐시 금지
)

# 선택적 헤더 (프로덕션 환경)
OPTIONAL_HEADERS=(
    "Strict-Transport-Security"  # HSTS (프로덕션에서만)
)

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

# 필수 헤더 체크
for HEADER in "${!REQUIRED_HEADERS[@]}"; do
    EXPECTED="${REQUIRED_HEADERS[$HEADER]}"

    if echo "$HEADERS" | grep -qi "^$HEADER:"; then
        ACTUAL=$(echo "$HEADERS" | grep -i "^$HEADER:" | cut -d: -f2- | xargs)

        if echo "$ACTUAL" | grep -qi "$EXPECTED"; then
            echo -e "${GREEN}✅ $HEADER: $ACTUAL${NC}"
            ((PASS_COUNT++))
        else
            echo -e "${RED}❌ $HEADER: Expected '$EXPECTED', Got '$ACTUAL'${NC}"
            ((FAIL_COUNT++))
        fi
    else
        echo -e "${RED}❌ $HEADER: Missing${NC}"
        ((FAIL_COUNT++))
    fi
done

# 선택적 헤더 체크 (프로덕션)
for HEADER in "${OPTIONAL_HEADERS[@]}"; do
    if echo "$HEADERS" | grep -qi "^$HEADER:"; then
        ACTUAL=$(echo "$HEADERS" | grep -i "^$HEADER:" | cut -d: -f2- | xargs)
        echo -e "${GREEN}✅ $HEADER: $ACTUAL (프로덕션 설정)${NC}"
        ((PASS_COUNT++))
    else
        echo -e "${YELLOW}⚠️  $HEADER: Not set (개발 환경 - 정상)${NC}"
        ((WARN_COUNT++))
    fi
done

echo ""

# Rate Limiting 헤더 체크
echo -e "${YELLOW}3. Rate Limiting 헤더 검증...${NC}"
RATE_HEADERS=$(curl -s -I "$API_URL/health")

if echo "$RATE_HEADERS" | grep -qi "X-RateLimit-Remaining:"; then
    REMAINING=$(echo "$RATE_HEADERS" | grep -i "X-RateLimit-Remaining:" | cut -d: -f2 | xargs)
    RESET=$(echo "$RATE_HEADERS" | grep -i "X-RateLimit-Reset:" | cut -d: -f2 | xargs)
    echo -e "${GREEN}✅ X-RateLimit-Remaining: $REMAINING${NC}"
    echo -e "${GREEN}✅ X-RateLimit-Reset: $RESET${NC}"
    ((PASS_COUNT+=2))
else
    echo -e "${YELLOW}⚠️  Rate limit 헤더 없음 (일부 엔드포인트에만 적용)${NC}"
    ((WARN_COUNT++))
fi

echo ""

# CORS 체크
echo -e "${YELLOW}4. CORS 설정 검증...${NC}"
CORS_RESPONSE=$(curl -s -I -X OPTIONS "$API_URL/health" \
    -H "Origin: http://localhost:3000" \
    -H "Access-Control-Request-Method: GET")

if echo "$CORS_RESPONSE" | grep -qi "Access-Control-Allow-Origin:"; then
    ALLOW_ORIGIN=$(echo "$CORS_RESPONSE" | grep -i "Access-Control-Allow-Origin:" | cut -d: -f2 | xargs)
    echo -e "${GREEN}✅ Access-Control-Allow-Origin: $ALLOW_ORIGIN${NC}"
    ((PASS_COUNT++))
else
    echo -e "${RED}❌ CORS 헤더 누락${NC}"
    ((FAIL_COUNT++))
fi

echo ""

# JWT 인증 테스트
echo -e "${YELLOW}5. JWT 인증 보안 테스트...${NC}"

# 인증 없이 보호된 엔드포인트 접근
PROTECTED_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_URL/account/balance")
PROTECTED_CODE=$(echo "$PROTECTED_RESPONSE" | tail -n 1)

if [ "$PROTECTED_CODE" == "401" ] || [ "$PROTECTED_CODE" == "403" ]; then
    echo -e "${GREEN}✅ 보호된 엔드포인트: 인증 필요 (HTTP $PROTECTED_CODE)${NC}"
    ((PASS_COUNT++))
else
    echo -e "${RED}❌ 보호된 엔드포인트: 인증 없이 접근 가능 (HTTP $PROTECTED_CODE)${NC}"
    ((FAIL_COUNT++))
fi

# 잘못된 JWT 토큰
INVALID_JWT_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_URL/account/balance" \
    -H "Authorization: Bearer invalid_token_here")
INVALID_JWT_CODE=$(echo "$INVALID_JWT_RESPONSE" | tail -n 1)

if [ "$INVALID_JWT_CODE" == "401" ] || [ "$INVALID_JWT_CODE" == "403" ]; then
    echo -e "${GREEN}✅ 잘못된 JWT: 거부됨 (HTTP $INVALID_JWT_CODE)${NC}"
    ((PASS_COUNT++))
else
    echo -e "${RED}❌ 잘못된 JWT: 허용됨 (HTTP $INVALID_JWT_CODE)${NC}"
    ((FAIL_COUNT++))
fi

echo ""

# 결과 요약
echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}  📊 테스트 결과 요약${NC}"
echo -e "${BLUE}=================================================${NC}"
echo -e "${GREEN}✅ 통과: $PASS_COUNT${NC}"
echo -e "${RED}❌ 실패: $FAIL_COUNT${NC}"
echo -e "${YELLOW}⚠️  경고: $WARN_COUNT${NC}"
echo ""

TOTAL=$((PASS_COUNT + FAIL_COUNT))
if [ $TOTAL -gt 0 ]; then
    SUCCESS_RATE=$(( PASS_COUNT * 100 / TOTAL ))
    echo -e "${BLUE}성공률: $SUCCESS_RATE%${NC}"
fi

echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}🎉 모든 보안 테스트 통과!${NC}"
    exit 0
else
    echo -e "${RED}⚠️  일부 보안 테스트 실패. 위 내용을 확인해주세요.${NC}"
    exit 1
fi
