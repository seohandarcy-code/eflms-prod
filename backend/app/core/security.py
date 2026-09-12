"""Auth abstraction.

AUTH_MODE=none (now) -> local -> sso, without changing route code.
Routes depend on `get_current_user`; only this module changes per mode.
"""
from dataclasses import dataclass

from app.core.config import get_settings


@dataclass
class CurrentUser:
    sub: str
    email: str | None = None
    roles: tuple[str, ...] = ()


def get_current_user() -> CurrentUser:
    settings = get_settings()
    if settings.auth_mode == "none":
        return CurrentUser(sub="anonymous")
    raise NotImplementedError(f"AUTH_MODE={settings.auth_mode!r} is not implemented yet")
