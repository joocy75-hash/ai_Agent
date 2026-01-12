"""
Chart Annotations API endpoints

차트에 사용자 정의 어노테이션(메모, 선, 도형 등)을 추가/수정/삭제하는 API
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.db import get_session
from ..database.models import AnnotationType as DBAnnotationType
from ..database.models import ChartAnnotation
from ..schemas.annotation_schema import (
    AnnotationCreateRequest,
    AnnotationDeleteResponse,
    AnnotationListResponse,
    AnnotationResponse,
    AnnotationUpdateRequest,
)
from ..utils.jwt_auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/annotations", tags=["annotations"])


def _annotation_to_response(annotation: ChartAnnotation) -> AnnotationResponse:
    """ChartAnnotation DB 모델을 API 응답 스키마로 변환합니다.

    데이터베이스에서 조회한 ChartAnnotation ORM 객체를 클라이언트에
    반환할 AnnotationResponse Pydantic 스키마로 변환합니다.
    datetime 필드는 Unix timestamp로, Decimal은 float로 변환합니다.

    Args:
        annotation: ChartAnnotation ORM 모델 인스턴스. 차트 어노테이션의
            모든 정보를 포함합니다:
            - id, user_id, symbol: 식별 정보
            - annotation_type: 어노테이션 유형 (Enum)
            - label, text: 표시 텍스트
            - timestamp, start_timestamp, end_timestamp: 시간 정보 (datetime)
            - price, start_price, end_price: 가격 정보 (Decimal)
            - style: 스타일 설정 (JSON dict)
            - alert_*: 알림 관련 설정
            - is_active, is_locked: 상태 플래그
            - created_at, updated_at: 메타데이터 (datetime)

    Returns:
        AnnotationResponse: API 응답용 Pydantic 스키마 객체.
            - datetime 필드들: Unix timestamp (int)로 변환됨
            - Decimal 필드들: float로 변환됨
            - annotation_type: Enum의 value 문자열로 변환됨
    """
    return AnnotationResponse(
        id=annotation.id,
        user_id=annotation.user_id,
        symbol=annotation.symbol,
        annotation_type=annotation.annotation_type.value,
        label=annotation.label,
        text=annotation.text,
        timestamp=int(annotation.timestamp.timestamp()) if annotation.timestamp else None,
        start_timestamp=int(annotation.start_timestamp.timestamp()) if annotation.start_timestamp else None,
        end_timestamp=int(annotation.end_timestamp.timestamp()) if annotation.end_timestamp else None,
        price=float(annotation.price) if annotation.price else None,
        start_price=float(annotation.start_price) if annotation.start_price else None,
        end_price=float(annotation.end_price) if annotation.end_price else None,
        style=annotation.style,
        alert_enabled=annotation.alert_enabled,
        alert_triggered=annotation.alert_triggered,
        alert_direction=annotation.alert_direction,
        is_active=annotation.is_active,
        is_locked=annotation.is_locked,
        created_at=int(annotation.created_at.timestamp()),
        updated_at=int(annotation.updated_at.timestamp()),
    )


@router.get("/{symbol}", response_model=AnnotationListResponse)
async def get_annotations(
    symbol: str,
    include_inactive: bool = Query(default=False, description="비활성 어노테이션 포함 여부"),
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    특정 심볼의 어노테이션 목록 조회

    Args:
        symbol: 심볼 (예: BTCUSDT)
        include_inactive: 비활성 어노테이션 포함 여부

    Returns:
        어노테이션 목록
    """
    try:
        symbol = symbol.upper()

        # 쿼리 조건 설정
        conditions = [
            ChartAnnotation.user_id == user_id,
            ChartAnnotation.symbol == symbol,
        ]

        if not include_inactive:
            conditions.append(ChartAnnotation.is_active == True)

        result = await session.execute(
            select(ChartAnnotation)
            .where(and_(*conditions))
            .order_by(ChartAnnotation.created_at.desc())
        )
        annotations = result.scalars().all()

        return AnnotationListResponse(
            symbol=symbol,
            annotations=[_annotation_to_response(a) for a in annotations],
            count=len(annotations),
        )

    except Exception as e:
        logger.error(f"Error fetching annotations for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/detail/{annotation_id}", response_model=AnnotationResponse)
async def get_annotation(
    annotation_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    단일 어노테이션 조회

    Args:
        annotation_id: 어노테이션 ID

    Returns:
        어노테이션 상세 정보
    """
    try:
        result = await session.execute(
            select(ChartAnnotation).where(
                and_(
                    ChartAnnotation.id == annotation_id,
                    ChartAnnotation.user_id == user_id,
                )
            )
        )
        annotation = result.scalar_one_or_none()

        if not annotation:
            raise HTTPException(status_code=404, detail="Annotation not found")

        return _annotation_to_response(annotation)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching annotation {annotation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("", response_model=AnnotationResponse)
async def create_annotation(
    request: AnnotationCreateRequest,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    새 어노테이션 생성

    Args:
        request: 어노테이션 생성 요청

    Returns:
        생성된 어노테이션 정보
    """
    try:
        # Unix timestamp를 datetime으로 변환
        timestamp = datetime.fromtimestamp(request.timestamp) if request.timestamp else None
        start_timestamp = datetime.fromtimestamp(request.start_timestamp) if request.start_timestamp else None
        end_timestamp = datetime.fromtimestamp(request.end_timestamp) if request.end_timestamp else None

        # 어노테이션 타입 변환
        annotation_type = DBAnnotationType(request.annotation_type.value)

        annotation = ChartAnnotation(
            user_id=user_id,
            symbol=request.symbol,
            annotation_type=annotation_type,
            label=request.label,
            text=request.text,
            timestamp=timestamp,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            price=request.price,
            start_price=request.start_price,
            end_price=request.end_price,
            style=request.style or {},
            alert_enabled=request.alert_enabled,
            alert_direction=request.alert_direction,
        )

        session.add(annotation)
        await session.commit()
        await session.refresh(annotation)

        logger.info(f"Created annotation {annotation.id} for user {user_id} on {request.symbol}")

        return _annotation_to_response(annotation)

    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating annotation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/{annotation_id}", response_model=AnnotationResponse)
async def update_annotation(
    annotation_id: int,
    request: AnnotationUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    어노테이션 수정

    Args:
        annotation_id: 어노테이션 ID
        request: 수정 요청

    Returns:
        수정된 어노테이션 정보
    """
    try:
        result = await session.execute(
            select(ChartAnnotation).where(
                and_(
                    ChartAnnotation.id == annotation_id,
                    ChartAnnotation.user_id == user_id,
                )
            )
        )
        annotation = result.scalar_one_or_none()

        if not annotation:
            raise HTTPException(status_code=404, detail="Annotation not found")

        if annotation.is_locked:
            raise HTTPException(status_code=403, detail="Annotation is locked")

        # 업데이트할 필드만 적용
        update_data = request.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:
                if field in ['timestamp', 'start_timestamp', 'end_timestamp'] and value:
                    # Unix timestamp를 datetime으로 변환
                    setattr(annotation, field, datetime.fromtimestamp(value))
                else:
                    setattr(annotation, field, value)

        annotation.updated_at = datetime.utcnow()

        await session.commit()
        await session.refresh(annotation)

        logger.info(f"Updated annotation {annotation_id} for user {user_id}")

        return _annotation_to_response(annotation)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating annotation {annotation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{annotation_id}", response_model=AnnotationDeleteResponse)
async def delete_annotation(
    annotation_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    어노테이션 삭제

    Args:
        annotation_id: 어노테이션 ID

    Returns:
        삭제 결과
    """
    try:
        result = await session.execute(
            select(ChartAnnotation).where(
                and_(
                    ChartAnnotation.id == annotation_id,
                    ChartAnnotation.user_id == user_id,
                )
            )
        )
        annotation = result.scalar_one_or_none()

        if not annotation:
            raise HTTPException(status_code=404, detail="Annotation not found")

        if annotation.is_locked:
            raise HTTPException(status_code=403, detail="Annotation is locked and cannot be deleted")

        await session.delete(annotation)
        await session.commit()

        logger.info(f"Deleted annotation {annotation_id} for user {user_id}")

        return AnnotationDeleteResponse(
            success=True,
            message="Annotation deleted successfully",
            deleted_id=annotation_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting annotation {annotation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{annotation_id}/toggle", response_model=AnnotationResponse)
async def toggle_annotation_visibility(
    annotation_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    어노테이션 표시/숨김 토글

    Args:
        annotation_id: 어노테이션 ID

    Returns:
        수정된 어노테이션 정보
    """
    try:
        result = await session.execute(
            select(ChartAnnotation).where(
                and_(
                    ChartAnnotation.id == annotation_id,
                    ChartAnnotation.user_id == user_id,
                )
            )
        )
        annotation = result.scalar_one_or_none()

        if not annotation:
            raise HTTPException(status_code=404, detail="Annotation not found")

        annotation.is_active = not annotation.is_active
        annotation.updated_at = datetime.utcnow()

        await session.commit()
        await session.refresh(annotation)

        status = "visible" if annotation.is_active else "hidden"
        logger.info(f"Toggled annotation {annotation_id} to {status} for user {user_id}")

        return _annotation_to_response(annotation)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error toggling annotation {annotation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{annotation_id}/lock", response_model=AnnotationResponse)
async def toggle_annotation_lock(
    annotation_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    어노테이션 잠금/잠금해제 토글

    Args:
        annotation_id: 어노테이션 ID

    Returns:
        수정된 어노테이션 정보
    """
    try:
        result = await session.execute(
            select(ChartAnnotation).where(
                and_(
                    ChartAnnotation.id == annotation_id,
                    ChartAnnotation.user_id == user_id,
                )
            )
        )
        annotation = result.scalar_one_or_none()

        if not annotation:
            raise HTTPException(status_code=404, detail="Annotation not found")

        annotation.is_locked = not annotation.is_locked
        annotation.updated_at = datetime.utcnow()

        await session.commit()
        await session.refresh(annotation)

        status = "locked" if annotation.is_locked else "unlocked"
        logger.info(f"Toggled annotation {annotation_id} to {status} for user {user_id}")

        return _annotation_to_response(annotation)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error toggling lock for annotation {annotation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{annotation_id}/reset-alert", response_model=AnnotationResponse)
async def reset_alert(
    annotation_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    가격 알림 리셋 (다시 트리거 가능하도록)

    Args:
        annotation_id: 어노테이션 ID

    Returns:
        수정된 어노테이션 정보
    """
    try:
        result = await session.execute(
            select(ChartAnnotation).where(
                and_(
                    ChartAnnotation.id == annotation_id,
                    ChartAnnotation.user_id == user_id,
                )
            )
        )
        annotation = result.scalar_one_or_none()

        if not annotation:
            raise HTTPException(status_code=404, detail="Annotation not found")

        if annotation.annotation_type.value != "price_level":
            raise HTTPException(status_code=400, detail="Only price_level annotations can have alerts reset")

        # 알림 리셋
        annotation.alert_triggered = False
        annotation.updated_at = datetime.utcnow()

        await session.commit()
        await session.refresh(annotation)

        # price_alert_service에도 리셋 알림
        try:
            from ..services.price_alert_service import price_alert_service
            await price_alert_service.reset_alert(annotation_id)
        except Exception as e:
            logger.warning(f"Failed to notify price_alert_service: {e}")

        logger.info(f"Reset alert for annotation {annotation_id} by user {user_id}")

        return _annotation_to_response(annotation)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error resetting alert for annotation {annotation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/symbol/{symbol}", response_model=dict)
async def delete_all_annotations_for_symbol(
    symbol: str,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    특정 심볼의 모든 어노테이션 삭제 (잠금되지 않은 것만)

    Args:
        symbol: 심볼 (예: BTCUSDT)

    Returns:
        삭제된 어노테이션 수
    """
    try:
        symbol = symbol.upper()

        result = await session.execute(
            select(ChartAnnotation).where(
                and_(
                    ChartAnnotation.user_id == user_id,
                    ChartAnnotation.symbol == symbol,
                    ChartAnnotation.is_locked == False,
                )
            )
        )
        annotations = result.scalars().all()

        deleted_count = len(annotations)

        for annotation in annotations:
            await session.delete(annotation)

        await session.commit()

        logger.info(f"Deleted {deleted_count} annotations for {symbol} by user {user_id}")

        return {
            "success": True,
            "symbol": symbol,
            "deleted_count": deleted_count,
            "message": f"Deleted {deleted_count} annotations for {symbol}",
        }

    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting annotations for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
