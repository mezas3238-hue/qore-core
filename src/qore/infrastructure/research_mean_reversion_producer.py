"""Deterministic mean-reversion trader methodology (DEMO/research scope).

Falsifiable rule: the equilibrium is the exact mean of the ``lookback`` PRIOR
closes (the current bar is never part of its own equilibrium). The exact,
division-free predicate compares ``current_close * K`` against
``equil_sum * (1 - threshold)`` (BUY) and ``equil_sum * (1 + threshold)``
(SELL). Equality at any boundary resolves to ABSTAIN. A constant series yields
``current_close * K == equil_sum`` and therefore ABSTAIN, so zero dispersion is
handled without a separate dispersion gate.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import ClassVar

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
class MeanReversionProducer(BoundedOhlcTraderEvaluator):
    """Mean-reversion hypothesis with a prior-bar equilibrium and threshold."""

    lookback: int
    deviation_threshold: Decimal
    config_fingerprint: str = field(init=False)

    _family: ClassVar[str] = "qore.trader.meanreversion"
    _software_revision: ClassVar[str] = "qore.trader.meanreversion.v1"

    def __post_init__(self) -> None:
        validate_lookback(self.lookback, field_name="lookback", minimum=1)
        validate_positive_decimal(
            self.deviation_threshold,
            field_name="deviation_threshold",
        )
        object.__setattr__(
            self,
            "config_fingerprint",
            compute_trader_config_fingerprint(
                schema="qore.trader.meanreversion.configuration.v1",
                fields={
                    "lookback": str(self.lookback),
                    "deviation_threshold": canonical_decimal_string(
                        self.deviation_threshold
                    ),
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
        equil_sum = sum((market_decimal(bar[0]) for bar in prior), Decimal(0))
        lookback = Decimal(self.lookback)
        lower = equil_sum * (Decimal(1) - self.deviation_threshold)
        upper = equil_sum * (Decimal(1) + self.deviation_threshold)
        evidence = {
            "equil_sum": canonical_decimal_string(equil_sum),
            "current_close": canonical_decimal_string(current_close),
            "deviation_threshold": canonical_decimal_string(
                self.deviation_threshold
            ),
            "lookback": str(self.lookback),
            "bars_used": str(len(bars)),
        }
        if current_close * lookback < lower:
            return (
                TraderSignalSide.BUY,
                "qore.trader.meanreversion.buy",
                "mean reversion below equilibrium",
                evidence,
            )
        if current_close * lookback > upper:
            return (
                TraderSignalSide.SELL,
                "qore.trader.meanreversion.sell",
                "mean reversion above equilibrium",
                evidence,
            )
        return (
            TraderSignalSide.ABSTAIN,
            "qore.trader.meanreversion.abstain.within-deviation",
            "mean reversion within deviation band",
            evidence,
        )
