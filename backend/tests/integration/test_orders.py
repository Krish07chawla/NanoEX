API = "/api/v1"


def order(**kw):
    base = {"symbol": "SBIN", "exchange": "NSE", "side": "BUY", "order_type": "MARKET", "quantity": 10}
    return {**base, **kw}


async def test_market_buy_fills_and_creates_position(client, auth):
    r = await client.post(f"{API}/orders", headers=auth, json=order())
    assert r.status_code == 201
    o = r.json()["data"]
    assert o["status"] == "FILLED" and o["filled_qty"] == 10 and o["avg_fill_price"] == 820.05
    positions = (await client.get(f"{API}/portfolio/positions", headers=auth)).json()["data"]
    assert positions[0]["symbol"] == "SBIN" and positions[0]["quantity"] == 10
    trades = (await client.get(f"{API}/trades", headers=auth)).json()
    assert trades["meta"]["total"] >= 1 and trades["data"][0]["fees"] > 0


async def test_round_trip_realizes_pnl_and_fees(client, auth, provider, container):
    await client.post(f"{API}/orders", headers=auth, json=order(quantity=100))
    provider.set("SBIN", "830.00", "830.00")
    await container.market.step()
    await client.post(f"{API}/orders", headers=auth, json=order(side="SELL", quantity=100))
    s = (await client.get(f"{API}/portfolio/summary", headers=auth)).json()["data"]
    assert s["open_positions"] == 0
    assert s["realized_pnl"] == 990.0  # (829.95 - 820.05) * 100
    assert s["total_pnl"] == round(s["realized_pnl"] - s["total_fees"], 2)


async def test_limit_order_rests_then_cancel_releases_funds(client, auth):
    r = await client.post(f"{API}/orders", headers=auth, json=order(order_type="LIMIT", price=800))
    o = r.json()["data"]
    assert o["status"] == "NEW"
    w = (await client.get(f"{API}/wallet", headers=auth)).json()["data"]
    assert w["blocked_margin"] > 8000
    r = await client.delete(f"{API}/orders/{o['id']}", headers=auth)
    assert r.json()["data"]["status"] == "CANCELLED"
    w = (await client.get(f"{API}/wallet", headers=auth)).json()["data"]
    assert w["blocked_margin"] == 0
    assert (await client.delete(f"{API}/orders/{o['id']}", headers=auth)).status_code == 409


async def test_resting_limit_fills_when_market_moves(client, auth, provider, container):
    r = await client.post(f"{API}/orders", headers=auth, json=order(order_type="LIMIT", price=815))
    oid = r.json()["data"]["id"]
    provider.set("SBIN", "812.00", "812.00")
    await container.market.step()
    orders = (await client.get(f"{API}/orders", headers=auth)).json()["data"]
    filled = next(o for o in orders if o["id"] == oid)
    assert filled["status"] == "FILLED" and filled["avg_fill_price"] == 815.0


async def test_risk_rejection_is_recorded(client, auth):
    r = await client.post(f"{API}/orders", headers=auth, json=order(quantity=6000))
    assert r.status_code == 400 and r.json()["error"]["code"] == "RISK_LIMIT_EXCEEDED"
    orders = (await client.get(f"{API}/orders?status=REJECTED", headers=auth)).json()["data"]
    assert orders and "exceeds limit" in orders[0]["reject_reason"]


async def test_insufficient_funds(client, auth):
    await client.put(f"{API}/risk", headers=auth, json={"max_order_notional": 10000000, "max_position_value": 10000000})
    r = await client.post(f"{API}/orders", headers=auth, json=order(symbol="TCS", quantity=200))
    assert r.json()["error"]["code"] == "INSUFFICIENT_FUNDS"


async def test_validation_errors(client, auth):
    assert (await client.post(f"{API}/orders", headers=auth, json=order(order_type="LIMIT"))).status_code == 422
    r = await client.post(f"{API}/orders", headers=auth, json=order(order_type="LIMIT", price=800.03))
    assert r.status_code == 422
    r = await client.post(f"{API}/orders", headers=auth, json=order(order_type="LIMIT", price=2000))
    assert r.status_code == 422
    assert (await client.post(f"{API}/orders", headers=auth, json=order(symbol="NOPE"))).status_code == 404


async def test_kill_switch_blocks_and_cancels(client, auth):
    r = await client.post(f"{API}/orders", headers=auth, json=order(order_type="LIMIT", price=800))
    r = await client.post(f"{API}/risk/kill-switch", headers=auth, json={"enabled": True})
    assert r.json()["data"]["cancelled_orders"] == 1
    r = await client.post(f"{API}/orders", headers=auth, json=order())
    assert r.status_code == 400 and "Kill switch" in r.json()["error"]["message"]
    await client.post(f"{API}/risk/kill-switch", headers=auth, json={"enabled": False})
    assert (await client.post(f"{API}/orders", headers=auth, json=order())).status_code == 201


async def test_market_endpoints(client, auth):
    syms = (await client.get(f"{API}/market/symbols", headers=auth)).json()["data"]
    assert {s["symbol"] for s in syms} == {"RELIANCE", "TCS", "SBIN"}
    depth = (await client.get(f"{API}/market/TCS/NSE/depth", headers=auth)).json()["data"]
    assert len(depth["bids"]) == 10 and depth["asks"][0]["price"] == 4100.05
    hist = (await client.get(f"{API}/market/TCS/history?exchange=BSE", headers=auth)).json()["data"]
    assert hist and "price" in hist[0]
    assert len((await client.get(f"{API}/market/quotes", headers=auth)).json()["data"]) == 6


async def test_trades_csv_export(client, auth):
    await client.post(f"{API}/orders", headers=auth, json=order())
    r = await client.get(f"{API}/trades/export.csv?symbol=SBIN", headers=auth)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("executed_at,symbol") and len(lines) >= 2


async def test_profit_dashboard(client, auth):
    await client.post(f"{API}/orders", headers=auth, json=order())
    await client.post(f"{API}/orders", headers=auth, json=order(side="SELL"))
    d = (await client.get(f"{API}/dashboard/profit", headers=auth)).json()["data"]
    assert d["summary"]["capital_added"] == 500000.0
    assert d["by_source"][0]["source"] == "MANUAL"
    assert d["closed_trades"] >= 1 and d["equity_curve"]
    perf = (await client.get(f"{API}/dashboard/performance", headers=auth)).json()["data"]
    assert perf["orders_total"] >= 2 and perf["avg_order_latency_us"] > 0
