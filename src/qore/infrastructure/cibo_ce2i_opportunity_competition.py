"""CE2I T09/T18 opportunity competition and cross-Trader allocation.

Pure research allocator. It compares simultaneous valid CIBO opportunities
under shared risk/margin/concentration budgets. Trader identity never grants a
fixed capital quota or score bonus.

No capital reservation and no broker mutation occur here.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


@dataclass(frozen=True, slots=True)
class CapitalOpportunityCandidate:
    signal_fingerprint: str
    trader_id: TraderLineage
    qore_symbol: str
    provider_symbol: str
    expected_net_value_usd: Decimal
    stop_risk_usd: Decimal
    margin_usd: Decimal
    expected_capital_minutes: Decimal
    concentration_group: str
    concentration_risk_usd: Decimal
    optionality_cost_usd: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        for name in (
            "signal_fingerprint",
            "qore_symbol",
            "provider_symbol",
            "concentration_group",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise CiboCapitalManagementError(f"{name} must be non-empty")
        if type(self.trader_id) is not TraderLineage:
            raise CiboCapitalManagementError(
                "trader_id must be TraderLineage"
            )
        for name in (
            "expected_net_value_usd",
            "stop_risk_usd",
            "margin_usd",
            "expected_capital_minutes",
            "concentration_risk_usd",
            "optionality_cost_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"{name} must be finite Decimal"
                )
        for name in (
            "stop_risk_usd",
            "margin_usd",
            "expected_capital_minutes",
            "concentration_risk_usd",
        ):
            if getattr(self, name) <= 0:
                raise CiboCapitalManagementError(
                    f"{name} must be positive"
                )
        if self.optionality_cost_usd < 0:
            raise CiboCapitalManagementError(
                "optionality_cost_usd must be non-negative"
            )
        if self.concentration_risk_usd > self.stop_risk_usd:
            raise CiboCapitalManagementError(
                "concentration risk cannot exceed stop risk"
            )

    @property
    def adjusted_net_value_usd(self) -> Decimal:
        return self.expected_net_value_usd - self.optionality_cost_usd

    @property
    def net_value_per_risk_usd(self) -> Decimal:
        return self.adjusted_net_value_usd / self.stop_risk_usd

    @property
    def net_value_per_risk_minute(self) -> Decimal:
        return self.adjusted_net_value_usd / (
            self.stop_risk_usd * self.expected_capital_minutes
        )


@dataclass(frozen=True, slots=True)
class OpportunityAllocationBudget:
    stop_risk_headroom_usd: Decimal
    margin_headroom_usd: Decimal
    concentration_limit_by_group: tuple[tuple[str, Decimal], ...]

    def __post_init__(self) -> None:
        for name in ("stop_risk_headroom_usd", "margin_headroom_usd"):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"{name} must be finite non-negative Decimal"
                )
        groups = tuple(name for name, _ in self.concentration_limit_by_group)
        if len(groups) != len(set(groups)):
            raise CiboCapitalManagementError(
                "duplicate concentration group budget"
            )
        for group, limit in self.concentration_limit_by_group:
            if not group:
                raise CiboCapitalManagementError(
                    "concentration group name required"
                )
            if (
                not isinstance(limit, Decimal)
                or not limit.is_finite()
                or limit < 0
            ):
                raise CiboCapitalManagementError(
                    "concentration limit must be finite non-negative Decimal"
                )

    def concentration_limit(self, group: str) -> Decimal | None:
        for name, limit in self.concentration_limit_by_group:
            if name == group:
                return limit
        return None


@dataclass(frozen=True, slots=True)
class OpportunityAllocationRow:
    rank: int
    signal_fingerprint: str
    trader_id: TraderLineage
    qore_symbol: str
    selected: bool
    adjusted_net_value_usd: Decimal
    net_value_per_risk_usd: Decimal
    net_value_per_risk_minute: Decimal
    reason: str


@dataclass(frozen=True, slots=True)
class OpportunityAllocationDecision:
    rows: tuple[OpportunityAllocationRow, ...]
    selected_signal_fingerprints: tuple[str, ...]
    used_stop_risk_usd: Decimal
    used_margin_usd: Decimal
    concentration_used_by_group: tuple[tuple[str, Decimal], ...]

    def __post_init__(self) -> None:
        selected_from_rows = tuple(
            row.signal_fingerprint for row in self.rows if row.selected
        )
        if selected_from_rows != self.selected_signal_fingerprints:
            raise CiboCapitalManagementError(
                "selected fingerprint summary mismatch"
            )


def allocate_competing_opportunities(
    candidates: tuple[CapitalOpportunityCandidate, ...],
    budget: OpportunityAllocationBudget,
) -> OpportunityAllocationDecision:
    """Greedy V1 allocation by positive net value per risk-minute.

    This is deterministic and causal but not claimed to be a globally optimal
    knapsack solver. Later Capital Opportunity Graph work may replace it.
    """

    if not candidates:
        return OpportunityAllocationDecision(
            rows=(),
            selected_signal_fingerprints=(),
            used_stop_risk_usd=Decimal(0),
            used_margin_usd=Decimal(0),
            concentration_used_by_group=(),
        )
    if not isinstance(budget, OpportunityAllocationBudget):
        raise CiboCapitalManagementError(
            "budget must be OpportunityAllocationBudget"
        )
    fingerprints = tuple(item.signal_fingerprint for item in candidates)
    if len(fingerprints) != len(set(fingerprints)):
        raise CiboCapitalManagementError(
            "duplicate opportunity signal_fingerprint"
        )

    ranked = sorted(
        candidates,
        key=lambda item: (
            -item.net_value_per_risk_minute,
            -item.net_value_per_risk_usd,
            -item.adjusted_net_value_usd,
            item.signal_fingerprint,
        ),
    )

    used_risk = Decimal(0)
    used_margin = Decimal(0)
    concentration_used: dict[str, Decimal] = {}
    rows: list[OpportunityAllocationRow] = []

    for rank, candidate in enumerate(ranked, start=1):
        selected = False
        reason: str
        group_used = concentration_used.get(
            candidate.concentration_group,
            Decimal(0),
        )
        group_limit = budget.concentration_limit(
            candidate.concentration_group
        )

        if candidate.adjusted_net_value_usd <= 0:
            reason = "non-positive adjusted expected net value"
        elif used_risk + candidate.stop_risk_usd > budget.stop_risk_headroom_usd:
            reason = "shared stop-risk headroom exhausted"
        elif used_margin + candidate.margin_usd > budget.margin_headroom_usd:
            reason = "shared margin headroom exhausted"
        elif (
            group_limit is not None
            and group_used + candidate.concentration_risk_usd > group_limit
        ):
            reason = "concentration-group risk limit exceeded"
        else:
            selected = True
            reason = "selected by positive net value per risk-minute"
            used_risk += candidate.stop_risk_usd
            used_margin += candidate.margin_usd
            concentration_used[candidate.concentration_group] = (
                group_used + candidate.concentration_risk_usd
            )

        rows.append(
            OpportunityAllocationRow(
                rank=rank,
                signal_fingerprint=candidate.signal_fingerprint,
                trader_id=candidate.trader_id,
                qore_symbol=candidate.qore_symbol,
                selected=selected,
                adjusted_net_value_usd=candidate.adjusted_net_value_usd,
                net_value_per_risk_usd=candidate.net_value_per_risk_usd,
                net_value_per_risk_minute=candidate.net_value_per_risk_minute,
                reason=reason,
            )
        )

    selected = tuple(
        row.signal_fingerprint for row in rows if row.selected
    )
    return OpportunityAllocationDecision(
        rows=tuple(rows),
        selected_signal_fingerprints=selected,
        used_stop_risk_usd=used_risk,
        used_margin_usd=used_margin,
        concentration_used_by_group=tuple(sorted(concentration_used.items())),
    )
