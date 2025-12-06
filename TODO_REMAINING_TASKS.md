# 📋 남은 작업 목록 (TODO)

> **작성일**: 2025-12-05  
> **프로젝트**: Auto Dashboard (암호화폐 자동 거래 시스템)  
> **현재 상태**: 핵심 기능 완료, 추가 개선 작업 진행 중

---

## 📊 완료 현황 요약

| 카테고리 | 완료율 | 상태 |
|----------|--------|------|
| 백테스트 오프라인 모드 | 100% | ✅ 완료 |
| 초보자 UI 개선 | 80% | 🔄 진행 중 |
| 트레이딩 페이지 개선 | 100% | ✅ 완료 |
| 관리자 기능 | 100% | ✅ 완료 |
| 버그 수정 | 100% | ✅ 완료 |

---

## 🔴 높은 우선순위 (즉시 진행 필요)

### 1. 백테스트 캔들 데이터 - 1h/4h 3년 데이터 확보

**예상 시간**: 2~3시간

**현재 상태**: ⚠️ Bitget API 제한으로 1h/4h 데이터 3년치 확보 불가

**현재 데이터 현황** (2025-12-05 기준):

| 타임프레임 | 데이터 범위 | 상태 |
|------------|-------------|------|
| **1d (일봉)** | 2021-12-26 ~ 현재 (약 4년) | ✅ 완료 |
| **4h (4시간봉)** | 2025-06-08 ~ 현재 (약 6개월) | ⚠️ 부족 |
| **1h (1시간봉)** | 2025-10-24 ~ 현재 (약 42일) | ⚠️ 부족 |

**문제점**: Bitget API가 1h/4h 타임프레임의 과거 데이터를 제공하지 않음

**해결 방안** (선택):

1. **Binance API 사용** - Binance는 더 오래된 1h/4h 데이터 제공
2. **외부 데이터 소스** - CryptoDataDownload 등에서 CSV 다운로드
3. **일봉(1d)로 백테스트** - 현재 3년 이상 데이터 확보됨

**작업 내용** (Binance 사용 시):

```bash
# Binance API용 다운로드 스크립트 생성 필요
# backend/scripts/download_binance_data.py

# 예시 구현
pip install python-binance
python scripts/download_binance_data.py --symbols BTCUSDT ETHUSDT --timeframes 1h 4h --years 3
```

**확인 방법**:

```bash
# 다운로드된 파일 확인
ls -la backend/candle_cache/
```

---

### 2. 실시간 환율 API 연동 (선택)

**예상 시간**: 1시간

**현재 상태**: 고정 환율 (1 USD = 1,460 KRW) 사용 중

**작업 내용**:

1. 환율 API 선택 (무료 옵션)
   - ExchangeRate-API (무료 1,500회/월)
   - Open Exchange Rates (무료 1,000회/월)
   - Fixer.io (무료 100회/월)

2. 백엔드에 환율 API 엔드포인트 추가

   ```python
   # backend/src/api/exchange_rate.py
   @router.get("/exchange-rate")
   async def get_exchange_rate():
       # 환율 API 호출 (캐싱 권장)
       return {"USD_KRW": 1460}
   ```

3. 프론트엔드에서 환율 가져오기

   ```javascript
   // 앱 시작 시 또는 1시간마다 갱신
   const rate = await api.getExchangeRate();
   ```

**파일 수정 필요**:

- `backend/src/api/exchange_rate.py` (신규)
- `frontend/src/pages/Trading.jsx` (수정)
- `frontend/src/components/TradingChart.jsx` (수정)

---

### 3. 폼 항목에 용어 설명 툴팁 적용

**예상 시간**: 30분

**현재 상태**: `TermTooltip` 컴포넌트 완성, 적용 필요

**작업 내용**:
`BacktestingPage.jsx`의 각 Form.Item에 `TermTooltip` 적용

**Before**:

```jsx
<Form.Item name="leverage" label="레버리지">
```

**After**:

```jsx
<Form.Item 
    name="leverage" 
    label={<TermTooltip term="leverage">레버리지</TermTooltip>}
>
```

**적용 대상 필드**:

- [ ] 레버리지 (leverage)
- [ ] 마진 모드 (margin_mode)
- [ ] 펀딩 피 (funding_fee)
- [ ] 슬리피지 (slippage)
- [ ] 초기 자금 (initial_balance)

---

## 🟡 중간 우선순위 (이번 주 내 진행)

### 4. 추천 설정 프리셋 버튼

**예상 시간**: 30분

**현재 상태**: `PresetButtons` 컴포넌트 완성, 적용 필요

**작업 내용**:
백테스트 설정 폼에 원클릭 프리셋 버튼 추가

```jsx
import { PresetButtons } from '../components/backtest/BeginnerGuide';

// 폼 위에 추가
<PresetButtons onSelect={(preset) => {
    form.setFieldsValue({
        leverage: preset.leverage,
        margin_mode: preset.marginMode,
        // ...
    });
}} />
```

**프리셋 옵션**:

| 프리셋 | 레버리지 | 마진 모드 | 대상 |
|--------|----------|-----------|------|
| 🐣 초보자 | 1x | 격리 | 입문자 |
| 🧑 중급자 | 3x | 격리 | 경험자 |
| 🔥 고급자 | 5x~10x | 격리 | 전문가 |

---

### 5. 청산가 실시간 계산기

**예상 시간**: 1시간

**현재 상태**: 미구현

**작업 내용**:
레버리지 설정 시 예상 청산 가격을 실시간으로 계산하여 표시

```jsx
// LiquidationCalculator.jsx (신규 생성)

const calculateLiquidationPrice = (entryPrice, leverage, direction) => {
    const maintenanceMargin = 0.005; // 0.5%
    
    if (direction === 'long') {
        return entryPrice * (1 - (1 / leverage) + maintenanceMargin);
    } else {
        return entryPrice * (1 + (1 / leverage) - maintenanceMargin);
    }
};

// 예: 진입가 $100, 10x 레버리지, 롱 포지션
// 청산가 = $100 * (1 - 0.1 + 0.005) = $90.5
```

**UI 표시**:

```
⚠️ 청산 경고
현재 설정 기준, 가격이 $90,500 이하로 떨어지면 청산됩니다.
(-9.5% 하락 시 청산)
```

---

### 6. crontab 자동 데이터 갱신 설정

**예상 시간**: 30분

**현재 상태**: 수동 다운로드만 가능

**작업 내용**:
매월 1일 자동으로 캔들 데이터 갱신

```bash
# crontab 편집
crontab -e

# 매월 1일 새벽 3시에 실행
0 3 1 * * cd /path/to/auto-dashboard/backend && python scripts/download_candle_data.py --all --years 3 >> /var/log/candle_download.log 2>&1
```

**대안**: GitHub Actions 또는 서버 스케줄러 사용

---

### 7. 결과 상세 해석 안내 모달

**예상 시간**: 1시간

**현재 상태**: 점수표 완성, 상세 설명 모달 미구현

**작업 내용**:
각 지표 클릭 시 상세 설명과 개선 방법 안내

```jsx
// MetricExplanationModal.jsx

const explanations = {
    sharpe_ratio: {
        title: '샤프 비율이란?',
        description: '위험 대비 수익률을 나타내는 지표입니다.',
        good: '2.0 이상이면 좋은 전략입니다.',
        improve: '손실을 줄이거나 수익을 높이면 개선됩니다.',
    },
    // ...
};
```

---

## 🟢 낮은 우선순위 (시간 여유 시)

### 8. 린트 경고 정리

**예상 시간**: 15분

**현재 상태**: 기능에 영향 없는 경고 존재

**작업 내용**:

```bash
# 경고 목록
backend/src/api/backtest.py:
  - os, uuid, tempfile 등 사용되지 않는 import 제거
  - 사용되지 않는 변수 e 제거
```

**수정 방법**:

```python
# Before
import os
import uuid
from fastapi.security import HTTPAuthorizationCredentials
import tempfile

# After
# 사용하지 않는 import 삭제
```

---

### 9. 마크다운 린트 수정

**예상 시간**: 10분

**현재 상태**: 코드 블록 언어 명시 누락

**파일 목록**:

- `BACKTEST_OFFLINE_DATA_GUIDE.md`
- `SESSION_HANDOVER.md`

**수정 방법**:

````markdown
<!-- Before -->
```
코드 내용
```

<!-- After -->
```bash
코드 내용
```
````

---

### 10. 관리자 웹 UI에서 수동 데이터 다운로드

**예상 시간**: 2시간

**현재 상태**: 터미널 명령어만 지원

**작업 내용**:

1. 백엔드 API 추가

   ```python
   @router.post("/cache/download")
   async def trigger_download(symbols: List[str], timeframes: List[str]):
       # 백그라운드에서 다운로드 실행
       pass
   ```

2. 관리자 페이지 UI 추가
   - 심볼/타임프레임 선택 체크박스
   - 다운로드 진행 상황 표시
   - 완료 알림

---

## 🔧 기술 부채 (Technical Debt)

### 1. 전략 코드 매핑 개선

**문제**: `strategy_id`에서 `strategy_code`로 변환 시 `params.type` 의존

**해결 방안**:

- Strategy 모델에 `code` 필드 추가
- 또는 별도 매핑 테이블 생성

### 2. 환율 중복 정의

**문제**: Trading.jsx와 TradingChart.jsx에서 환율 중복 정의

**해결 방안**:

```javascript
// constants/exchange.js
export const USD_KRW_RATE = 1460;
```

### 3. 에러 핸들링 표준화

**문제**: API 에러 처리 방식 불일치

**해결 방안**:

- 공통 에러 핸들러 설정
- 에러 코드 표준화

---

## 📅 추천 작업 순서

### 이번 주 (Day 1-2)

1. ✅ 캔들 데이터 다운로드 (필수)
2. ✅ 폼 항목 툴팁 적용
3. ✅ 추천 설정 프리셋 버튼

### 다음 주 (Day 3-5)

4. 청산가 계산기
5. 결과 상세 해석 모달
6. crontab 설정

### 여유 시

7. 실시간 환율 API
8. 린트 정리
9. 관리자 다운로드 UI

---

## 📝 참고 문서

- `BACKTEST_OFFLINE_DATA_GUIDE.md` - 오프라인 데이터 관리 가이드
- `BACKTEST_BEGINNER_GUIDE.md` - 초보자용 백테스트 가이드
- `SESSION_HANDOVER.md` - 세션 인수인계서
- `CODE_REVIEW_AND_IMPROVEMENTS.md` - 코드 리뷰 및 개선사항
- `DEVELOPMENT_GUIDE.md` - 개발 환경 설정 가이드

---

## ✅ 체크리스트

### 데이터 다운로드

- [ ] BTCUSDT 3년치 다운로드
- [ ] ETHUSDT 3년치 다운로드
- [ ] 기타 심볼 다운로드
- [ ] 캐시 파일 확인

### UI 개선

- [ ] 폼 항목 툴팁 적용
- [ ] 프리셋 버튼 추가
- [ ] 청산가 계산기 추가

### 유지보수

- [ ] 린트 경고 정리
- [ ] 환율 상수 통합
- [ ] 에러 핸들링 표준화

---

*마지막 업데이트: 2025-12-05 15:08*
