from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AllowedUser(Base):
    """`/admin` SSO 로그인 접근 허용 목록. IdP 인증 성공 ≠ 접근 허용 —

    여기 등록된 sso_id만 실제로 세션이 발급된다(관리자가 화면에서 직접 등록/삭제).
    """

    __tablename__ = "allowed_users"

    sso_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    team: Mapped[str | None] = mapped_column(String(100), default=None)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
