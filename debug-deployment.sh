#!/bin/bash
# 배포 서버 디버깅 스크립트

echo "🔍 배포 서버 연결 문제 진단"
echo "========================================"
echo ""

# 1. 백엔드 상태
echo "1️⃣ 백엔드 API 상태 확인..."
BACKEND_HEALTH=$(curl -s http://158.247.245.197:8000/health)
echo "   $BACKEND_HEALTH"
echo ""

# 2. 프론트엔드 접속
echo "2️⃣ 프론트엔드 접속 확인..."
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://158.247.245.197:3000)
echo "   HTTP Status: $FRONTEND_STATUS"
echo ""

# 3. 로그인 API 테스트
echo "3️⃣ 로그인 API 직접 테스트..."
LOGIN_RESULT=$(curl -s -X POST http://158.247.245.197:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@admin.com","password":"Admin123!"}')
echo "   $LOGIN_RESULT" | python3 -m json.tool 2>/dev/null || echo "   $LOGIN_RESULT"
echo ""

# 4. CORS 헤더 확인
echo "4️⃣ CORS 헤더 확인..."
curl -s -I -X OPTIONS http://158.247.245.197:8000/auth/login \
  -H "Origin: http://158.247.245.197:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" | grep -i "access-control"
echo ""

# 5. 프론트엔드 번들에서 API URL 확인
echo "5️⃣ 프론트엔드가 사용하는 API URL 확인..."
echo "   (JavaScript 파일에서 API URL 검색)"
FRONTEND_HTML=$(curl -s http://158.247.245.197:3000)
JS_FILES=$(echo "$FRONTEND_HTML" | grep -o 'src="[^"]*\.js"' | cut -d'"' -f2 | head -3)

for js_file in $JS_FILES; do
    if [[ $js_file == /* ]]; then
        js_url="http://158.247.245.197:3000$js_file"
    else
        js_url="http://158.247.245.197:3000/$js_file"
    fi

    echo "   검사 중: $js_url"
    API_URL=$(curl -s "$js_url" | grep -o 'http://[^"]*:8000' | head -1)
    if [ ! -z "$API_URL" ]; then
        echo "   ✅ 발견: $API_URL"
        break
    fi
done

echo ""
echo "========================================"
echo ""
echo "📋 진단 결과 요약:"
echo ""

if echo "$LOGIN_RESULT" | grep -q "access_token"; then
    echo "✅ 백엔드 로그인: 정상 작동"
    echo "✅ 관리자 계정: 존재함"
else
    echo "❌ 백엔드 로그인: 실패"
    echo "   → 관리자 계정이 없거나 비밀번호 불일치"
fi

if [ "$FRONTEND_STATUS" = "200" ]; then
    echo "✅ 프론트엔드: 접근 가능"
else
    echo "❌ 프론트엔드: 접근 불가 (HTTP $FRONTEND_STATUS)"
fi

if [ ! -z "$API_URL" ]; then
    if echo "$API_URL" | grep -q "158.247.245.197"; then
        echo "✅ 프론트엔드 API URL: 올바르게 설정됨 ($API_URL)"
    else
        echo "❌ 프론트엔드 API URL: 잘못됨 ($API_URL)"
        echo "   → 프론트엔드 재빌드 필요!"
    fi
else
    echo "⚠️  프론트엔드 API URL: 확인 불가"
fi

echo ""
echo "========================================"
