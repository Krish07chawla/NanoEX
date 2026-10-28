"""WebSocket endpoints.

/ws/market            batched ticks, NSE-BSE spread board, optional depth of one book
                      (client sends {"action": "depth", "symbol": "TCS", "exchange": "NSE"})
/ws/user?token=...    the user's order updates, fills, arbitrage results and wallet changes
"""

import asyncio
import contextlib
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.constants import Exchange
from app.core.event_bus import Topics
from app.core.exceptions import AuthenticationError
from app.core.security import ACCESS_TOKEN_TYPE, decode_token

router = APIRouter()
POLICY_VIOLATION = 1008
USER_TOPICS = (Topics.ORDER_UPDATE, Topics.TRADE, Topics.ARB_RESULT, Topics.WALLET)


async def _authenticate(ws: WebSocket) -> str | None:
    token = ws.query_params.get("token")
    try:
        return decode_token(token or "", ACCESS_TOKEN_TYPE)["sub"]
    except AuthenticationError:
        await ws.close(code=POLICY_VIOLATION)
        return None


@router.websocket("/ws/market")
async def market_ws(ws: WebSocket):
    if await _authenticate(ws) is None:
        return
    await ws.accept()
    c = ws.app.state.container
    queue = c.bus.subscribe(Topics.TICK, Topics.ARB_OPPORTUNITY)
    selected: dict[str, str] = {"symbol": "RELIANCE", "exchange": Exchange.NSE.value}

    async def reader() -> None:
        while True:
            msg = json.loads(await ws.receive_text())
            if msg.get("action") == "depth" and msg.get("exchange") in {e.value for e in Exchange}:
                selected.update(symbol=str(msg.get("symbol", "")).upper(), exchange=msg["exchange"])

    read_task = asyncio.create_task(reader())
    try:
        while True:
            event = await queue.get()
            await ws.send_json({"type": event["topic"], "data": event["data"]})
            if event["topic"] == Topics.TICK and selected["symbol"] in c.market.symbols():
                await ws.send_json({"type": "depth", "data": c.engine.depth(selected["symbol"], selected["exchange"])})
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        read_task.cancel()
        c.bus.unsubscribe(queue)


@router.websocket("/ws/user")
async def user_ws(ws: WebSocket):
    user_id = await _authenticate(ws)
    if user_id is None:
        return
    await ws.accept()
    c = ws.app.state.container
    queue = c.bus.subscribe(*USER_TOPICS)
    try:
        while True:
            event = await queue.get()
            data = event["data"]
            if isinstance(data, dict) and data.get("user_id") == user_id:
                payload = {k: v for k, v in data.items() if k != "user_id"}
                await ws.send_json({"type": event["topic"], "data": payload})
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        c.bus.unsubscribe(queue)
        with contextlib.suppress(Exception):
            await ws.close()
