# 거래소 API 등록 시스템 수정 계획서

> **최종 업데이트**: 2026-01-11
> **작업 목표**: 5개 거래소 지원 + 1계정당 1거래소 운용 시스템 구현

---

## 현재 상황

### 문제점
1. **Frontend가 Bitget만 고정**: Backend는 5개 거래소를 지원하지만 Frontend UI가 Bitget만 표시
2. **거래소 선택 UI 없음**: Settings 페이지에 거래소 선택 드롭다운이 없음
3. **등록된 키 조회 오류**: 새로고침 시 등록된 거래소 정보가 표시되지 않음
4. **Passphrase 필수/선택 구분 없음**: 거래소별로 Passphrase 필요 여부가 다름

### 지원 거래소 (5개)
| 거래소 | REST API | WebSocket | Passphrase |
|--------|----------|-----------|------------|
| Bitget | ✅ | ✅ | **필수** |
| Binance | ✅ | ✅ | 불필요 |
| OKX | ✅ | ✅ | **필수** |
| Bybit | ✅ | ✅ | 불필요 |
| Gate.io | ✅ | ✅ | 불필요 |

### 핵심 정책
- **1계정 = 1거래소**: 사용자당 하나의 거래소만 활성화
- **거래소 변경 가능**: 다른 거래소로 변경 시 기존 키 덮어쓰기
- **동시 운용 불가**: 여러 거래소 동시 사용 불가

---

## 작업 체크리스트

### Phase 1: Backend 수정 ✅ 완료

#### 1.1 get_my_keys API 수정 ✅
- [x] **파일**: `backend/src/api/account.py`
- [x] **작업**: `get_my_keys` 응답에 `exchange` 필드 추가
- [x] **검증**: 사용자의 User.exchange 정보를 함께 반환

```python
# 수정된 응답 형식
{
    "api_key": "...",
    "secret_key": "...",
    "passphrase": "...",
    "exchange": "bitget",  # 추가됨
    "warning": "..."
}
```

**완료 확인**: ✅ 2026-01-11 완료

---

### Phase 2: Frontend API 수정 ✅ 완료

#### 2.1 account.js 수정 ✅
- [x] **파일**: `frontend/src/api/account.js`
- [x] **작업**: `saveApiKeys` 함수에 `exchange` 파라미터 추가

```javascript
// 수정된 함수 시그니처
saveApiKeys: async (apiKey, secretKey, passphrase = '', exchange = 'bitget')
```

**완료 확인**: ✅ 2026-01-11 완료

---

### Phase 3: Settings.jsx UI 수정 ✅ 완료

#### 3.1 거래소 선택 상태 추가 ✅
- [x] **파일**: `frontend/src/pages/Settings.jsx`
- [x] **작업**:
  - `selectedExchange` 상태 추가
  - 지원 거래소 목록 상수 정의 (SUPPORTED_EXCHANGES)

**완료 확인**: ✅ 2026-01-11

#### 3.2 거래소 선택 드롭다운 UI 추가 ✅
- [x] **파일**: `frontend/src/pages/Settings.jsx`
- [x] **작업**: API Key 입력 폼 상단에 거래소 선택 드롭다운 추가
- [x] **추가 기능**: 거래소 변경 경고 메시지 표시

**완료 확인**: ✅ 2026-01-11

#### 3.3 Passphrase 필드 동적 처리 ✅
- [x] **파일**: `frontend/src/pages/Settings.jsx`
- [x] **작업**:
  - 선택된 거래소에 따라 Passphrase 필수/선택 표시
  - Bitget, OKX: "* (필수)" 표시 (빨간색)
  - 나머지: "(선택사항)" 표시 (회색)
  - placeholder도 동적으로 변경

**완료 확인**: ✅ 2026-01-11

#### 3.4 handleSaveKeys 함수 수정 ✅
- [x] **파일**: `frontend/src/pages/Settings.jsx`
- [x] **작업**:
  - `accountAPI.saveApiKeys` 호출 시 `selectedExchange` 전달
  - Passphrase 필수 거래소 검증 추가
  - 성공 메시지에 거래소 이름 포함

**완료 확인**: ✅ 2026-01-11

#### 3.5 checkSavedKeys 함수 수정 ✅
- [x] **파일**: `frontend/src/pages/Settings.jsx`
- [x] **작업**:
  - API 응답에서 `exchange` 정보 추출
  - `savedKeyInfo`에 거래소 정보 (value, label, logo) 포함
  - `setSelectedExchange`로 저장된 거래소 선택 상태 동기화

**완료 확인**: ✅ 2026-01-11

#### 3.6 등록된 키 정보 UI 수정 ✅
- [x] **파일**: `frontend/src/pages/Settings.jsx`
- [x] **작업**:
  - 현재 등록된 거래소 이름 및 로고 명시
  - 거래소 정보를 별도 행으로 표시

**완료 확인**: ✅ 2026-01-11

---

### Phase 4: 도움말 탭 업데이트 ✅ 완료

#### 4.1 FAQ 업데이트 ✅
- [x] **파일**: `frontend/src/pages/Settings.jsx`
- [x] **작업**:
  - "여러 거래소를 지원하나요?" 답변 수정
  - 5개 거래소 지원 + 1계정=1거래소 정책 안내
  - Passphrase 관련 FAQ 추가

**완료 확인**: ✅ 2026-01-11

---

### Phase 5: 연결 테스트 수정 ✅ 완료

#### 5.1 연결 테스트 거래소별 처리 ✅
- [x] **파일**: `frontend/src/pages/Settings.jsx`
- [x] **작업**:
  - `handleTestConnection` 함수를 범용 `accountAPI.getBalance()` 사용으로 변경
  - 더 이상 bitgetAPI 직접 호출하지 않음
  - 연결된 거래소 이름과 잔고 표시

**완료 확인**: ✅ 2026-01-11

---

### Phase 6: 테스트 및 검증 ✅ 완료

#### 6.1 빌드 테스트 ✅
- [x] `npm run build` 성공 확인
- [x] Python 구문 검사 통과 확인

**완료 확인**: ✅ 2026-01-11

---

## 수정 대상 파일 목록

| 파일 | Phase | 상태 |
|------|-------|------|
| `backend/src/api/account.py` | 1 | ✅ 완료 |
| `frontend/src/api/account.js` | 2 | ✅ 완료 |
| `frontend/src/pages/Settings.jsx` | 3, 4, 5 | ⏳ 예정 |

---

## 세부 코드 변경 사항

### Settings.jsx 변경 위치 가이드

```
Settings.jsx 구조:
├── 상태 정의 (라인 38-72)
│   └── [추가] selectedExchange 상태
├── checkSavedKeys (라인 234-253)
│   └── [수정] exchange 정보 처리
├── handleSaveKeys (라인 255-290)
│   └── [수정] exchange 파라미터 전달
├── API Keys Tab (라인 574-842)
│   ├── 헤더 (라인 588-616)
│   │   └── [수정] 설명 텍스트
│   ├── 저장된 키 정보 (라인 618-652)
│   │   └── [수정] 거래소명 표시
│   ├── 입력 폼 (라인 654-749)
│   │   ├── [추가] 거래소 선택 드롭다운
│   │   └── [수정] Passphrase 라벨
│   └── 버튼 (라인 750-839)
└── Info Tab (라인 1459-1549)
    └── [수정] FAQ 답변
```

---

## 작업 순서 (권장)

1. **Phase 3.1**: 상태 및 상수 추가 → 바로 완료 체크
2. **Phase 3.2**: 드롭다운 UI → 바로 완료 체크
3. **Phase 3.3**: Passphrase 동적 처리 → 바로 완료 체크
4. **Phase 3.4**: handleSaveKeys 수정 → 바로 완료 체크
5. **Phase 3.5**: checkSavedKeys 수정 → 바로 완료 체크
6. **Phase 3.6**: 등록된 키 UI 수정 → 바로 완료 체크
7. **Phase 4**: 도움말 탭 → 바로 완료 체크
8. **Phase 5**: 연결 테스트 → 바로 완료 체크
9. **Phase 6**: 테스트 및 검증

---

## 다른 AI 작업자를 위한 지침

### 시작 전 확인사항
1. 이 문서를 먼저 읽고 현재 완료된 Phase 확인
2. `git status`로 변경된 파일 확인
3. 미완료 Phase부터 순차적으로 작업

### 작업 중 지침
1. 각 세부 작업 완료 시 즉시 이 문서의 체크박스 업데이트
2. 날짜도 함께 기록 (예: ✅ 2026-01-11)
3. 토큰 소진 전 가능하면 commit 권장

### 완료 후 확인
1. 빌드 테스트: `cd frontend && npm run build`
2. Python 구문 검사: `python -m py_compile backend/src/api/account.py`

---

## Git Commit 메시지 템플릿

```
feat: 거래소 API 등록 시스템 개선 (Phase X 완료)

- [Phase X.Y 내용]
- [Phase X.Z 내용]

지원 거래소: Bitget, Binance, OKX, Bybit, Gate.io
```

---

**문서 버전**: v1.0
**작성자**: Claude Code
**다음 작업**: Phase 3.1부터 시작
