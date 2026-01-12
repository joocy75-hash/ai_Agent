from fastapi import APIRouter, Depends

from ..utils.auth_dependencies import require_admin
from ..utils.crypto_secrets import CryptoError, decrypt_secret, encrypt_secret, get_fernet

router = APIRouter(prefix="/admin/system", tags=["admin_diagnostics"])


def _build_encryption_info() -> dict:
    """암호화 상태 정보를 담은 기본 딕셔너리를 생성합니다.

    암호화 헬스체크에 사용되는 초기 상태 딕셔너리를 반환합니다.
    모든 값은 기본적으로 False로 설정되며, 실제 검증 과정에서
    각 항목이 True로 업데이트됩니다.

    Returns:
        dict: 암호화 상태 정보를 담은 딕셔너리.
            - enabled (bool): 암호화 기능 활성화 여부. 기본값 False.
            - fernet_init (bool): Fernet 암호화 객체 초기화 성공 여부. 기본값 False.
            - round_trip_ok (bool): 암호화/복호화 라운드트립 테스트 성공 여부. 기본값 False.

    Example:
        >>> info = _build_encryption_info()
        >>> info
        {'enabled': False, 'fernet_init': False, 'round_trip_ok': False}
    """
    return {"enabled": False, "fernet_init": False, "round_trip_ok": False}


@router.get("/diagnostics/encryption")
async def encryption_health(admin_id: int = Depends(require_admin)):
    info = _build_encryption_info()
    try:
        _ = get_fernet()
        info["enabled"] = True
        token = encrypt_secret("health-check")
        decrypted = decrypt_secret(token)
        info["fernet_init"] = True
        success = decrypted == "health-check"
        info["round_trip_ok"] = success
        status = "ok" if success else "error"
        return {"status": status, "encryption": info}
    except CryptoError as error:
        return {"status": "error", "encryption": info, "detail": str(error)}
