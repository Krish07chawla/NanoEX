from app.arbitrage.executor import LegPlan
from app.core.constants import Side

API = "/api/v1"


async def make_dislocation(provider, container):
    provider.set("TCS", "4100.00", "4110.00")  # BSE Rs 10 dearer
    await container.market.step()


async def test_spread_board_and_live_opportunities(client, auth, provider, container):
    await make_dislocation(provider, container)
    board = (await client.get(f"{API}/arbitrage/spreads", headers=auth)).json()
    tcs = next(r for r in board["data"] if r["symbol"] == "TCS")
    assert tcs["spread_abs"] == 10.0 and "low-latency" in board["meta"]["note"]
    opps = (await client.get(f"{API}/arbitrage/opportunities", headers=auth)).json()["data"]
    assert opps[0]["symbol"] == "TCS" and opps[0]["buy_exchange"] == "NSE" and opps[0]["actionable"]


async def test_manual_execution_two_legs_completed(client, auth, provider, container):
    await make_dislocation(provider, container)
    r = await client.post(f"{API}/arbitrage/execute", headers=auth, json={"symbol": "TCS", "quantity": 50})
    assert r.status_code == 200, r.text
    t = r.json()["data"]
    assert t["status"] == "COMPLETED" and t["matched_qty"] == 50
    assert t["net_pnl"] == round(t["gross_pnl"] - t["total_costs"], 2) and t["net_pnl"] > 0
    positions = (await client.get(f"{API}/portfolio/positions", headers=auth)).json()["data"]
    assert positions == []  # bought NSE, sold BSE: net flat
    trades = (await client.get(f"{API}/trades?source=ARBITRAGE", headers=auth)).json()["data"]
    assert {(x["exchange"], x["side"]) for x in trades} == {("NSE", "BUY"), ("BSE", "SELL")}
    stats = (await client.get(f"{API}/arbitrage/stats", headers=auth)).json()["data"]
    assert stats["completed"] == 1 and stats["hit_rate_pct"] == 100.0


async def test_no_opportunity_when_prices_equal(client, auth):
    r = await client.post(f"{API}/arbitrage/execute", headers=auth, json={"symbol": "TCS", "quantity": 50})
    assert r.status_code == 409 and r.json()["error"]["code"] == "NO_OPPORTUNITY"


async def test_failed_leg_is_flattened(client, auth, provider, container, monkeypatch):
    await make_dislocation(provider, container)

    def plan(opp):
        return [
            LegPlan(Side.BUY, opp.buy_exchange, 1, fails=False),
            LegPlan(Side.SELL, opp.sell_exchange, 2, fails=True),
        ]

    monkeypatch.setattr(container.arb_executor, "_plan_legs", plan)
    t = (await client.post(f"{API}/arbitrage/execute", headers=auth, json={"symbol": "TCS", "quantity": 50})).json()[
        "data"
    ]
    assert t["status"] == "HEDGED" and t["matched_qty"] == 0
    assert "timed out" in t["failure_reason"] and "Flattened 50/50" in t["failure_reason"]
    assert t["net_pnl"] < 0  # leg risk costs money
    assert (await client.get(f"{API}/portfolio/positions", headers=auth)).json()["data"] == []


async def test_both_legs_fail(client, auth, provider, container, monkeypatch):
    await make_dislocation(provider, container)
    monkeypatch.setattr(
        container.arb_executor,
        "_plan_legs",
        lambda opp: [LegPlan(Side.BUY, opp.buy_exchange, 1, True), LegPlan(Side.SELL, opp.sell_exchange, 1, True)],
    )
    t = (await client.post(f"{API}/arbitrage/execute", headers=auth, json={"symbol": "TCS", "quantity": 50})).json()[
        "data"
    ]
    assert t["status"] == "FAILED" and t["net_pnl"] == 0


async def test_auto_mode_executes_above_threshold(client, auth, provider, container):
    r = await client.put(
        f"{API}/arbitrage/auto", headers=auth, json={"enabled": True, "min_profit": 50, "quantity": 50}
    )
    assert r.json()["data"]["enabled"] is True
    assert await container.auto_arb.scan_once() == 0  # no dislocation yet
    await make_dislocation(provider, container)
    assert await container.auto_arb.scan_once() == 1
    trades = (await client.get(f"{API}/arbitrage/trades", headers=auth)).json()["data"]
    assert trades[0]["mode"] == "AUTO"


async def test_auto_mode_respects_kill_switch(client, auth):
    await client.post(f"{API}/risk/kill-switch", headers=auth, json={"enabled": True})
    r = await client.put(f"{API}/arbitrage/auto", headers=auth, json={"enabled": True})
    assert r.status_code == 422
