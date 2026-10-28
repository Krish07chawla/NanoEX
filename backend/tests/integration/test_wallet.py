API = "/api/v1"


async def test_top_up_adds_capital_not_profit(client, auth):
    r = await client.post(f"{API}/wallet/topup", headers=auth, json={"amount": 100000})
    assert r.status_code == 200
    w = r.json()["data"]
    assert w["balance"] == 600000.0 and w["capital_added"] == 600000.0
    summary = (await client.get(f"{API}/portfolio/summary", headers=auth)).json()["data"]
    assert summary["total_pnl"] == 0.0
    txns = (await client.get(f"{API}/wallet/transactions", headers=auth)).json()
    assert [t["type"] for t in txns["data"]][:2] == ["TOPUP", "INITIAL"]


async def test_top_up_limits(client, auth):
    r = await client.post(f"{API}/wallet/topup", headers=auth, json={"amount": 5000000})
    assert r.status_code == 422 and r.json()["error"]["code"] == "TOPUP_LIMIT"
    r = await client.post(f"{API}/wallet/topup", headers=auth, json={"amount": -5})
    assert r.status_code == 422


async def test_reset_requires_flat_portfolio(client, auth):
    await client.post(
        f"{API}/orders",
        headers=auth,
        json={"symbol": "SBIN", "exchange": "NSE", "side": "BUY", "order_type": "MARKET", "quantity": 10},
    )
    r = await client.post(f"{API}/wallet/reset", headers=auth)
    assert r.status_code == 409
    await client.post(
        f"{API}/orders",
        headers=auth,
        json={"symbol": "SBIN", "exchange": "NSE", "side": "SELL", "order_type": "MARKET", "quantity": 10},
    )
    r = await client.post(f"{API}/wallet/reset", headers=auth)
    assert r.status_code == 200 and r.json()["data"]["balance"] == 500000.0
