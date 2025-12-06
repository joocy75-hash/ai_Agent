import os
import uuid
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from ..utils.jwt_auth import get_current_user_id

router = APIRouter(prefix="/upload", tags=["upload"])

# 업로드 디렉토리 설정
UPLOAD_DIR = Path(__file__).parent.parent.parent / "backtest_data"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/csv")
async def upload_csv(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
):
    """
    CSV 파일 업로드

    Args:
        file: 업로드할 CSV 파일

    Returns:
        file_path: 저장된 파일의 경로
    """
    # CSV 파일 확인
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="CSV 파일만 업로드 가능합니다")

    # 고유한 파일명 생성
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = UPLOAD_DIR / unique_filename

    # 파일 저장
    try:
        contents = await file.read()
        with open(file_path, 'wb') as f:
            f.write(contents)

        return {
            "message": "파일 업로드 성공",
            "file_path": str(file_path),
            "filename": unique_filename
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"파일 저장 실패: {str(e)}"
        )
