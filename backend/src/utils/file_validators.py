"""
파일 업로드 검증 유틸리티

파일 업로드 시 보안과 안정성을 위한 검증 기능을 제공합니다.
"""
import os
import magic
from pathlib import Path
from typing import Optional, Set
from fastapi import UploadFile, HTTPException, status


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
    try:
        mime_type = magic.from_buffer(contents, mime=True)
        if mime_type not in FileValidationRules.ALLOWED_CSV_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Expected CSV, got {mime_type}"
            )
    except Exception as e:
        # magic 라이브러리 사용 불가능한 경우 경고만 출력
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
    try:
        mime_type = magic.from_buffer(contents, mime=True)
        if mime_type not in FileValidationRules.ALLOWED_IMAGE_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Expected image, got {mime_type}"
            )
    except Exception as e:
        # magic 라이브러리 사용 불가능한 경우 경고만 출력
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
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        )

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
        )
    finally:
        await file.seek(0)

    return file_path
