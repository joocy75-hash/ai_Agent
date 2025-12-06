 자동매매 플랫폼 관리자 페이지 최종 구성안 (핵심 기능)

이 문서는 다수 사용자를 대상으로 하는 자동매매 플랫폼의 인프라 안정성, 글로벌 제어, 리스크 감사에 중점을 둔 관리자 프런트엔드 설계 청사진입니다. 굳이 필요 없는 사용자 개별의 복잡한 통계 기능은 배제하고, 시스템 운영의 핵심 기능에 집중합니다.

📌 0. 상위 구조 요약 (9대 핵심 모듈)

카테고리 (Category)

기능 요약 (Summary)

핵심 목적 (Core Purpose)

I. 통합 관제 대시보드 (Global Dashboard)

시스템 건전성, 자원 사용량, 글로벌 P&L 및 AUM 요약

시스템 전반의 ‘운영 리스크 및 건강 상태’ 파악

II. 사용자 및 봇 모니터링 (User & Bot Monitoring)

전체 사용자 목록, 봇 상태, 개별 봇 프로세스 정보 및 제어

‘다수 사용자 활동’ 실시간 추적 및 문제 해결

III. 보안 및 감사 (Security & Audit)

API 키 상태 관리, 위험 정책 위반 감사 로그

‘시스템 보안 및 정책 준수’ 강제 및 기록

IV. 전략 및 버전 관리 (Strategy & Versioning)

신규 전략 배포, 버전 태그, 사용자 그룹별 전략 적용

‘운영 전략의 안정적 배포’ 및 관리

V. 서버 및 인프라 관리 (Server & Infrastructure)

서버 리소스 모니터링, 핵심 서비스 제어, 중앙 로그 조회

‘인프라 성능 및 안정성’ 유지 및 관리

VI. 글로벌 알림 및 공지 (Global Alerts & Announcements)

시스템 오류 경고, 사용자 대상 서비스 공지 생성 및 발송

‘위험 상황 전파 및 사용자 소통’ 기능

VII. 통합 이벤트 타임라인 (Global Event Timeline)

플랫폼 전반의 모든 주요 사건을 시간순 스트림으로 추적

‘무슨 일이 언제 발생했는지’ 시간순으로 완벽 추적

VIII. 전역 검색 기능 (Global Search)

User ID, Order ID, Log 등 플랫폼 전반 데이터 검색

‘관리자 업무 효율’ 극대화 및 빠른 정보 접근

IX. 운영자 알림 라우팅 (Operator Alert Routing)

관리자 전용 Webhook/Telegram 알림 채널 설정

**‘치명적 위험 상황’**에 대한 즉각적인 경보 수신

Ⅰ. 통합 관제 대시보드 (Global Dashboard)

목표: 플랫폼 전체의 실시간 건전성과 글로벌 리스크를 한눈에 파악합니다.

1. 글로벌 핵심 요약 (Global Summary)

총 관리 자산 (Total AUM): 전체 사용자 자산 합계 (USD).

글로벌 P&L: 지난 24시간, 7일, 누적 총 수익률(%).

활성 사용자/봇 수: 현재 로그인한 사용자 수 / 현재 Running 상태인 봇 프로세스 수.

2. 시스템 건전성 및 리소스 (System Health & Resources)

주요 서비스 상태: Web Server, Trading Engine Daemon, Database, WebSocket Service 상태 (🟢/🔴).

서버 리소스 게이지: CPU/RAM/Network 사용률을 실시간 게이지로 표시.

거래소 API 상태: 연동된 거래소(Bitget)의 전체 API 연결 상태 및 최근 Rate Limit 초과 여부.

3. 글로벌 리스크 지표

최대 동시 포지션 개수: 전체 사용자의 현재 포지션 개수 합계 / 최대 허용치 대비 비율.

현재 가장 위험한 사용자 Top 5: 청산 임박 순으로 표시.

최신 치명적 오류: 지난 1시간 동안 발생한 CRITICAL ERROR 수량 및 목록 요약.

Ⅱ. 사용자 및 봇 모니터링 (User & Bot Monitoring)

목표: 개별 사용자의 활동을 모니터링하고, 필요 시 개별/글로벌 제어를 수행합니다.

1. 전체 사용자 목록 테이블 (All Users Status)

필수 칼럼: User ID, Email, 가입일, Total P&L, 현재 MDD, Last Login Time.

기능: 사용자 검색 및 필터링 (P&L 순, MDD 높은 순, 봇 활성화 여부 순).

2. 사용자 상세 (User Detail)

API Key 상태, 활성 전략, 현재 오픈 포지션, 사용자 오류 로그, 사용자 위험 상태(MDD, 청산 위험).

계정 제어: 계정 비활성화(Suspend), Force Logout 기능.

3. 활성 봇 목록 및 제어 (Active Bot List & Control)

필수 칼럼: User ID, Strategy Name, Version, Bot Status (Running/Paused/Error), Server Uptime.

개별 제어: 특정 사용자의 봇 강제 정지 (Force Pause) 또는 강제 재시작 (Force Restart) 버튼.

4. 글로벌 비상 제어 (Global Emergency Control)

버튼: 전체 봇 일시 정지 (Pause All Trading) 버튼. (사용 시 관리자 기록 및 경고 모달 필수)

버튼: 특정 사용자 강제 로그아웃 및 계정 정지 기능.

Ⅲ. 보안 및 감사 (Security & Audit)

목표: 플랫폼의 보안 정책을 유지하고 위험 행위를 감사합니다.

1. API 키 관리 및 감사 (API Key Management)

필수 칼럼: User ID, Exchange, Key Status (Valid/Invalid), Revoke/Disable 버튼.

감사 로그: API 키 변경/생성/삭제 기록.

2. 위험 정책 감사 (Risk Policy Audit)

위반 목록: 일일 손실 한도 초과(Daily Stop-Loss), 누적 손실 한도 초과(Total Stop-Loss), 허용 레버리지 초과 등 정책 위반 사용자 목록.

강제 조치 기록: 정책 위반 사용자 봇 자동 정지 (Auto-Pause) 기록 및 해제 기능.

3. 보안 이벤트 로그

로그인 시도: 실패한 로그인 시도 및 의심 IP 로그인 기록.

2FA 감사: 2단계 인증 활성화/비활성화 기록.

Ⅳ. 전략 및 버전 관리 (Strategy & Versioning)

목표: 새로운 전략 버전을 안전하게 배포하고 관리합니다.

1. 전략 파일 관리 (Strategy File Management)

업로드 폼: 신규 전략 파일 업로드 및 버전 태그, Changelog 기록.

버전 목록: 모든 전략의 버전별 목록 및 상세 변경 사항.

2. 버전 배포 제어 (Version Deployment Control)

전체 배포: 최신 전략 버전을 모든 사용자에게 적용하는 기능.

선택 배포: 특정 사용자 그룹(A/B 테스트) 또는 개별 사용자에게 특정 버전을 적용하는 기능.

3. 마이그레이션 및 롤백

롤백 기능: 특정 전략 버전을 이전 안정화 버전으로 즉시 롤백하는 기능.

롤백 기록 저장 필수.

Ⅴ. 서버 및 인프라 관리 (Server & Infrastructure)

목표: 서버 자원을 모니터링하고 서비스 상태를 직접 제어합니다.

1. 서버 리소스 모니터링 상세 (Detailed Resource Monitoring)

차트: CPU, Memory, Disk I/O, Network의 시간별 사용량 추이 그래프.

경고 임계치 설정: 각 리소스의 경고 (Warning) / 치명적 (Critical) 임계치 설정 기능.

2. 서비스 제어 (Service Control)

핵심 프로세스 목록: Trading Daemon, Web Server, Worker/Scheduler 등 핵심 프로세스의 ID, 메모리 사용량, Uptime 표시.

제어 버튼: 각 프로세스의 재시작 (Restart), 중지 (Stop), 리로드 (Reload) 기능.

3. 중앙 로그 시스템 (Central Log Access)

로그 유형 필터: CRITICAL, ERROR, WARNING, INFO 레벨별 로그 조회.

검색 기능: Timestamp, User ID, Strategy Name 기준 검색.

다운로드 기능 제공.

Ⅵ. 글로벌 알림 및 공지 (Global Alerts & Announcements)

목표: 시스템 전반의 위험을 알리고, 사용자에게 공지 사항을 전달합니다.

1. 시스템 오류 경고 (System Error Alerts)

긴급 경고 목록: API 장애, DB 연결 끊김, 서버 다운 등 시스템 자체의 치명적 경고 목록.

처리 상태: 각 경고에 대한 확인 / 처리 중 / 완료 상태 변경 기능.

2. 사용자 공지 관리 (User Announcement Management)

공지 생성/편집: 제목, 내용, 게시 기간을 설정하여 모든 사용자에게 표시될 공지를 작성하고 게시하는 기능.

발송 기록: 공지 메일 또는 텔레그램 발송 성공/실패 기록.

3. 알림 템플릿 관리 (Notification Template)

이메일, Webhook, Telegram 등 외부 알림 채널로 발송되는 메시지의 템플릿을 관리하고 테스트하는 기능.

🧩 VII. 통합 이벤트 타임라인 (Global Event Timeline)

목표: 플랫폼 전체에서 **'무슨 일이 언제 일어났는가'**를 시간순으로 완벽하게 추적.

포함 이벤트: 시스템 오류, API 장애, 전략 오류·실패, 서버/봇 재시작, 사용자 API 오류, 정책 위반(Daily Stop-Loss 초과), 공지 발송, 사용자 계정 제어 이벤트 등 모든 주요 사건.

UI: Timestamp 기준 시간순 스트림(Log Timeline) 형태로 제공.

🧩 VIII. 전역 검색 기능 (Global Search)

목표: 관리자 업무 효율을 극대화하기 위해 플랫폼 전반을 즉시 검색.

검색창: 상단 고정(Global Search Bar) 형태로 제공.

검색 가능 대상: User ID, Order ID, Strategy Name, Log Content, Error Code, IP 주소, Event Timeline 전체.

검색 위치: 사용자 테이블, 봇 상태, 에러 로그, 거래 로그 등 모든 핵심 모듈.

🧩 IX. 운영자 알림 라우팅 (Operator Alert Routing)

목표: 치명적 위험 상황 발생 시 운영자에게 즉각적인 경보 전송.

경보 채널: Slack, Telegram, Email 등 운영자 전용 채널 설정.

발송 조건: API 오류 연속 3회 이상, 전략 오류 급증, DB 지연 증가, 주요 프로세스 다운(Trading Engine 등), 서버 리소스(CPU/RAM) 임계치 초과, 사용자 청산 위험 급증.

🎯 최종 요약

이 문서는 자동매매 SaaS 플랫폼 운영에 반드시 필요한 관리자 기능만을 정확히 선별한 완성형 설계 청사진입니다. 이 구성을 통해 시스템의 안정적인 운영과 신속한 장애 대응이 가능해집니다.