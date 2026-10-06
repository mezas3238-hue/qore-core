"""Bounded-cycle control for the Phase20D cTrader DEMO runtime.

This helper changes only process lifetime. It grants no execution, provider,
Risk, sizing, LIVE, FundedNext, real-capital or merge authority. The runtime
continues to require the canonical Owner-bound DEMO execution activation file.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


@dataclass(slots=True)
class Phase20BoundedCycleBudget:
    """Count completed runtime cycles and stop only at a configured boundary."""

    max_cycles: int | None
    completed_cycles: int = 0

    def __post_init__(self) -> None:
        if self.max_cycles is not None and (
            not isinstance(self.max_cycles, int)
            or isinstance(self.max_cycles, bool)
            or self.max_cycles <= 0
        ):
            raise CiboCapitalManagementError(
                "Phase20D bounded runtime max_cycles must be positive int"
            )
        if (
            not isinstance(self.completed_cycles, int)
            or isinstance(self.completed_cycles, bool)
            or self.completed_cycles < 0
        ):
            raise CiboCapitalManagementError(
                "Phase20D bounded runtime completed_cycles invalid"
            )
        if (
            self.max_cycles is not None
            and self.completed_cycles > self.max_cycles
        ):
            raise CiboCapitalManagementError(
                "Phase20D bounded runtime cycle count exceeds budget"
            )

    def complete_cycle(self) -> bool:
        """Record one complete cycle and report whether the process should stop."""

        self.completed_cycles += 1
        if self.max_cycles is None:
            return False
        return self.completed_cycles >= self.max_cycles
