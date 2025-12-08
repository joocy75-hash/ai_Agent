#!/usr/bin/env python3
"""
기본 공용 전략 등록 스크립트

모든 회원이 사용할 수 있는 3가지 대표 전략을 등록합니다:
1. 🔥 공격적 스캘핑 전략 (RSI + MACD 조합)
2. ⚡ 단기 스윙 전략 (볼린저밴드 + RSI 반전)
3. 📈 중장기 추세추종 전략 (골든크로스 + ADX)

실행 방법:
    python register_default_strategies.py

로컬 실행 (SQLite):
    DATABASE_URL=sqlite+aiosqlite:///./trading.db python register_default_strategies.py
"""

import asyncio
import json
import sys
import os

# 프로젝트 루트를 PYTHONPATH에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# 환경 변수에서 DATABASE_URL 가져오기 (기본값: 로컬 SQLite)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./trading.db")
print(
    f"📡 데이터베이스: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}"
)

# 엔진 생성
local_engine = create_async_engine(DATABASE_URL, echo=False)
LocalAsyncSession = async_sessionmaker(
    local_engine, class_=AsyncSession, expire_on_commit=False
)

from src.database.models import Strategy


# ====================================================================
# 전략 1: 공격적 스캘핑 전략 (RSI + MACD Divergence)
# ====================================================================
AGGRESSIVE_STRATEGY = {
    "name": "🔥 공격적 스캘핑 전략",
    "description": """RSI와 MACD 다이버전스를 활용한 고빈도 스캘핑 전략입니다.
    
[전략 특징]
• 높은 수익 잠재력 (레버리지 10배)
• 단기간 많은 거래 (15분봉 기준)
• 계좌의 40% 사용으로 리스크 관리

[진입 조건]
• 롱 진입: RSI < 30 + MACD 골든크로스
• 숏 진입: RSI > 70 + MACD 데드크로스

[리스크 관리]
• 손절: 1.5% (레버리지 고려 실질 15%)
• 익절: 3.0% (손익비 1:2)
• 트레일링 스탑: 1.0%

⚠️ 주의: 변동성이 큰 시장에서 높은 수익을 추구하지만, 
그만큼 리스크도 높습니다. 경험 있는 트레이더에게 추천합니다.""",
    "params": {
        "type": "aggressive_scalping",
        "symbol": "BTCUSDT",
        "timeframe": "15m",
        "strategy_style": "scalping",
        # 포지션 설정 (계좌 잔고 기반)
        "position_size_percent": 40,  # 계좌의 40% 사용
        "leverage": 10,
        # RSI 설정
        "rsi_period": 14,
        "rsi_oversold": 30,
        "rsi_overbought": 70,
        # MACD 설정
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        # 리스크 관리
        "stop_loss": 1.5,
        "take_profit": 3.0,
        "trailing_stop": True,
        "trailing_distance": 1.0,
        # 추가 필터
        "volume_filter": True,
        "min_volume_multiplier": 1.5,
        "max_positions": 3,
        # 거래 시간 필터 (UTC)
        "trading_hours": "all",  # 24시간 거래
    },
    "code": """
# 🔥 공격적 스캘핑 전략 (RSI + MACD Divergence)
# 
# 이 전략은 RSI 과매도/과매수 구간에서 MACD 크로스오버가 발생할 때 진입합니다.
# 
# 매매 로직:
# 1. RSI가 30 이하이고 MACD가 시그널을 상향 돌파 → 롱 진입
# 2. RSI가 70 이상이고 MACD가 시그널을 하향 돌파 → 숏 진입
# 3. 손절/익절은 ATR 기반 동적 조절

def calculate_position_size(balance, params):
    '''계좌 잔고 기반 포지션 크기 계산'''
    percent = params.get('position_size_percent', 40) / 100
    leverage = params.get('leverage', 10)
    return balance * percent * leverage

def check_entry_signal(candles, params):
    '''진입 시그널 확인'''
    rsi = calculate_rsi(candles, params['rsi_period'])
    macd, signal, hist = calculate_macd(candles, params['macd_fast'], params['macd_slow'], params['macd_signal'])
    
    # 롱 진입 조건
    if rsi[-1] < params['rsi_oversold'] and macd[-1] > signal[-1] and macd[-2] <= signal[-2]:
        return 'LONG'
    
    # 숏 진입 조건
    if rsi[-1] > params['rsi_overbought'] and macd[-1] < signal[-1] and macd[-2] >= signal[-2]:
        return 'SHORT'
    
    return None

def calculate_stop_loss(entry_price, side, params):
    '''손절가 계산'''
    sl_percent = params['stop_loss'] / 100
    if side == 'LONG':
        return entry_price * (1 - sl_percent)
    return entry_price * (1 + sl_percent)

def calculate_take_profit(entry_price, side, params):
    '''익절가 계산'''
    tp_percent = params['take_profit'] / 100
    if side == 'LONG':
        return entry_price * (1 + tp_percent)
    return entry_price * (1 - tp_percent)
""",
}


# ====================================================================
# 전략 2: 단기 스윙 전략 (볼린저밴드 + RSI 반전)
# ====================================================================
SHORT_TERM_STRATEGY = {
    "name": "⚡ 단기 스윙 전략",
    "description": """볼린저밴드와 RSI를 결합한 평균 회귀 전략입니다.

[전략 특징]
• 안정적인 수익 추구 (레버리지 5배)
• 1시간~4시간 봉 기준 스윙 트레이딩
• 계좌의 35% 사용

[진입 조건]
• 롱 진입: 가격이 볼린저밴드 하단 터치 + RSI < 35
• 숏 진입: 가격이 볼린저밴드 상단 터치 + RSI > 65

[리스크 관리]
• 손절: 2.0%
• 익절: 4.0% (손익비 1:2)
• 볼린저밴드 중앙선에서 부분 익절

✅ 추천: 안정적인 수익을 원하는 중급 트레이더에게 적합합니다.
횡보장에서 특히 효과적입니다.""",
    "params": {
        "type": "swing_trading",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "strategy_style": "mean_reversion",
        # 포지션 설정
        "position_size_percent": 35,  # 계좌의 35% 사용
        "leverage": 5,
        # 볼린저밴드 설정
        "bb_period": 20,
        "bb_std_dev": 2.0,
        # RSI 설정
        "rsi_period": 14,
        "rsi_oversold": 35,
        "rsi_overbought": 65,
        # 리스크 관리
        "stop_loss": 2.0,
        "take_profit": 4.0,
        "partial_take_profit": 2.0,  # 중앙선에서 50% 익절
        "partial_tp_percent": 50,
        # 추가 필터
        "atr_filter": True,
        "min_atr": 0.5,  # 최소 변동성 필터
        "max_positions": 2,
        # 재진입 방지
        "cooldown_bars": 5,  # 5봉 후 재진입 가능
    },
    "code": """
# ⚡ 단기 스윙 전략 (볼린저밴드 + RSI 반전)
#
# 가격이 볼린저밴드 밴드에 닿고 RSI가 과매도/과매수 구간일 때
# 평균으로 회귀하는 것을 노리는 전략입니다.
#
# 매매 로직:
# 1. 가격이 하단 밴드 터치 + RSI < 35 → 롱 진입 (반등 기대)
# 2. 가격이 상단 밴드 터치 + RSI > 65 → 숏 진입 (조정 기대)
# 3. 중앙선에서 절반 익절, 반대편 밴드에서 전량 익절

def calculate_position_size(balance, params):
    '''계좌 잔고 기반 포지션 크기 계산'''
    percent = params.get('position_size_percent', 35) / 100
    leverage = params.get('leverage', 5)
    return balance * percent * leverage

def check_entry_signal(candles, params):
    '''진입 시그널 확인'''
    close = candles[-1]['close']
    rsi = calculate_rsi(candles, params['rsi_period'])
    upper, middle, lower = calculate_bollinger_bands(candles, params['bb_period'], params['bb_std_dev'])
    
    # 롱 진입: 하단밴드 터치 + RSI 과매도
    if close <= lower[-1] and rsi[-1] < params['rsi_oversold']:
        return 'LONG'
    
    # 숏 진입: 상단밴드 터치 + RSI 과매수
    if close >= upper[-1] and rsi[-1] > params['rsi_overbought']:
        return 'SHORT'
    
    return None

def should_partial_exit(position, current_price, candles, params):
    '''부분 익절 여부 확인'''
    upper, middle, lower = calculate_bollinger_bands(candles, params['bb_period'], params['bb_std_dev'])
    
    if position['side'] == 'LONG' and current_price >= middle[-1]:
        return True, params['partial_tp_percent']
    if position['side'] == 'SHORT' and current_price <= middle[-1]:
        return True, params['partial_tp_percent']
    
    return False, 0
""",
}


# ====================================================================
# 전략 3: 중장기 추세추종 전략 (골든크로스 + ADX)
# ====================================================================
LONG_TERM_STRATEGY = {
    "name": "📈 중장기 추세추종 전략",
    "description": """이동평균선 골든크로스와 ADX를 활용한 추세추종 전략입니다.

[전략 특징]
• 낮은 거래 빈도, 높은 승률 추구
• 4시간~일봉 기준 포지션 트레이딩
• 계좌의 30% 사용 (가장 보수적)
• 레버리지 3배로 안전한 운용

[진입 조건]
• 롱 진입: EMA9 > EMA21 > EMA50 + ADX > 25
• 숏 진입: EMA9 < EMA21 < EMA50 + ADX > 25

[리스크 관리]
• 손절: 3.0% (ATR 기반 동적 조절)
• 익절: 9.0% (손익비 1:3)
• 트레일링 스탑: 2.0%

✅ 강력 추천: 안정적인 장기 수익을 원하는 모든 트레이더에게 적합합니다.
강한 추세장에서 큰 수익을 낼 수 있습니다.""",
    "params": {
        "type": "trend_following",
        "symbol": "BTCUSDT",
        "timeframe": "4h",
        "strategy_style": "position_trading",
        # 포지션 설정 (가장 보수적)
        "position_size_percent": 30,  # 계좌의 30% 사용
        "leverage": 3,
        # EMA 설정 (3중 이동평균선)
        "ema_fast": 9,
        "ema_medium": 21,
        "ema_slow": 50,
        # ADX 설정 (추세 강도 필터)
        "adx_period": 14,
        "adx_threshold": 25,  # 25 이상일 때만 진입
        # 리스크 관리
        "stop_loss": 3.0,
        "take_profit": 9.0,
        "trailing_stop": True,
        "trailing_distance": 2.0,
        # ATR 기반 손절
        "use_atr_stop": True,
        "atr_period": 14,
        "atr_multiplier": 2.5,
        # 피라미딩 설정
        "allow_pyramiding": True,
        "max_pyramid_entries": 2,
        "pyramid_threshold": 2.0,  # 2% 수익 시 추가 진입
        # 필터
        "max_positions": 1,
        "min_trend_bars": 3,  # 최소 3봉 연속 추세 확인
    },
    "code": """
# 📈 중장기 추세추종 전략 (골든크로스 + ADX)
#
# 세 개의 EMA가 정배열/역배열을 이루고 ADX가 강한 추세를 나타낼 때
# 추세 방향으로 진입하는 전략입니다.
#
# 매매 로직:
# 1. EMA 9 > EMA 21 > EMA 50 + ADX > 25 → 롱 진입 (상승 추세)
# 2. EMA 9 < EMA 21 < EMA 50 + ADX > 25 → 숏 진입 (하락 추세)
# 3. 추세가 지속되면 피라미딩으로 포지션 확대

def calculate_position_size(balance, params):
    '''계좌 잔고 기반 포지션 크기 계산'''
    percent = params.get('position_size_percent', 30) / 100
    leverage = params.get('leverage', 3)
    return balance * percent * leverage

def check_entry_signal(candles, params):
    '''진입 시그널 확인'''
    ema_fast = calculate_ema(candles, params['ema_fast'])
    ema_medium = calculate_ema(candles, params['ema_medium'])
    ema_slow = calculate_ema(candles, params['ema_slow'])
    adx = calculate_adx(candles, params['adx_period'])
    
    # ADX 필터: 추세가 충분히 강해야 함
    if adx[-1] < params['adx_threshold']:
        return None
    
    # 롱 진입: 정배열 (9 > 21 > 50)
    if ema_fast[-1] > ema_medium[-1] > ema_slow[-1]:
        # 추가 확인: 최근 3봉 동안 정배열 유지
        if all(ema_fast[-i] > ema_medium[-i] > ema_slow[-i] for i in range(1, 4)):
            return 'LONG'
    
    # 숏 진입: 역배열 (9 < 21 < 50)
    if ema_fast[-1] < ema_medium[-1] < ema_slow[-1]:
        if all(ema_fast[-i] < ema_medium[-i] < ema_slow[-i] for i in range(1, 4)):
            return 'SHORT'
    
    return None

def calculate_dynamic_stop_loss(entry_price, side, candles, params):
    '''ATR 기반 동적 손절가 계산'''
    atr = calculate_atr(candles, params['atr_period'])
    atr_stop = atr[-1] * params['atr_multiplier']
    
    # 고정 손절과 ATR 손절 중 큰 값 사용
    fixed_sl = entry_price * params['stop_loss'] / 100
    dynamic_sl = atr_stop
    
    actual_sl = max(fixed_sl, dynamic_sl)
    
    if side == 'LONG':
        return entry_price - actual_sl
    return entry_price + actual_sl

def should_pyramid(position, current_price, params):
    '''피라미딩 조건 확인'''
    if not params.get('allow_pyramiding', False):
        return False
    
    if position.get('pyramid_count', 0) >= params['max_pyramid_entries']:
        return False
    
    pnl_percent = ((current_price - position['entry_price']) / position['entry_price']) * 100
    if position['side'] == 'SHORT':
        pnl_percent = -pnl_percent
    
    return pnl_percent >= params['pyramid_threshold']
""",
}


async def register_strategies():
    """데이터베이스에 기본 전략 등록"""

    async with LocalAsyncSession() as session:
        strategies_to_add = [
            AGGRESSIVE_STRATEGY,
            SHORT_TERM_STRATEGY,
            LONG_TERM_STRATEGY,
        ]

        registered_count = 0

        for strategy_data in strategies_to_add:
            # 같은 이름의 전략이 이미 있는지 확인
            result = await session.execute(
                select(Strategy).where(
                    Strategy.name == strategy_data["name"], Strategy.user_id.is_(None)
                )
            )
            existing = result.scalars().first()

            if existing:
                print(f"⚠️  이미 존재: {strategy_data['name']} (ID: {existing.id})")
                # 기존 전략 업데이트
                existing.description = strategy_data["description"]
                existing.code = strategy_data["code"]
                existing.params = json.dumps(strategy_data["params"])
                existing.is_active = True
                print("   → 업데이트 완료")
            else:
                # 새 전략 생성
                new_strategy = Strategy(
                    user_id=None,  # 공용 전략 (NULL)
                    name=strategy_data["name"],
                    description=strategy_data["description"],
                    code=strategy_data["code"],
                    params=json.dumps(strategy_data["params"]),
                    is_active=True,  # 활성화 상태로 등록
                )
                session.add(new_strategy)
                registered_count += 1
                print(f"✅ 등록 완료: {strategy_data['name']}")

        await session.commit()

        print("\n" + "=" * 60)
        print(f"📊 등록 결과: {registered_count}개 신규 등록")
        print("=" * 60)

        # 등록된 전략 목록 출력
        result = await session.execute(
            select(Strategy).where(
                Strategy.user_id.is_(None), Strategy.is_active.is_(True)
            )
        )
        all_strategies = result.scalars().all()

        print("\n[등록된 공용 전략 목록]")
        for s in all_strategies:
            params = json.loads(s.params) if s.params else {}
            print(f"  • ID {s.id}: {s.name}")
            print(f"    - 심볼: {params.get('symbol', 'N/A')}")
            print(f"    - 타임프레임: {params.get('timeframe', 'N/A')}")
            print(f"    - 포지션 크기: {params.get('position_size_percent', 'N/A')}%")
            print(f"    - 레버리지: {params.get('leverage', 'N/A')}x")
            print()


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 기본 공용 전략 등록 스크립트")
    print("=" * 60)
    print()

    asyncio.run(register_strategies())

    print("\n✅ 완료! 이제 모든 회원이 이 전략들을 사용할 수 있습니다.")
