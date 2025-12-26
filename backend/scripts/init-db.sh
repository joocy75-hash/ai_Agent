#!/bin/bash
# ============================================================
# PostgreSQL Initialization Script
# 이 스크립트는 PostgreSQL 컨테이너 시작 시 자동으로 실행됩니다.
# /docker-entrypoint-initdb.d/ 디렉토리에 마운트되어야 합니다.
# ============================================================
#
# 주요 기능:
# 1. trading_user 비밀번호를 환경변수와 동기화
# 2. 필요한 확장 기능 설치
#
# 이 스크립트는 PostgreSQL 볼륨이 새로 생성될 때만 실행됩니다.
# 기존 볼륨이 있으면 실행되지 않습니다.
# ============================================================

set -e

echo "🔧 PostgreSQL initialization script starting..."

# 비밀번호는 환경변수에서 가져옴
# POSTGRES_PASSWORD는 docker-compose.yml에서 전달됨

# 확장 기능 설치 (필요시)
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- UUID 확장 (필요시 활성화)
    -- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

    -- 현재 설정 확인
    SELECT current_user, current_database();

    -- 연결 테스트용 쿼리
    SELECT 'PostgreSQL initialized successfully!' as status;
EOSQL

echo "✅ PostgreSQL initialization complete!"
