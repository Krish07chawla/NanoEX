from sqlalchemy import update

from app.db.session import session_factory
from app.models.user import User
from tests.conftest import PASSWORD, register_and_login

API = "/api/v1"


async def make_admin(client, email="admin@example.com") -> dict:
    await register_and_login(client, email)
    async with session_factory()() as s:
        await s.execute(update(User).where(User.email == email).values(role="ADMIN"))
        await s.commit()
    r = await client.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


async def test_non_admin_forbidden(client, auth):
    assert (await client.get(f"{API}/admin/users", headers=auth)).status_code == 403


async def test_admin_can_list_disable_and_adjust(client, auth):
    admin = await make_admin(client)
    users = (await client.get(f"{API}/admin/users", headers=admin)).json()
    assert users["meta"]["total"] == 2
    target = next(u for u in users["data"] if u["email"] == "trader@example.com")
    r = await client.post(
        f"{API}/admin/users/{target['id']}/wallet-adjust", headers=admin, json={"amount": 2500, "note": "Prize money"}
    )
    assert r.json()["data"]["balance"] == 502500.0
    r = await client.patch(f"{API}/admin/users/{target['id']}", headers=admin, json={"is_active": False})
    assert r.json()["data"]["is_active"] is False
    assert (await client.get(f"{API}/users/me", headers=auth)).status_code == 401
    r = await client.post(f"{API}/auth/login", json={"email": "trader@example.com", "password": PASSWORD})
    assert r.status_code == 403


async def test_admin_metrics_and_audit(client, auth):
    admin = await make_admin(client)
    m = (await client.get(f"{API}/admin/metrics", headers=admin)).json()["data"]
    assert m["users"] == 2 and "orders_per_sec" in m
    logs = (await client.get(f"{API}/admin/audit-logs?action=LOGIN", headers=admin)).json()
    assert logs["meta"]["total"] >= 2
