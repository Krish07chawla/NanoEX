"""RiskManager runs every order through the rule chain before it reaches the engine."""

from app.engine.risk.base_rule import RiskContext, RiskRule
from app.engine.risk.rules import DEFAULT_RULES


class RiskManager:
    def __init__(self, rules: list[RiskRule] | None = None):
        self.rules = rules if rules is not None else [rule() for rule in DEFAULT_RULES]

    def check(self, ctx: RiskContext) -> None:
        """First failing rule raises; passing all rules returns None."""
        for rule in self.rules:
            rule.check(ctx)
