# 🤖 Bitget AI Bots 마스터 플랜

> **작성일**: 2024년 12월 8일
> **프로젝트**: 비트겟 스타일 AI 자동매매 봇 시스템 구현
> **목표**: 초보자도 투자 금액 비율만 설정하면 AI가 자동으로 최적의 전략을 추천하고 실행하는 시스템

---

## 📋 문서 구성

이 프로젝트는 **4개의 상세 문서**로 구성되어 있습니다:

1. **`AI_BOTS_MASTER_PLAN.md`** (본 문서) - 전체 개요 및 요약
2. **`AI_BOTS_TECHNICAL_SPEC.md`** - 기술 사양, 데이터베이스 설계, 아키텍처
3. **`AI_BOTS_IMPLEMENTATION_GUIDE.md`** - 단계별 구현 가이드 (Phase 1~5)
4. **`AI_BOTS_QNA.md`** - 자주 묻는 질문 및 상세 답변

---

## 🎯 Executive Summary

### 프로젝트 목표
비트겟의 AI 자동매매 봇 시스템을 참고하여, **초보자도 쉽게 사용할 수 있는** AI 기반 자동매매 플랫폼 구축

### 핵심 차별점
- ✅ **비트겟보다 더 쉬운 UX**: 투자 비율(%) 입력만으로 봇 실행
- ✅ **무료 AI 추천**: DeepSeek API 활용으로 비용 최소화 (월 $5 이하)
- ✅ **한국어 중심**: 인터페이스 및 AI 설명 완전 한글화
- ✅ **다중 봇 관리**: 1명의 사용자가 여러 봇을 동시 실행 가능
- ✅ **완벽한 격리**: 사용자별 계좌, 주문, 데이터 완전 분리

### 주요 기능
1. **AI 기반 전략 추천**: 시장 분석 후 최적의 봇 파라미터 자동 생성
2. **간단한 설정**: 투자 금액 비율만 입력 → AI가 나머지 설정
3. **실시간 ROI 표시**: 30일 예상 APY 및 차트 시각화
4. **다중 봇 실행**: 사용자당 최대 10개 봇 동시 운영
5. **리스크 관리**: 손실 한도, 레버리지 제한, 포지션 수 제한

---

## 🤖 비트겟 AI 봇 시스템 분석

### 비트겟이 제공하는 봇 종류 (총 7종)

#### 1. Futures Grid Bot ⭐⭐⭐⭐⭐ (우선순위 1위)
- **설명**: 선물 계약으로 설정된 가격 범위 내에서 자동 매매 반복
- **그리드 타입**:
  - **Long Grid**: 상승장에서 저점 매수 → 고점 매도
  - **Short Grid**: 하락장에서 고점 매도 → 저점 매수
  - **Neutral Grid**: 양방향 거래 (횡보장 최적)
- **레버리지**: 최대 125x
- **AI 역할**: 7일간 백테스트 기반 최적 파라미터 자동 생성
- **핵심 파라미터**:
  - Direction (Long/Short/Neutral)
  - Price Range (Lowest/Highest)
  - Number of Grids (1-200개)
  - Leverage (1-125x)
  - Investment Amount (USDT)
  - Take Profit / Stop Loss (선택)
  - Trigger Price (선택)
  - Grid Mode (Arithmetic/Geometric)

#### 2. CTA Bot (Commodity Trading Advisor) ⭐⭐⭐⭐ (우선순위 2위)
- **설명**: 기술적 지표 기반 자동 매매
- **지원 지표**: MACD, MA, Bollinger Bands, RSI 등
- **AI 역할**: 현재 시장에 최적화된 지표 조합 추천
- **적합한 사용자**: 기술적 분석을 선호하는 트레이더

#### 3. Martingale Bot ⭐⭐⭐ (고위험 고수익)
- **설명**: 손실 시 투자 금액을 2배로 늘려 평균 단가 낮춤
- **적합한 시장**: 트렌드 시장 (반등 예상 시)
- **리스크**: 매우 높음 (연속 손실 시 청산 위험)
- **AI 역할**: Conservative/Balanced/Aggressive 3단계 리스크 레벨 제공
- **핵심 파라미터**:
  - Initial Order Size
  - Price Step (몇 % 하락 시 추가 매수)
  - Multiplier (기본 2배)
  - Max Safety Orders (최대 추가 매수 횟수)

#### 4. Spot Grid Bot ⭐⭐
- **설명**: 현물 거래로 그리드 전략 실행
- **차이점**: Futures Grid와 동일하나 레버리지 없음
- **리스크**: 낮음 (현물이므로 청산 위험 없음)

#### 5. Smart Portfolio Bot ⭐⭐
- **설명**: 여러 코인의 비율을 유지하며 자동 리밸런싱
- **예시**: BTC 50%, ETH 30%, SOL 20% 비율 유지
- **리밸런싱 조건**: 시간 기반 또는 편차 기반
- **적합한 사용자**: 장기 투자자

#### 6. Auto-Invest Bot (DCA) ⭐⭐
- **설명**: 정기적으로 일정 금액 매수 (적립식 투자)
- **주기**: 매일, 매주, 매월
- **리스크**: 매우 낮음
- **적합한 사용자**: 초보자, 장기 투자자

#### 7. TradingView Signal Bot ⭐ (제외 예정)
- **설명**: TradingView 지표 시그널을 Webhook으로 받아 자동 주문
- **제외 이유**: 사용자층 한정적, 구현 복잡도 높음

---

## 🎯 우리가 구현할 봇 우선순위

### Phase 1: MVP (3주) ⭐⭐⭐⭐⭐
1. **Futures Grid Bot AI** (가장 인기, ROI 시각화 쉬움)
2. **CTA Bot (RSI + MACD 기반)** (기존 전략 시스템 활용 가능)

### Phase 2: 확장 (2주)
3. **Martingale Bot** (고위험 고수익, 일부 사용자 수요)
4. **Auto-Invest Bot (DCA)** (초보자 친화적)

### Phase 3: 고급 (2주)
5. **Smart Portfolio Bot** (고급 사용자용)
6. **Spot Grid Bot** (Futures Grid와 로직 유사)

**제외**: TradingView Signal Bot

---

## 🔍 현재 시스템 분석

### 이미 구현된 기능 ✅

#### 1. 백엔드 인프라
- ✅ FastAPI 기반 REST API
- ✅ SQLAlchemy ORM (비동기)
- ✅ JWT 인증 시스템
- ✅ WebSocket 실시간 통신
- ✅ Bitget REST API 클라이언트 완비
  - 주문 실행 (시장가/지정가)
  - 포지션 관리
  - 계좌 조회
  - 레버리지 설정
  - 과거 캔들 데이터 조회
- ✅ Bitget WebSocket 마켓 데이터 수집

#### 2. 봇 실행 시스템
- ✅ BotRunner (비동기 봇 실행 루프)
- ✅ BotManager (다중 사용자 봇 관리)
- ✅ Strategy Engine (전략 코드 실행, 시그널 생성)

#### 3. 리스크 관리
- ✅ 일일 손실 한도 체크
- ✅ 최대 포지션 개수 제한
- ✅ 레버리지 제한
- ✅ RiskSettings 모델

#### 4. AI 전략 생성
- ✅ DeepSeek API 연동
- ✅ AI 전략 생성 엔드포인트 (`/ai/strategies/generate`)
- ✅ 전략 목록 조회/삭제

#### 5. 데이터베이스 모델
- ✅ User, ApiKey, Strategy, BotStatus
- ✅ Trade, Position, Equity
- ✅ RiskSettings, SystemAlert

#### 6. 프론트엔드
- ✅ React + Ant Design
- ✅ 전략 관리 페이지
- ✅ 대시보드
- ✅ 실시간 차트 및 거래 내역

### 추가 구현이 필요한 기능 ❌

#### 1. Grid Bot 전용 모델 (신규)
- ❌ `AIBot` 모델 (통합 봇 관리)
- ❌ `GridPosition` 모델 (그리드 레벨별 포지션 추적)
- ❌ `AIStrategyRecommendation` 모델 (AI 추천 전략 캐싱)

#### 2. AI 분석 서비스 (신규)
- ❌ 시장 분석 로직 (변동성, 트렌드, 지지/저항선)
- ❌ DeepSeek 프롬프트 최적화
- ❌ 그리드 파라미터 계산 알고리즘
- ❌ 백테스트 시뮬레이션

#### 3. Grid Bot 실행 엔진 (신규)
- ❌ 그리드 레벨 계산 (Arithmetic/Geometric)
- ❌ 초기 주문 배치 (Long/Short/Neutral)
- ❌ 주문 체결 모니터링
- ❌ 자동 재주문 (매수 체결 → 매도 주문, 매도 체결 → 매수 주문)
- ❌ 수익 계산 및 기록

#### 4. 투자 금액 비율 계산 (신규)
- ❌ 계좌 잔고 조회
- ❌ 비율 기반 투자 금액 자동 계산
- ❌ 잔고 부족 체크

#### 5. 다중 봇 관리 UI (신규)
- ❌ AI 추천 전략 카드 컴포넌트
- ❌ ROI 차트 (30일 APY)
- ❌ 실행 중인 봇 목록 테이블
- ❌ 투자 비율 슬라이더

#### 6. API 엔드포인트 (신규)
- ❌ `/grid-bot/analyze` - AI 전략 추천
- ❌ `/grid-bot/create` - 봇 생성
- ❌ `/grid-bot/{bot_id}/start` - 봇 시작
- ❌ `/grid-bot/{bot_id}/stop` - 봇 정지
- ❌ `/grid-bot/list` - 봇 목록 조회
- ❌ `/grid-bot/{bot_id}/performance` - 성과 조회

---

## 📊 현재 시스템 vs 비트겟 비교

| 항목 | 비트겟 | 우리 시스템 (현재) | 격차 | 구현 난이도 |
|------|--------|-------------------|------|------------|
| **봇 종류** | 7종 | 1종 | ❌ 큰 격차 | 중간 |
| **AI 추천** | ✅ 7일 백테스트 기반 | ✅ DeepSeek API | ✅ 유사 | 쉬움 |
| **투자 금액 설정** | 금액 직접 입력 | 금액 직접 입력 | ✅ 동일 | - |
| **ROI 표시** | ✅ 30일 APY + 차트 | ❌ 없음 | ❌ 격차 | 쉬움 |
| **다중 봇 관리** | ✅ 여러 봇 동시 실행 | ✅ 인프라 준비됨 | ✅ 가능 | 쉬움 |
| **레버리지 설정** | ✅ 최대 125x | ✅ Bitget API 지원 | ✅ 동일 | - |
| **리스크 관리** | ✅ TP/SL, 일일 손실 한도 | ✅ 이미 구현됨 | ✅ 동일 | - |
| **백테스트** | ✅ 7일 기반 자동 | ✅ 별도 페이지 있음 | ✅ 유사 | - |
| **그리드 전략** | ✅ 200개 그리드 지원 | ❌ 없음 | ❌ 큰 격차 | 어려움 |
| **포지션 추적** | ✅ 그리드 레벨별 추적 | ⚠️ 단일 포지션만 | ❌ 격차 | 중간 |
| **UI/UX** | ✅ 매우 직관적 | ⚠️ 복잡함 | ❌ 격차 | 중간 |

### 종합 평가
- **강점**: AI 연동, 리스크 관리, 백엔드 인프라 이미 준비됨 (80%)
- **약점**: 그리드 봇 로직, ROI 시각화, 다중 포지션 관리 미구현 (20%)
- **결론**: **핵심 로직 20% 추가로 비트겟과 동등한 수준 달성 가능**

---

## 🤖 AI의 역할 명확화

### AI가 할 일 (초기 설정 단계만)

#### 1. 시장 분석
```
입력: 심볼(BTCUSDT), 타임프레임(1h)
출력:
- 변동성 지표 (24시간 변동률, ATR)
- 트렌드 판단 (Uptrend/Downtrend/Sideways)
- 지지선/저항선 (7일 최저/최고)
- RSI, MACD 값
```

#### 2. 전략 추천
```
입력: 시장 분석 결과, 투자 금액, 리스크 선호도
출력: 3개 전략 (Conservative/Balanced/Aggressive)
- 가격 범위 (95,000 - 105,000 USDT)
- 그리드 개수 (30개)
- 레버리지 (3배)
- 예상 ROI (30일 APY: 15.2%)
- 리스크 레벨 (low/medium/high)
- 설명 (한글, 2-3문장)
```

#### 3. ROI 예측
```
입력: 전략 파라미터, 과거 7일 캔들 데이터
출력:
- 30일 예상 ROI (백테스트 기반)
- 최대 낙폭 (Max Drawdown: -8.5%)
- 예상 승률 (Win Rate: 75%)
```

### AI가 하지 않을 일 (백엔드 봇 엔진)

- ❌ 실제 주문 실행 (Bitget API 호출)
- ❌ 포지션 모니터링 (실시간 가격 추적)
- ❌ 자동 재주문 (그리드 체결 후 재배치)
- ❌ 수익 계산 (실시간 PnL)

### AI 호출 플로우
```
사용자: "BTC 그리드 봇 실행하고 싶어요"
   ↓
[1회 AI 호출] DeepSeek API
   → 시장 분석 (7일 캔들 데이터)
   → 3개 전략 추천
   → 예상 ROI 계산
   ↓
사용자: "Conservative 전략 선택" (1,000 USDT 투자)
   ↓
[봇 엔진 시작] - AI 없이 자동 실행
   → 그리드 레벨 30개 생성
   → Bitget API로 지정가 주문 30개 배치
   → 3초마다 주문 체결 확인
   → 체결되면 반대 주문 자동 생성
   → 무한 반복 ♻️ (사용자가 정지할 때까지)
```

**중요**: AI는 **봇 생성 시 단 1회만 호출**되며, 이후 실시간 거래는 백엔드 봇 엔진이 자동으로 처리합니다.

---

## 💰 AI API 비용 예측

### DeepSeek API 가격
- **입력**: $0.14 / 1M tokens
- **출력**: $0.28 / 1M tokens

### 1회 AI 호출 비용
- **입력**: ~2,000 tokens (시장 데이터 + 프롬프트)
- **출력**: ~1,000 tokens (3개 전략 JSON)
- **총 비용**: $0.0006 (0.06센트)

### 캐싱 전략
1. **동일 요청 캐싱**: 1시간 동안 같은 심볼/투자금액 요청은 캐시 반환
2. **사전 생성**: 인기 코인(BTC, ETH, SOL, BNB)의 전략을 1시간마다 자동 생성
3. **캐싱 효과**: 90% 요청이 캐시 히트 → 실제 API 호출 10%만

### 월간 비용 예측 (사용자 100명 기준)

#### 시나리오 1: 캐싱 없을 때
```
100명 * 월 10회 요청 * $0.0006 = $0.60/월
```

#### 시나리오 2: 캐싱 있을 때 (90% 캐시 히트)
```
100명 * 월 10회 * 10% * $0.0006 = $0.06/월
```

#### 시나리오 3: 사전 생성 포함
```
사전 생성: 4 코인 * 4 투자 티어 * 24시간 * 30일 * $0.0006 = $3.46/월
실제 요청: $0.06/월
총합: $3.52/월
```

### 최종 결론
- **월 AI API 비용**: **$3.52** (사용자 100명 기준)
- **사용자당 비용**: **$0.035/월** (3.5센트)
- **평가**: **무시할 수준의 비용**

---

## 📅 구현 일정 (총 3주)

### Week 1: 인프라 및 AI 서비스 (5일)
- **Day 1**: 데이터베이스 모델 추가 (`AIBot`, `GridPosition`, `AIStrategyRecommendation`)
- **Day 2**: AI 분석 서비스 기본 구조 (시장 분석 로직)
- **Day 3**: DeepSeek 프롬프트 최적화 (Futures Grid 전략 추천)
- **Day 4**: API 엔드포인트 기본 틀 (`/grid-bot/analyze`, `/grid-bot/create`)
- **Day 5**: 투자 금액 비율 계산 로직

### Week 2: 그리드 봇 엔진 (5일)
- **Day 6-7**: GridBotEngine 기본 구조 (그리드 레벨 계산, 주문 수량 계산)
- **Day 8-9**: 초기 주문 배치 로직 (Long/Short/Neutral Grid)
- **Day 10**: 주문 체결 모니터링 및 재주문

### Week 3: 프론트엔드 및 테스트 (5일)
- **Day 11-12**: Futures Grid Bot 페이지 제작 (AI 전략 카드, ROI 차트)
- **Day 13**: 실행 중인 봇 목록 UI (실시간 업데이트)
- **Day 14**: 단위 테스트 및 모의 거래
- **Day 15**: 문서화 및 배포

---

## 🚀 성공 지표 (KPI)

### 기술적 지표
- ✅ AI 응답 시간 < 3초
- ✅ 봇 시작 시간 < 5초
- ✅ 주문 체결 감지 시간 < 5초
- ✅ 동시 실행 가능 봇 수 > 100개
- ✅ 시스템 가동 시간 > 99.5%

### 사용자 경험 지표
- ✅ 봇 생성 클릭 수 < 3회
- ✅ AI 추천 정확도 > 70%
- ✅ 사용자 만족도 > 4.0/5.0
- ✅ 봇 실행 성공률 > 95%

### 비즈니스 지표
- ✅ 월 활성 사용자(MAU) > 50명
- ✅ 평균 봇 실행 시간 > 24시간
- ✅ 사용자 재방문율 > 60%

---

## ⚠️ 리스크 및 주의사항

### 1. 기술적 리스크
- **청산 위험**: 레버리지 높을수록 위험 → 초보자에게 경고 메시지 필수
- **API Rate Limit**: Bitget API 호출 빈도 제한 확인 필요
- **주문 실패**: 네트워크 오류, 잔고 부족 등 예외 처리 철저히
- **데이터베이스 부하**: 수천 개 GridPosition 레코드 → 인덱스 최적화 필수

### 2. 법적 리스크
- **투자 손실 책임**: 면책 조항 명시 필수
- **자본시장법**: 자문 서비스로 간주될 수 있음 → 법률 검토 필요
- **개인정보보호**: API 키 암호화 저장 필수

### 3. 운영 리스크
- **고객 지원**: AI 추천이 틀렸을 때 대응 방안 마련
- **시스템 장애**: 봇이 멈췄을 때 알림 시스템 구축
- **보안**: API 키 유출 방지, SQL Injection 방어

### 4. 비즈니스 리스크
- **초기 사용자 확보**: 마케팅 전략 필요
- **경쟁사 대응**: 비트겟, 바이낸스 등 대형 거래소와 차별화
- **수익 모델**: 수수료, 구독료 등 수익 구조 고민 필요

---

## 📚 참고 자료

### Bitget 공식 문서
- [A Complete Guide to AI Trading Bots on Bitget](https://beincrypto.com/learn/ai-trading-bots-bitget-guide/)
- [Mastering Bitget Trading Bots With Use Cases](https://www.bitget.com/support/articles/12560603805406)
- [Bitget Futures Grid Bot Setup Guide](https://www.bitget.com/academy/futures-grid-101)
- [Futures Grid parameters explained](https://www.bitget.com/support/articles/12560603791590)
- [Bitget's Martingale Strategy](https://www.bitget.com/academy/bitget-martingale-strategy-a-hands-on-tutorial)

### 기술 문서
- [DeepSeek API Documentation](https://platform.deepseek.com/api-docs/)
- [Bitget API v2 Documentation](https://www.bitget.com/api-doc/common/intro)
- [FastAPI Async Documentation](https://fastapi.tiangolo.com/async/)

---

## 📞 다음 단계

### 즉시 작업 가능한 항목
1. ✅ 새 Git 브랜치 생성 (`git checkout -b feature/ai-bots`)
2. ✅ 데이터베이스 모델 추가 (Day 1 작업)
3. ✅ Alembic 마이그레이션 파일 생성

### 준비가 필요한 항목
1. ⏳ 테스트용 Bitget 계좌 준비 (모의 거래 환경)
2. ⏳ DeepSeek API 키 확인 (이미 있는지 확인 필요)
3. ⏳ 프로덕션 환경 분리 (새 서버 또는 Docker 컨테이너)

### 의사결정 필요 항목
1. ❓ 어떤 봇부터 먼저 구현할지 (추천: Futures Grid Bot)
2. ❓ 사용자당 최대 봇 개수 제한 (추천: 10개)
3. ❓ 최소 투자 금액 설정 (추천: 10 USDT)

---

## 🎯 최종 결론

### 구현 가능성: ✅ 매우 높음 (95%)
- 현재 인프라의 80%가 이미 준비됨
- 핵심 로직 20%만 추가하면 완성
- AI API 비용 매우 저렴 (월 $5 이하)

### 예상 작업 기간: 3주 (풀타임 기준)
- Week 1: 인프라 및 AI 서비스
- Week 2: 그리드 봇 엔진
- Week 3: 프론트엔드 및 테스트

### 차별화 포인트
1. 🎯 비트겟보다 **더 쉬운 UX**
2. 💰 **무료 AI 추천** (경쟁사는 유료)
3. 🇰🇷 **한국어 완벽 지원**
4. 🔒 **완벽한 보안** (API 키 암호화)

### 권장 사항
1. ✅ **MVP 먼저**: Futures Grid Bot만 먼저 완성
2. ✅ **테스트 철저히**: 소액으로 충분히 검증 후 배포
3. ✅ **문서화**: 사용자 가이드 및 API 문서 작성
4. ✅ **점진적 확장**: CTA, Martingale 등은 Phase 2에서

---

## 📖 관련 문서

- **기술 사양**: [`AI_BOTS_TECHNICAL_SPEC.md`](./AI_BOTS_TECHNICAL_SPEC.md)
- **구현 가이드**: [`AI_BOTS_IMPLEMENTATION_GUIDE.md`](./AI_BOTS_IMPLEMENTATION_GUIDE.md)
- **Q&A**: [`AI_BOTS_QNA.md`](./AI_BOTS_QNA.md)

---

**작성자**: Claude AI
**최종 업데이트**: 2024년 12월 8일
**버전**: 1.0.0
