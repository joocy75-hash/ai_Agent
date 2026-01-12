import logging
import re
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import UserFile
from ..database.db import get_session
from ..middleware.rate_limit_improved import EndpointRateLimiter
from ..utils.file_validators import upload_quota_manager
from ..utils.jwt_auth import get_current_user_id

# Optional magic import for MIME type detection
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

router = APIRouter(prefix="/upload", tags=["upload"])
logger = logging.getLogger(__name__)

# 업로드 디렉토리 설정
UPLOAD_DIR = Path(__file__).parent.parent.parent / "backtest_data"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# SECURITY: 파일 업로드 보안 설정
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB 제한
MIN_FREE_DISK_SPACE = 100 * 1024 * 1024  # 최소 100MB 디스크 여유 공간 필요
ALLOWED_MIME_TYPES = {"text/csv", "application/csv", "text/plain"}
ALLOWED_EXTENSIONS = {".csv"}

# Rate Limiter: 시간당 10개 파일
upload_rate_limiter = EndpointRateLimiter(limit=10, window=3600, name="file_upload")


def sanitize_filename(filename: str) -> str:
    """파일명에서 보안 위험이 있는 문자를 제거합니다.

    업로드된 파일의 원본 파일명에서 경로 탐색(path traversal) 공격이나
    시스템 명령 주입에 사용될 수 있는 위험한 문자들을 제거하거나
    안전한 문자로 대체합니다.

    Args:
        filename: 정제할 원본 파일명 문자열. 사용자가 업로드한 파일의
            원래 이름으로, 악의적인 문자가 포함될 수 있습니다.

    Returns:
        str: 안전하게 정제된 파일명.
            - 영문자, 숫자, 하이픈(-), 언더스코어(_), 점(.)만 허용
            - 그 외 모든 문자는 언더스코어(_)로 대체됨
            - 연속된 점(..)은 언더스코어로 대체되어 경로 탐색 방지

    Examples:
        >>> sanitize_filename("../../../etc/passwd")
        '______etc_passwd'
        >>> sanitize_filename("my file (1).csv")
        'my_file__1_.csv'
        >>> sanitize_filename("data_2024-01-15.csv")
        'data_2024-01-15.csv'

    Security:
        - 경로 구분자 (/, \\) 제거로 디렉토리 탐색 방지
        - 특수문자 제거로 명령 주입 방지
        - '..' 패턴 제거로 상위 디렉토리 접근 방지
    """
    # 경로 구분자 및 특수문자 제거
    safe_name = re.sub(r'[^\w\-_\.]', '_', filename)
    # 경로 traversal 방지
    safe_name = safe_name.replace('..', '_')
    return safe_name


@router.post("/csv")
async def upload_csv(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session),
):
    """
    CSV 파일 업로드 (보안 강화)

    Args:
        file: 업로드할 CSV 파일 (최대 10MB)

    Returns:
        file_path: 저장된 파일의 경로
    """
    # SECURITY: Rate Limit 체크
    try:
        upload_rate_limiter.check(user_id)
    except Exception as e:
        logger.warning(f"[SECURITY] Upload rate limit exceeded for user {user_id}")
        raise HTTPException(status_code=429, detail=str(e)) from e

    # SECURITY: 디스크 공간 확인
    try:
        disk_stat = shutil.disk_usage(UPLOAD_DIR)
        if disk_stat.free < MIN_FREE_DISK_SPACE:
            logger.error(f"[SECURITY] Insufficient disk space: {disk_stat.free} bytes free")
            raise HTTPException(status_code=507, detail="서버 저장 공간이 부족합니다")
    except OSError as e:
        logger.error(f"[SECURITY] Disk space check failed: {e}")

    # SECURITY: 파일 확장자 검증
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일명이 없습니다")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        logger.warning(f"[SECURITY] Blocked file upload with extension: {file_ext}")
        raise HTTPException(status_code=400, detail="CSV 파일만 업로드 가능합니다")

    # SECURITY: MIME type 검증 (필수)
    if not file.content_type or file.content_type not in ALLOWED_MIME_TYPES:
        logger.warning(f"[SECURITY] Blocked file upload with MIME type: {file.content_type}")
        raise HTTPException(status_code=400, detail="허용되지 않는 파일 형식입니다")

    # SECURITY: 파일 크기 제한 (스트리밍 방식으로 읽기)
    try:
        contents = await file.read()
        file_size = len(contents)

        if file_size > MAX_UPLOAD_SIZE:
            logger.warning(f"[SECURITY] Blocked large file upload: {file_size} bytes")
            raise HTTPException(
                status_code=413,
                detail=f"파일 크기가 너무 큽니다. 최대 {MAX_UPLOAD_SIZE // (1024*1024)}MB까지 허용됩니다"
            )

        # SECURITY: 사용자별 쿼터 확인 (데이터베이스 기반)
        allowed, message = await upload_quota_manager.check_user_quota(user_id, file_size, db)
        if not allowed:
            logger.warning(f"[SECURITY] User {user_id} quota exceeded: {message}")
            raise HTTPException(status_code=413, detail=message)

        # SECURITY: 전역 스토리지 쿼터 확인
        allowed, message = await upload_quota_manager.check_global_quota(file_size, db)
        if not allowed:
            logger.warning(f"[SECURITY] Global storage quota exceeded: {message}")
            raise HTTPException(status_code=413, detail=message)

        # SECURITY: CSV 내용 기본 검증 (첫 줄이 유효한 CSV 헤더인지)
        try:
            first_lines = contents[:1024].decode('utf-8', errors='ignore')
            if '\x00' in first_lines:  # 바이너리 파일 감지
                raise HTTPException(status_code=400, detail="유효한 CSV 파일이 아닙니다")
        except UnicodeDecodeError as e:
            raise HTTPException(status_code=400, detail="유효한 텍스트 파일이 아닙니다") from e

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File read error: {e}")
        raise HTTPException(status_code=500, detail="파일 읽기 실패") from e

    # SECURITY: 안전한 파일명 생성
    safe_filename = sanitize_filename(file.filename)
    unique_filename = f"{uuid.uuid4()}_{safe_filename}"
    file_path = UPLOAD_DIR / unique_filename

    # 파일 저장
    try:
        with open(file_path, 'wb') as f:
            f.write(contents)

        # MIME 타입 감지
        mime_type = file.content_type
        if HAS_MAGIC:
            try:
                mime_type = magic.from_buffer(contents[:1024], mime=True)
            except Exception:
                pass

        # 데이터베이스에 파일 정보 저장
        user_file = UserFile(
            user_id=user_id,
            filename=safe_filename,
            file_size_bytes=file_size,
            file_path=str(file_path),
            mime_type=mime_type,
        )
        db.add(user_file)
        await db.commit()

        # 사용자 사용량 조회
        usage = await upload_quota_manager.get_user_usage(user_id, db)

        logger.info(f"File uploaded successfully: {unique_filename} ({file_size} bytes) by user {user_id}")
        return {
            "message": "파일 업로드 성공",
            "file_path": str(file_path),
            "filename": unique_filename,
            "size": file_size,
            "remaining_quota": usage["quota_bytes"] - usage["used_bytes"],
            "file_count": usage["file_count"],
            "max_files": usage["quota_files"],
        }

    except Exception as e:
        logger.error(f"File save error: {e}")
        # 파일이 저장되었다면 삭제
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=500,
            detail="파일 저장 실패"
        ) from e
