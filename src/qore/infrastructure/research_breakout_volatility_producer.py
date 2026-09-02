"""Deterministic breakout/volatility trader methodology (DEMO/research scope).

Falsifiable rule: the current bar is the last bar; the prior ``lookback`` bars
define a historical high/low range that never includes the current bar.
``upper = prior_high * (1 + breakout_margin)`` and
``lower = prior_low * (1 - breakout_margin)``. BUY iff the current close exceeds
``upper``, SELL iff it falls below ``lower``, otherwise ABSTAIN. A zero prior
range (or an insufficient relative range when ``require_min_range`` is set)
fails closed with ABSTAIN.
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
class BreakoutVolatilityProducer(BoundedOhlcTraderEvaluator):
    """Breakout/volatility hypothesis with an explicit prior-window range."""

    lookback: int
    breakout_margin: Decimal
    require_min_range: bool
    min_range: Decimal
    config_fingerprint: str = field(init=False)

    _family: ClassVar[str] = "qore.trader.breakout"
    _software_revision: ClassVar[str] = "qore.trader.breakout.v1"

    def __post_init__(self) -> None:
        validate_lookback(self.lookback, field_name="lookback", minimum=1)
        validate_positive_decimal(self.breakout_margin, field_name="breakout_margin")
        if type(self.require_min_range) is not bool:
            raise ResearchLineageValidationError(
                "require_min_range must be an exact bool; int rejected"
            )
        validate_positive_decimal(self.min_range, field_name="min_range")
        object.__setattr__(
            self,
            "config_fingerprint",
            compute_trader_config_fingerprint(
                schema="qore.trader.breakout.configuration.v1",
                fields={
                    "lookback": str(self.lookback),
                    "breakout_margin": canonical_decimal_string(
                        self.breakout_margin
                    ),
                    "require_min_range": (
                        "true" if self.require_min_range else "false"
                    ),
                    "min_range": canonical_decimal_string(self.min_range),
                },
            ),
        )

    @property
    def required_lookback(self) -> int:
        return self.lookback + 1

    @property
    def window_capacity(self) -> int:
        return self.lookback + 1

    def _decide(
        self,
        bars: tuple[tuple[float, float, float], ...],
    ) -> tuple[TraderSignalSide, str, str, Mapping[str, str]]:
        prior = bars[:-1]
        current_close = market_decimal(bars[-1][0])
        prior_high = max((market_decimal(bar[1]) for bar in prior), default=Decimal(0))
        prior_low = min((market_decimal(bar[2]) for bar in prior), default=Decimal(0))
        prior_range = prior_high - prior_low
        upper = prior_high * (Decimal(1) + self.breakout_margin)
        lower = prior_low * (Decimal(1) - self.breakout_margin)
        evidence = {
            "prior_high": canonical_decimal_string(prior_high),
            "prior_low": canonical_decimal_string(prior_low),
            "prior_range": canonical_decimal_string(prior_range),
            "upper": canonical_decimal_string(upper),
            "lower": canonical_decimal_string(lower),
            "current_close": canonical_decimal_string(current_close),
            "breakout_margin": canonical_decimal_string(self.breakout_margin),
            "min_range": canonical_decimal_string(self.min_range),
            "require_min_range": (
                "true" if self.require_min_range else "false"
            ),
            "lookback": str(self.lookback),
            "bars_used": str(len(bars)),
        }
        if prior_range == 0:
            return (
                TraderSignalSide.ABSTAIN,
                "qore.trader.breakout.abstain.zero-range",
                "breakout prior range is zero",
                evidence,
            )
        if self.require_min_range and prior_range < self.min_range * prior_low:
            return (
                TraderSignalSide.ABSTAIN,
                "qore.trader.breakout.abstain.insufficient-range",
                "breakout prior range insufficient",
                evidence,
            )
        if current_close > upper:
            return (
                TraderSignalSide.BUY,
                "qore.trader.breakout.buy",
                "breakout above prior range",
                evidence,
            )
        if current_close < lower:
            return (
                TraderSignalSide.SELL,
                "qore.trader.breakout.sell",
                "breakout below prior range",
                evidence,
            )
        return (
            TraderSignalSide.ABSTAIN,
            "qore.trader.breakout.abstain.no-breakout",
            "breakout within prior range",
            evidence,
        )
