"""
AI Integrated Smart Strategy 등록 스크립트

4개의 AI 에이전트를 활용하는 완벽한 전략을 데이터베이스에 등록합니다.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import os


async def register_ai_smart_strategy():
    """AI Integrated Smart Strategy 등록"""

    # Database connection
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./trading.db")
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 전략 정보
        strategy_data = {
            "user_id": None,  # NULL = 시스템 전략 (모든 사용자 사용 가능)
            "name": "AI 통합 스마트 전략",
            "code": "ai_integrated_smart_strategy.AIIntegratedSmartStrategy",
            "description": """4개의 AI 에이전트가 협력하는 완벽한 트레이딩 전략

🤖 AI 에이전트:
- Market Regime Agent: 시장 체제 실시간 분석 (추세/횡보/고변동성)
- Signal Validator Agent: 11가지 규칙으로 신호 검증
- Anomaly Detector Agent: 이상 거래 패턴 감지
- Portfolio Optimizer Agent: 리스크 관리 및 최적화

🎯 전략 특징:
- 시장 체제 기반 동적 파라미터 조정
- AI 신호 검증으로 정확도 향상 (false positive 감소)
- 이상 감지로 리스크 최소화
- 포트폴리오 최적화로 수익 극대화

💡 DeepSeek-V3.2 API 사용으로 비용 효율적 운영 (85% 비용 절감)

📊 적용 시장:
- 추세장: 추세 추종 전략
- 횡보장: 평균 회귀 전략
- 고변동성: 보수적 접근

⚙️ 리스크 레벨: conservative/moderate/aggressive 선택 가능""",
            "params": """{
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "enable_ai": true,
    "risk_level": "moderate",
    "max_position_size": 0.3
}""",
            "is_active": True
        }

        # 전략 삽입
        insert_query = text("""
            INSERT INTO strategies (
                user_id, name, code, description, params, is_active
            ) VALUES (
                :user_id, :name, :code, :description, :params, :is_active
            )
        """)

        await session.execute(insert_query, strategy_data)
        await session.commit()

        # 등록된 전략 확인
        result = await session.execute(
            text("SELECT id, name, code, is_active FROM strategies WHERE code = :code"),
            {"code": "ai_integrated_smart_strategy.AIIntegratedSmartStrategy"}
        )
        strategy = result.fetchone()

        if strategy:
            print("=" * 70)
            print(" ✅ AI Integrated Smart Strategy 등록 완료 ".center(70, "="))
            print("=" * 70)
            print(f"전략 ID: {strategy[0]}")
            print(f"전략 이름: {strategy[1]}")
            print(f"전략 타입: {strategy[2]}")
            print(f"활성 상태: {'✓ 활성' if strategy[3] else '✗ 비활성'}")
            print("=" * 70)
            print()
            print("🤖 AI 에이전트:")
            print("  1. Market Regime Agent - 시장 체제 분석")
            print("  2. Signal Validator Agent - 신호 검증 (11 rules)")
            print("  3. Anomaly Detector Agent - 이상 감지")
            print("  4. Portfolio Optimizer Agent - 포트폴리오 최적화")
            print()
            print("💡 DeepSeek-V3.2 API 사용 (85% 비용 절감)")
            print("=" * 70)
        else:
            print("❌ 전략 등록 실패")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(register_ai_smart_strategy())
