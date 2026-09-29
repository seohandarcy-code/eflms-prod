import pytest

from app.auth import access_store
from app.auth.access_store import LastAdminError


async def test_create_and_get(session_factory):
    async with session_factory() as session:
        await access_store.create(session, "alice@company.com", "Alice", "PlatformTeam", is_admin=True)

        user = await access_store.get_by_sso_id(session, "alice@company.com")
        assert user is not None
        assert user.name == "Alice"
        assert user.is_admin is True

        assert await access_store.get_by_sso_id(session, "nobody@company.com") is None


async def test_list_all_ordered(session_factory):
    async with session_factory() as session:
        await access_store.create(session, "a@company.com", "A", None, is_admin=False)
        await access_store.create(session, "b@company.com", "B", None, is_admin=False)

        users = await access_store.list_all(session)
        assert [u.sso_id for u in users] == ["a@company.com", "b@company.com"]


async def test_update_fields(session_factory):
    async with session_factory() as session:
        await access_store.create(session, "a@company.com", "A", None, is_admin=False)

        updated = await access_store.update(session, "a@company.com", name="A2", team="Team X")
        assert updated is not None
        assert updated.name == "A2"
        assert updated.team == "Team X"

        assert await access_store.update(session, "missing@company.com", name="x") is None


async def test_cannot_demote_last_admin(session_factory):
    async with session_factory() as session:
        await access_store.create(session, "admin@company.com", "Admin", None, is_admin=True)

        with pytest.raises(LastAdminError):
            await access_store.update(session, "admin@company.com", is_admin=False)


async def test_cannot_delete_last_admin_but_can_delete_others(session_factory):
    async with session_factory() as session:
        await access_store.create(session, "admin@company.com", "Admin", None, is_admin=True)
        await access_store.create(session, "user@company.com", "User", None, is_admin=False)

        assert await access_store.delete(session, "user@company.com") is True

        with pytest.raises(LastAdminError):
            await access_store.delete(session, "admin@company.com")

        # 두 번째 admin이 생기면 첫 번째는 삭제 가능해짐
        await access_store.create(session, "admin2@company.com", "Admin2", None, is_admin=True)
        assert await access_store.delete(session, "admin@company.com") is True


async def test_upsert_bootstrap_admin_creates_and_preserves_name(session_factory):
    async with session_factory() as session:
        created = await access_store.upsert_bootstrap_admin(session, "boot@company.com")
        assert created.is_admin is True

        # 관리자가 이름을 바꿔둔 뒤 다시 로그인해도 이름은 덮어쓰지 않는다
        await access_store.update(session, "boot@company.com", name="관리자가 고친 이름")
        again = await access_store.upsert_bootstrap_admin(session, "boot@company.com")
        assert again.name == "관리자가 고친 이름"
        assert again.is_admin is True
