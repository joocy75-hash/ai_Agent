#!/bin/bash
# 배포 서버 로그인 문제 해결 스크립트
# Fix deployment server login issues

set -e  # Exit on error

SERVER_IP="158.247.245.197"
SERVER_USER="root"

echo "🔧 배포 서버 로그인 문제 해결 중..."
echo "=================================="
echo ""

# Step 1: Check server connectivity
echo "📡 Step 1: 서버 연결 확인..."
if curl -s --connect-timeout 5 http://${SERVER_IP}:8000/health > /dev/null; then
    echo "✅ 서버 연결 성공"
else
    echo "❌ 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요."
    exit 1
fi

echo ""
echo "🔍 Step 2: 배포 서버에 SSH 연결을 시도합니다..."
echo "⚠️  SSH 비밀번호를 입력해야 합니다."
echo ""

# Step 2: Create admin user on server
cat << 'REMOTE_SCRIPT' | ssh ${SERVER_USER}@${SERVER_IP} 'bash -s'
#!/bin/bash
set -e

echo "📦 Step 3: Docker 컨테이너 상태 확인..."
if ! docker ps | grep -q trading-backend; then
    echo "❌ trading-backend 컨테이너가 실행되고 있지 않습니다."
    echo "   다음 명령어로 컨테이너를 시작하세요:"
    echo "   cd /root/auto-dashboard && docker-compose --env-file .env.production up -d"
    exit 1
fi
echo "✅ Backend 컨테이너 실행 중"

echo ""
echo "👤 Step 4: 관리자 계정 생성 중..."
docker exec trading-backend python -m src.scripts.create_admin_user

echo ""
echo "🧪 Step 5: 로그인 테스트..."
LOGIN_RESULT=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@admin.com","password":"Admin123!"}')

if echo "$LOGIN_RESULT" | grep -q "access_token"; then
    echo "✅ 로그인 성공!"
    echo "   이메일: admin@admin.com"
    echo "   비밀번호: Admin123!"
else
    echo "⚠️  로그인 응답:"
    echo "$LOGIN_RESULT" | python3 -m json.tool 2>/dev/null || echo "$LOGIN_RESULT"
fi

echo ""
echo "📊 Step 6: 컨테이너 로그 확인 (최근 20줄)..."
echo "--- Backend Logs ---"
docker logs trading-backend --tail 20

REMOTE_SCRIPT

echo ""
echo "=================================="
echo "✨ 완료!"
echo ""
echo "🌐 배포 서버 접속:"
echo "   프론트엔드: http://${SERVER_IP}:3000"
echo "   백엔드 API: http://${SERVER_IP}:8000"
echo "   API 문서:   http://${SERVER_IP}:8000/docs"
echo ""
echo "🔐 로그인 정보:"
echo "   이메일:     admin@admin.com"
echo "   비밀번호:   Admin123!"
echo ""
