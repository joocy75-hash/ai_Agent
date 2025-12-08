# 📱 모바일 대시보드 페이지 디자인 스펙 (Mobile Dashboard Design Specification)

> **Deep Signal 트레이딩 대시보드 모바일 버전 디자인 가이드**
>
> 작성일: 2025-12-07
> 기준 화면: `window.innerWidth < 768px`

---

## 📐 레이아웃 기본 설정

### 전역 컨테이너 (MainLayout)

```jsx
// Content 영역 패딩
padding: isMobile ? 8 : 28     // 모바일: 8px, 데스크톱: 28px
```

### 페이지 컨테이너 (Dashboard.jsx)

```jsx
<div style={{ 
  maxWidth: 1400,              // 최대 너비
  margin: '0 auto',            // 중앙 정렬
  padding: isMobile ? 0 : undefined  // 모바일: 0px (MainLayout 패딩만 사용)
}}>
```

---

## 📊 Row/Col 그리드 시스템

### 통계 카드 Row

```jsx
<Row gutter={isMobile ? [8, 8] : [16, 16]}>
  // 모바일: 8px 간격
  // 데스크톱: 16px 간격
```

### 통계 카드 Col

```jsx
<Col xs={12} sm={12} md={6}>
  // 모바일: 화면의 50% (2열 레이아웃)
  // 태블릿: 화면의 50% (2열 레이아웃)
  // 데스크톱: 화면의 25% (4열 레이아웃)
```

### Row Margin

```jsx
style={{ marginBottom: isMobile ? 16 : 24 }}
  // 모바일: 16px
  // 데스크톱: 24px
```

---

## 🎴 StatCard (통계 카드) 사이즈

### 카드 컨테이너

| 속성 | 모바일 | 데스크톱 |
|------|--------|----------|
| `borderRadius` | 12px | 16px |
| `padding` | 14px 16px | 24px |
| `minHeight` | auto | undefined (기본값) |

### 타이틀 (라벨)

| 속성 | 모바일 | 데스크톱 |
|------|--------|----------|
| `fontSize` | 11px | 13px |
| `marginBottom` | 4px | 8px |
| `fontWeight` | 500 | 500 |
| `color` | #86868b | #86868b |

### 값 (Value)

| 속성 | 모바일 | 데스크톱 |
|------|--------|----------|
| `fontSize` | 20px | 28px |
| `fontWeight` | 600 | 600 |
| `color` | #1d1d1f | #1d1d1f |

### 접미사 (Suffix)

| 속성 | 모바일 | 데스크톱 |
|------|--------|----------|
| `fontSize` | 12px | 16px |
| `color` | #86868b | #86868b |

### 트렌드 표시

| 속성 | 모바일 | 데스크톱 |
|------|--------|----------|
| 아이콘 `fontSize` | 10px | 12px |
| 값 `fontSize` | 11px | 13px |
| `marginTop` | 4px | 8px |

### 아이콘 박스

| 속성 | 모바일 | 데스크톱 |
|------|--------|----------|
| `width` | 32px | 48px |
| `height` | 32px | 48px |
| `borderRadius` | 8px | 12px |
| `fontSize` | 14px | 20px |
| `background` | #f5f5f7 | #f5f5f7 |
| `color` | #86868b | #86868b |

---

## 📈 PositionCard (포지션 카드) 사이즈

### 카드 컨테이너

| 속성 | 모바일 | 데스크톱 |
|------|--------|----------|
| `borderRadius` | 12px | 16px |
| `padding` | 14px 16px | 24px |

### 타이틀

| 속성 | 모바일 | 데스크톱 |
|------|--------|----------|
| `fontSize` | 11px | 13px |
| `marginBottom` | 4px | 8px |

### Long/Short 컨테이너

| 속성 | 모바일 | 데스크톱 |
|------|--------|----------|
| `gap` | 6px | 12px |
| `marginTop` | 2px | 4px |

### Long/Short 아이템

| 속성 | 모바일 | 데스크톱 |
|------|--------|----------|
| 아이콘-텍스트 `gap` | 2px | 4px |
| 아이콘 `fontSize` | 12px | 16px |
| 라벨 `fontSize` | 11px | 14px |
| 숫자 `fontSize` | 16px | 22px |
| 숫자 `marginLeft` | 1px | 2px |

### 구분선 (Divider)

| 속성 | 모바일 | 데스크톱 |
|------|--------|----------|
| `fontSize` | 16px | 20px |
| `color` | #d2d2d7 | #d2d2d7 |

---

## 🏆 ProfitLossCard (최대 이익/손실 카드)

### 카드 컨테이너

| 속성 | 모바일 | 데스크톱 |
|------|--------|----------|
| `borderRadius` | 12px | 16px |
| `padding` | 14px 16px | 24px |

### 타이틀

| 속성 | 모바일 | 데스크톱 |
|------|--------|----------|
| `fontSize` | 11px | 13px |
| `marginBottom` | 4px | 8px |

### 이익/손실 값

| 속성 | 모바일 | 데스크톱 |
|------|--------|----------|
| 값 `fontSize` | 16px | 22px |
| % 기호 `fontSize` | 11px | 14px |
| `gap` | 1px | 2px |
| 컨테이너 `gap` | 6px | 12px |

---

## 💵 BalanceCard (잔고 카드) 사이즈

### 카드 컨테이너

| 속성 | 모바일 | 데스크톱 |
|------|--------|----------|
| `borderRadius` | 12px | 16px |
| `padding` | 16px | 24px |
| `marginBottom` | 12px | 20px |

### 그리드 레이아웃

```jsx
gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(auto-fit, minmax(150px, 1fr))'
gap: isMobile ? 8 : 12
// 모바일: 2열 고정
// 데스크톱: 자동 fit (최소 150px)
```

### StatItem (개별 잔고 아이템)

| 속성 | 모바일 | 데스크톱 |
|------|--------|----------|
| `borderRadius` | 10px | 12px |
| `padding` | 12px | 16px |
| 라벨 `fontSize` | 11px | 12px |
| 값 `fontSize` | 15px | 18px |
| 단위 `fontSize` | 10px | 12px |
| `marginBottom` (라벨) | 2px | 4px |

---

## 📅 PeriodProfitCard (기간별 수익 카드)

### 카드 컨테이너 (변동 없음)

| 속성 | 값 |
|------|-----|
| `borderRadius` | 12px |
| `padding` | 20px |

### 타이틀

| 속성 | 값 |
|------|-----|
| `fontSize` | 12px |
| `marginBottom` | 12px |
| `textTransform` | uppercase |

### 수익률 값

| 속성 | 값 |
|------|-----|
| `fontSize` | 24px |
| 아이콘 `fontSize` | 14px |
| % 기호 `fontSize` | 14px |

### PnL 서브값

| 속성 | 값 |
|------|-----|
| `fontSize` | 12px |
| `marginTop` | 6px |

---

## 🎨 색상 팔레트

### 기본 색상

| 용도 | 색상 코드 |
|------|-----------|
| 텍스트 (기본) | #1d1d1f |
| 텍스트 (보조) | #86868b |
| 배경 (카드) | #ffffff |
| 배경 (페이지) | #f5f5f7 |
| 테두리 | #f5f5f7 |
| 구분선 | #d2d2d7 |

### 시맨틱 색상

| 용도 | 색상 코드 |
|------|-----------|
| 상승/Long/성공 | #34c759 |
| 하락/Short/실패 | #ff3b30 |
| 기본/정보 | #0071e3 |
| 경고 | #ff9500 |

---

## 📱 Ant Design 모바일 오버라이드

### 버튼/메뉴 아이템

```css
min-height: 44px !important;
padding: 12px 16px !important;
```

### 카드 헤드

```css
.ant-card-head {
  padding: 12px 16px !important;
}
.ant-card-head-title {
  font-size: 15px !important;
}
```

### 카드 바디

```css
.ant-card-body {
  padding: 12px 16px !important;
}
```

### Statistic 컴포넌트

```css
.ant-statistic-title {
  font-size: 11px !important;
}
.ant-statistic-content {
  font-size: 18px !important;
}
```

### 폼 입력 필드

```css
.ant-input, .ant-select-selector, .ant-picker {
  height: 44px !important;
  font-size: 16px !important;  /* iOS 확대 방지 */
}
```

### 태그

```css
.ant-tag {
  font-size: 11px !important;
  padding: 2px 6px !important;
}
```

### 테이블

```css
.ant-table-thead>tr>th,
.ant-table-tbody>tr>td {
  padding: 10px 8px !important;
  font-size: 13px !important;
}
```

---

## 🔄 반응형 체크포인트

### isMobile 상태 감지

```jsx
const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

useEffect(() => {
  const handleResize = () => setIsMobile(window.innerWidth < 768);
  window.addEventListener('resize', handleResize);
  return () => window.removeEventListener('resize', handleResize);
}, []);
```

### 브레이크포인트

| 이름 | 조건 |
|------|------|
| 모바일 | `< 768px` |
| 태블릿 | `768px ~ 1024px` |
| 데스크톱 | `> 1024px` |

---

## 📋 적용 페이지 체크리스트

모든 페이지에 아래 패턴을 동일하게 적용:

- [x] Dashboard.jsx
- [x] Trading.jsx
- [x] Settings.jsx
- [x] TradingHistory.jsx
- [x] Notifications.jsx
- [x] BacktestingPage.jsx
- [x] BacktestHistoryPage.jsx
- [x] Strategy.jsx

### 표준 페이지 구조

```jsx
export default function PageName() {
  // 1. 모바일 감지
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  
  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    // 2. 표준 컨테이너
    <div style={{ maxWidth: 1400, margin: '0 auto', padding: isMobile ? 0 : 24 }}>
      
      {/* 3. 헤더 */}
      <div style={{ marginBottom: isMobile ? 12 : 24 }}>
        <Title level={isMobile ? 3 : 2}>
          <Icon style={{ marginRight: 8 }} />
          페이지 제목
        </Title>
        {!isMobile && <Text>설명 텍스트</Text>}
      </div>
      
      {/* 4. 메인 콘텐츠 */}
      <Row gutter={isMobile ? [8, 8] : [16, 16]}>
        ...
      </Row>
    </div>
  );
}
```

---

## 🎯 핵심 원칙

1. **패딩 최소화**: 모바일에서 화면 전체 활용
2. **2열 그리드**: 통계 카드는 모바일에서 50%:50%
3. **폰트 축소**: 모바일에서 약 20~30% 축소
4. **터치 친화적**: 최소 44px 터치 영역
5. **iOS 확대 방지**: 입력 필드 font-size: 16px
6. **설명 숨김**: 모바일에서 부가 설명 텍스트 숨김
7. **아이콘 축소**: 모바일에서 아이콘 약 30% 축소
