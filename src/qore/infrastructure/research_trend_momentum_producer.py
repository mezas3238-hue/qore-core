"""Deterministic trend/momentum trader methodology (DEMO/research scope).

Falsifiable rule: compare short and long bounded close sums over the most
recent ``long_lookback`` bars. The exact, division-free predicate compares
``lhs = short_sum * L - long_sum * S`` against ``rhs = min_strength * long_sum
* S``. BUY iff ``lhs > +rhs``, SELL iff ``lhs < -rhs``, otherwise ABSTAIN.
Equality at any boundary resolves to ABSTAIN. No lookahead: only bars already
visible (``closed_at <= available_at <= simulated_now``) enter the window.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import ClassVar

from qore.infrastructure.research_lineage_errors import ResearchLineageValidationError
from qore.infrastructure.research_trader_producer_base import BoundedOhlcTraderEvaluator
from qore.infrastructure.research_trader_signal import (
    TraderSignalSide,
    canonical_decimal_string,
    compute_trader_config_fingerprint,
    market_decimal,
    validate_lookback,
    validate_positive_decimal,
)


@dataclass(frozen=True, slots=True)
class TrendMomentumProducer(BoundedOhlcTraderEvaluator):
    """Trend/momentum hypothesis with explicit bounded windows and threshold."""

    short_lookback: int
    long_lookback: int
    min_strength: Decimal
    config_fingerprint: str = field(init=False)

    _family: ClassVar[str] = "qore.trader.trend"
    _software_revision: ClassVar[str] = "qore.trader.trend.v1"

    def __post_init__(self) -> None:
        validate_lookback(self.short_lookback, field_name="short_lookback", minimum=1)
        validate_lookback(self.long_lookback, field_name="long_lookback", minimum=1)
        if self.long_lookback <= self.short_lookback:
            raise ResearchLineageValidationError(
                "long_lookback must be strictly greater than short_lookback"
            )
        validate_positive_decimal(self.min_strength, field_name="min_strength")
        object.__setattr__(
            self,
            "config_fingerprint",
            compute_trader_config_fingerprint(
                schema="qore.trader.trend.configuration.v1",
                fields={
                    "short_lookback": str(self.short_lookback),
                    "long_lookback": str(self.long_lookback),
                    "min_strength": canonical_decimal_string(self.min_strength),
                },
            ),
        )

    @property
    def required_lookback(self) -> int:
        return self.long_lookback

    @property
    def window_capacity(self) -> int:
        return self.long_lookback

    def _decide(
        self,
        bars: tuple[tuple[float, float, float], ...],
    ) -> tuple[TraderSignalSide, str, str, Mapping[str, str]]:
        closes = [market_decimal(bar[0]) for bar in bars]
        short_sum = sum(closes[-self.short_lookback :], Decimal(0))
        long_sum = sum(closes, Decimal(0))
        short_lookback = Decimal(self.short_lookback)
        long_lookback = Decimal(self.long_lookback)
        lhs = short_sum * long_lookback - long_sum * short_lookback
        rhs = self.min_strength * long_sum * short_lookback
        evidence = {
            "short_sum": canonical_decimal_string(short_sum),
            "long_sum": canonical_decimal_string(long_sum),
            "lhs": canonical_decimal_string(lhs),
            "rhs": canonical_decimal_string(rhs),
            "min_strength": canonical_decimal_string(self.min_strength),
            "short_lookback": str(self.short_lookback),
            "long_lookback": str(self.long_lookback),
            "bars_used": str(len(bars)),
        }
        if lhs > rhs:
            return (
                TraderSignalSide.BUY,
                "qore.trader.trend.buy",
                "trend momentum upward",
                evidence,
            )
        if lhs < -rhs:
            return (
                TraderSignalSide.SELL,
                "qore.trader.trend.sell",
                "trend momentum downward",
                evidence,
            )
        return (
            TraderSignalSide.ABSTAIN,
            "qore.trader.trend.abstain.insufficient-strength",
            "trend momentum insufficient strength",
            evidence,
        )
