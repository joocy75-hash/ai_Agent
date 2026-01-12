"""
파일 업로드 검증 유틸리티

파일 업로드 시 보안과 안정성을 위한 검증 기능을 제공합니다.
"""
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Set

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select

# Optional magic import for MIME type detection
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class FileValidationRules:
    """파일 검증 규칙"""

    # 파일 크기 제한 (바이트 단위)
    MAX_CSV_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB

    # 허용된 확장자
    ALLOWED_CSV_EXTENSIONS = {'.csv', '.txt'}
    ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif'}

    # MIME 타입
    ALLOWED_CSV_MIME_TYPES = {
        'text/csv',
        'text/plain',
        'application/csv',
        'application/vnd.ms-excel'
    }
    ALLOWED_IMAGE_MIME_TYPES = {
        'image/jpeg',
        'image/png',
        'image/gif'
    }


async def validate_csv_upload(
    file: UploadFile,
    max_size: int = FileValidationRules.MAX_CSV_SIZE
) -> None:
    """
    CSV 파일 업로드 검증

    Args:
        file: FastAPI UploadFile 객체
        max_size: 최대 파일 크기 (바이트)

    Raises:
        HTTPException: 검증 실패 시
    """
    # 파일 확장자 검증
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in FileValidationRules.ALLOWED_CSV_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension. Allowed: {', '.join(FileValidationRules.ALLOWED_CSV_EXTENSIONS)}"
        )

    # 파일 크기 검증
    contents = await file.read()
    file_size = len(contents)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty"
        )

    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size ({max_size / 1024 / 1024:.1f}MB)"
        )

    # MIME 타입 검증 (python-magic 사용)
    if HAS_MAGIC:
        try:
            mime_type = magic.from_buffer(contents, mime=True)
            if mime_type not in FileValidationRules.ALLOWED_CSV_MIME_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid file type. Expected CSV, got {mime_type}"
                )
        except ImportError:
            # magic 라이브러리 사용 불가능한 경우 경고만 출력
            pass
        except Exception:
            pass

    # 파일 포인터를 처음으로 되돌림
    await file.seek(0)


async def validate_image_upload(
    file: UploadFile,
    max_size: int = FileValidationRules.MAX_IMAGE_SIZE
) -> None:
    """
    이미지 파일 업로드 검증

    Args:
        file: FastAPI UploadFile 객체
        max_size: 최대 파일 크기 (바이트)

    Raises:
        HTTPException: 검증 실패 시
    """
    # 파일 확장자 검증
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in FileValidationRules.ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension. Allowed: {', '.join(FileValidationRules.ALLOWED_IMAGE_EXTENSIONS)}"
        )

    # 파일 크기 검증
    contents = await file.read()
    file_size = len(contents)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty"
        )

    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size ({max_size / 1024 / 1024:.1f}MB)"
        )

    # MIME 타입 검증
    if HAS_MAGIC:
        try:
            mime_type = magic.from_buffer(contents, mime=True)
            if mime_type not in FileValidationRules.ALLOWED_IMAGE_MIME_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid file type. Expected image, got {mime_type}"
                )
        except ImportError:
            # magic 라이브러리 사용 불가능한 경우 경고만 출력
            pass
        except Exception:
            pass

    # 파일 포인터를 처음으로 되돌림
    await file.seek(0)


def sanitize_filename(filename: str) -> str:
    """
    안전한 파일명 생성

    Path Traversal 공격 방지를 위해 위험한 문자 제거

    Args:
        filename: 원본 파일명

    Returns:
        안전한 파일명
    """
    # 경로 구분자 제거
    filename = os.path.basename(filename)

    # 위험한 문자 제거
    dangerous_chars = ['..', '/', '\\', '\0', '<', '>', ':', '"', '|', '?', '*']
    for char in dangerous_chars:
        filename = filename.replace(char, '_')

    # 공백을 언더스코어로 변경
    filename = filename.replace(' ', '_')

    # 최대 길이 제한 (확장자 포함 255자)
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext

    return filename


def validate_file_path_security(file_path: Path, allowed_base_dirs: Set[Path]) -> None:
    """
    파일 경로 보안 검증

    Path Traversal 공격 방지: 허용된 디렉토리 내에만 파일 저장 가능

    Args:
        file_path: 검증할 파일 경로
        allowed_base_dirs: 허용된 기본 디렉토리 집합

    Raises:
        HTTPException: 보안 위반 시
    """
    try:
        resolved_path = file_path.resolve()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        ) from e

    # 허용된 디렉토리 내에 있는지 확인
    is_allowed = any(
        resolved_path.is_relative_to(base_dir.resolve())
        for base_dir in allowed_base_dirs
    )

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="File path is outside allowed directories"
        )


async def save_upload_file(
    file: UploadFile,
    destination_dir: Path,
    allowed_extensions: Optional[Set[str]] = None
) -> Path:
    """
    업로드 파일을 안전하게 저장

    Args:
        file: FastAPI UploadFile 객체
        destination_dir: 저장할 디렉토리
        allowed_extensions: 허용된 확장자 집합 (None이면 모두 허용)

    Returns:
        저장된 파일의 경로

    Raises:
        HTTPException: 검증 실패 또는 저장 실패 시
    """
    # 파일명 안전하게 처리
    safe_filename = sanitize_filename(file.filename)

    # 확장자 검증
    if allowed_extensions:
        file_ext = Path(safe_filename).suffix.lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file extension. Allowed: {', '.join(allowed_extensions)}"
            )

    # 대상 디렉토리 생성
    destination_dir.mkdir(parents=True, exist_ok=True)

    # 파일 경로 생성
    file_path = destination_dir / safe_filename

    # 프로젝트 루트 기준으로 허용된 디렉토리 검증
    project_root = Path(__file__).parent.parent.parent
    allowed_dirs = {
        project_root / "data",
        project_root / "backtest_data",
        project_root / "uploads"
    }
    validate_file_path_security(file_path, allowed_dirs)

    # 파일 저장
    try:
        contents = await file.read()
        with open(file_path, 'wb') as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        ) from e
    finally:
        await file.seek(0)

    return file_path


class UploadQuotaManager:
    """
    업로드 쿼터 관리자

    사용자별 및 전역 업로드 쿼터를 관리합니다.
    - 사용자당 최대 100MB
    - 사용자당 최대 50개 파일
    - 전역 최대 100GB
    """

    MAX_PER_USER_MB: int = 100  # 100MB per user
    MAX_TOTAL_STORAGE_GB: int = 100  # 100GB total
    MAX_FILES_PER_USER: int = 50

    async def check_user_quota(
        self,
        user_id: int,
        file_size_bytes: int,
        db: "AsyncSession"
    ) -> tuple[bool, str]:
        """
        사용자 쿼터 확인

        Args:
            user_id: 사용자 ID
            file_size_bytes: 업로드할 파일 크기 (바이트)
            db: 데이터베이스 세션

        Returns:
            (허용 여부, 메시지) 튜플
        """
        from ..database.models import UserFile

        # 현재 사용량 조회
        result = await db.execute(
            select(
                func.coalesce(func.sum(UserFile.file_size_bytes), 0).label("total_bytes"),
                func.count(UserFile.id).label("file_count")
            ).where(UserFile.user_id == user_id)
        )
        row = result.first()
        current_bytes = int(row.total_bytes) if row else 0
        file_count = int(row.file_count) if row else 0

        max_bytes = self.MAX_PER_USER_MB * 1024 * 1024

        # 파일 개수 제한 확인
        if file_count >= self.MAX_FILES_PER_USER:
            return False, f"File count limit exceeded. Maximum: {self.MAX_FILES_PER_USER} files"

        # 용량 제한 확인
        if current_bytes + file_size_bytes > max_bytes:
            used_mb = current_bytes / (1024 * 1024)
            return False, f"Storage quota exceeded. Used: {used_mb:.1f}MB, Limit: {self.MAX_PER_USER_MB}MB"

        return True, "OK"

    async def check_global_quota(
        self,
        file_size_bytes: int,
        db: "AsyncSession"
    ) -> tuple[bool, str]:
        """
        전역 스토리지 쿼터 확인

        Args:
            file_size_bytes: 업로드할 파일 크기 (바이트)
            db: 데이터베이스 세션

        Returns:
            (허용 여부, 메시지) 튜플
        """
        from ..database.models import UserFile

        # 전체 사용량 조회
        result = await db.execute(
            select(func.coalesce(func.sum(UserFile.file_size_bytes), 0))
        )
        current_bytes = int(result.scalar() or 0)

        max_bytes = self.MAX_TOTAL_STORAGE_GB * 1024 * 1024 * 1024

        if current_bytes + file_size_bytes > max_bytes:
            used_gb = current_bytes / (1024 * 1024 * 1024)
            return False, f"Global storage quota exceeded. Used: {used_gb:.1f}GB, Limit: {self.MAX_TOTAL_STORAGE_GB}GB"

        return True, "OK"

    async def get_user_usage(
        self,
        user_id: int,
        db: "AsyncSession"
    ) -> dict:
        """
        사용자 사용량 통계 조회

        Args:
            user_id: 사용자 ID
            db: 데이터베이스 세션

        Returns:
            사용량 통계 딕셔너리
        """
        from ..database.models import UserFile

        result = await db.execute(
            select(
                func.coalesce(func.sum(UserFile.file_size_bytes), 0).label("total_bytes"),
                func.count(UserFile.id).label("file_count")
            ).where(UserFile.user_id == user_id)
        )
        row = result.first()

        used_bytes = int(row.total_bytes) if row else 0
        file_count = int(row.file_count) if row else 0

        return {
            "used_bytes": used_bytes,
            "file_count": file_count,
            "quota_bytes": self.MAX_PER_USER_MB * 1024 * 1024,
            "quota_files": self.MAX_FILES_PER_USER,
            "used_percent": (used_bytes / (self.MAX_PER_USER_MB * 1024 * 1024)) * 100 if self.MAX_PER_USER_MB > 0 else 0
        }


# 싱글톤 인스턴스
upload_quota_manager = UploadQuotaManager()
