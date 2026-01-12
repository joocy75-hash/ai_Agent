"""
Grid Template Service
- 템플릿 CRUD
- 통계 업데이트
- 템플릿으로 봇 생성
"""

import math
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import (
    BotInstance,
    BotType,
    GridBotConfig,
    GridBotTemplate,
    GridMode,
    GridOrder,
    GridOrderStatus,
)
from ..schemas.grid_template_schema import (
    GridTemplateCreate,
    GridTemplateUpdate,
    UseTemplateRequest,
)


class GridTemplateService:
    """그리드 템플릿 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ===== 조회 =====

    async def get_active_templates(
        self, symbol: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> List[GridBotTemplate]:
        """
        활성화된 템플릿 목록 조회 (사용자용)
        - is_active=True인 것만
        - is_featured 우선, sort_order 순
        """
        query = (
            select(GridBotTemplate)
            .where(GridBotTemplate.is_active is True)
            .order_by(
                GridBotTemplate.is_featured.desc(),
                GridBotTemplate.sort_order.asc(),
                GridBotTemplate.backtest_roi_30d.desc().nullslast(),
            )
            .offset(offset)
            .limit(limit)
        )

        if symbol:
            query = query.where(GridBotTemplate.symbol == symbol.upper())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_template_by_id(self, template_id: int) -> Optional[GridBotTemplate]:
        """템플릿 ID로 조회"""
        result = await self.db.execute(
            select(GridBotTemplate).where(GridBotTemplate.id == template_id)
        )
        return result.scalar_one_or_none()

    async def get_all_templates(
        self, include_inactive: bool = False
    ) -> List[GridBotTemplate]:
        """모든 템플릿 조회 (관리자용)"""
        query = select(GridBotTemplate).order_by(
            GridBotTemplate.sort_order.asc(), GridBotTemplate.created_at.desc()
        )

        if not include_inactive:
            query = query.where(GridBotTemplate.is_active is True)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ===== 생성/수정/삭제 =====

    async def create_template(
        self, data: GridTemplateCreate, created_by: int
    ) -> GridBotTemplate:
        """템플릿 생성 (관리자)"""
        template = GridBotTemplate(
            name=data.name,
            symbol=data.symbol.upper(),
            direction=data.direction,
            leverage=data.leverage,
            lower_price=data.lower_price,
            upper_price=data.upper_price,
            grid_count=data.grid_count,
            grid_mode=data.grid_mode,
            min_investment=data.min_investment,
            recommended_investment=data.recommended_investment,
            recommended_period=data.recommended_period,
            description=data.description,
            tags=data.tags,
            is_active=data.is_active,
            is_featured=data.is_featured,
            sort_order=data.sort_order,
            created_by=created_by,
        )
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def update_template(
        self, template_id: int, data: GridTemplateUpdate
    ) -> Optional[GridBotTemplate]:
        """템플릿 수정 (관리자)"""
        template = await self.get_template_by_id(template_id)
        if not template:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(template, key, value)

        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def delete_template(self, template_id: int) -> bool:
        """템플릿 삭제 (관리자) - 실제 삭제가 아닌 비활성화"""
        template = await self.get_template_by_id(template_id)
        if not template:
            return False

        template.is_active = False
        await self.db.commit()
        return True

    async def toggle_template(self, template_id: int) -> Optional[GridBotTemplate]:
        """템플릿 공개/비공개 토글"""
        template = await self.get_template_by_id(template_id)
        if not template:
            return None

        template.is_active = not template.is_active
        await self.db.commit()
        await self.db.refresh(template)
        return template

    # ===== 템플릿 사용 (봇 생성) =====

    async def use_template(
        self, template_id: int, user_id: int, request: UseTemplateRequest
    ) -> tuple[BotInstance, GridBotConfig]:
        """
        템플릿으로 봇 인스턴스 생성

        1. 템플릿 조회
        2. 최소 투자금액 검증
        3. BotInstance 생성
        4. GridBotConfig 생성 (템플릿 설정 복사)
        5. GridOrder 레코드 생성
        6. 템플릿 통계 업데이트
        """
        # 1. 템플릿 조회
        template = await self.get_template_by_id(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        if not template.is_active:
            raise ValueError("This template is not available")

        # 2. 최소 투자금액 검증
        if request.investment_amount < template.min_investment:
            raise ValueError(f"Minimum investment is {template.min_investment} USDT")

        # 레버리지 결정 (요청값 or 템플릿 기본값)
        leverage = request.leverage or template.leverage

        # 3. BotInstance 생성
        bot_instance = BotInstance(
            user_id=user_id,
            name=f"{template.symbol} Grid ({template.direction.value.upper()})",
            bot_type=BotType.GRID,
            symbol=template.symbol,
            max_leverage=leverage,
            template_id=template.id,
            is_active=True,
            is_running=True,  # 생성 후 자동 시작
            allocation_percent=Decimal("10.0"),  # 기본값
        )
        self.db.add(bot_instance)
        await self.db.flush()  # ID 할당

        # 4. GridBotConfig 생성
        per_grid_amount = self._calculate_per_grid_amount(
            request.investment_amount, template.grid_count, leverage
        )

        grid_config = GridBotConfig(
            bot_instance_id=bot_instance.id,
            lower_price=template.lower_price,
            upper_price=template.upper_price,
            grid_count=template.grid_count,
            grid_mode=template.grid_mode,
            total_investment=request.investment_amount,
            per_grid_amount=per_grid_amount,
        )
        self.db.add(grid_config)
        await self.db.flush()

        # 5. GridOrder 레코드 생성
        grid_prices = self._calculate_grid_prices(
            template.lower_price,
            template.upper_price,
            template.grid_count,
            template.grid_mode,
        )

        for idx, price in enumerate(grid_prices):
            grid_order = GridOrder(
                grid_config_id=grid_config.id,
                grid_index=idx,
                grid_price=price,
                status=GridOrderStatus.PENDING,
            )
            self.db.add(grid_order)

        # 6. 템플릿 통계 업데이트
        template.active_users = (template.active_users or 0) + 1
        template.total_users = (template.total_users or 0) + 1
        template.total_funds_in_use = (
            Decimal(str(template.total_funds_in_use or 0)) + request.investment_amount
        )

        await self.db.commit()
        await self.db.refresh(bot_instance)
        await self.db.refresh(grid_config)

        return bot_instance, grid_config

    # ===== 통계 업데이트 =====

    async def decrement_active_user(self, template_id: int, investment_amount: Decimal):
        """봇 종료 시 활성 사용자 감소"""
        template = await self.get_template_by_id(template_id)
        if template and template.active_users > 0:
            template.active_users -= 1
            current_funds = Decimal(str(template.total_funds_in_use or 0))
            template.total_funds_in_use = max(
                Decimal("0"), current_funds - investment_amount
            )
            await self.db.commit()

    # ===== 백테스트 결과 저장 =====

    async def save_backtest_result(
        self,
        template_id: int,
        roi_30d: Decimal,
        max_drawdown: Decimal,
        total_trades: int,
        win_rate: Decimal,
        roi_history: List[float],
    ) -> Optional[GridBotTemplate]:
        """백테스트 결과 저장"""
        from datetime import datetime

        template = await self.get_template_by_id(template_id)
        if not template:
            return None

        template.backtest_roi_30d = roi_30d
        template.backtest_max_drawdown = max_drawdown
        template.backtest_total_trades = total_trades
        template.backtest_win_rate = win_rate
        template.backtest_roi_history = roi_history
        template.backtest_updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(template)
        return template

    # ===== Helper 함수 =====

    def _calculate_per_grid_amount(
        self, total_investment: Decimal, grid_count: int, leverage: int
    ) -> Decimal:
        """그리드당 투자금액 계산"""
        return (total_investment * leverage) / grid_count

    def _calculate_grid_prices(
        self,
        lower_price: Decimal,
        upper_price: Decimal,
        grid_count: int,
        grid_mode: GridMode,
    ) -> List[Decimal]:
        """그리드 가격 배열 계산"""
        prices = []
        lower = Decimal(str(lower_price))
        upper = Decimal(str(upper_price))

        if grid_mode == GridMode.ARITHMETIC:
            # 등차 방식
            step = (upper - lower) / (grid_count - 1)
            for i in range(grid_count):
                prices.append(lower + (step * i))
        else:
            # 등비 방식
            ratio = math.pow(float(upper / lower), 1 / (grid_count - 1))
            for i in range(grid_count):
                prices.append(lower * Decimal(str(pow(ratio, i))))

        return prices
