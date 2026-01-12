"""
TOTP (Time-based One-Time Password) 2FA 서비스

Google Authenticator, Microsoft Authenticator 등의 앱과 호환됩니다.
"""

import base64
import io
import logging
import os
from typing import Optional, Tuple

import pyotp
import qrcode
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class TOTPService:
    """TOTP 2FA 관리 서비스"""

    def __init__(self):
        # 암호화 키 로드 (API 키 암호화와 동일한 키 사용)
        self.encryption_key = os.environ.get("ENCRYPTION_KEY", "")
        if self.encryption_key:
            try:
                self.fernet = Fernet(self.encryption_key.encode())
            except Exception as e:
                logger.error(f"Failed to initialize Fernet: {e}")
                self.fernet = None
        else:
            logger.warning(
                "ENCRYPTION_KEY not set, TOTP secrets will be stored unencrypted"
            )
            self.fernet = None

    def generate_secret(self) -> str:
        """
        새 TOTP 시크릿 생성

        Returns:
            Base32 인코딩된 시크릿 문자열
        """
        return pyotp.random_base32()

    def encrypt_secret(self, secret: str) -> str:
        """
        TOTP 시크릿 암호화

        Args:
            secret: 평문 시크릿

        Returns:
            암호화된 시크릿 (또는 암호화 실패 시 평문)
        """
        if self.fernet:
            try:
                return self.fernet.encrypt(secret.encode()).decode()
            except Exception as e:
                logger.error(f"Failed to encrypt TOTP secret: {e}")
                return secret
        return secret

    def decrypt_secret(self, encrypted_secret: str) -> Optional[str]:
        """
        TOTP 시크릿 복호화

        Args:
            encrypted_secret: 암호화된 시크릿

        Returns:
            복호화된 시크릿 문자열 (또는 실패 시 None)
        """
        if self.fernet:
            try:
                return self.fernet.decrypt(encrypted_secret.encode()).decode()
            except InvalidToken:
                # 암호화되지 않은 레거시 데이터일 수 있음
                logger.warning("TOTP secret may not be encrypted, using as-is")
                return encrypted_secret
            except Exception as e:
                logger.error(f"Failed to decrypt TOTP secret: {e}")
                return None
        return encrypted_secret

    def get_totp_uri(self, secret: str, email: str, issuer: str = "DeepSignal") -> str:
        """
        TOTP QR 코드용 URI 생성

        Args:
            secret: TOTP 시크릿
            email: 사용자 이메일
            issuer: 앱 발급자 이름

        Returns:
            otpauth:// URI 문자열
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=issuer)

    def generate_qr_code(self, uri: str) -> str:
        """
        TOTP URI를 QR 코드 이미지로 변환

        Args:
            uri: otpauth:// URI

        Returns:
            Base64 인코딩된 PNG 이미지 데이터 URI
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # 이미지를 Base64로 변환
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return f"data:image/png;base64,{img_str}"

    def verify_totp(self, secret: str, code: str, window: int = 1) -> bool:
        """
        TOTP 코드 검증

        Args:
            secret: TOTP 시크릿
            code: 사용자가 입력한 6자리 코드
            window: 허용할 시간 윈도우 (각 방향으로 30초 * window)

        Returns:
            검증 성공 여부
        """
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(code, valid_window=window)
        except Exception as e:
            logger.error(f"TOTP verification failed: {e}")
            return False

    def setup_2fa(self, email: str) -> Tuple[str, str, str]:
        """
        2FA 설정 시작 - 시크릿과 QR 코드 생성

        Args:
            email: 사용자 이메일

        Returns:
            (시크릿, 암호화된_시크릿, QR코드_데이터_URI) 튜플
        """
        secret = self.generate_secret()
        encrypted_secret = self.encrypt_secret(secret)
        uri = self.get_totp_uri(secret, email)
        qr_code = self.generate_qr_code(uri)

        return secret, encrypted_secret, qr_code

    def generate_backup_codes(self, count: int = 8) -> list:
        """
        백업 코드 생성 (2FA 접근 불가 시 사용)

        Args:
            count: 생성할 백업 코드 수

        Returns:
            백업 코드 목록
        """
        import secrets

        codes = []
        for _ in range(count):
            # 8자리 숫자 코드 생성
            code = "".join(str(secrets.randbelow(10)) for _ in range(8))
            # 가독성을 위해 4자리씩 분리
            formatted_code = f"{code[:4]}-{code[4:]}"
            codes.append(formatted_code)
        return codes


# 싱글톤 인스턴스
totp_service = TOTPService()
