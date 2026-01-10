# Trading 페이지 리디자인 구현 계획서

> **버전**: 1.0.0
> **작성일**: 2026-01-10
> **상태**: 📋 계획 완료, 구현 대기
> **참조**: Bitget/Bybit 봇 마켓플레이스 UI

---

## 📋 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [목표 UI 설계](#목표-ui-설계)
3. [현재 상태 분석](#현재-상태-분석)
4. [아키텍처 설계](#아키텍처-설계)
5. [Phase 1: 컴포넌트 생성](#phase-1-컴포넌트-생성)
6. [Phase 2: Trading 페이지 교체](#phase-2-trading-페이지-교체)
7. [Phase 3: 상세 모달 구현](#phase-3-상세-모달-구현)
8. [Phase 4: 스타일링 및 반응형](#phase-4-스타일링-및-반응형)
9. [Phase 5: 테스트 및 배포](#phase-5-테스트-및-배포)
10. [작업 체크리스트](#작업-체크리스트)
11. [파일별 상세 구현 가이드](#파일별-상세-구현-가이드)

---

## 프로젝트 개요

### 목표
기존 Trading 페이지(차트 + 단일 봇 제어)를 **Bitget/Bybit 스타일의 봇 마켓플레이스 UI**로 완전 교체

### 핵심 변경사항
| 항목 | 기존 | 변경 |
|------|------|------|
| 레이아웃 | 차트 + 봇 컨트롤 패널 | 봇 카드 리스트 |
| 테마 | 라이트 모드 | **다크 모드** |
| 봇 시작 방식 | 전략 선택 → 시작 | 카드 클릭 → 금액 입력 → 시작 |
| 정보 표시 | 전략 설명 | 30D ROI, 승률, MDD, 사용자 수 |

### 참조 UI (Bitget)
```
┌─────────────────────────────────────────────────┐
│  Highest ROI ▼                    [정렬 드롭다운]│
├─────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────┐ │
│ │ BTCUSDT              [Short] [5x]    [Use]  │ │
│ │ 30-day APY                          📈      │ │
│ │ +984.52%                                    │ │
│ │ Min investment    41.7804 USDT              │ │
│ │ Recommended       7-30 days                 │ │
│ │ Users             5967                      │ │
│ └─────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────┐ │
│ │ ETHUSDT              [Long] [10x]    [Use]  │ │
│ │ ...                                         │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

---

## 목표 UI 설계

### 1. 목록 화면 (Trading 페이지)

```
┌─────────────────────────────────────────────────────────────┐
│  🤖 AI 봇 트레이딩                                           │
│  전문 트레이더의 전략을 복사하여 자동으로 수익을 창출하세요      │
├─────────────────────────────────────────────────────────────┤
│  [Highest ROI ▼]  [All Symbols ▼]  [🔄 새로고침]             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────┐  ┌──────────────────────┐        │
│  │ BTCUSDT              │  │ ETHUSDT              │        │
│  │ [Short] [5x]   [Use] │  │ [Long] [10x]   [Use] │        │
│  │                      │  │                      │        │
│  │ 30-day APY           │  │ 30-day APY           │        │
│  │ +984.52%      📈     │  │ +893.76%      📈     │        │
│  │                      │  │                      │        │
│  │ Min: 41.78 USDT      │  │ Min: 23.02 USDT      │        │
│  │ Duration: 7-30 days  │  │ Duration: 7-30 days  │        │
│  │ Users: 5967          │  │ Users: 2697          │        │
│  └──────────────────────┘  └──────────────────────┘        │
│                                                             │
│  ┌──────────────────────┐  ┌──────────────────────┐        │
│  │ SOLUSDT              │  │ XRPUSDT              │        │
│  │ ...                  │  │ ...                  │        │
│  └──────────────────────┘  └──────────────────────┘        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2. 상세 모달 (Use 클릭 시)

```
┌─────────────────────────────────────────────────────────────┐
│  ← BTCUSDT                                           [X]    │
│    [Futures grid] [Short] [5x]                              │
├─────────────────────────────────────────────────────────────┤
│  ┌────────────────────┬────────────────────┐                │
│  │ 30D backtested ROI │ Funds in use(USDT) │                │
│  │ +984.52%           │ 1,202,997.44       │                │
│  ├────────────────────┼────────────────────┤                │
│  │ Users              │ 30D max drawdown   │                │
│  │ 5,967              │ 16.12%             │                │
│  └────────────────────┴────────────────────┘                │
├─────────────────────────────────────────────────────────────┤
│  Bot details                                                │
│  Grid bots execute trades automatically based on preset     │
│  price levels, profiting from buying low and selling high   │
│  during market fluctuations. They are particularly          │
│  effective in volatile or range-bound markets.              │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         📊 그리드/추세 차트 (시각화)                  │   │
│  │         [Buy/Sell 포인트 표시]                       │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  Bot parameters                                             │
│  ┌────────────────────┬────────────────────┐                │
│  │ 손절가             │ 익절가             │                │
│  │ -2.5%              │ +5.0%              │                │
│  └────────────────────┴────────────────────┘                │
├─────────────────────────────────────────────────────────────┤
│  투자 금액                                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  $_________ USDT        [25%] [50%] [75%] [MAX]     │   │
│  └─────────────────────────────────────────────────────┘   │
│  Min: $50 USDT  |  Available: $1,234.56 USDT               │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    [ Use ]                           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 현재 상태 분석

### 재활용 가능한 컴포넌트

| 컴포넌트 | 경로 | 재활용 여부 | 수정 필요 |
|---------|------|------------|---------|
| `TrendTemplateCard` | `components/trend/templates/` | ⚠️ 부분 활용 | 다크모드 + 레이아웃 변경 |
| `TrendTemplateList` | `components/trend/templates/` | ❌ 새로 작성 | 정렬/필터 UI 추가 |
| `UseTrendTemplateModal` | `components/trend/` | ⚠️ 부분 활용 | Bitget 스타일로 변경 |
| `multibot.js` API | `api/` | ✅ 그대로 사용 | - |

### 삭제/대체 대상

| 컴포넌트 | 경로 | 처리 |
|---------|------|------|
| `TradingViewWidget` | `components/` | 삭제 (차트 제거) |
| `BalanceCard` | `components/` | Trading에서 제거 |
| `PositionList` | `components/` | Trading에서 제거 |
| `BotLogViewer` | `components/` | Trading에서 제거 |

---

## 아키텍처 설계

### 새 컴포넌트 구조

```
frontend/src/
├── pages/
│   └── Trading.jsx              # 완전 교체
├── components/
│   └── trading/                 # 새 폴더
│       ├── index.js             # 배럴 export
│       ├── BotMarketplace.jsx   # 메인 컨테이너
│       ├── BotCard.jsx          # 봇 카드 (다크모드)
│       ├── BotCardList.jsx      # 카드 그리드
│       ├── BotDetailModal.jsx   # 상세 + 금액 입력 모달
│       ├── BotFilters.jsx       # 정렬/필터 컨트롤
│       ├── ActiveBotsBanner.jsx # 실행 중인 봇 상단 배너
│       └── styles/
│           ├── BotCard.css
│           ├── BotDetailModal.css
│           └── BotMarketplace.css
└── hooks/
    └── useBotMarketplace.js     # 상태 관리 훅
```

### 데이터 흐름

```
┌─────────────────────────────────────────────────────────────┐
│                     Trading.jsx                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                BotMarketplace.jsx                    │    │
│  │                                                      │    │
│  │  ┌──────────────┐                                   │    │
│  │  │ BotFilters   │  정렬: ROI/Users/New              │    │
│  │  └──────────────┘  필터: Symbol                     │    │
│  │                                                      │    │
│  │  ┌──────────────────────────────────────────────┐   │    │
│  │  │ ActiveBotsBanner (실행 중인 봇 요약)          │   │    │
│  │  └──────────────────────────────────────────────┘   │    │
│  │                                                      │    │
│  │  ┌──────────────────────────────────────────────┐   │    │
│  │  │ BotCardList                                   │   │    │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐     │   │    │
│  │  │  │ BotCard  │ │ BotCard  │ │ BotCard  │     │   │    │
│  │  │  └──────────┘ └──────────┘ └──────────┘     │   │    │
│  │  └──────────────────────────────────────────────┘   │    │
│  │                                                      │    │
│  │  ┌──────────────────────────────────────────────┐   │    │
│  │  │ BotDetailModal (선택된 봇 상세)               │   │    │
│  │  └──────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### API 연동

```javascript
// 사용할 API (multibot.js)
multibotAPI.getTemplates()      // 템플릿 목록
multibotAPI.getTemplateDetail() // 템플릿 상세
multibotAPI.startBot()          // 봇 시작
multibotAPI.getSummary()        // 잔고 + 활성 봇 요약
multibotAPI.checkBalance()      // 잔고 확인 (프리뷰)
```

---

## Phase 1: 컴포넌트 생성

### 1.1 BotCard.jsx (다크모드 카드)

**목적**: Bitget 스타일의 봇 템플릿 카드

**Props**:
```typescript
interface BotCardProps {
  template: {
    id: number;
    name: string;
    symbol: string;
    direction: 'long' | 'short' | 'both';
    leverage: number;
    backtest_roi_30d: number;
    min_investment: number;
    recommended_duration: string;
    active_users: number;
    is_featured: boolean;
  };
  onUse: (template) => void;
  loading?: boolean;
}
```

**디자인 요구사항**:
- 다크 배경 (#1a1a1a)
- 흰색/회색 텍스트
- 녹색 수익률 (+), 빨간색 손실 (-)
- 미니 라인 차트 (오른쪽 상단)
- [Use] 버튼 테두리 스타일

### 1.2 BotCardList.jsx (카드 그리드)

**목적**: 카드 반응형 그리드 레이아웃

**Props**:
```typescript
interface BotCardListProps {
  templates: Template[];
  onUseTemplate: (template) => void;
  loading: boolean;
  sortBy: 'roi' | 'users' | 'new';
  filterSymbol: string | null;
}
```

**레이아웃**:
- Desktop: 2열 그리드
- Tablet: 2열 그리드
- Mobile: 1열 스택

### 1.3 BotDetailModal.jsx (상세 모달)

**목적**: 봇 상세 정보 + 금액 입력 + 시작

**Props**:
```typescript
interface BotDetailModalProps {
  template: Template | null;
  open: boolean;
  onClose: () => void;
  onStart: (templateId, amount) => Promise<void>;
  availableBalance: number;
}
```

**섹션**:
1. 헤더: 심볼 + 태그들
2. 통계 그리드: ROI, Funds, Users, MDD
3. Bot details: 설명 텍스트
4. Bot parameters: 손절/익절
5. 금액 입력: 슬라이더 + 퍼센트 버튼
6. 확인 버튼

### 1.4 BotFilters.jsx (필터/정렬)

**Props**:
```typescript
interface BotFiltersProps {
  sortBy: string;
  onSortChange: (value) => void;
  filterSymbol: string | null;
  onFilterChange: (value) => void;
  symbols: string[];  // 사용 가능한 심볼 목록
}
```

### 1.5 ActiveBotsBanner.jsx (활성 봇 배너)

**목적**: 실행 중인 봇이 있으면 상단에 요약 표시

**Props**:
```typescript
interface ActiveBotsBannerProps {
  activeBots: Bot[];
  totalPnl: number;
  onViewAll: () => void;
}
```

### 1.6 useBotMarketplace.js (커스텀 훅)

**목적**: 상태 관리 로직 분리

```javascript
export function useBotMarketplace() {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState(null);
  const [sortBy, setSortBy] = useState('roi');
  const [filterSymbol, setFilterSymbol] = useState(null);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);

  // API 호출 함수들
  const loadTemplates = async () => { ... };
  const loadSummary = async () => { ... };
  const startBot = async (templateId, amount) => { ... };

  return {
    templates, loading, summary,
    sortBy, setSortBy,
    filterSymbol, setFilterSymbol,
    selectedTemplate, setSelectedTemplate,
    detailModalOpen, setDetailModalOpen,
    loadTemplates, loadSummary, startBot,
  };
}
```

---

## Phase 2: Trading 페이지 교체

### 2.1 Trading.jsx 완전 교체

**기존 코드**: 532줄 (차트 + 봇 컨트롤)
**새 코드**: ~150줄 (BotMarketplace 래퍼)

```jsx
// 새 Trading.jsx 구조
import { BotMarketplace } from '../components/trading';

export default function Trading() {
  return (
    <div className="trading-page dark-theme">
      <BotMarketplace />
    </div>
  );
}
```

### 2.2 BotMarketplace.jsx (메인 컨테이너)

```jsx
// 구조
export default function BotMarketplace() {
  const {
    templates, loading, summary,
    sortBy, setSortBy,
    filterSymbol, setFilterSymbol,
    selectedTemplate, setSelectedTemplate,
    detailModalOpen, setDetailModalOpen,
    loadTemplates, loadSummary, startBot,
  } = useBotMarketplace();

  useEffect(() => {
    loadTemplates();
    loadSummary();
  }, []);

  return (
    <div className="bot-marketplace">
      {/* 페이지 헤더 */}
      <PageHeader />

      {/* 활성 봇 배너 */}
      {summary?.active_bot_count > 0 && (
        <ActiveBotsBanner ... />
      )}

      {/* 필터/정렬 */}
      <BotFilters ... />

      {/* 봇 카드 리스트 */}
      <BotCardList ... />

      {/* 상세 모달 */}
      <BotDetailModal ... />
    </div>
  );
}
```

---

## Phase 3: 상세 모달 구현

### 3.1 모달 레이아웃

```jsx
<Modal
  open={open}
  onCancel={onClose}
  footer={null}
  width={480}
  className="bot-detail-modal dark"
>
  {/* 1. 헤더 */}
  <div className="modal-header">
    <div className="symbol-info">
      <img src={coinLogo} />
      <h2>{symbol}</h2>
    </div>
    <div className="tags">
      <Tag>{strategyType}</Tag>
      <Tag>{direction}</Tag>
      <Tag>{leverage}x</Tag>
    </div>
  </div>

  {/* 2. 통계 그리드 */}
  <div className="stats-grid">
    <StatItem label="30D ROI" value={roi} />
    <StatItem label="Funds in use" value={funds} />
    <StatItem label="Users" value={users} />
    <StatItem label="Max drawdown" value={mdd} />
  </div>

  {/* 3. 설명 */}
  <div className="bot-details">
    <h3>Bot details</h3>
    <p>{description}</p>
  </div>

  {/* 4. 파라미터 */}
  <div className="bot-parameters">
    <h3>Bot parameters</h3>
    <div className="param-row">
      <span>손절가: -{stopLoss}%</span>
      <span>익절가: +{takeProfit}%</span>
    </div>
  </div>

  {/* 5. 금액 입력 */}
  <div className="amount-input">
    <InputNumber
      value={amount}
      onChange={setAmount}
      min={minInvestment}
      max={availableBalance}
    />
    <div className="percent-buttons">
      <Button onClick={() => setAmount(available * 0.25)}>25%</Button>
      <Button onClick={() => setAmount(available * 0.50)}>50%</Button>
      <Button onClick={() => setAmount(available * 0.75)}>75%</Button>
      <Button onClick={() => setAmount(available)}>MAX</Button>
    </div>
    <div className="balance-info">
      Min: ${minInvestment} | Available: ${availableBalance}
    </div>
  </div>

  {/* 6. 시작 버튼 */}
  <Button
    type="primary"
    block
    size="large"
    onClick={handleStart}
    loading={starting}
  >
    Use
  </Button>
</Modal>
```

### 3.2 금액 검증 로직

```javascript
const handleStart = async () => {
  // 1. 최소 금액 체크
  if (amount < template.min_investment) {
    message.error(`최소 ${template.min_investment} USDT 이상 입력하세요`);
    return;
  }

  // 2. 잔고 체크 (API)
  const checkResult = await multibotAPI.checkBalance(amount);
  if (!checkResult.available) {
    message.error(checkResult.message);
    return;
  }

  // 3. 봇 시작
  try {
    await onStart(template.id, amount);
    message.success('봇이 시작되었습니다!');
    onClose();
  } catch (err) {
    message.error(err.response?.data?.detail || '봇 시작 실패');
  }
};
```

---

## Phase 4: 스타일링 및 반응형

### 4.1 다크 테마 색상 팔레트

```css
:root {
  /* 배경 */
  --bg-primary: #0d0d0d;
  --bg-secondary: #1a1a1a;
  --bg-card: #1e1e1e;
  --bg-card-hover: #252525;

  /* 텍스트 */
  --text-primary: #ffffff;
  --text-secondary: #a0a0a0;
  --text-muted: #6b6b6b;

  /* 액센트 */
  --accent-green: #00d26a;
  --accent-red: #ff4757;
  --accent-blue: #3b82f6;
  --accent-cyan: #00d4ff;

  /* 태그 */
  --tag-long: rgba(0, 210, 106, 0.2);
  --tag-short: rgba(255, 71, 87, 0.2);
  --tag-leverage: rgba(0, 212, 255, 0.2);

  /* 보더 */
  --border-color: #2a2a2a;
  --border-radius: 12px;
}
```

### 4.2 BotCard.css

```css
.bot-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: 20px;
  transition: all 0.2s ease;
}

.bot-card:hover {
  background: var(--bg-card-hover);
  transform: translateY(-2px);
}

.bot-card .symbol {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.bot-card .roi-value {
  font-size: 28px;
  font-weight: 700;
}

.bot-card .roi-value.positive {
  color: var(--accent-green);
}

.bot-card .roi-value.negative {
  color: var(--accent-red);
}

.bot-card .use-button {
  background: transparent;
  border: 1px solid var(--text-secondary);
  color: var(--text-primary);
  border-radius: 20px;
  padding: 6px 20px;
  font-weight: 600;
}

.bot-card .use-button:hover {
  background: var(--text-primary);
  color: var(--bg-primary);
}
```

### 4.3 반응형 그리드

```css
.bot-card-grid {
  display: grid;
  gap: 16px;
}

/* Desktop: 2열 */
@media (min-width: 768px) {
  .bot-card-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* Mobile: 1열 */
@media (max-width: 767px) {
  .bot-card-grid {
    grid-template-columns: 1fr;
  }
}
```

---

## Phase 5: 테스트 및 배포

### 5.1 테스트 케이스

| 카테고리 | 테스트 | 예상 결과 |
|---------|--------|----------|
| 목록 로딩 | 페이지 진입 | 템플릿 카드 표시 |
| 정렬 | ROI 정렬 선택 | 높은 ROI 순 정렬 |
| 필터 | BTCUSDT 필터 | BTC 봇만 표시 |
| 상세 모달 | Use 클릭 | 모달 오픈, 상세 정보 표시 |
| 금액 입력 | 퍼센트 버튼 | 금액 자동 계산 |
| 잔고 검증 | 잔고 초과 입력 | 에러 메시지 |
| 봇 시작 | Use 버튼 클릭 | 봇 생성, 성공 메시지 |
| 반응형 | 모바일 뷰 | 1열 레이아웃 |

### 5.2 배포 체크리스트

```bash
# 1. 로컬 테스트
cd frontend
npm run build

# 2. 구문 검사
npx eslint src/pages/Trading.jsx
npx eslint src/components/trading/

# 3. 배포
git add .
git commit -m "feat(trading): Redesign Trading page with Bitget-style bot marketplace"
git push hetzner main

# 4. 검증
curl https://deepsignal.shop/trading
```

---

## 작업 체크리스트

### Phase 1: 컴포넌트 생성 (Day 1)

- [ ] **1.1** `components/trading/` 폴더 생성
- [ ] **1.2** `BotCard.jsx` 컴포넌트 생성
- [ ] **1.3** `BotCard.css` 스타일 (다크모드)
- [ ] **1.4** `BotCardList.jsx` 컴포넌트 생성
- [ ] **1.5** `BotFilters.jsx` 컴포넌트 생성
- [ ] **1.6** `ActiveBotsBanner.jsx` 컴포넌트 생성
- [ ] **1.7** `useBotMarketplace.js` 훅 생성
- [ ] **1.8** `index.js` 배럴 export

### Phase 2: Trading 페이지 교체 (Day 1-2)

- [ ] **2.1** `BotMarketplace.jsx` 메인 컨테이너 생성
- [ ] **2.2** `BotMarketplace.css` 스타일
- [ ] **2.3** `Trading.jsx` 완전 교체
- [ ] **2.4** 기존 import 정리 (사용 안하는 컴포넌트 제거)

### Phase 3: 상세 모달 구현 (Day 2)

- [ ] **3.1** `BotDetailModal.jsx` 컴포넌트 생성
- [ ] **3.2** `BotDetailModal.css` 스타일
- [ ] **3.3** 금액 입력 UI (InputNumber + 퍼센트 버튼)
- [ ] **3.4** 잔고 검증 로직 연동
- [ ] **3.5** 봇 시작 API 연동

### Phase 4: 스타일링 및 반응형 (Day 2-3)

- [ ] **4.1** 다크 테마 CSS 변수 정의
- [ ] **4.2** 반응형 그리드 구현
- [ ] **4.3** 모바일 최적화
- [ ] **4.4** 로딩/에러 상태 UI
- [ ] **4.5** 애니메이션/트랜지션

### Phase 5: 테스트 및 배포 (Day 3)

- [ ] **5.1** 로컬 빌드 테스트
- [ ] **5.2** 기능 테스트 (목록, 상세, 시작)
- [ ] **5.3** 반응형 테스트
- [ ] **5.4** Production 배포
- [ ] **5.5** 문서 업데이트

---

## 파일별 상세 구현 가이드

### 1. components/trading/BotCard.jsx

```jsx
/**
 * BotCard - Bitget 스타일 봇 템플릿 카드
 *
 * 다크 테마 + 미니 차트 + Use 버튼
 */
import React from 'react';
import { Button, Tag } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import './styles/BotCard.css';

// 코인 로고 URL
const getCoinLogo = (symbol) => {
  const coin = symbol.replace('USDT', '').toLowerCase();
  return `https://assets.coincap.io/assets/icons/${coin}@2x.png`;
};

export default function BotCard({ template, onUse, loading }) {
  const {
    symbol,
    direction,
    leverage,
    backtest_roi_30d,
    min_investment,
    active_users,
    is_featured,
  } = template;

  const isLong = direction === 'long';
  const roi = backtest_roi_30d || 0;
  const isPositive = roi >= 0;

  return (
    <div className={`bot-card ${is_featured ? 'featured' : ''}`}>
      {/* 헤더: 심볼 + 태그 + Use 버튼 */}
      <div className="card-header">
        <div className="symbol-section">
          <img
            src={getCoinLogo(symbol)}
            alt={symbol}
            className="coin-logo"
            onError={(e) => e.target.style.display = 'none'}
          />
          <span className="symbol">{symbol}</span>
        </div>
        <div className="header-right">
          <Tag className={`direction-tag ${isLong ? 'long' : 'short'}`}>
            {isLong ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
            {isLong ? 'Long' : 'Short'}
          </Tag>
          <Tag className="leverage-tag">{leverage}x</Tag>
          <Button
            className="use-button"
            onClick={() => onUse(template)}
            loading={loading}
          >
            Use
          </Button>
        </div>
      </div>

      {/* 본문: 수익률 + 미니차트 */}
      <div className="card-body">
        <div className="roi-section">
          <span className="roi-label">30-day APY</span>
          <span className={`roi-value ${isPositive ? 'positive' : 'negative'}`}>
            {isPositive ? '+' : ''}{roi.toFixed(2)}%
          </span>
        </div>
        <div className="mini-chart">
          {/* 미니 라인 차트 - SVG 또는 간단한 스파크라인 */}
          <svg width="60" height="30" viewBox="0 0 60 30">
            <polyline
              points="0,25 10,20 20,22 30,15 40,18 50,10 60,5"
              fill="none"
              stroke={isPositive ? '#00d26a' : '#ff4757'}
              strokeWidth="2"
            />
          </svg>
        </div>
      </div>

      {/* 푸터: 상세 정보 */}
      <div className="card-footer">
        <div className="info-row">
          <span className="info-label">Min investment</span>
          <span className="info-value">{min_investment} USDT</span>
        </div>
        <div className="info-row">
          <span className="info-label">Recommended duration</span>
          <span className="info-value">7-30 days</span>
        </div>
        <div className="info-row">
          <span className="info-label">Users</span>
          <span className="info-value">{(active_users || 0).toLocaleString()}</span>
        </div>
      </div>

      {/* HOT 배지 */}
      {is_featured && (
        <div className="hot-badge">HOT</div>
      )}
    </div>
  );
}
```

### 2. components/trading/BotDetailModal.jsx

```jsx
/**
 * BotDetailModal - 봇 상세 + 금액 입력 모달
 */
import React, { useState, useEffect } from 'react';
import { Modal, Button, InputNumber, Tag, message, Spin } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import multibotAPI from '../../api/multibot';
import './styles/BotDetailModal.css';

export default function BotDetailModal({
  template,
  open,
  onClose,
  onStart,
  availableBalance,
}) {
  const [amount, setAmount] = useState(0);
  const [loading, setLoading] = useState(false);

  // 모달 열릴 때 최소 금액으로 초기화
  useEffect(() => {
    if (open && template) {
      setAmount(template.min_investment || 50);
    }
  }, [open, template]);

  if (!template) return null;

  const {
    symbol,
    direction,
    leverage,
    strategy_type,
    description,
    backtest_roi_30d,
    backtest_max_drawdown,
    active_users,
    total_funds_used,
    stop_loss_percent,
    take_profit_percent,
    min_investment,
  } = template;

  const handlePercentClick = (percent) => {
    setAmount(Math.floor(availableBalance * percent));
  };

  const handleStart = async () => {
    if (amount < min_investment) {
      message.error(`최소 ${min_investment} USDT 이상 입력하세요`);
      return;
    }

    if (amount > availableBalance) {
      message.error('잔고가 부족합니다');
      return;
    }

    setLoading(true);
    try {
      await onStart(template.id, amount);
      message.success('봇이 시작되었습니다!');
      onClose();
    } catch (err) {
      message.error(err.response?.data?.detail || '봇 시작 실패');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width={480}
      className="bot-detail-modal"
      closable={false}
    >
      {/* 헤더 */}
      <div className="modal-header">
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={onClose}
          className="back-button"
        />
        <h2 className="modal-title">{symbol}</h2>
        <div className="modal-tags">
          <Tag>{strategy_type}</Tag>
          <Tag className={direction === 'long' ? 'long' : 'short'}>
            {direction === 'long' ? 'Long' : 'Short'}
          </Tag>
          <Tag>{leverage}x</Tag>
        </div>
      </div>

      {/* 통계 그리드 */}
      <div className="stats-grid">
        <div className="stat-item">
          <span className="stat-label">30D backtested ROI</span>
          <span className={`stat-value ${backtest_roi_30d >= 0 ? 'positive' : 'negative'}`}>
            {backtest_roi_30d >= 0 ? '+' : ''}{backtest_roi_30d?.toFixed(2)}%
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Funds in use(USDT)</span>
          <span className="stat-value">
            {(total_funds_used || 0).toLocaleString()}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Users</span>
          <span className="stat-value">
            {(active_users || 0).toLocaleString()}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">30D max drawdown</span>
          <span className="stat-value negative">
            {backtest_max_drawdown?.toFixed(2)}%
          </span>
        </div>
      </div>

      {/* Bot details */}
      <div className="bot-details">
        <h3>Bot details</h3>
        <p>{description || '이 봇은 시장 상황에 따라 자동으로 매매를 실행합니다.'}</p>
      </div>

      {/* Bot parameters */}
      <div className="bot-parameters">
        <h3>Bot parameters</h3>
        <div className="param-grid">
          <div className="param-item">
            <span className="param-label">손절가</span>
            <span className="param-value negative">-{stop_loss_percent}%</span>
          </div>
          <div className="param-item">
            <span className="param-label">익절가</span>
            <span className="param-value positive">+{take_profit_percent}%</span>
          </div>
        </div>
      </div>

      {/* 금액 입력 */}
      <div className="amount-section">
        <h3>투자 금액</h3>
        <InputNumber
          value={amount}
          onChange={setAmount}
          min={min_investment}
          max={availableBalance}
          className="amount-input"
          addonAfter="USDT"
        />
        <div className="percent-buttons">
          <Button onClick={() => handlePercentClick(0.25)}>25%</Button>
          <Button onClick={() => handlePercentClick(0.50)}>50%</Button>
          <Button onClick={() => handlePercentClick(0.75)}>75%</Button>
          <Button onClick={() => handlePercentClick(1.00)}>MAX</Button>
        </div>
        <div className="balance-info">
          <span>Min: ${min_investment} USDT</span>
          <span>Available: ${availableBalance?.toFixed(2)} USDT</span>
        </div>
      </div>

      {/* 시작 버튼 */}
      <Button
        type="primary"
        block
        size="large"
        className="start-button"
        onClick={handleStart}
        loading={loading}
      >
        Use
      </Button>
    </Modal>
  );
}
```

### 3. hooks/useBotMarketplace.js

```javascript
/**
 * useBotMarketplace - 봇 마켓플레이스 상태 관리 훅
 */
import { useState, useCallback, useMemo } from 'react';
import multibotAPI from '../api/multibot';

export function useBotMarketplace() {
  // 데이터 상태
  const [templates, setTemplates] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);

  // UI 상태
  const [sortBy, setSortBy] = useState('roi'); // roi | users | new
  const [filterSymbol, setFilterSymbol] = useState(null);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);

  // 템플릿 목록 로드
  const loadTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const response = await multibotAPI.getTemplates();
      setTemplates(response.templates || response || []);
    } catch (err) {
      console.error('템플릿 로드 실패:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // 잔고 요약 로드
  const loadSummary = useCallback(async () => {
    try {
      const response = await multibotAPI.getSummary();
      setSummary(response);
    } catch (err) {
      console.error('요약 로드 실패:', err);
    }
  }, []);

  // 봇 시작
  const startBot = useCallback(async (templateId, amount) => {
    const response = await multibotAPI.startBot({
      template_id: templateId,
      amount: amount,
    });
    // 성공 후 요약 새로고침
    await loadSummary();
    return response;
  }, [loadSummary]);

  // 정렬된 템플릿
  const sortedTemplates = useMemo(() => {
    let result = [...templates];

    // 필터 적용
    if (filterSymbol) {
      result = result.filter(t => t.symbol === filterSymbol);
    }

    // 정렬 적용
    switch (sortBy) {
      case 'roi':
        result.sort((a, b) => (b.backtest_roi_30d || 0) - (a.backtest_roi_30d || 0));
        break;
      case 'users':
        result.sort((a, b) => (b.active_users || 0) - (a.active_users || 0));
        break;
      case 'new':
        result.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        break;
    }

    // featured 우선
    result.sort((a, b) => (b.is_featured ? 1 : 0) - (a.is_featured ? 1 : 0));

    return result;
  }, [templates, sortBy, filterSymbol]);

  // 사용 가능한 심볼 목록
  const availableSymbols = useMemo(() => {
    return [...new Set(templates.map(t => t.symbol))];
  }, [templates]);

  // 템플릿 선택 (모달 열기)
  const selectTemplate = useCallback((template) => {
    setSelectedTemplate(template);
    setDetailModalOpen(true);
  }, []);

  // 모달 닫기
  const closeDetailModal = useCallback(() => {
    setDetailModalOpen(false);
    setSelectedTemplate(null);
  }, []);

  return {
    // 데이터
    templates: sortedTemplates,
    summary,
    loading,
    availableSymbols,

    // UI 상태
    sortBy,
    setSortBy,
    filterSymbol,
    setFilterSymbol,
    selectedTemplate,
    detailModalOpen,

    // 액션
    loadTemplates,
    loadSummary,
    startBot,
    selectTemplate,
    closeDetailModal,
  };
}

export default useBotMarketplace;
```

---

## 협업 가이드

### AI 작업자별 분배

```
AI-1: Phase 1.1-1.4 (컴포넌트 기초)
AI-2: Phase 1.5-1.8 + Phase 2 (컴포넌트 완성 + 페이지)
AI-3: Phase 3 (상세 모달)
AI-4: Phase 4-5 (스타일링 + 배포)
```

### 작업 시작 전 필수 확인

1. `git pull origin main`
2. 이 문서에서 자신의 작업 단계 확인
3. 진행 상황 파일 업데이트 (TRADING_REDESIGN_PROGRESS.md)

### 커밋 컨벤션

```
feat(trading): Add BotCard component          # Phase 1.2
feat(trading): Add BotDetailModal             # Phase 3.1
style(trading): Apply dark theme              # Phase 4.1
refactor(trading): Replace Trading.jsx        # Phase 2.3
```

---

## 참조 문서

- [멀티봇 구현 계획서](./MULTI_BOT_IMPLEMENTATION_PLAN.md)
- [프로젝트 가이드](../CLAUDE.md)
- [스킬 파일](../.claude/skills/trading-redesign.md)

---

**문서 끝**
