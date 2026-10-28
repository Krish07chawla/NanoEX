"""Strategy config CRUD, start/stop of live bots, and backtests."""

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.backtest.data_loader import load_prices
from app.backtest.runner import BacktestConfig, Backtester
from app.core.exceptions import NotFound, ValidationFailed
from app.models.backtest_result import BacktestResult
from app.models.strategy_config import StrategyConfig
from app.repositories.strategy_repo import BacktestRepository, StrategyConfigRepository
from app.schemas.strategy import BacktestRequest, StrategyConfigIn
from app.strategies.factory import StrategyFactory

if TYPE_CHECKING:
    from app.container import Container


def _validate_strategy(key: str, params: dict) -> None:
    try:
        StrategyFactory.create(key, params)
    except ValueError as exc:
        raise ValidationFailed(str(exc), code="INVALID_STRATEGY") from exc


class StrategyService:
    def __init__(self, session: AsyncSession, container: "Container"):
        self.session = session
        self.c = container
        self.repo = StrategyConfigRepository(session)

    async def list(self, user_id: str) -> list[StrategyConfig]:
        return await self.repo.for_user(user_id)

    async def create(self, user_id: str, body: StrategyConfigIn) -> StrategyConfig:
        symbol = body.symbol.upper()
        if symbol not in self.c.market.symbols():
            raise ValidationFailed(f"Unknown symbol {symbol}")
        _validate_strategy(body.strategy_type, body.params)
        return await self.repo.add(StrategyConfig(user_id=user_id, **{**body.model_dump(), "symbol": symbol}))

    async def get_owned(self, user_id: str, config_id: str) -> StrategyConfig:
        cfg = await self.repo.get(config_id)
        if cfg is None or cfg.user_id != user_id:
            raise NotFound("Strategy not found")
        return cfg

    async def update(self, user_id: str, config_id: str, body: StrategyConfigIn) -> StrategyConfig:
        cfg = await self.get_owned(user_id, config_id)
        _validate_strategy(body.strategy_type, body.params)
        for key, value in body.model_dump().items():
            setattr(cfg, key, value.upper() if key == "symbol" else value)
        self.c.bot_runner.bots.pop(cfg.id, None)  # rebuilt with new params on next refresh
        await self.session.flush()
        return cfg

    async def delete(self, user_id: str, config_id: str) -> None:
        cfg = await self.get_owned(user_id, config_id)
        self.c.bot_runner.bots.pop(cfg.id, None)
        await self.repo.delete(cfg)

    async def set_active(self, user_id: str, config_id: str, active: bool) -> StrategyConfig:
        cfg = await self.get_owned(user_id, config_id)
        cfg.is_active = active
        if not active:
            self.c.bot_runner.bots.pop(cfg.id, None)
        await self.session.flush()
        return cfg

    async def backtest(self, user_id: str, req: BacktestRequest) -> dict:
        _validate_strategy(req.strategy_type, req.params)
        prices = load_prices(req.symbol.upper(), req.bars, req.data_source, req.seed)
        report = Backtester(self.c.cost_model).run(
            BacktestConfig(
                strategy_key=req.strategy_type,
                params=req.params,
                symbol=req.symbol.upper(),
                initial_capital=float(req.initial_capital),
                position_size_pct=req.position_size_pct,
                slippage_bps=req.slippage_bps,
                stop_loss_pct=req.stop_loss_pct,
                take_profit_pct=req.take_profit_pct,
                trailing_stop_pct=req.trailing_stop_pct,
            ),
            prices,
        )
        result = {"metrics": report.metrics, "equity_curve": report.equity_curve, "trades": report.trades}
        if req.save:
            saved = await BacktestRepository(self.session).add(
                BacktestResult(
                    user_id=user_id,
                    strategy_type=req.strategy_type,
                    params=req.params,
                    symbol=req.symbol.upper(),
                    data_source=req.data_source,
                    bars=len(prices),
                    seed=req.seed,
                    initial_capital=req.initial_capital,
                    metrics=report.metrics,
                    equity_curve=report.equity_curve,
                    trades=report.trades,
                )
            )
            result["id"] = saved.id
        return result
