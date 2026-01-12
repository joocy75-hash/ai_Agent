"""
AI 전략 생성 API
DeepSeek AI를 사용하여 자동으로 거래 전략을 생성합니다.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.db import get_session
from ..database.models import Strategy
from ..middleware.rate_limit_improved import ai_strategy_limiter
from ..services.deepseek_service import deepseek_service
from ..utils.jwt_auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Strategy"])


class StrategyGenerateRequest(BaseModel):
    """전략 생성 요청"""

    prompt: Optional[str] = None
    count: int = 3


class StrategyResponse(BaseModel):
    """전략 응답"""

    id: int
    name: str
    description: str
    type: str
    symbol: str
    timeframe: str
    parameters: dict


@router.post("/strategies/generate")
async def generate_strategies(
    request: StrategyGenerateRequest,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    AI를 사용하여 거래 전략 생성

    - DeepSeek AI가 3개의 기본 전략을 자동 생성합니다
    - 생성된 전략은 데이터베이스에 저장됩니다

    **Rate Limit**: 시간당 5회 제한
    """
    # Rate Limit 체크 (시간당 5회)
    ai_strategy_limiter.check(user_id)

    logger.info(f"User {user_id} requested AI strategy generation")

    try:
        # DeepSeek AI로 전략 생성
        strategies_data = deepseek_service.generate_trading_strategies()

        created_strategies = []

        for strategy_data in strategies_data:
            # params JSON에 모든 파라미터 저장
            params_dict = {
                "type": strategy_data["type"],
                "symbol": strategy_data["symbol"],
                "timeframe": strategy_data["timeframe"],
                **strategy_data["parameters"],  # 추가 파라미터 병합
            }

            # 데이터베이스에 저장
            new_strategy = Strategy(
                user_id=user_id,
                name=strategy_data["name"],
                description=strategy_data.get("description", ""),
                code=strategy_data.get("code", ""),  # AI가 생성한 전략 코드
                params=json.dumps(params_dict),
                is_active=False,  # 기본적으로 비활성화
            )

            session.add(new_strategy)
            await session.flush()  # ID 생성

            created_strategies.append(
                {
                    "id": new_strategy.id,
                    "name": new_strategy.name,
                    "description": new_strategy.description,
                    "type": strategy_data["type"],
                    "symbol": strategy_data["symbol"],
                    "timeframe": strategy_data["timeframe"],
                    "parameters": strategy_data["parameters"],
                }
            )

        await session.commit()

        return {
            "success": True,
            "message": f"{len(created_strategies)}개의 전략이 생성되었습니다.",
            "strategies": created_strategies,
        }

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"전략 생성 실패: {str(e)}") from e


@router.get("/strategies/list")
async def list_ai_strategies(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    전략 목록 조회

    반환하는 전략:
    1. 공용 전략 (user_id=NULL, is_active=True) - 모든 사용자가 볼 수 있는 활성화된 공용 전략
    2. 현재 사용자가 생성한 전략 - 활성화 여부 무관
    """
    from sqlalchemy import or_, select

    result = await session.execute(
        select(Strategy)
        .where(
            or_(
                # 공용 전략: user_id=NULL이고 활성화된 것만
                (Strategy.user_id.is_(None)) & (Strategy.is_active is True),
                # 사용자 본인의 전략: 활성화 여부 무관
                Strategy.user_id == user_id,
            )
        )
        .order_by(Strategy.id.desc())  # 최신순 정렬
    )
    strategies = result.scalars().all()
    logger.info(
        f"[Strategy List] User {user_id}: Found {len(strategies)} strategies (including public)"
    )

    def parse_strategy(s):
        """Strategy 객체의 JSON 파라미터를 파싱하여 구조화된 딕셔너리로 변환합니다.

        데이터베이스에 저장된 Strategy 객체의 params 필드(JSON 문자열)를
        파싱하고, 프론트엔드에서 사용할 수 있는 표준화된 형식으로 변환합니다.
        레거시 데이터와의 호환성을 위해 JSON 파싱 실패 시에도 안전하게 처리합니다.

        Args:
            s (Strategy): 파싱할 Strategy 데이터베이스 모델 객체.
                필수 속성:
                - id (int): 전략 ID
                - name (str): 전략 이름
                - description (str, optional): 전략 설명
                - params (str, optional): JSON 형식의 파라미터 문자열
                - is_active (bool, optional): 활성화 상태

        Returns:
            dict: 구조화된 전략 정보 딕셔너리.
                - id (int): 전략 ID
                - name (str): 전략 이름
                - description (str): 전략 설명 (없으면 빈 문자열)
                - type (str): 전략 유형 (기본값: "CUSTOM")
                - symbol (str): 거래 심볼 (기본값: "BTC/USDT")
                - timeframe (str): 타임프레임 (기본값: "1h")
                - leverage (int): 레버리지 배수 (기본값: 1)
                - risk_level (str): 위험도 ("low", "medium", "high")
                - stop_loss (float): 손절 비율 (기본값: 1.5)
                - take_profit (float): 익절 비율 (기본값: 3.0)
                - parameters (dict): 원본 파라미터 딕셔너리
                - is_active (bool): 활성화 상태
                - created_at (None): 생성 시각 (현재 미구현)

        Note:
            - risk_level은 leverage 값에 따라 자동 결정됩니다:
              leverage >= 10: "high", leverage >= 5: "medium", 그 외: "low"
            - JSON 파싱 실패 시 원본 문자열이 {"_raw": 원본값} 형태로 보존됩니다.
        """
        # JSON 파싱 시 예외 처리 (레거시 데이터 호환)
        params = {}
        if s.params:
            try:
                params = json.loads(s.params)
            except json.JSONDecodeError:
                # 레거시 형식의 params는 빈 dict로 처리
                logger.warning(f"[AI Strategy] Invalid JSON in params for strategy {s.id}: {s.params[:50]}...")
                params = {"_raw": s.params}  # 원본 보존

        leverage = params.get("leverage", 1)
        # 위험도 결정: leverage 기준
        if leverage >= 10:
            risk_level = "high"
        elif leverage >= 5:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "id": s.id,
            "name": s.name,
            "description": s.description or "",
            "type": params.get("type", "CUSTOM"),
            "symbol": params.get("symbol", "BTC/USDT"),
            "timeframe": params.get("timeframe", "1h"),
            "leverage": leverage,
            "risk_level": params.get("risk_level", risk_level),
            "stop_loss": params.get("stop_loss", 1.5),
            "take_profit": params.get("take_profit", 3.0),
            "parameters": params,
            "is_active": s.is_active if hasattr(s, "is_active") else False,
            "created_at": None,
        }

    return {
        "strategies": [parse_strategy(s) for s in strategies]
    }


@router.delete("/strategies/{strategy_id}")
async def delete_strategy(
    strategy_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """전략 삭제"""
    from sqlalchemy import select

    result = await session.execute(
        select(Strategy).where(Strategy.id == strategy_id, Strategy.user_id == user_id)
    )
    strategy = result.scalars().first()

    if not strategy:
        raise HTTPException(status_code=404, detail="전략을 찾을 수 없습니다.")

    await session.delete(strategy)
    await session.commit()

    return {"success": True, "message": "전략이 삭제되었습니다."}


@router.get("/status")
async def get_ai_status():
    """AI 서비스 상태 확인"""
    from src.config import settings

    has_api_key = bool(settings.deepseek_api_key)

    return {
        "provider": "DeepSeek",
        "model": "deepseek-chat",
        "status": "active" if has_api_key else "inactive",
        "api_key_configured": has_api_key,
        "features": ["전략 자동 생성", "시장 분석", "AI 기반 추천"],
    }
