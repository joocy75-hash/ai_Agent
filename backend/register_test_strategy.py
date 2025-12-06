"""
실전거래 테스트용 AI 전략을 데이터베이스에 등록하는 스크립트

사용법:
    python register_test_strategy.py
"""

import asyncio
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from src.database.models import Strategy, User


async def register_test_strategy():
    """실전거래 테스트 전략 등록"""

    # 데이터베이스 연결
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./trading.db")
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. 기존 전략 확인
        result = await session.execute(
            select(Strategy).where(Strategy.name == "SafeTest AI Strategy")
        )
        existing_strategy = result.scalar_one_or_none()

        if existing_strategy:
            print("⚠️  전략이 이미 존재합니다.")
            print(f"   Strategy ID: {existing_strategy.id}")
            print(f"   Name: {existing_strategy.name}")

            # 업데이트 여부 확인
            response = input("\n전략을 업데이트하시겠습니까? (y/n): ")
            if response.lower() != 'y':
                print("취소되었습니다.")
                return

            # 업데이트
            existing_strategy.description = """
실전거래 테스트용 보수적 AI 전략

특징:
- EMA 크로스오버로 트렌드 확인
- RSI로 모멘텀 확인
- ATR로 변동성 필터링
- 거래량 증가 확인
- 엄격한 리스크 관리 (2% 손절, 3% 익절)
- 최소 거래 수량 (0.001)
- 70% 이상 신뢰도에서만 진입

⚠️ 주의사항:
1. 실전 테스트 전 반드시 백테스트 완료
2. 최소 수량으로 시작
3. Stop Loss 자동 설정
4. 거래 로그 실시간 모니터링
"""
            existing_strategy.code = "safe_test_ai_strategy"
            existing_strategy.params = """{
    "ema_fast": 9,
    "ema_slow": 21,
    "rsi_period": 14,
    "rsi_oversold": 30,
    "rsi_overbought": 70,
    "atr_period": 14,
    "atr_multiplier": 1.5,
    "volume_period": 20,
    "volume_threshold": 1.2,
    "stop_loss_pct": 2.0,
    "take_profit_pct": 3.0,
    "max_position_size": 0.001,
    "cooldown_candles": 5
}"""
            await session.commit()
            print("\n✅ 전략이 업데이트되었습니다!")
            print(f"   Strategy ID: {existing_strategy.id}")

        else:
            # 2. 새로운 전략 생성
            new_strategy = Strategy(
                user_id=None,  # 전역 전략
                name="SafeTest AI Strategy",
                description="""
실전거래 테스트용 보수적 AI 전략

특징:
- EMA 크로스오버로 트렌드 확인
- RSI로 모멘텀 확인
- ATR로 변동성 필터링
- 거래량 증가 확인
- 엄격한 리스크 관리 (2% 손절, 3% 익절)
- 최소 거래 수량 (0.001)
- 70% 이상 신뢰도에서만 진입

⚠️ 주의사항:
1. 실전 테스트 전 반드시 백테스트 완료
2. 최소 수량으로 시작
3. Stop Loss 자동 설정
4. 거래 로그 실시간 모니터링
""",
                code="safe_test_ai_strategy",
                params="""{
    "ema_fast": 9,
    "ema_slow": 21,
    "rsi_period": 14,
    "rsi_oversold": 30,
    "rsi_overbought": 70,
    "atr_period": 14,
    "atr_multiplier": 1.5,
    "volume_period": 20,
    "volume_threshold": 1.2,
    "stop_loss_pct": 2.0,
    "take_profit_pct": 3.0,
    "max_position_size": 0.001,
    "cooldown_candles": 5
}"""
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
            select(Strategy).where(Strategy.name == "SafeTest AI Strategy")
        )
        strategy = result.scalar_one()

        print(f"\n📊 전략 이름: {strategy.name}")
        print(f"📝 설명:\n{strategy.description}")
        print(f"\n⚙️  파라미터:")

        import json
        params = json.loads(strategy.params)
        for key, value in params.items():
            print(f"   - {key}: {value}")

        print("\n" + "="*60)
        print("실전 테스트 가이드")
        print("="*60)
        print("""
1. 백테스트 실행
   - 최소 30일 이상 데이터로 테스트
   - 다양한 시장 상황에서 성과 확인

2. API 키 설정
   - Settings 페이지에서 Bitget API 키 등록
   - 테스트넷 사용 권장

3. 봇 시작
   - Dashboard에서 봇 시작
   - 실시간 로그 모니터링

4. 모니터링 항목
   - 진입/청산 시그널
   - 손익률 (Stop Loss, Take Profit)
   - 거래 빈도
   - API 응답 시간

5. 비상 중단
   - 예상치 못한 손실 시 즉시 봇 중지
   - 포지션 수동 청산
   - 로그 분석 후 전략 조정

⚠️  주의: 실전 거래는 자신의 책임하에 진행하세요!
""")

    await engine.dispose()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("실전거래 테스트용 AI 전략 등록")
    print("="*60 + "\n")

    asyncio.run(register_test_strategy())
