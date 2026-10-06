"""Portfolio competition surface diagnostics for CIBO Trader Lab.

Evaluation-only. Measures where real account-wide competition exists:
new opportunity vs new opportunity in the same epoch, and new opportunity vs
capital already occupied by open positions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


@dataclass(frozen=True, slots=True)
class CiboPortfolioCompetitionSurfaceReport:
    positive_context_allowed_count: int
    same_epoch_competition_count: int
    open_position_competition_count: int
    no_competition_count: int
    maximum_simultaneous_new_opportunities: int
    maximum_open_positions_at_decision: int
    same_epoch_competition_rate: Decimal
    open_position_competition_rate: Decimal
    any_competition_rate: Decimal
    outcome_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "positive_context_allowed_count",
            "same_epoch_competition_count",
            "open_position_competition_count",
            "no_competition_count",
            "maximum_simultaneous_new_opportunities",
            "maximum_open_positions_at_decision",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise CiboCapitalManagementError(
                    f"portfolio surface {name} must be non-negative int"
                )
        for name in (
            "same_epoch_competition_rate",
            "open_position_competition_rate",
            "any_competition_rate",
        ):
            value = getattr(self, name)
            if value < 0 or value > 1:
                raise CiboCapitalManagementError(
                    f"portfolio surface {name} outside [0,1]"
                )
        if self.outcome_used or self.productive_authority:
            raise CiboCapitalManagementError(
                "portfolio surface sensor cannot use outcomes or authority"
            )


def _dt(value: object) -> datetime:
    if not isinstance(value, str):
        raise CiboCapitalManagementError(
            "portfolio surface timestamp must be string"
        )
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise CiboCapitalManagementError(
            "portfolio surface timestamp must be timezone-aware"
        )
    return result


def _ratio(num: int, den: int) -> Decimal:
    if den <= 0:
        return Decimal(0)
    return Decimal(num) / Decimal(den)


def measure_portfolio_competition_surface(
    decision_trace: dict[str, Any],
) -> CiboPortfolioCompetitionSurfaceReport:
    rows = decision_trace.get("opportunities")
    if not isinstance(rows, list):
        raise CiboCapitalManagementError(
            "portfolio surface requires decision-trace opportunities"
        )

    eligible = []
    by_epoch: dict[str, list[dict[str, Any]]] = {}
    intervals: list[tuple[datetime, datetime, str]] = []

    for row in rows:
        if not isinstance(row, dict):
            raise CiboCapitalManagementError(
                "portfolio surface opportunity row must be object"
            )
        expectation = row.get("expectation")
        context = row.get("context_quality")
        allocation = row.get("allocation")
        if (
            not isinstance(expectation, dict)
            or not isinstance(context, dict)
            or not isinstance(allocation, dict)
        ):
            raise CiboCapitalManagementError(
                "portfolio surface row surfaces missing"
            )
        ev = Decimal(str(expectation.get("expected_net_value_usd", "0")))
        if not ev.is_finite():
            raise CiboCapitalManagementError(
                "portfolio surface expectation must be finite"
            )
        if ev > 0 and context.get("disposition") == "ALLOW":
            eligible.append(row)
            epoch_id = str(row.get("decision_epoch_id", ""))
            by_epoch.setdefault(epoch_id, []).append(row)

        if bool(allocation.get("selected_by_cibo_policy")):
            settlement = row.get("settlement")
            if isinstance(settlement, dict):
                deployed = settlement.get("capital_deployed_at")
                released = settlement.get("capital_released_at")
                if deployed and released:
                    intervals.append(
                        (
                            _dt(deployed),
                            _dt(released),
                            str(row.get("signal_fingerprint", "")),
                        )
                    )

    same_epoch_count = 0
    open_position_count = 0
    any_count = 0
    max_new = 0
    max_open = 0

    for row in eligible:
        epoch_rows = by_epoch.get(str(row.get("decision_epoch_id", "")), [])
        simultaneous_new = max(0, len(epoch_rows) - 1)
        max_new = max(max_new, len(epoch_rows))
        when = _dt(row.get("market_decision_at"))
        fingerprint = str(row.get("signal_fingerprint", ""))
        active = sum(
            start < when < end and position_id != fingerprint
            for start, end, position_id in intervals
        )
        max_open = max(max_open, active)
        has_same_epoch = simultaneous_new > 0
        has_open = active > 0
        same_epoch_count += int(has_same_epoch)
        open_position_count += int(has_open)
        any_count += int(has_same_epoch or has_open)

    total = len(eligible)
    return CiboPortfolioCompetitionSurfaceReport(
        positive_context_allowed_count=total,
        same_epoch_competition_count=same_epoch_count,
        open_position_competition_count=open_position_count,
        no_competition_count=total - any_count,
        maximum_simultaneous_new_opportunities=max_new,
        maximum_open_positions_at_decision=max_open,
        same_epoch_competition_rate=_ratio(same_epoch_count, total),
        open_position_competition_rate=_ratio(open_position_count, total),
        any_competition_rate=_ratio(any_count, total),
    )
