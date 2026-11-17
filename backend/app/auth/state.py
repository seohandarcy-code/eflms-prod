"""로그인 세션 상태 — 전부 메모리에만 보관, 서버 재기동 시 초기화된다.

비밀번호는 파일에 저장하지 않는다: 재기동하면 항상 `ADMIN_BOOTSTRAP_PASSWORD`(비어있으면
기본값)로 리셋된다. 토큰은 opaque random string이며 세션 딕셔너리에만 존재한다 — 서버가
재시작되면 사라진다(프론트는 401을 받으면 들고 있던 토큰을 지우고 다시 로그인하게 한다).

세션 발급/검증은 로그인 "수단"(local 비밀번호 vs sso)과 무관하게 이 클래스 하나를 공유한다.
세션마다 역할(role)을 하나 들고 있다(Stage 16-1, a-ims-prod와 같은 구분):

- `admin`   — 관리자. local 비밀번호 로그인은 항상 admin, sso는 `allowed_users.is_admin=True`
- `user`    — `allowed_users`에 등록된 일반 사용자. 대시보드 + 관리자 화면 테이블 조회
- `general` — sso 인증에는 성공했지만 `allowed_users`에 없는 사용자. 대시보드 조회만
  (`SSO_DENY_UNREGISTERED_USERS=true`면 이 역할 대신 로그인 자체를 거부)
"""
from __future__ import annotations

import hmac
import secrets
import threading
import time
from typing import Literal

from app.core.config import get_settings

Role = Literal["admin", "user", "general"]
ROLES: tuple[str, ...] = ("admin", "user", "general")

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
        # token -> (expires_at, role)
        self._sessions: dict[str, tuple[float, str]] = {}
        self._fail_count = 0
        self._locked_until: float = 0.0

    def _password(self) -> str:
        return get_settings().admin_bootstrap_password or DEFAULT_PASSWORD

    def login(self, password: str) -> tuple[str, int]:
        """local 비밀번호 로그인 — 항상 admin 세션을 발급한다."""
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
            return self._issue_locked("admin")

    def issue_session(self, role: Role) -> tuple[str, int]:
        """sso 콜백 등, 비밀번호 없이 이미 검증된 사용자에게 세션을 내준다."""
        if role not in ROLES:
            raise ValueError(f"알 수 없는 역할: {role!r}")
        with self._lock:
            return self._issue_locked(role)

    def _issue_locked(self, role: str) -> tuple[str, int]:
        token = secrets.token_urlsafe(32)
        self._sessions[token] = (time.monotonic() + TOKEN_TTL_SECONDS, role)
        return token, TOKEN_TTL_SECONDS

    def logout(self, token: str) -> None:
        with self._lock:
            self._sessions.pop(token, None)

    def is_valid(self, token: str) -> bool:
        return self.get_role(token) is not None

    def get_role(self, token: str) -> str | None:
        with self._lock:
            entry = self._sessions.get(token)
            if entry is None:
                return None
            expires_at, role = entry
            if time.monotonic() > expires_at:
                self._sessions.pop(token, None)
                return None
            return role

    def get_is_admin(self, token: str) -> bool:
        return self.get_role(token) == "admin"


admin_auth_store = AdminAuthStore()


def get_auth_store() -> AdminAuthStore:
    return admin_auth_store
