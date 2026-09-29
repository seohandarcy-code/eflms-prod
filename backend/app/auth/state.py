"""관리자 인증 상태 — 전부 메모리에만 보관, 서버 재기동 시 초기화된다.

비밀번호는 파일에 저장하지 않는다: 재기동하면 항상 `ADMIN_BOOTSTRAP_PASSWORD`(비어있으면
기본값)로 리셋된다. 토큰은 opaque random string이며 세션 딕셔너리에만 존재한다 — 서버가
재시작되면 사라진다(프론트도 새로고침하면 로그아웃되는 설계와 합친다).
"""
from __future__ import annotations

import hmac
import secrets
import threading
import time

from app.core.config import get_settings

DEFAULT_PASSWORD = "0000"
TOKEN_TTL_SECONDS = 60 * 60 * 8
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 60 * 5


class InvalidCredentialsError(RuntimeError):
    pass


class AccountLockedError(RuntimeError):
    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__("로그인 시도 횟수를 초과했습니다. 잠시 후 다시 시도해주세요.")


class AdminAuthStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, float] = {}
        self._fail_count = 0
        self._locked_until: float = 0.0

    def _password(self) -> str:
        return get_settings().admin_bootstrap_password or DEFAULT_PASSWORD

    def login(self, password: str) -> tuple[str, int]:
        with self._lock:
            now = time.monotonic()

            if now < self._locked_until:
                raise AccountLockedError(self._locked_until - now)

            if not hmac.compare_digest(password, self._password()):
                self._fail_count += 1
                if self._fail_count >= MAX_LOGIN_ATTEMPTS:
                    self._locked_until = now + LOCKOUT_SECONDS
                    self._fail_count = 0
                raise InvalidCredentialsError("비밀번호가 올바르지 않습니다.")

            self._fail_count = 0
            token = secrets.token_urlsafe(32)
            self._sessions[token] = now + TOKEN_TTL_SECONDS
            return token, TOKEN_TTL_SECONDS

    def logout(self, token: str) -> None:
        with self._lock:
            self._sessions.pop(token, None)

    def is_valid(self, token: str) -> bool:
        with self._lock:
            expires_at = self._sessions.get(token)
            if expires_at is None:
                return False
            if time.monotonic() > expires_at:
                self._sessions.pop(token, None)
                return False
            return True


admin_auth_store = AdminAuthStore()


def get_auth_store() -> AdminAuthStore:
    return admin_auth_store
