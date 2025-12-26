# 📚 문서 가이드 (Documentation Guide)

> **새로운 작업자는 이 파일을 가장 먼저 읽으세요!**

---

## 🗂️ 문서 읽는 순서

### Step 1: 필수 문서 (작업 시작 전 반드시 읽기)

```
📖 1. CLAUDE.md (프로젝트 루트)
   ↓  AI 개발 가이드, 절대 금지 사항, 배포 방법
   ↓
📖 2. docs/CODEBASE_OVERVIEW.md
   ↓  전체 코드베이스 구조, 핵심 파일 맵, 데이터 흐름
   ↓
📖 3. docs/BACKEND_ARCHITECTURE.md
      백엔드 상세 아키텍처, 사용자 격리 원리
```

### Step 2: 작업별 추가 문서

| 작업 유형 | 추가로 읽을 문서 |
|----------|----------------|
| **백엔드 API 개발** | `backend/README.md` |
| **봇 로직 수정** | `CLAUDE.md` (bot_runner 섹션) |
| **배포** | `docs/DEPLOYMENT_GUIDE.md` |
| **환경 설정** | `backend/ENV_SETUP.md` |
| **ML 모델** | `docs/ML_TRAINING_SYSTEM.md` |

---

## 📁 전체 문서 목록

### 프로젝트 루트

| 파일 | 중요도 | 설명 |
|------|--------|------|
| `CLAUDE.md` | ⭐⭐⭐ | **AI 개발 필독 가이드** - 절대 금지 사항, 배포 방법, 핵심 데이터 구조 |
| `README.md` | ⭐⭐ | 프로젝트 개요, 설치 방법 |

### docs/ 폴더

| 파일 | 중요도 | 설명 | 대상 |
|------|--------|------|------|
| `CODEBASE_OVERVIEW.md` | ⭐⭐⭐ | **전체 코드베이스 개요** - 디렉토리 구조, 핵심 파일, 데이터 흐름 | 모든 작업자 |
| `BACKEND_ARCHITECTURE.md` | ⭐⭐⭐ | 백엔드 아키텍처, DB 구조, API 목록, 사용자 격리 | 백엔드 작업자 |
| `DEPLOYMENT_GUIDE.md` | ⭐⭐ | 서버 배포 가이드 | 배포 담당자 |
| `ML_TRAINING_SYSTEM.md` | ⭐⭐ | ML 학습 시스템 가이드 | ML 작업자 |

### backend/ 폴더

| 파일 | 중요도 | 설명 |
|------|--------|------|
| `README.md` | ⭐⭐ | 백엔드 개요, 로컬 실행 방법 |
| `ENV_SETUP.md` | ⭐ | 환경 변수 설정 |

### 계획 문서 (참고용)

> 아래 문서들은 진행 중인 계획서입니다. 구현 완료 후 삭제됩니다.

| 파일 | 설명 |
|------|------|
| `AI_RATE_LIMIT_FIX_PLAN.md` | AI API Rate Limit 해결 계획 |
| `ML_MODEL_INTEGRATION_PLAN.md` | DeepSeek + LightGBM 하이브리드 시스템 계획 |
| `PERFORMANCE_OPTIMIZATION_PLAN.md` | 성능 최적화 계획 |

---

## 📊 문서 관계도

```
                    ┌─────────────────────────────────┐
                    │         CLAUDE.md               │
                    │   (AI 개발 필독 가이드)           │
                    └────────────────┬────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    ▼                                 ▼
    ┌───────────────────────────┐    ┌───────────────────────────┐
    │   CODEBASE_OVERVIEW.md    │    │   README.md               │
    │   (전체 코드 구조)          │    │   (프로젝트 소개)          │
    └────────────┬──────────────┘    └───────────────────────────┘
                 │
    ┌────────────┼────────────────────────┐
    │            │                        │
    ▼            ▼                        ▼
┌──────────┐ ┌──────────────┐  ┌────────────────────────────────┐
│BACKEND   │ │DEPLOYMENT    │  │ ML_TRAINING_SYSTEM             │
│ARCHITECTURE│ │GUIDE        │  │ (ML 학습 시스템)               │
└──────────┘ └──────────────┘  └────────────────────────────────┘
```

---

## ✅ 온보딩 체크리스트

### 새로운 백엔드 개발자

- [ ] `CLAUDE.md` 읽기 (특히 "절대 하면 안 되는 것들")
- [ ] `docs/CODEBASE_OVERVIEW.md` 읽기
- [ ] `docs/BACKEND_ARCHITECTURE.md` 읽기
- [ ] 로컬 환경 설정 (`backend/README.md` 참고)
- [ ] 테스트 봇 실행해보기
- [ ] `bot_runner.py` 구조 파악

### 배포 담당자

- [ ] `CLAUDE.md` 읽기 ("배포 프로세스" 섹션)
- [ ] `docs/DEPLOYMENT_GUIDE.md` 읽기
- [ ] 서버 SSH 접속 테스트
- [ ] Docker 컨테이너 상태 확인

---

## 💡 팁

### 빠르게 파악하기

1. **코드 검색**: VS Code에서 `Cmd+Shift+F`로 전체 검색
2. **함수 정의 찾기**: 함수명으로 `grep` 검색
3. **API 엔드포인트 확인**: `backend/src/api/` 폴더 확인
4. **DB 스키마 확인**: `backend/src/database/models.py`

### 도움 요청

- **기술적 질문**: 이 문서들을 참고한 후 질문
- **코드 히스토리**: Git log 확인 (`git log --oneline -20`)
- **최근 변경**: `git diff HEAD~5` 또는 `git log --stat -5`

---

**최종 업데이트**: 2025-12-24
