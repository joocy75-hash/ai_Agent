# 🚨 종합 시스템 체크 결과 - 발견된 Critical Bugs

**검사 일시**: 2025-12-03 15:45
**검사 범위**: WebSocket, 인증, API 엔드포인트, 백테스트, 데이터베이스
**상태**: ⚠️ **CRITICAL ISSUES FOUND - 배포 불가 상태**

---

## ⚠️ CRITICAL - 즉시 수정 필요

### 1. WebSocket 무한 루프 크래시 🔴🔴🔴

**문제**:
- 클라이언트가 연결 해제 후 `receive()` 계속 호출하여 무한 에러 루프 발생
- 초당 수백 개의 에러 메시지 로깅
- 서버 리소스 과도 사용 및 로그 폭발

**에러 메시지**:
```
Error receiving WebSocket message for user 6: Cannot call "receive" once a disconnect message has been received.
[이 메시지가 무한 반복됨 - 16,293,861 lines!]
```

**원인**:
[ws_server.py:307-337](backend/src/websockets/ws_server.py#L307-L337) - disconnect 예외를 제대로 처리하지 않음

**수정**:
```python
# ❌ BEFORE - continue로 무한 루프
except Exception as e:
    logger.error(f"Error receiving WebSocket message for user {user_id}: {e}")
    continue  # disconnect 후에도 계속 시도!

# ✅ AFTER - disconnect 시 루프 종료
except WebSocketDisconnect:
    break  # 루프 종료
except Exception as e:
    logger.error(f"Error receiving WebSocket message for user {user_id}: {e}")
    if "disconnect" in str(e).lower() or "cannot call" in str(e).lower():
        break  # disconnect 관련 에러면 루프 종료
    continue
```

**영향**: 🔴🔴🔴 CRITICAL
- 프로덕션에서 서버 크래시 가능성
- 로그 파일 폭발로 디스크 full 가능
- CPU/메모리 과다 사용

---

### 2. 에러 핸들러 로깅 충돌 크래시 🔴🔴🔴

**문제**:
- 에러 발생 시 에러 핸들러 자체가 크래시
- 모든 에러가 500 Internal Server Error로 반환됨
- 사용자에게 적절한 에러 메시지 전달 불가

**에러 메시지**:
```
KeyError: "Attempt to overwrite 'message' in LogRecord"
```

**원인**:
[error_handler.py:66-76](backend/src/middleware/error_handler.py#L66-L76) - `message`는 logging의 예약어인데 extra 파라미터로 사용

**수정**:
```python
# ❌ BEFORE - 'message'는 logging 예약어
logger.warning(
    f"AppException: {exc.error_code}",
    extra={
        "message": exc.message,  # KeyError 발생!
    }
)

# ✅ AFTER - 'error_message'로 변경
logger.warning(
    f"AppException: {exc.error_code}",
    extra={
        "error_message": exc.message,  # 정상 동작
    }
)
```

**영향**: 🔴🔴🔴 CRITICAL
- 모든 인증 에러가 500 에러로 표시됨
- 로그인 불가
- 프론트엔드에서 적절한 에러 처리 불가

**테스트 결과**:
```bash
POST /auth/login HTTP/1.1" 500 Internal Server Error
# 실제로는 "Invalid email or password" (401)이어야 하지만 500 반환
```

---

### 3. WebSocket JSON 파싱 에러 🔴🔴

**문제**:
- 프론트엔드가 ping을 문자열로 보내는데 JSON으로 파싱 시도
- 매 30초마다 에러 발생

**에러 메시지**:
```
Invalid JSON from user 6: Expecting value: line 1 column 1 (char 0), message: ping
```

**원인**:
프론트엔드 [useWebSocket.js:40](frontend/src/hooks/useWebSocket.js#L40)에서:
```javascript
ws.send(JSON.stringify({ action: 'ping' }));  // JSON으로 보냄
```

하지만 어딘가에서 `"ping"` 문자열만 보내는 코드 존재

**수정 필요**:
1. 프론트엔드에서 일관되게 JSON으로 ping 전송
2. 백엔드에서 문자열 "ping"도 허용하도록 수정

**영향**: 🔴🔴 HIGH
- 30초마다 불필요한 에러 로깅
- WebSocket 안정성 저하
- 사용자 경험 저하 (연결 끊김 가능성)

---

## ⚠️ HIGH - 우선 수정 필요

### 4. 봇 실행 로그 미출력 🔴🔴

**문제**:
- 봇이 실행 중이지만 로그가 stdout에 나타나지 않음
- 디버깅 및 모니터링 불가

**원인**:
[main.py](backend/src/main.py) - 로깅 설정이 전혀 없음

**현재 상태**:
```python
# main.py에 logging import 없음
# setup_logging() 호출 없음
# uvicorn 로그 레벨 설정 없음
```

**수정 필요**:
```python
# main.py에 추가
from .utils.logging_config import setup_logging

def create_app() -> FastAPI:
    # 로깅 설정 추가
    setup_logging(log_level=logging.INFO, detailed=True)

    app = FastAPI(...)
    ...
```

**영향**: 🔴🔴 HIGH
- 봇 실행 상태 모니터링 불가
- 에러 발생 시 원인 파악 어려움
- 프로덕션 운영 불가

---

### 5. 데이터베이스 스키마 문서화 부족 🔴

**문제**:
- 테이블 스키마가 문서화되어 있지 않음
- 코드와 실제 DB 스키마 불일치 가능성

**발견 사항**:
```sql
-- trades 테이블
- 코드에서 'size' 사용 → 실제로는 'qty'
- 코드에서 'status' 사용 → 실제 컬럼 없음

-- positions 테이블
- 코드에서 'unrealized_pnl' 사용 → 실제로는 'pnl'

-- open_orders 테이블
- 'price', 'order_type' 컬럼이 실제로는 없음
```

**수정 필요**:
1. 모든 테이블 스키마를 문서화
2. 모델과 실제 DB 스키마 동기화
3. Alembic 마이그레이션 파일 검증

**영향**: 🔴 MEDIUM-HIGH
- API 응답 데이터 누락 가능성
- 프론트엔드 표시 오류
- 데이터 무결성 문제

---

## 📊 테스트 결과 요약

### ✅ 통과한 테스트
1. **Health Check** - ✅ 정상
2. **WebSocket 연결** - ✅ 연결 성공 (하지만 disconnect 시 문제)
3. **Database** - ✅ 연결 정상, 데이터 존재

### ❌ 실패한 테스트
1. **Authentication** - ❌ 로그인 500 에러 (에러 핸들러 크래시)
2. **Bot Status API** - ❌ 테스트 불가 (인증 필요)
3. **Strategy List API** - ❌ 테스트 불가 (인증 필요)
4. **Chart API** - ❌ 테스트 불가 (인증 필요)
5. **Position API** - ❌ 테스트 불가 (인증 필요)
6. **Backtest** - ❌ 테스트 불가 (인증 필요)

---

## 🔧 수정 완료된 사항

### Session 8에서 수정한 버그들:
1. ✅ **WebSocket disconnect 무한 루프** - 수정 완료
2. ✅ **Error handler logging conflict** - `message` → `error_message` 변경
3. ✅ **MA Cross Strategy 구현** - 완료
4. ✅ **Strategy Loader 등록** - 완료
5. ✅ **Bitget 최소 주문량** - 0.01 BTC로 수정

---

## 📋 즉시 수행해야 할 작업 (우선순위순)

### Priority 1 - CRITICAL (배포 차단 이슈)
1. ✅ **WebSocket disconnect 루프** - 수정 완료, 테스트 필요
2. ✅ **Error handler logging** - 수정 완료, 테스트 필요
3. ⏳ **로그인 테스트** - 수정 후 재테스트 필요

### Priority 2 - HIGH (기능 차단 이슈)
4. ⏳ **Bot 로깅 설정** - main.py에 setup_logging() 추가 필요
5. ⏳ **WebSocket ping 처리** - 일관된 형식으로 수정
6. ⏳ **전체 API 엔드포인트 테스트** - 인증 수정 후 재테스트

### Priority 3 - MEDIUM (개선 필요)
7. ⏳ **데이터베이스 스키마 문서화**
8. ⏳ **프론트엔드 WebSocket 핸들링 개선**
9. ⏳ **에러 처리 표준화**

---

## 🚀 다음 단계

1. **백엔드 재시작** - 수정사항 적용 확인
2. **로그인 테스트** - 에러 핸들러 수정 검증
3. **전체 API 테스트** - 종합 시스템 체크 재실행
4. **WebSocket 안정성 테스트** - 연결/해제 반복 테스트
5. **봇 실행 테스트** - 로깅 확인 및 실제 거래 시뮬레이션
6. **백테스트 테스트** - 전체 워크플로우 검증

---

## 📝 배포 전 체크리스트

- [ ] 로그인 정상 동작
- [ ] WebSocket 연결/해제 안정적
- [ ] 봇 시작/중지 정상 동작
- [ ] 전략 목록 조회 정상
- [ ] 차트 데이터 200개 로드
- [ ] 포지션 조회 정상
- [ ] 백테스트 실행 및 결과 조회
- [ ] 모든 critical 로그 제거
- [ ] 에러 핸들링 정상 동작
- [ ] 데이터베이스 스키마 검증

**현재 상태**: ❌ **배포 불가** - Critical 이슈 2개 수정 필요

---

**작성자**: Claude Code (Session 8)
**다음 작업자를 위한 메모**:
- 모든 수정사항은 코드에 반영되었으나 테스트가 필요합니다.
- 백엔드를 재시작하고 종합 테스트 스크립트를 다시 실행하세요: `/tmp/comprehensive_system_check.py`
- WebSocket 안정성이 최우선 과제입니다.
