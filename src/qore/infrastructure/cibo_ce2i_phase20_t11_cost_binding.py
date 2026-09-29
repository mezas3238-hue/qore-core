"""Fresh T11 realized entry-cost and quoted-spread binding audit.

This audit binds three evidence planes without promoting CE2I T11:

1. the fresh FORWARD_OBSERVED candidate/provider snapshot sealed pre-decision;
2. the reconciled executed-risk evidence for the filled position; and
3. the broker-derived CMA settlement book, where entry deal commission is
   persisted as CTRADER_DEMO_ENTRY_COST_SETTLEMENT.

The provider snapshot supplies the quoted spread at decision time. The
settlement book supplies realized entry commission. These are deliberately kept
separate: a quoted spread is not relabeled as a separately identified realized
spread component, and no current DEMO observation is projected onto 2017.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    VersionedPhase20ExecutedRiskBook,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_forward_population import (
    iter_phase20_forward_candidate_facts,
)
from qore.infrastructure.cibo_cma_settlement_store import (
    VersionedCmaSettlementBook,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    normalize_provider_economics,
)


@dataclass(frozen=True, slots=True)
class Phase20T11CostBindingAudit:
    execution_instances: int
    provider_spread_bound_instances: int
    settlement_bound_instances: int
    realized_entry_commission_instances: int
    terminal_settlement_instances: int
    unbound_execution_instances: int
    total_predecision_quoted_spread_usd: Decimal
    mean_predecision_quoted_spread_usd: Decimal | None
    total_realized_entry_commission_usd: Decimal
    mean_realized_entry_commission_usd: Decimal | None
    quoted_spread_coverage_complete: bool
    realized_entry_commission_coverage_complete: bool
    realized_spread_component_identified: bool
    historical_2017_execution_terms_proven: bool
    execution_cost_model_ready: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "execution_instances",
            "provider_spread_bound_instances",
            "settlement_bound_instances",
            "realized_entry_commission_instances",
            "terminal_settlement_instances",
            "unbound_execution_instances",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T11 cost binding {name} must be non-negative int"
                )
        for name in (
            "provider_spread_bound_instances",
            "settlement_bound_instances",
            "realized_entry_commission_instances",
            "terminal_settlement_instances",
            "unbound_execution_instances",
        ):
            if getattr(self, name) > self.execution_instances:
                raise CiboCapitalManagementError(
                    f"Phase20 T11 cost binding {name} exceeds executions"
                )
        if (
            self.provider_spread_bound_instances
            + self.unbound_execution_instances
            != self.execution_instances
        ):
            raise CiboCapitalManagementError(
                "Phase20 T11 provider binding accounting drift"
            )
        for name in (
            "total_predecision_quoted_spread_usd",
            "total_realized_entry_commission_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"Phase20 T11 cost binding {name} must be finite Decimal"
                )
        if self.total_predecision_quoted_spread_usd < 0:
            raise CiboCapitalManagementError(
                "Phase20 T11 quoted spread total cannot be negative"
            )
        for name in (
            "mean_predecision_quoted_spread_usd",
            "mean_realized_entry_commission_usd",
        ):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, Decimal) or not value.is_finite()
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T11 cost binding {name} must be finite Decimal/null"
                )
        for name in (
            "quoted_spread_coverage_complete",
            "realized_entry_commission_coverage_complete",
            "realized_spread_component_identified",
            "historical_2017_execution_terms_proven",
            "execution_cost_model_ready",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"Phase20 T11 cost binding {name} must be bool"
                )
        if (
            self.realized_spread_component_identified
            or self.historical_2017_execution_terms_proven
            or self.execution_cost_model_ready
        ):
            raise CiboCapitalManagementError(
                "Phase20 T11 cost binding audit cannot promote execution economics"
            )


def assess_phase20_t11_cost_binding(
    *,
    evidence_book,
    executed_risk_book: VersionedPhase20ExecutedRiskBook,
    settlement_book: VersionedCmaSettlementBook,
) -> Phase20T11CostBindingAudit:
    """Bind fresh executed positions to quoted spread and realized commission."""

    if not isinstance(executed_risk_book, VersionedPhase20ExecutedRiskBook):
        raise CiboCapitalManagementError(
            "Phase20 T11 cost binding requires canonical executed-risk book"
        )
    if not isinstance(settlement_book, VersionedCmaSettlementBook):
        raise CiboCapitalManagementError(
            "Phase20 T11 cost binding requires canonical settlement book"
        )

    facts = iter_phase20_forward_candidate_facts(
        evidence_book=evidence_book,
    )
    fact_by_key = {}
    for fact in facts:
        key = (
            fact.decision_sha256,
            fact.opportunity.signal_fingerprint,
        )
        if key in fact_by_key:
            raise CiboCapitalManagementError(
                "Phase20 T11 candidate/provider fact is duplicated"
            )
        fact_by_key[key] = fact

    execution_instances = 0
    provider_bound = 0
    settlement_bound = 0
    commission_bound = 0
    terminal_bound = 0
    unbound = 0
    quoted_spreads: list[Decimal] = []
    commissions: list[Decimal] = []

    for execution in executed_risk_book.evidences:
        if not execution.fill_reconciled or not execution.mutation_outcome_known:
            continue
        execution_instances += 1
        key = (
            execution.decision_evidence_sha256,
            execution.signal_fingerprint,
        )
        fact = fact_by_key.get(key)
        if fact is None:
            unbound += 1
            continue
        if fact.opportunity.qore_symbol != execution.qore_symbol:
            raise CiboCapitalManagementError(
                "Phase20 T11 execution/provider QORE symbol mismatch"
            )
        normalized = normalize_provider_economics(
            opportunity=fact.opportunity,
            observation=fact.provider_observation,
        )
        quoted_spreads.append(
            normalized.spread_cost_per_volume_usd
            * execution.filled_source_volume
        )
        provider_bound += 1

        settlement = settlement_book.state_for(
            signal_fingerprint=execution.signal_fingerprint,
            position_id=execution.position_id,
        )
        if settlement is None:
            continue
        settlement_bound += 1
        if settlement.position_closed:
            terminal_bound += 1
        entry_cost_records = tuple(
            record
            for record in settlement.records
            if record.event == "CTRADER_DEMO_ENTRY_COST_SETTLEMENT"
        )
        if not entry_cost_records:
            continue
        commissions.append(
            sum(
                (record.net_profit_usd for record in entry_cost_records),
                Decimal(0),
            )
        )
        commission_bound += 1

    quoted_complete = (
        execution_instances > 0
        and provider_bound == execution_instances
        and unbound == 0
    )
    commission_complete = (
        execution_instances > 0
        and commission_bound == execution_instances
    )

    blockers: list[str] = []
    if execution_instances == 0:
        blockers.append("NO_FRESH_FORWARD_EXECUTION_INSTANCES")
    if unbound:
        blockers.append(
            "T11_EXECUTION_PROVIDER_FACT_BINDING_INCOMPLETE:"
            f"{provider_bound}/{execution_instances}"
        )
    if commission_bound != execution_instances:
        blockers.append(
            "T11_REALIZED_ENTRY_COMMISSION_COVERAGE_INCOMPLETE:"
            f"{commission_bound}/{execution_instances}"
        )
    blockers.extend(
        (
            "REALIZED_SPREAD_COMPONENT_NOT_SEPARATELY_IDENTIFIED",
            "EMPIRICAL_EXECUTION_POPULATION_DOES_NOT_PROVE_2017_TERMS",
            "T11_EXECUTION_EFFICIENCY_POLICY_NOT_IDENTIFIED",
        )
    )

    return Phase20T11CostBindingAudit(
        execution_instances=execution_instances,
        provider_spread_bound_instances=provider_bound,
        settlement_bound_instances=settlement_bound,
        realized_entry_commission_instances=commission_bound,
        terminal_settlement_instances=terminal_bound,
        unbound_execution_instances=unbound,
        total_predecision_quoted_spread_usd=sum(
            quoted_spreads,
            Decimal(0),
        ),
        mean_predecision_quoted_spread_usd=_mean(quoted_spreads),
        total_realized_entry_commission_usd=sum(
            commissions,
            Decimal(0),
        ),
        mean_realized_entry_commission_usd=_mean(commissions),
        quoted_spread_coverage_complete=quoted_complete,
        realized_entry_commission_coverage_complete=commission_complete,
        realized_spread_component_identified=False,
        historical_2017_execution_terms_proven=False,
        execution_cost_model_ready=False,
        blockers=tuple(blockers),
    )


def _mean(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    return sum(values, Decimal(0)) / Decimal(len(values))
