🏆 자동매매 플랫폼 프런트엔드 최종 구성안 (핵심 기능 최적화)

이 문서는 자동매매 시스템 운영에 필수적인 모니터링, 분석, 제어, 리스크 관리 기능을 중심으로 압축 정리된 최종 프런트엔드 설계 청사진입니다.

📌 0. 상위 구조 요약 (6대 핵심 모듈)

카테고리 (Category)

기능 요약 (Summary)

핵심 목적 (Core Purpose)

I. 핵심 대시보드 (Dashboard)

성과 추이, 핵심 리스크 지표, 잔고 및 시스템 상태 요약

시스템 전반의 **‘건강 상태’**를 한눈에 파악

II. 실시간 거래 모니터링 (Live Trading)

실시간 포지션, 청산가, 주문 로그 및 긴급 제어

봇의 ‘현재 활동’ 및 ‘실시간 리스크’ 추적 및 관리

III. 성능 및 히스토리 분석 (Performance & History)

과거 거래 기록, MDD/샤프 비율, 기간별 성과 보고서

전략의 ‘객관적인 효율성’ 심층 분석

IV. 전략 및 백테스팅 관리 (Strategy Management)

전략 파라미터 관리, 백테스팅 실행 및 초보자용 결과 비교

시스템의 ‘미래 성능’ 검증 및 전략 변경

V. 시스템 및 보안 설정 (Settings)

API 키 연동, 리스크 한도 설정, 계정·보안 관리

시스템의 ‘안정적 운영 환경’ 설정

VI. 알림 센터 (Notification Center)

오류/위험/주문 알림 목록 및 알림 설정

즉각 조치가 필요한 ‘위험 상황’ 전달

Ⅰ. 핵심 대시보드 (Dashboard)

목표: 10초 이내에 **안전성(리스크)**과 **수익성(성과)**을 판단하게 합니다.

1. 성과 추이 및 핵심 요약 (Performance Summary)

자산 가치 변화 곡선 (Equity Curve): 누적 자산 가치 변화(USD/%)를 벤치마크(예: BTC 보유)와 필수 비교 표시.

주요 성과 지표 (KPI Cards): Total P&L %, 현재 총 자산, 오늘의 실현 손익, 실시간 미실현 손익 (%) 4가지 핵심 지표.

2. 리스크 및 위험 관리 (Risk Management)

핵심 리스크 지표: 최대 낙폭(MDD), 샤프 비율, 승률을 수치와 상태(양호/주의/경고)로 표시.

리스크 게이지: 현재 MDD와 설정된 최대 MDD 한도 대비 비율, 최대 사용 레버리지를 색상 게이지로 시각화.

3. 시스템 상태 (System Status & Connection)

봇 / API 상태: Bitget API 상태 (🟢/🔴), 마지막 데이터 수신 시간, 현재 실행 전략 및 버전, 서버 Uptime.

긴급 알림 요약: 최신 ERROR / WARNING 3개 요약 표시 (VI. 알림 센터와 연동).

Ⅱ. 실시간 거래 모니터링 (Live Trading)

목표: 리스크 지표(청산가) 확인과 수동 청산에 집중합니다.

1. 실시간 포지션 관리 테이블 (Active Position Management)

필수 칼럼: PAIR, Side, Size, Entry Price, P&L (USD/%), Liquidation Price (청산가), SL/TP 설정 여부, Position Value.

제어 기능: Panic Close (즉시 청산) 버튼.

실시간 표시: WebSocket 기반의 ‘실시간 동기 상태’ 아이콘 (🟢 Live) 필수.

2. 주문 및 거래 활동 로그 (Order & Execution Log)

필수 칼럼: Timestamp, Event Type (ERROR/WARNING/ORDER/FILL), Pair, Message, Order ID.

부가 기능: 심각도 필터링, 자동 스크롤.

Ⅲ. 성능 및 히스토리 분석 (Performance & History)

목표: 전략의 장기적인 효율성을 통계적, 시각적으로 증명합니다.

1. 기간별 핵심 지표 (Key Metrics Summary)

기간 선택기: 전체, 3M, 6M, YTD, Custom 설정 가능.

KPIs: 총 거래 횟수, 승률, 평균 손익비, 샤프/캘마/소르티노 비율, 총 수수료.

2. 성과 시각화 차트 (Performance Charts)

월별 수익률 히트맵: 월별 P&L (%)을 색상 강도로 표시.

P&L 분포 히스토그램: 수익/손실 거래의 크기 분포 분석.

3. 거래 기록 상세 테이블 (Detailed Trade History)

필수 칼럼: 거래 ID, Pair / Side, 진입/청산 시간, 실현 P&L, 수수료, 전략 버전.

부가 기능: CSV 내보내기 및 상세 필터링/검색 기능.

Ⅳ. 전략 및 백테스팅 관리 (Strategy Management)

목표: 초보자도 이해하기 쉬운 핵심 지표로 전략을 검증하고, 현재 활성 전략을 안전하게 제어합니다.

1. 활성 전략 제어 (Active Strategy Control)

현재 전략명/버전/파라미터 표시 및 파라미터 수정 (Hot Swap) 기능.

수정 시 ‘변경 미리보기’ 및 ‘적용 시 경고 모달’ 필수.

Pause / Resume 버튼 제공.

2. 백테스팅 실행 및 기록 (Backtesting Execution & History)

백테스트 실행 폼: 코인, 기간, 전략 버전, 초기 자본 설정 입력.

실행 기록 테이블: 과거 백테스트 결과를 요약 표시.

필수 표시 지표 (초보자용):

총 수익률 (%)

최대 낙폭 (MDD %)

총 거래 횟수

승률 (%)

샤프 비율

결과 비교 차트: 2개 이상의 백테스팅 결과를 Equity Curve Overlay로 중첩 비교.

Ⅴ. 시스템 및 보안 설정 (Settings)

목표: 시스템 안정성 및 사용자 계정 보안의 핵심을 관리합니다.

1. 연결 및 알림 설정

Bitget API Key 관리: 키 입력 및 연결 테스트 버튼.

알림 채널 설정: Webhook URL, 텔레그램 Bot ID 등 외부 알림 채널 설정.

2. 위험 관리 한도 (Risk Limits)

누적 손실 한도 (Total Stop-Loss) 설정 (계좌 보호).

최대 레버리지 제한, 최대 포지션 개수 제한 설정 (운영 리스크 통제).

3. 계정 및 보안 (Account & Security)

비밀번호 변경 및 2FA(2단계 인증) 활성화 기능.

로그인 기록 표시 (최근 접속 일시/IP 주소).

Ⅵ. 알림 센터 (Notification Center)

목표: 긴급 상황을 놓치지 않고, 알림 피로도를 낮춥니다.

1. 실시간 알림 목록

필수 칼럼: Timestamp, Severity (ERROR/WARNING/INFO), Message, Related Pair.

부가 기능: 읽음 표시 및 중요도/시간순 정렬 필터링.

2. 알림 설정 (Notification Preferences)

알림 유형별 On/Off: Error, Risk Warning, Order Fill 등 유형별 수신 설정.

알림 방식: 팝업 / 사운드 재생 설정.