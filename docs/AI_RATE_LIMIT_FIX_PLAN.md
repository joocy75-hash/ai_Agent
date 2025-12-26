# AI Rate Limit 완벽 해결 계획서

> **작성일**: 2025-12-24
> **목적**: 다중 사용자 24시간 운영 환경에서 AI API Rate Limit 문제 완전 해결

---

## 1. 현재 문제 분석

### 1.1 증상
```
2025-12-23 20:23:45 - ERROR - Gemini API error: 429 Client Error: Too Many Requests
2025-12-23 20:17:35 - WARNING - Rate limit hit #412, backoff multiplier: 8x
```

- Gemini API 429 에러 **412회 이상** 누적
- Backoff multiplier가 **8x**로 최대치 도달
- 1명 사용자 테스트 환경에서도 문제 발생

### 1.2 근본 원인 (Critical)

```
봇 루프 (6초마다)
    ↓
strategy_loader.load_strategy_class() 호출
    ↓
❌ 새로운 ETHAutonomous40PctStrategy 인스턴스 생성 (매번!)
    ↓
❌ 새로운 SmartSamplingManager 생성 (매번!)
    ↓
❌ _memory_cache = {} 빈 상태로 초기화
    ↓
❌ 첫 호출로 인식 → AI API 호출 시도
    ↓
🔴 Gemini Rate Limit 초과 → 429 에러
```

**핵심 문제**: 전략 인스턴스가 매번 새로 생성되어 SmartSamplingManager의 인메모리 캐시가 초기화됨

### 1.3 API 제한 현황 (2025.12 기준)

| Provider | Rate Limit | 비용 | 특징 |
|----------|------------|------|------|
| **Gemini 2.5 Pro** | 5 RPM, 100 RPD | 무료 | ❌ 2025.12.7 이후 대폭 축소 |
| **Gemini 2.5 Flash** | 10 RPM, 250 RPD | 무료 | ⚠️ 일일 한도 낮음 |
| **DeepSeek V3** | **무제한** | $0.28/1M tokens | ✅ Rate Limit 없음 |

**Sources**:
- [Gemini Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [DeepSeek Rate Limit](https://api-docs.deepseek.com/quick_start/rate_limit)

---

## 2. 해결 전략

### 2.1 아키텍처 변경 개요

```
[현재 - 문제]
┌─────────────────────────────────────────────────────────────┐
│  Bot Loop (6초마다)                                          │
│    ↓                                                        │
│  load_strategy_class() → 새 Strategy 인스턴스 생성            │
│    ↓                                                        │
│  새 SmartSamplingManager (캐시 초기화됨)                      │
│    ↓                                                        │
│  AI 호출 시도 → Rate Limit!                                  │
└─────────────────────────────────────────────────────────────┘

[수정 후 - 해결]
┌─────────────────────────────────────────────────────────────┐
│  Application Startup                                         │
│    ↓                                                        │
│  글로벌 SmartSamplingManager 초기화 (싱글톤)                   │
│  글로벌 IntegratedAIService 초기화 (싱글톤)                    │
│  전략 캐시 딕셔너리 초기화                                     │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Bot Loop (6초마다)                                          │
│    ↓                                                        │
│  get_cached_strategy() → 캐시된 Strategy 재사용               │
│    ↓                                                        │
│  글로벌 SmartSamplingManager (캐시 유지!)                     │
│    ↓                                                        │
│  45초 경과 확인 → 경과 안 됨 → 스킵 (캐시 응답)                │
│                 → 경과 됨 → DeepSeek 호출 (무제한)            │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 세부 변경 사항

#### A. 전략 인스턴스 싱글톤 캐시 (strategy_loader.py)

```python
# 전략 인스턴스 캐시 (user_id별로 관리)
_strategy_cache: Dict[str, Any] = {}

def get_cached_strategy(strategy_code: str, user_id: int, params: dict) -> Any:
    """캐시된 전략 인스턴스 반환 또는 신규 생성"""
    cache_key = f"{strategy_code}:{user_id}"

    if cache_key not in _strategy_cache:
        _strategy_cache[cache_key] = _create_strategy_instance(strategy_code, params, user_id)
        logger.info(f"✅ Strategy instance created and cached: {cache_key}")
    else:
        logger.debug(f"♻️ Reusing cached strategy: {cache_key}")

    return _strategy_cache[cache_key]
```

#### B. DeepSeek 기본 사용 + Gemini 폴백 (integrated_ai_service.py)

```python
# 기본값을 DeepSeek로 변경 (Rate Limit 없음)
AI_PROVIDER = "deepseek"  # 기본값 변경

# Gemini는 특별한 경우에만 사용 (고급 추론 필요 시)
async def call_ai(self, ...):
    try:
        if self.ai_provider == "deepseek":
            return await self._call_deepseek_api(...)
    except Exception as e:
        # DeepSeek 실패 시 Gemini 폴백 (선택적)
        logger.warning(f"DeepSeek failed, falling back to Gemini: {e}")
        return await self._call_gemini_api(...)
```

#### C. 글로벌 SmartSamplingManager (smart_sampling.py)

```python
# 글로벌 싱글톤 인스턴스
_global_sampling_manager: Optional[SmartSamplingManager] = None

def get_global_sampling_manager() -> SmartSamplingManager:
    """글로벌 SmartSamplingManager 싱글톤 반환"""
    global _global_sampling_manager

    if _global_sampling_manager is None:
        _global_sampling_manager = SmartSamplingManager()
        logger.info("✅ Global SmartSamplingManager initialized")

    return _global_sampling_manager
```

#### D. IntegratedAIService 싱글톤 강화 (integrated_ai_service.py)

```python
# 기존 싱글톤 로직 강화
_integrated_ai_service_instance: Optional[IntegratedAIService] = None
_service_lock = threading.Lock()

def get_integrated_ai_service(redis_client=None) -> IntegratedAIService:
    """Thread-safe 싱글톤 반환"""
    global _integrated_ai_service_instance

    with _service_lock:
        if _integrated_ai_service_instance is None:
            _integrated_ai_service_instance = IntegratedAIService(redis_client)
            # 글로벌 SmartSamplingManager 주입
            _integrated_ai_service_instance.sampling_manager = get_global_sampling_manager()

    return _integrated_ai_service_instance
```

---

## 3. 다중 사용자 환경 설계

### 3.1 사용자별 분리 vs 공유

| 컴포넌트 | 공유 방식 | 이유 |
|----------|----------|------|
| `IntegratedAIService` | **글로벌 공유** | API 키, Rate Limit 관리 일원화 |
| `SmartSamplingManager` | **글로벌 공유** | 캐시 상태 유지 필수 |
| `Strategy Instance` | **사용자별 캐시** | 포지션, 상태가 사용자별로 다름 |
| `Market Regime 결과` | **글로벌 캐시** | 동일 심볼은 모든 사용자에게 동일 |

### 3.2 시뮬레이션: 10명 사용자 동시 운영

```
설정:
- 사용자: 10명
- 봇 루프: 6초마다
- AI 호출 간격: 45초 (market_regime)

[수정 전]
- 분당 AI 호출 시도: 10명 × 10회 = 100회/분
- Gemini 한도: 5-10회/분
- 결과: ❌ 즉시 Rate Limit

[수정 후 - DeepSeek]
- 분당 AI 호출: 60초/45초 = 1.3회/분 (전체 공유)
- DeepSeek 한도: 무제한
- 결과: ✅ 문제 없음

[비용 예상]
- 호출당 토큰: ~500 tokens
- 시간당 호출: 80회
- 일일 호출: 1,920회
- 일일 비용: 1,920 × 500 × $0.28/1M = $0.27/일
- 월간 비용: ~$8/월 (10명 기준)
```

---

## 4. 구현 단계

### Phase 1: 핵심 수정 (필수)

| 순서 | 파일 | 변경 내용 | 우선순위 |
|------|------|----------|----------|
| 1 | `src/services/__init__.py` | 글로벌 SmartSamplingManager 초기화 추가 | 🔴 Critical |
| 2 | `src/services/ai_optimization/smart_sampling.py` | 글로벌 싱글톤 함수 추가 | 🔴 Critical |
| 3 | `src/services/ai_optimization/integrated_ai_service.py` | 글로벌 sampling_manager 사용, DeepSeek 기본값 | 🔴 Critical |
| 4 | `src/services/strategy_loader.py` | 전략 인스턴스 캐시 구현 | 🔴 Critical |
| 5 | `src/config.py` | AI_PROVIDER 기본값 "deepseek" 변경 | 🟡 High |

### Phase 2: 최적화 (권장)

| 순서 | 파일 | 변경 내용 | 우선순위 |
|------|------|----------|----------|
| 6 | `src/agents/market_regime/agent.py` | 글로벌 캐시 결과 공유 | 🟢 Medium |
| 7 | `src/strategies/eth_ai_autonomous_40pct_strategy.py` | 싱글톤 AI 서비스 사용 확인 | 🟢 Medium |

### Phase 3: 배포 및 검증

| 순서 | 작업 | 설명 |
|------|------|------|
| 8 | 문법 검증 | `python3 -m py_compile` |
| 9 | 로컬 테스트 | Docker 로컬 실행 |
| 10 | 서버 배포 | rsync + docker compose rebuild |
| 11 | 로그 모니터링 | Rate Limit 에러 없는지 확인 |

---

## 5. 롤백 계획

문제 발생 시:

```bash
# 1. 봇 중지
ssh root@158.247.245.197 "curl -X POST http://localhost:8000/api/v1/bot/stop -H 'Authorization: Bearer TOKEN'"

# 2. 이전 버전으로 롤백
ssh root@158.247.245.197 "cd /root/auto-dashboard && git checkout HEAD~1 -- backend/src/services/"

# 3. 재빌드 및 재시작
ssh root@158.247.245.197 "cd /root/auto-dashboard && docker compose build backend && docker compose up -d backend"
```

---

## 6. 성공 기준

| 지표 | 현재 | 목표 |
|------|------|------|
| Rate Limit 에러 | 412회+ | **0회** |
| Backoff Multiplier | 8x | **1x** |
| AI 호출 성공률 | ~10% | **99%+** |
| 전략 초기화 빈도 | 매 6초 | **앱 시작 시 1회** |
| 일일 API 비용 | N/A | **< $1** |

---

## 7. 예상 결과

### Before (현재)
```
20:23:45 - 🚀 Loading ETH AI Autonomous 40% Margin Strategy
20:23:45 - ✅ All 4 AI agents initialized
20:23:45 - ERROR - Gemini API error: 429 Too Many Requests
20:23:51 - 🚀 Loading ETH AI Autonomous 40% Margin Strategy  ← 다시 초기화!
20:23:51 - ✅ All 4 AI agents initialized  ← 다시 초기화!
```

### After (수정 후)
```
[앱 시작 시]
12:00:00 - ✅ Global SmartSamplingManager initialized
12:00:00 - ✅ IntegratedAIService initialized (DeepSeek V3)

[첫 번째 봇 루프]
12:00:05 - ✅ Strategy instance created and cached: eth_autonomous_40pct:1
12:00:05 - ✅ AI call for market_regime: $0.000140, 500 tokens

[이후 봇 루프 - 45초 이내]
12:00:11 - ♻️ Reusing cached strategy: eth_autonomous_40pct:1
12:00:11 - ⏭️ Skipping AI call for market_regime: periodic_wait_39s

[45초 경과 후]
12:00:50 - ♻️ Reusing cached strategy: eth_autonomous_40pct:1
12:00:50 - ✅ AI call for market_regime: $0.000140, 500 tokens
```

---

## 8. 결론

**DeepSeek를 기본 AI Provider로 사용하고, 전략/AI 서비스를 싱글톤으로 관리**하면:

1. ✅ **Rate Limit 완전 해결** (DeepSeek은 제한 없음)
2. ✅ **다중 사용자 지원** (10명+ 동시 운영 가능)
3. ✅ **비용 효율** (월 $8~10 예상, Gemini 무료보다 저렴한 수준)
4. ✅ **빠른 응답** (45초 간격 유지, 선물거래 대응 가능)
5. ✅ **안정성** (429 에러 없음, 24시간 운영)

---

**승인 후 구현을 시작하겠습니다.**
