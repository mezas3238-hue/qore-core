"""Deterministic source-compatible entry execution boundary for Capitalizer V2.

Author-supported sequence:
- wait for lower-timeframe structure/protected swing confirmation;
- participate in the following continuation rather than front-running confirmation.

QORE deterministic replay convention:
- after the source framework is fully confirmed at a closed bar,
- use the OPEN of the immediately following execution bar as the planned entry price.

The exact fill convention is explicitly QORE operationalization, not attributed verbatim to
ICT/TTrades. It is causal and uses no future classification of the execution bar.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)


@dataclass(frozen=True, slots=True)
class CapitalizerSourceExecutionOpen:
    open_price: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.open_price, Decimal) or not self.open_price.is_finite():
            raise ValueError("execution open price must be finite Decimal")


@dataclass(frozen=True, slots=True)
class CapitalizerSourceEntryObservation:
    direction: CapitalizerSourceDirection
    entry_price: Decimal
    source_framework_confirmed_before_entry: bool
    author_sequence_supported: bool = True
    qore_next_bar_open_operationalization: bool = True
    future_execution_bar_close_used: bool = False
    grants_execution_authority: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.entry_price, Decimal) or not self.entry_price.is_finite():
            raise ValueError("source entry price must be finite Decimal")
        if not self.source_framework_confirmed_before_entry:
            raise ValueError("Capitalizer entry cannot front-run source confirmation")
        if not self.author_sequence_supported:
            raise ValueError("Capitalizer entry sequence must remain source-supported")
        if not self.qore_next_bar_open_operationalization:
            raise ValueError("deterministic replay entry convention must remain explicit")
        if self.future_execution_bar_close_used:
            raise ValueError("entry cannot classify next candle using its future close")
        if self.grants_execution_authority or self.grants_capital_authority:
            raise ValueError("entry observation stops before QORE Risk/execution")


def derive_next_bar_open_entry(
    *,
    direction: CapitalizerSourceDirection,
    source_framework_confirmed: bool,
    execution_open: CapitalizerSourceExecutionOpen,
) -> CapitalizerSourceEntryObservation:
    """Plan entry at next bar open only after the source framework is already complete."""

    if not source_framework_confirmed:
        raise ValueError("next-bar entry requires completed source framework")
    return CapitalizerSourceEntryObservation(
        direction=direction,
        entry_price=execution_open.open_price,
        source_framework_confirmed_before_entry=True,
    )
