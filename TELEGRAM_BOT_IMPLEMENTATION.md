# 📱 텔레그램 알림 봇 구현 계획

> **작성일**: 2025-12-05  
> **목적**: 실시간 거래 알림을 텔레그램으로 전송하는 시스템 구현  
> **예상 시간**: 1~2시간

---

## 📋 목차

1. [알림 유형 정의](#1-알림-유형-정의)
2. [메시지 포맷 설계](#2-메시지-포맷-설계)
3. [시스템 아키텍처](#3-시스템-아키텍처)
4. [구현 단계](#4-구현-단계)
5. [환경변수 설정](#5-환경변수-설정)
6. [파일 구조](#6-파일-구조)
7. [테스트 계획](#7-테스트-계획)

---

## 1. 알림 유형 정의

### 1.1 거래 알림

| 알림 유형 | 설명 | 우선순위 |
|-----------|------|----------|
| **신규 진입** | 새로운 포지션 오픈 | 🔴 높음 |
| **포지션 종료** | 포지션 청산 (익절/손절/시그널) | 🔴 높음 |
| **손절 경고** | 손실률 특정 수준 도달 시 | 🟡 중간 |

### 1.2 시스템 알림

| 알림 유형 | 설명 | 우선순위 |
|-----------|------|----------|
| **봇 시작** | AI 자동매매 시작 | 🔴 높음 |
| **봇 종료** | AI 자동매매 종료 | 🔴 높음 |
| **미청산 경고** | 미청산 포지션 존재 시 경고 | 🟡 중간 |
| **에러 알림** | API 에러, 연결 실패 등 | 🔴 높음 |

---

## 2. 메시지 포맷 설계

### 2.1 신규 거래 알림

```
🟢 Bitget: 신규 거래

• 코인: SOL/USDT
• 방향: Long 📈
• 진입가: 136.073 USDT
• 수량: 0.25721488
• 총액: 35 USDT

⏰ 2025-12-05 17:15:00
```

### 2.2 포지션 종료 알림 (수익)

```
🔴 Bitget: 포지션 종료

📈 손익: +1.50% (+0.525 USDT)
━━━━━━━━━━━━━━━━━━━━━
• 코인: BTC/USDT
• 방향: Long
• 진입가: 90,930.30 USDT
• 종료가: 92,294.25 USDT
• 수량: 0.0003
• 종료 사유: 🎯 익절 (take_profit)
• 보유 기간: 6시간 5분

⏰ 2025-12-05 17:15:00
```

### 2.3 포지션 종료 알림 (손실)

```
🔴 Bitget: 포지션 종료

📉 손익: -2.30% (-0.805 USDT)
━━━━━━━━━━━━━━━━━━━━━
• 코인: ETH/USDT
• 방향: Short
• 진입가: 3,450.00 USDT
• 종료가: 3,529.35 USDT
• 수량: 0.01
• 종료 사유: 🛑 손절 (stop_loss)
• 보유 기간: 2시간 30분

⏰ 2025-12-05 17:15:00
```

### 2.4 봇 시작 알림

```
🚀 AI 자동매매 시작

✅ AI봇이 성공적으로 연결되었습니다!
📝 거래 알림을 실시간으로 받으실 수 있습니다.

현재 설정:
━━━━━━━━━━━━━━━━━━━━━
• 거래소: BITGET
• 거래당 금액: 35 USDT
• 손절가: -5.0%
• 타임프레임: 5m
• 전략: FreqAIStarterStrategy

⏰ 2025-12-05 17:15:00
```

### 2.5 봇 종료 알림

```
⏹️ AI 자동매매 종료

상태: 정상 종료됨

📊 세션 요약:
━━━━━━━━━━━━━━━━━━━━━
• 총 거래 수: 15
• 승률: 60% (9승 6패)
• 총 손익: +12.5 USDT (+3.57%)
• 운영 시간: 8시간 30분

⏰ 2025-12-05 17:15:00
```

### 2.6 미청산 포지션 경고

```
⚠️ 미청산 포지션 경고

⚠️ 2개 미청산 포지션이 남아 있습니다.

현재 포지션:
━━━━━━━━━━━━━━━━━━━━━
1. BTC/USDT Long (+0.5%)
2. ETH/USDT Short (-1.2%)

💡 Bitget에서 직접 처리하거나,
'/start'로 봇을 다시 켠 후 
'/stopentry'로 신규 진입을 막고 정리해 주세요.

⏰ 2025-12-05 17:15:00
```

### 2.7 에러 알림

```
🚨 시스템 에러

❌ API 연결 실패

에러 내용:
━━━━━━━━━━━━━━━━━━━━━
Bitget API Rate Limit Exceeded

💡 5분 후 자동 재시도됩니다.
수동 확인이 필요하면 관리자에게 문의하세요.

⏰ 2025-12-05 17:15:00
```

---

## 3. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        Auto Dashboard                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  Trading     │    │   Bot        │    │  WebSocket   │      │
│  │  Service     │───▶│   Manager    │───▶│   Handler    │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│          │                   │                   │              │
│          ▼                   ▼                   ▼              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Telegram Notifier                      │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │   │
│  │  │ Trade   │  │ System  │  │ Error   │  │ Message │    │   │
│  │  │ Notify  │  │ Notify  │  │ Notify  │  │ Format  │    │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                             │                                   │
└─────────────────────────────┼───────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Telegram API   │
                    │  (Bot API)      │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  User's         │
                    │  Telegram App   │
                    └─────────────────┘
```

---

## 4. 구현 단계

### 4.1 Phase 1: 텔레그램 봇 생성 (5분)

1. 텔레그램에서 `@BotFather` 검색
2. `/newbot` 명령어로 봇 생성
3. 봇 이름 입력 (예: `AutoDashboard_Bot`)
4. 봇 API 토큰 저장

### 4.2 Phase 2: Chat ID 획득 (5분)

1. 생성한 봇에게 아무 메시지 전송
2. `https://api.telegram.org/bot<TOKEN>/getUpdates` 접속
3. 응답에서 `chat.id` 값 확인 및 저장

### 4.3 Phase 3: 백엔드 서비스 구현 (30분)

#### 파일 생성 목록

```
backend/src/services/
├── telegram_notifier.py     # 메인 알림 서비스
├── telegram_messages.py     # 메시지 포맷터
└── telegram_types.py        # 타입 정의
```

#### telegram_notifier.py 핵심 구조

```python
class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = bool(bot_token and chat_id)
    
    async def send_message(self, message: str) -> bool:
        """텔레그램 메시지 전송"""
        pass
    
    async def notify_new_trade(self, trade: TradeInfo) -> bool:
        """신규 거래 알림"""
        pass
    
    async def notify_close_trade(self, trade: TradeResult) -> bool:
        """포지션 종료 알림"""
        pass
    
    async def notify_bot_start(self, config: BotConfig) -> bool:
        """봇 시작 알림"""
        pass
    
    async def notify_bot_stop(self, summary: SessionSummary) -> bool:
        """봇 종료 알림"""
        pass
    
    async def notify_warning(self, warning: WarningInfo) -> bool:
        """경고 알림"""
        pass
    
    async def notify_error(self, error: ErrorInfo) -> bool:
        """에러 알림"""
        pass
```

### 4.4 Phase 4: 트레이딩 서비스 연동 (30분)

#### 연동 포인트

| 파일 | 연동 위치 | 알림 유형 |
|------|----------|----------|
| `bot_manager.py` | `start_bot()` | 봇 시작 |
| `bot_manager.py` | `stop_bot()` | 봇 종료 |
| `trading_service.py` | `open_position()` | 신규 거래 |
| `trading_service.py` | `close_position()` | 포지션 종료 |
| `websocket_handler.py` | 에러 발생 시 | 에러 알림 |

### 4.5 Phase 5: 설정 페이지 UI (선택, 30분)

- 프론트엔드 Settings 페이지에 텔레그램 설정 섹션 추가
- 봇 토큰, Chat ID 입력 필드
- 알림 테스트 버튼
- 알림 유형별 On/Off 토글

---

## 5. 환경변수 설정

### 5.1 .env 파일 추가

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321

# 알림 설정 (선택)
TELEGRAM_NOTIFY_TRADES=true
TELEGRAM_NOTIFY_SYSTEM=true
TELEGRAM_NOTIFY_ERRORS=true
```

### 5.2 config.py 추가

```python
# Telegram 설정
telegram_bot_token: str = Field(default="", env="TELEGRAM_BOT_TOKEN")
telegram_chat_id: str = Field(default="", env="TELEGRAM_CHAT_ID")
telegram_notify_trades: bool = Field(default=True, env="TELEGRAM_NOTIFY_TRADES")
telegram_notify_system: bool = Field(default=True, env="TELEGRAM_NOTIFY_SYSTEM")
telegram_notify_errors: bool = Field(default=True, env="TELEGRAM_NOTIFY_ERRORS")
```

---

## 6. 파일 구조

```
backend/src/
├── services/
│   ├── telegram/
│   │   ├── __init__.py
│   │   ├── notifier.py        # TelegramNotifier 클래스
│   │   ├── messages.py        # 메시지 포맷 함수들
│   │   └── types.py           # Pydantic 모델
│   ├── bot_manager.py         # 봇 시작/종료 시 알림 연동
│   └── trading_service.py     # 거래 시 알림 연동
├── api/
│   └── telegram.py            # 텔레그램 설정 API (선택)
└── config.py                  # 환경변수 추가
```

---

## 7. 테스트 계획

### 7.1 단위 테스트

```python
# tests/test_telegram_notifier.py

async def test_message_format_new_trade():
    """신규 거래 메시지 포맷 테스트"""
    pass

async def test_message_format_close_trade_profit():
    """수익 종료 메시지 포맷 테스트"""
    pass

async def test_message_format_close_trade_loss():
    """손실 종료 메시지 포맷 테스트"""
    pass

async def test_send_message_success():
    """메시지 전송 성공 테스트"""
    pass

async def test_send_message_disabled():
    """비활성화 시 전송 안 함 테스트"""
    pass
```

### 7.2 수동 테스트

```bash
# 테스트 메시지 전송
curl -X POST "http://localhost:8000/api/telegram/test" \
  -H "Authorization: Bearer <token>"
```

---

## 8. 구현 체크리스트

### Phase 1: 기본 설정

- [ ] BotFather로 봇 생성
- [ ] 봇 토큰 획득
- [ ] Chat ID 획득
- [ ] 환경변수 설정 (.env 파일)

### Phase 2: 백엔드 구현 ✅ 완료

- [x] `telegram/types.py` 생성
- [x] `telegram/messages.py` 생성
- [x] `telegram/notifier.py` 생성
- [x] `config.py` 수정 (TelegramConfig 추가)
- [x] `api/telegram.py` 생성
- [x] `main.py`에 라우터 등록

### Phase 3: 서비스 연동 (다음 단계)

- [ ] `bot_manager.py` 연동 (시작/종료)
- [ ] `trading_service.py` 연동 (거래)
- [ ] 에러 핸들러 연동

### Phase 4: 테스트

- [ ] 단위 테스트 작성
- [ ] 통합 테스트 실행
- [ ] 실제 알림 테스트

### Phase 5: 문서화 (선택)

- [ ] API 문서 업데이트
- [ ] 사용자 가이드 작성

---

## 9. 예상 결과

구현 완료 시 다음과 같은 실시간 알림을 받을 수 있습니다:

1. ✅ 봇 시작/종료 알림
2. ✅ 신규 거래 진입 알림
3. ✅ 포지션 종료 (수익/손실) 알림
4. ✅ 미청산 포지션 경고
5. ✅ 시스템 에러 알림

---

*마지막 업데이트: 2025-12-05 17:19*
