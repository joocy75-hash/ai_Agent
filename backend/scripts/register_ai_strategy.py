"""
AI 자율 적응형 전략 등록 스크립트
"""
import sys
import os
import asyncio
import json

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.db import AsyncSessionLocal
from src.database.models import Strategy
from sqlalchemy import select, delete


async def register_ai_strategy():
    """AI 자율 적응형 전략을 데이터베이스에 등록"""

    # 전략 코드 읽기
    strategy_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        'src',
        'strategies',
        'ai_autonomous_adaptive_strategy.py'
    )

    with open(strategy_path, 'r', encoding='utf-8') as f:
        strategy_code = f.read()

    # 기본 파라미터
    default_params = {
        # 전략 메타데이터
        "type": "ai_adaptive",
        "symbol": "BTCUSDT",
        "timeframe": "5m",

        # EMA 설정
        "ema_fast": 20,
        "ema_slow": 50,

        # RSI 설정
        "rsi_period": 14,
        "rsi_oversold": 35,
        "rsi_overbought": 65,

        # 리스크 관리
        "base_sl_percent": 1.5,  # 기본 손절 1.5%
        "risk_reward_ratio": 2.0,  # 손익비 1:2
        "stop_loss": 1.5,  # 프론트엔드 표시용
        "take_profit": 3.0,  # 프론트엔드 표시용
        "risk_level": "high",  # 10배 레버리지 = 고위험

        # 포지션 크기
        "position_size_percent": 40,  # 잔고의 40%
        "leverage": 10,  # 10배 레버리지

        # 시장 환경 판단
        "trending_adx_threshold": 25,
        "ranging_adx_threshold": 20,
        "volatile_atr_multiplier": 2.0,

        # 최소 데이터
        "min_candles": 50
    }

    async with AsyncSessionLocal() as session:
        try:
            # 기존 전략 삭제 (admin 사용자 전략만)
            print("기존 전략 삭제 중...")
            await session.execute(
                delete(Strategy).where(Strategy.user_id == 1)
            )
            await session.commit()
            print("✓ 기존 전략 삭제 완료")

            # 새 전략 등록
            print("\nAI 자율 적응형 전략 등록 중...")
            new_strategy = Strategy(
                user_id=1,  # admin 사용자
                name="AI 자율 적응형 전략",
                description="""
🤖 완전 AI 주도형 매매 전략

AI 에이전트들이 모든 매매 결정을 자율적으로 수행합니다.
시장 환경에 따라 전략을 자동으로 전환하고, 다중 지표 합의 기반으로 고신뢰도 진입합니다.

✨ 핵심 기능:
- Market Regime 자동 감지 (Trending/Ranging/Volatile)
- 시장 환경별 최적 전략 자동 전환
- 다중 지표 합의 기반 진입 (최소 3개 지표 동의)
- Signal Validator 자동 검증
- Risk Monitor 실시간 모니터링
- ATR 기반 동적 손절/익절
- 트레일링 스탑 자동 적용

📊 시장 환경별 전략:
- TRENDING: EMA 크로스 + 모멘텀 → 트렌드 추종
- RANGING: RSI 평균회귀 + 볼린저 밴드 → 레인지 트레이딩
- VOLATILE: 보수적 진입 + 넓은 손절 → 리스크 최소화
- LOW_VOLUME: 거래 중지 → 유동성 부족 회피

🛡️ 리스크 관리:
- 변동성 기반 포지션 크기 자동 조절
- 일일 손실 한도 자동 체크
- 청산가 근접 자동 감지
- 손익비 최소 1:2 유지
                """.strip(),
                code=strategy_code,
                params=json.dumps(default_params)  # dict를 JSON 문자열로 변환
            )

            session.add(new_strategy)
            await session.commit()
            await session.refresh(new_strategy)

            print(f"✓ 전략 등록 완료!")
            print(f"  - ID: {new_strategy.id}")
            print(f"  - Name: {new_strategy.name}")
            print(f"  - User ID: {new_strategy.user_id}")
            print(f"\n📝 기본 파라미터:")
            for key, value in default_params.items():
                print(f"  - {key}: {value}")

            return new_strategy.id

        except Exception as e:
            await session.rollback()
            print(f"✗ 에러 발생: {e}")
            raise


if __name__ == "__main__":
    print("=" * 60)
    print(" AI 자율 적응형 전략 등록")
    print("=" * 60)
    print()

    strategy_id = asyncio.run(register_ai_strategy())

    print()
    print("=" * 60)
    print(" 등록 완료!")
    print("=" * 60)
    print()
    print(f"전략 ID: {strategy_id}")
    print()
    print("이제 프론트엔드에서 이 전략을 선택하여 봇을 시작할 수 있습니다.")
    print()
