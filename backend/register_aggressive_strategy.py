"""
공격적 테스트 전략을 데이터베이스에 등록

사용법:
    python3 register_aggressive_strategy.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from src.database.models import Strategy


async def register_aggressive_strategy():
    """공격적 테스트 전략 등록"""

    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./trading.db")
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. 기존 전략 확인
        result = await session.execute(
            select(Strategy).where(Strategy.name == "Aggressive Test Strategy")
        )
        existing_strategy = result.scalar_one_or_none()

        if existing_strategy:
            print("⚠️  전략이 이미 존재합니다.")
            print(f"   Strategy ID: {existing_strategy.id}")
            print(f"   Name: {existing_strategy.name}")

            response = input("\n전략을 업데이트하시겠습니까? (y/n): ")
            if response.lower() != 'y':
                print("취소되었습니다.")
                return

            # 업데이트
            existing_strategy.description = """
🚀 공격적 테스트 전략

목적: 실전 매매 시스템 빠른 검증

특징:
- 매우 빠른 진입 (30% 신뢰도만 있으면 진입)
- 빠른 EMA (5/10) - 즉각 반응
- 공격적 RSI (40/60) - 쉬운 진입
- 빠른 청산 (1% 손절, 2% 익절)
- 짧은 쿨다운 (2 캔들)
- 최소 수량 (0.001 BTC)

진입 조건:
- 롱: EMA 상승 OR RSI < 40
- 숏: EMA 하락 OR RSI > 60
- 신뢰도 30% 이상

청산 조건:
- 익절: +2%
- 손절: -1%

⚠️ 주의사항:
1. 테스트 목적으로만 사용
2. 거래 빈도가 매우 높음
3. 수수료 고려 필요
4. 실전 사용 권장하지 않음
"""
            existing_strategy.code = "aggressive_test_strategy"
            existing_strategy.params = """{
    "ema_fast": 5,
    "ema_slow": 10,
    "rsi_period": 7,
    "rsi_oversold": 40,
    "rsi_overbought": 60,
    "stop_loss_pct": 1.0,
    "take_profit_pct": 2.0,
    "max_position_size": 0.001,
    "cooldown_candles": 2,
    "min_confidence": 0.3,
    "type": "AGGRESSIVE_TEST",
    "symbol": "BTCUSDT",
    "timeframe": "5m"
}"""
            await session.commit()
            print("\n✅ 전략이 업데이트되었습니다!")
            print(f"   Strategy ID: {existing_strategy.id}")

        else:
            # 2. 새로운 전략 생성
            new_strategy = Strategy(
                user_id=None,  # 전역 전략
                name="Aggressive Test Strategy",
                description="""
🚀 공격적 테스트 전략

목적: 실전 매매 시스템 빠른 검증

특징:
- 매우 빠른 진입 (30% 신뢰도만 있으면 진입)
- 빠른 EMA (5/10) - 즉각 반응
- 공격적 RSI (40/60) - 쉬운 진입
- 빠른 청산 (1% 손절, 2% 익절)
- 짧은 쿨다운 (2 캔들)
- 최소 수량 (0.001 BTC)

진입 조건:
- 롱: EMA 상승 OR RSI < 40
- 숏: EMA 하락 OR RSI > 60
- 신뢰도 30% 이상

청산 조건:
- 익절: +2%
- 손절: -1%

⚠️ 주의사항:
1. 테스트 목적으로만 사용
2. 거래 빈도가 매우 높음
3. 수수료 고려 필요
4. 실전 사용 권장하지 않음
""",
                code="aggressive_test_strategy",
                params="""{
    "ema_fast": 5,
    "ema_slow": 10,
    "rsi_period": 7,
    "rsi_oversold": 40,
    "rsi_overbought": 60,
    "stop_loss_pct": 1.0,
    "take_profit_pct": 2.0,
    "max_position_size": 0.001,
    "cooldown_candles": 2,
    "min_confidence": 0.3,
    "type": "AGGRESSIVE_TEST",
    "symbol": "BTCUSDT",
    "timeframe": "5m"
}""",
                is_active=False
            )

            session.add(new_strategy)
            await session.commit()
            await session.refresh(new_strategy)

            print("\n✅ 새로운 전략이 등록되었습니다!")
            print(f"   Strategy ID: {new_strategy.id}")
            print(f"   Name: {new_strategy.name}")

        # 3. 등록된 전략 정보 출력
        print("\n" + "="*60)
        print("전략 상세 정보")
        print("="*60)

        result = await session.execute(
            select(Strategy).where(Strategy.name == "Aggressive Test Strategy")
        )
        strategy = result.scalar_one()

        print(f"\n🚀 전략 이름: {strategy.name}")
        print(f"📝 설명:\n{strategy.description}")
        print(f"\n⚙️  파라미터:")

        import json
        params = json.loads(strategy.params)
        for key, value in params.items():
            print(f"   - {key}: {value}")

        print("\n" + "="*60)
        print("테스트 가이드")
        print("="*60)
        print("""
1. 전략 활성화
   - 프론트엔드 전략 관리 페이지에서 "Aggressive Test Strategy" ON

2. Bitget API 키 설정
   - Settings 페이지에서 API 키 등록
   - 권한: Read + Trade only

3. 봇 시작
   - Dashboard에서 "Aggressive Test Strategy" 선택
   - "Start Bot" 클릭

4. 모니터링 (중요!)
   - 백엔드 로그 실시간 확인
   - 거래 빈도 모니터링 (매우 높을 수 있음)
   - 포지션 변화 확인
   - 손익 추적

5. 예상 동작
   - 5분마다 시그널 체크
   - 조건 충족 시 즉시 진입
   - 2% 익절 또는 1% 손절에서 자동 청산
   - 2 캔들(10분) 후 다음 거래 가능

6. 중단 조건
   - 5회 연속 손실
   - 누적 손실 -5% 초과
   - 예상과 다른 동작
   - API 에러 반복

⚠️  주의:
- 거래 빈도가 높아 수수료 부담 큼
- 최소 금액(0.001 BTC = 약 $50)으로 시작
- 실전 수익 목적이 아닌 시스템 테스트 목적
- 언제든 수동으로 중단할 준비 필요
""")

    await engine.dispose()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 공격적 테스트 전략 등록")
    print("="*60 + "\n")

    asyncio.run(register_aggressive_strategy())
