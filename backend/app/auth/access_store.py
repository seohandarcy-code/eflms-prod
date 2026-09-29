"""`allowed_users` 테이블 CRUD — SSO 로그인 접근 허용 목록 관리.

`DataStore`(pandas 캐시/백업 버전관리) 성격의 다른 서비스들과 달리, 이건 단순 flat
메타데이터 테이블이라 `engine`을 직접 쓰는 얇은 CRUD 함수로 둔다(a-ims-prod 패턴).
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AllowedUser


class LastAdminError(RuntimeError):
    """마지막 admin을 삭제/강등하려는 시도 — 전체 락아웃 방지를 위해 막는다."""


async def get_by_sso_id(session: AsyncSession, sso_id: str) -> AllowedUser | None:
    return await session.get(AllowedUser, sso_id)


async def list_all(session: AsyncSession) -> list[AllowedUser]:
    result = await session.execute(select(AllowedUser).order_by(AllowedUser.created_at))
    return list(result.scalars())


async def _admin_count(session: AsyncSession) -> int:
    count = await session.scalar(
        select(func.count()).select_from(AllowedUser).where(AllowedUser.is_admin.is_(True))
    )
    return count or 0


async def create(session: AsyncSession, sso_id: str, name: str, team: str | None, is_admin: bool) -> AllowedUser:
    user = AllowedUser(sso_id=sso_id, name=name, team=team, is_admin=is_admin)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update(
    session: AsyncSession,
    sso_id: str,
    name: str | None = None,
    team: str | None = None,
    is_admin: bool | None = None,
) -> AllowedUser | None:
    user = await get_by_sso_id(session, sso_id)
    if user is None:
        return None

    if is_admin is False and user.is_admin and await _admin_count(session) <= 1:
        raise LastAdminError("마지막 관리자는 강등할 수 없습니다.")

    if name is not None:
        user.name = name
    if team is not None:
        user.team = team
    if is_admin is not None:
        user.is_admin = is_admin

    await session.commit()
    await session.refresh(user)
    return user


async def delete(session: AsyncSession, sso_id: str) -> bool:
    user = await get_by_sso_id(session, sso_id)
    if user is None:
        return False

    if user.is_admin and await _admin_count(session) <= 1:
        raise LastAdminError("마지막 관리자는 삭제할 수 없습니다.")

    await session.delete(user)
    await session.commit()
    return True


async def upsert_bootstrap_admin(session: AsyncSession, sso_id: str) -> AllowedUser:
    """`SSO_ADMIN_ALLOWLIST`에 매칭되는 계정의 admin 권한을 로그인마다 보장한다.

    행이 없으면 새로 만들고, 있으면 is_admin=True만 보장하고 이름/팀은 건드리지 않는다
    (관리자가 화면에서 고친 값을 덮어쓰지 않기 위함).
    """
    user = await get_by_sso_id(session, sso_id)
    if user is None:
        user = AllowedUser(sso_id=sso_id, name=sso_id, team=None, is_admin=True)
        session.add(user)
    elif not user.is_admin:
        user.is_admin = True

    await session.commit()
    await session.refresh(user)
    return user
