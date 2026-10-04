"""Coverage sensor for open-position continuation intelligence.

Research-only.  Measures whether Portfolio has enough causal state to compare
KEEP/RELEASE against new opportunities.  It never infers continuation value.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_full_economic_digital_twin import (
    CiboObservedEconomicTwin,
)


@dataclass(frozen=True, slots=True)
class CiboPositionContinuationCoverage:
    twin_id: str
    open_position_count: int
    entry_expectation_identified_count: int
    continuation_value_identified_count: int
    remaining_reward_identified_count: int
    releasable_with_identified_value_count: int
    continuation_coverage: Decimal
    portfolio_actionable_coverage: Decimal
    primary_blocker: str
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.twin_id or not self.primary_blocker:
            raise CiboCapitalManagementError(
                "continuation coverage identity/blocker required"
            )
        for name in (
            "open_position_count",
            "entry_expectation_identified_count",
            "continuation_value_identified_count",
            "remaining_reward_identified_count",
            "releasable_with_identified_value_count",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise CiboCapitalManagementError(
                    f"continuation coverage {name} invalid"
                )
        for name in ("continuation_coverage", "portfolio_actionable_coverage"):
            value = getattr(self, name)
            if value < 0 or value > 1:
                raise CiboCapitalManagementError(
                    f"continuation coverage {name} outside [0,1]"
                )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "continuation coverage sensor cannot acquire authority"
            )


def _ratio(num: int, den: int) -> Decimal:
    if den <= 0:
        return Decimal(1)
    return Decimal(num) / Decimal(den)


def measure_position_continuation_coverage(
    twin: CiboObservedEconomicTwin,
) -> CiboPositionContinuationCoverage:
    if not isinstance(twin, CiboObservedEconomicTwin):
        raise CiboCapitalManagementError(
            "continuation coverage requires canonical Full Economic Twin"
        )

    positions = twin.positions
    total = len(positions)
    entry = sum(
        bool(item.expectation_evidence_sha256)
        and item.entry_expected_capital_minutes > 0
        for item in positions
    )
    continuation = sum(
        item.continuation_value_identified
        for item in positions
    )
    reward = sum(
        item.remaining_reward_identified
        for item in positions
    )
    actionable = sum(
        item.releasable and item.continuation_value_identified
        for item in positions
    )

    if total == 0:
        blocker = "NO_OPEN_POSITION_COMPETITION"
    elif continuation == 0:
        blocker = "CONTINUATION_VALUE_UNIDENTIFIED"
    elif reward == 0:
        blocker = "REMAINING_REWARD_UNIDENTIFIED"
    elif actionable < total:
        blocker = "PARTIAL_PORTFOLIO_ACTIONABILITY"
    else:
        blocker = "NONE"

    return CiboPositionContinuationCoverage(
        twin_id=twin.twin_id,
        open_position_count=total,
        entry_expectation_identified_count=entry,
        continuation_value_identified_count=continuation,
        remaining_reward_identified_count=reward,
        releasable_with_identified_value_count=actionable,
        continuation_coverage=_ratio(continuation, total),
        portfolio_actionable_coverage=_ratio(actionable, total),
        primary_blocker=blocker,
    )
