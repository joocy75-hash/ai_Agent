from fastapi import APIRouter, Depends

from ..utils.crypto_secrets import CryptoError, decrypt_secret, encrypt_secret, get_fernet
from ..utils.auth_dependencies import require_admin

router = APIRouter(prefix="/admin/system", tags=["admin_diagnostics"])


def _build_encryption_info() -> dict:
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
