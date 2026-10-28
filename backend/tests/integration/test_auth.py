from tests.conftest import PASSWORD, register_and_login

API = "/api/v1"


async def test_register_login_me(client):
    headers = await register_and_login(client, "kartik@example.com")
    r = await client.get(f"{API}/users/me", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] and body["data"]["email"] == "kartik@example.com" and body["data"]["role"] == "USER"


async def test_new_user_gets_five_lakh_wallet(client, auth):
    data = (await client.get(f"{API}/wallet", headers=auth)).json()["data"]
    assert data["balance"] == 500000.0 and data["capital_added"] == 500000.0


async def test_duplicate_email(client):
    await register_and_login(client, "dup@example.com")
    r = await client.post(
        f"{API}/auth/register", json={"email": "dup@example.com", "password": PASSWORD, "full_name": "Again"}
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "EMAIL_TAKEN"


async def test_weak_password_and_bad_email(client):
    r = await client.post(
        f"{API}/auth/register", json={"email": "x@example.com", "password": "short", "full_name": "X Y"}
    )
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"
    r = await client.post(
        f"{API}/auth/register", json={"email": "not-an-email", "password": PASSWORD, "full_name": "X Y"}
    )
    assert r.status_code == 422


async def test_wrong_password(client):
    await register_and_login(client, "wp@example.com")
    r = await client.post(f"{API}/auth/login", json={"email": "wp@example.com", "password": "wrongpass1"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_protected_route_requires_token(client):
    assert (await client.get(f"{API}/users/me")).status_code == 401
    r = await client.get(f"{API}/users/me", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401


async def test_refresh_rotates_and_detects_reuse(client):
    await register_and_login(client, "rot@example.com")
    old_cookie = client.cookies.get("nanoex_refresh")
    r = await client.post(f"{API}/auth/refresh")
    assert r.status_code == 200 and r.json()["data"]["access_token"]
    assert client.cookies.get("nanoex_refresh") != old_cookie
    # replaying the old (revoked) token is rejected and revokes the whole family
    client.cookies.set("nanoex_refresh", old_cookie, path="/api/v1/auth")
    assert (await client.post(f"{API}/auth/refresh")).status_code == 401


async def test_logout_revokes_refresh(client):
    await register_and_login(client, "out@example.com")
    token = client.cookies.get("nanoex_refresh")
    assert (await client.post(f"{API}/auth/logout")).status_code == 200
    client.cookies.set("nanoex_refresh", token, path="/api/v1/auth")
    assert (await client.post(f"{API}/auth/refresh")).status_code == 401


async def test_change_password(client):
    headers = await register_and_login(client, "cp@example.com")
    r = await client.post(
        f"{API}/auth/change-password",
        headers=headers,
        json={"current_password": "nope12345", "new_password": "newpass123"},
    )
    assert r.status_code == 401
    r = await client.post(
        f"{API}/auth/change-password",
        headers=headers,
        json={"current_password": PASSWORD, "new_password": "newpass123"},
    )
    assert r.status_code == 200
    r = await client.post(f"{API}/auth/login", json={"email": "cp@example.com", "password": "newpass123"})
    assert r.status_code == 200


async def test_login_rate_limited(client):
    statuses = []
    for _ in range(12):
        r = await client.post(f"{API}/auth/login", json={"email": "rl@example.com", "password": "whatever1"})
        statuses.append(r.status_code)
    assert 429 in statuses


async def test_update_profile(client, auth):
    r = await client.patch(f"{API}/users/me", headers=auth, json={"full_name": "New Name"})
    assert r.json()["data"]["full_name"] == "New Name"


async def test_health_and_metrics(client):
    assert (await client.get("/health")).json()["data"]["database"] is True
    r = await client.get("/metrics")
    assert r.status_code == 200 and "nanoex_orders_total" in r.text
