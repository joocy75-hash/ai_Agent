"""
2FA (Two-Factor Authentication) API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.db import get_session
from ..database.models import User
from ..services.totp_service import totp_service
from ..utils.jwt_auth import get_current_user_id

router = APIRouter(prefix="/auth/2fa", tags=["2fa"])


# ========== 스키마 ==========


class Setup2FAResponse(BaseModel):
    """2FA 설정 응답"""

    secret: str  # 수동 입력용 시크릿
    qr_code: str  # QR 코드 이미지 (Base64 데이터 URI)
    backup_codes: list[str]  # 백업 코드


class Verify2FARequest(BaseModel):
    """2FA 검증 요청"""

    code: str  # 6자리 TOTP 코드


class Disable2FARequest(BaseModel):
    """2FA 비활성화 요청"""

    code: str  # 확인용 TOTP 코드
    password: str  # 비밀번호 확인


class Status2FAResponse(BaseModel):
    """2FA 상태 응답"""

    is_enabled: bool
    email: str


# ========== 엔드포인트 ==========


@router.get("/status", response_model=Status2FAResponse)
async def get_2fa_status(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    현재 사용자의 2FA 상태 조회

    Returns:
        is_enabled: 2FA 활성화 여부
        email: 사용자 이메일
    """
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다"
        )

    return Status2FAResponse(is_enabled=user.is_2fa_enabled, email=user.email)


@router.post("/setup", response_model=Setup2FAResponse)
async def setup_2fa(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    2FA 설정 시작 - QR 코드와 시크릿 발급

    주의: 이 단계에서는 2FA가 활성화되지 않습니다.
    /verify 엔드포인트로 코드를 검증해야 활성화됩니다.

    Returns:
        secret: 수동 입력용 시크릿 (앱에서 QR 스캔이 안 될 때 사용)
        qr_code: QR 코드 이미지 (Base64 데이터 URI)
        backup_codes: 백업 코드 목록 (안전하게 보관해야 함)
    """
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다"
        )

    if user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA가 이미 활성화되어 있습니다. 먼저 비활성화하세요.",
        )

    # 2FA 설정 생성
    secret, encrypted_secret, qr_code = totp_service.setup_2fa(user.email)
    backup_codes = totp_service.generate_backup_codes()

    # 시크릿을 임시로 저장 (나중에 verify에서 활성화)
    user.totp_secret = encrypted_secret
    await session.commit()

    return Setup2FAResponse(secret=secret, qr_code=qr_code, backup_codes=backup_codes)


@router.post("/verify")
async def verify_and_enable_2fa(
    payload: Verify2FARequest,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    2FA 코드 검증 및 활성화

    /setup에서 받은 QR 코드를 인증 앱으로 스캔한 후,
    앱에서 표시되는 6자리 코드를 입력하세요.

    Args:
        code: 인증 앱에서 표시되는 6자리 코드

    Returns:
        성공 메시지
    """
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다"
        )

    if not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="먼저 /setup을 호출하여 2FA를 설정하세요",
        )

    if user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA가 이미 활성화되어 있습니다",
        )

    # 시크릿 복호화 및 코드 검증
    secret = totp_service.decrypt_secret(user.totp_secret)
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="시크릿 복호화 실패",
        )

    if not totp_service.verify_totp(secret, payload.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 2FA 코드입니다. 다시 시도하세요.",
        )

    # 2FA 활성화
    user.is_2fa_enabled = True
    await session.commit()

    return {"message": "2FA가 성공적으로 활성화되었습니다"}


@router.post("/disable")
async def disable_2fa(
    payload: Disable2FARequest,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    2FA 비활성화

    보안을 위해 현재 비밀번호와 2FA 코드 모두 필요합니다.

    Args:
        code: 인증 앱에서 표시되는 6자리 코드
        password: 현재 비밀번호

    Returns:
        성공 메시지
    """
    from ..utils.jwt_auth import JWTAuth

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다"
        )

    if not user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA가 활성화되어 있지 않습니다",
        )

    # 비밀번호 확인
    if not JWTAuth.verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비밀번호가 올바르지 않습니다",
        )

    # 2FA 코드 검증
    secret = totp_service.decrypt_secret(user.totp_secret)
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="시크릿 복호화 실패",
        )

    if not totp_service.verify_totp(secret, payload.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 2FA 코드입니다",
        )

    # 2FA 비활성화
    user.is_2fa_enabled = False
    user.totp_secret = None
    await session.commit()

    return {"message": "2FA가 비활성화되었습니다"}


@router.post("/validate")
async def validate_2fa_code(
    payload: Verify2FARequest,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    2FA 코드 유효성 검사 (민감한 작업 전 확인용)

    Args:
        code: 6자리 TOTP 코드

    Returns:
        valid: 코드 유효 여부
    """
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_2fa_enabled or not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA가 활성화되어 있지 않습니다",
        )

    secret = totp_service.decrypt_secret(user.totp_secret)
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="시크릿 복호화 실패",
        )

    is_valid = totp_service.verify_totp(secret, payload.code)

    return {"valid": is_valid}
