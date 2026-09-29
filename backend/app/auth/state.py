"""관리자 인증 상태 — 전부 메모리에만 보관, 서버 재기동 시 초기화된다.

비밀번호는 파일에 저장하지 않는다: 재기동하면 항상 `ADMIN_BOOTSTRAP_PASSWORD`(비어있으면
기본값)로 리셋된다. 토큰은 opaque random string이며 세션 딕셔너리에만 존재한다 — 서버가
재시작되면 사라진다(프론트도 새로고침하면 로그아웃되는 설계와 합친다).

세션 발급/검증은 로그인 "수단"(local 비밀번호 vs sso)과 무관하게 이 클래스 하나를 공유한다
— local은 항상 is_admin=True로, sso는 `allowed_users` 조회 결과로 is_admin을 정해
`issue_session()`을 호출한다.
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
        # token -> (expires_at, is_admin)
        self._sessions: dict[str, tuple[float, bool]] = {}
        self._fail_count = 0
        self._locked_until: float = 0.0

    def _password(self) -> str:
        return get_settings().admin_bootstrap_password or DEFAULT_PASSWORD

    def login(self, password: str) -> tuple[str, int]:
        """local 모드 비밀번호 로그인 — 항상 is_admin=True 세션을 발급한다."""
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
            return self._issue_locked(is_admin=True)

    def issue_session(self, is_admin: bool) -> tuple[str, int]:
        """sso 콜백 등, 비밀번호 없이 이미 검증된 사용자에게 세션을 내준다."""
        with self._lock:
            return self._issue_locked(is_admin)

    def _issue_locked(self, is_admin: bool) -> tuple[str, int]:
        token = secrets.token_urlsafe(32)
        self._sessions[token] = (time.monotonic() + TOKEN_TTL_SECONDS, is_admin)
        return token, TOKEN_TTL_SECONDS

    def logout(self, token: str) -> None:
        with self._lock:
            self._sessions.pop(token, None)

    def is_valid(self, token: str) -> bool:
        return self._get(token) is not None

    def get_is_admin(self, token: str) -> bool:
        entry = self._get(token)
        return entry is not None and entry[1]

    def _get(self, token: str) -> tuple[float, bool] | None:
        with self._lock:
            entry = self._sessions.get(token)
            if entry is None:
                return None
            expires_at, _ = entry
            if time.monotonic() > expires_at:
                self._sessions.pop(token, None)
                return None
            return entry


admin_auth_store = AdminAuthStore()


def get_auth_store() -> AdminAuthStore:
    return admin_auth_store
