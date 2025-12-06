#!/usr/bin/env python3
"""
암호화 키 생성 스크립트

이 스크립트는 API 키 암호화를 위한 Fernet 키를 생성합니다.
생성된 키를 .env 파일의 ENCRYPTION_KEY에 추가하세요.
"""

from cryptography.fernet import Fernet


def generate_encryption_key():
    """새로운 Fernet 암호화 키 생성"""
    key = Fernet.generate_key()
    return key.decode()


if __name__ == "__main__":
    key = generate_encryption_key()
    print("=" * 70)
    print("새로운 암호화 키가 생성되었습니다!")
    print("=" * 70)
    print()
    print("생성된 키:")
    print(key)
    print()
    print("=" * 70)
    print("다음 단계:")
    print("1. 위의 키를 복사하세요")
    print("2. backend/.env 파일을 열어주세요")
    print("3. 다음 줄을 추가하거나 수정하세요:")
    print(f"   ENCRYPTION_KEY={key}")
    print("4. 백엔드 서버를 재시작하세요")
    print("=" * 70)
