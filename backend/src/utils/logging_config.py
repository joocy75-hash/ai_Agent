"""
로깅 설정

프로젝트 전체에서 사용할 표준 로깅 설정입니다.
"""
import logging
import sys
from pathlib import Path
from typing import Optional

# 로그 레벨
LOG_LEVEL = logging.INFO

# 로그 포맷
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DETAILED_LOG_FORMAT = (
    "%(asctime)s - %(name)s - %(levelname)s - "
    "%(filename)s:%(lineno)d - %(funcName)s - %(message)s"
)


def setup_logging(
    log_level: int = LOG_LEVEL,
    log_file: Optional[Path] = None,
    detailed: bool = False,
) -> None:
    """
    로깅 시스템 설정

    Args:
        log_level: 로그 레벨 (logging.INFO, logging.DEBUG, 등)
        log_file: 로그 파일 경로 (None이면 파일 로깅 안함)
        detailed: True면 상세한 로그 포맷 사용

    Example:
        setup_logging(
            log_level=logging.DEBUG,
            log_file=Path("logs/app.log"),
            detailed=True
        )
    """
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 포맷터
    formatter = logging.Formatter(
        DETAILED_LOG_FORMAT if detailed else LOG_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 파일 핸들러 (옵션)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)

    root_logger.info(f"Logging configured (level={logging.getLevelName(log_level)})")


# 개발 환경용 간편 설정
def setup_dev_logging():
    """개발 환경용 로깅 (상세 모드)"""
    setup_logging(
        log_level=logging.DEBUG,
        detailed=True,
    )


# 프로덕션 환경용 간편 설정
def setup_prod_logging(log_dir: Path = Path("logs")):
    """프로덕션 환경용 로깅 (파일 저장)"""
    setup_logging(
        log_level=logging.INFO,
        log_file=log_dir / "app.log",
        detailed=False,
    )
