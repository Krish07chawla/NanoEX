API = "/api/v1"

BOT = {
    "name": "SBIN momentum",
    "strategy_type": "momentum",
    "symbol": "SBIN",
    "quantity": 10,
    "params": {"lookback": 2, "threshold_pct": 0.5},
    "stop_loss_pct": 2,
}


async def test_strategy_types(client, auth):
    types = (await client.get(f"{API}/strategies/types", headers=auth)).json()["data"]
    assert len(types) == 9 and {"key", "params"} <= set(types[0])


async def test_strategy_crud_and_validation(client, auth):
    r = await client.post(f"{API}/strategies", headers=auth, json={**BOT, "params": {"lookback": 0}})
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_STRATEGY"
    cfg = (await client.post(f"{API}/strategies", headers=auth, json=BOT)).json()["data"]
    assert cfg["is_active"] is False
    cfg = (await client.post(f"{API}/strategies/{cfg['id']}/start", headers=auth)).json()["data"]
    assert cfg["is_active"] is True
    r = await client.put(f"{API}/strategies/{cfg['id']}", headers=auth, json={**BOT, "quantity": 20})
    assert r.json()["data"]["quantity"] == 20
    assert (await client.post(f"{API}/strategies/{cfg['id']}/stop", headers=auth)).json()["data"]["is_active"] is False
    assert (await client.delete(f"{API}/strategies/{cfg['id']}", headers=auth)).status_code == 200
    assert (await client.get(f"{API}/strategies", headers=auth)).json()["data"] == []


async def test_bot_trades_on_signal(client, auth, provider, container):
    cfg = (await client.post(f"{API}/strategies", headers=auth, json=BOT)).json()["data"]
    await client.post(f"{API}/strategies/{cfg['id']}/start", headers=auth)
    await container.bot_runner.refresh()
    for price in ("820.00", "820.00", "830.00"):  # +1.2% momentum -> BUY
        provider.set("SBIN", price, price)
        quotes = await container.market.step()
        await container.bot_runner.on_ticks([q.to_dict() for q in quotes])
    trades = (await client.get(f"{API}/trades?source=STRATEGY", headers=auth)).json()["data"]
    assert trades and trades[0]["strategy_name"] == "SBIN momentum" and "Momentum" in trades[0]["signal_reason"]


async def test_backtest_endpoint_is_reproducible(client, auth):
    body = {
        "strategy_type": "ema_crossover",
        "params": {"fast": 5, "slow": 20},
        "symbol": "TCS",
        "bars": 300,
        "seed": 9,
        "stop_loss_pct": 3,
    }
    a = (await client.post(f"{API}/backtests", headers=auth, json=body)).json()["data"]
    b = (await client.post(f"{API}/backtests", headers=auth, json=body)).json()["data"]
    assert a["metrics"] == b["metrics"] and a["id"] != b["id"]
    listing = (await client.get(f"{API}/backtests", headers=auth)).json()
    assert listing["meta"]["total"] == 2
    one = (await client.get(f"{API}/backtests/{a['id']}", headers=auth)).json()["data"]
    assert len(one["equity_curve"]) == 300
