"""Execute one simultaneous CIBO ceiling-discovery epoch through Native MAX and Risk.

This is the chronology/authority kernel for the single-account ceiling runner.
It deliberately does not construct market evidence, economic twins or settlement
outcomes. Trader Lab adapters must build those from causal evidence. This kernel
only:
- evaluates every opportunity with the full simultaneous opportunity surface;
- lets Native MAX derive MPC worlds from its own cognition when none are supplied;
- preserves CIBO portfolio priority before QORE Risk serialization;
- records one canonical decision receipt per opportunity.

No order submission, broker mutation, LIVE/production authority or outcome
consumption exists here.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    AccountWideRiskEngine,
    RiskAuthorization,
    RiskDecision,
)
from qore.infrastructure.cibo_account_capital_mission import (
    CiboCapitalMissionPolicy,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    CiboCapitalState,
    TraderOpportunityEnvelope,
    minimum_seed_volume,
)
from qore.infrastructure.cibo_ce2i_regime_selector import CiboCapitalRegimeState
from qore.infrastructure.cibo_ceiling_ablation import CiboCeilingAblationMode
from qore.infrastructure.cibo_economic_engine_wiring import CiboLifecycleWireRequest
from qore.infrastructure.cibo_full_economic_digital_twin import (
    CiboObservedEconomicTwin,
)
from qore.infrastructure.cibo_multi_period_capital_mpc import (
    Genc11KnownOptionSchedule,
    Genc11WorldPath,
)
from qore.infrastructure.cibo_native_sovereign_capital_runtime import (
    CiboNativeSovereignCapitalDecision,
    run_cibo_native_sovereign_capital_runtime,
)
from qore.infrastructure.cibo_single_account_sovereign_ceiling_run import (
    CiboSovereignCeilingDecisionReceipt,
    decision_receipt_from_native_runtime,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCapitalManagementError(
            f"sovereign ceiling epoch {name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class CiboSovereignCeilingEpochResult:
    decision_epoch_id: str
    decision_receipts: tuple[CiboSovereignCeilingDecisionReceipt, ...]
    native_decisions: tuple[CiboNativeSovereignCapitalDecision, ...]
    risk_authorizations: tuple[RiskAuthorization, ...]
    risk_submission_order: tuple[str, ...]
    provider_cost_reserve_usd: Decimal = Decimal(0)
    full_simultaneous_surface_used: bool = True
    outcome_used_for_predecision: bool = False
    broker_mutation: bool = False

    def __post_init__(self) -> None:
        if not self.decision_epoch_id:
            raise CiboCapitalManagementError(
                "sovereign ceiling epoch result identity is required"
            )
        count = len(self.decision_receipts)
        if count != len(self.native_decisions):
            raise CiboCapitalManagementError(
                "sovereign ceiling epoch runtime/receipt count drift"
            )
        receipt_signals = tuple(
            item.signal_fingerprint for item in self.decision_receipts
        )
        if len(receipt_signals) != len(set(receipt_signals)):
            raise CiboCapitalManagementError(
                "sovereign ceiling epoch duplicate receipt signal"
            )
        if len(self.risk_submission_order) != len(
            set(self.risk_submission_order)
        ):
            raise CiboCapitalManagementError(
                "sovereign ceiling epoch Risk order contains duplicates"
            )
        if (
            not isinstance(self.provider_cost_reserve_usd, Decimal)
            or not self.provider_cost_reserve_usd.is_finite()
            or self.provider_cost_reserve_usd < 0
        ):
            raise CiboCapitalManagementError(
                "sovereign ceiling provider cost reserve must be non-negative"
            )
        if any(
            type(getattr(self, name)) is not bool
            for name in (
                "full_simultaneous_surface_used",
                "outcome_used_for_predecision",
                "broker_mutation",
            )
        ):
            raise CiboCapitalManagementError(
                "sovereign ceiling epoch governance flags malformed"
            )
        if (
            not self.full_simultaneous_surface_used
            or self.outcome_used_for_predecision
            or self.broker_mutation
        ):
            raise CiboCapitalManagementError(
                "sovereign ceiling epoch governance violated"
            )


def _provider_cost_per_volume(
    *,
    opportunity: TraderOpportunityEnvelope,
    option_id: str,
    twin: CiboObservedEconomicTwin,
) -> Decimal:
    rows = tuple(
        item for item in twin.opportunities if item.option_id == option_id
    )
    if len(rows) != 1:
        raise CiboCapitalManagementError(
            "sovereign ceiling provider cost option missing from twin"
        )
    minimum_volume = minimum_seed_volume(opportunity)
    provider_cost = rows[0].provider_cost_usd
    if (
        not isinstance(provider_cost, Decimal)
        or not provider_cost.is_finite()
        or provider_cost < 0
    ):
        raise CiboCapitalManagementError(
            "sovereign ceiling provider cost must be finite non-negative"
        )
    return provider_cost / minimum_volume


def _risk_priority(
    native_decision: CiboNativeSovereignCapitalDecision,
) -> tuple[Decimal, Decimal, Decimal]:
    """Rank Risk-ready requests by causal portfolio utility, not row order."""

    capital = native_decision.capital
    lines = tuple(
        item
        for item in capital.economic_run.portfolio_plan.lines
        if item.option_id == capital.option_id
    )
    if len(lines) != 1:
        raise CiboCapitalManagementError(
            "sovereign ceiling Risk priority target missing from portfolio plan"
        )
    line = lines[0]
    velocity = line.expected_net_utility_usd / line.expected_capital_minutes
    return (
        velocity,
        line.expected_net_utility_usd,
        -line.stop_risk_usd,
    )


def execute_sovereign_ceiling_epoch(
    *,
    decision_epoch_id: str,
    decision_at: datetime,
    expires_at: datetime,
    opportunities: tuple[TraderOpportunityEnvelope, ...],
    option_id_by_signal: tuple[tuple[str, str], ...],
    twin: CiboObservedEconomicTwin,
    capital: CiboCapitalState,
    regime_state: CiboCapitalRegimeState,
    evidence_ref: CiboEvidenceRef,
    mission_policy: CiboCapitalMissionPolicy,
    risk_snapshot: AccountRiskSnapshot,
    risk_engine: AccountWideRiskEngine,
    survival_capital_usd: Decimal,
    protected_capital_usd: Decimal,
    world_paths: tuple[Genc11WorldPath, ...] = (),
    option_schedules: tuple[Genc11KnownOptionSchedule, ...] = (),
    lifecycle_requests: tuple[CiboLifecycleWireRequest, ...] = (),
    ablation_mode: CiboCeilingAblationMode = CiboCeilingAblationMode.FULL,
) -> CiboSovereignCeilingEpochResult:
    """Execute one complete simultaneous epoch without outcome knowledge."""

    if not decision_epoch_id:
        raise CiboCapitalManagementError(
            "sovereign ceiling decision_epoch_id is required"
        )
    _aware(decision_at, "decision_at")
    _aware(expires_at, "expires_at")
    if expires_at <= decision_at:
        raise CiboCapitalManagementError(
            "sovereign ceiling epoch expiry must follow decision"
        )
    if not opportunities or any(
        not isinstance(item, TraderOpportunityEnvelope)
        for item in opportunities
    ):
        raise CiboCapitalManagementError(
            "sovereign ceiling epoch requires canonical opportunities"
        )
    signals = tuple(item.signal_fingerprint for item in opportunities)
    if len(signals) != len(set(signals)):
        raise CiboCapitalManagementError(
            "sovereign ceiling epoch duplicate opportunity signal"
        )
    mapping = dict(option_id_by_signal)
    if (
        len(mapping) != len(option_id_by_signal)
        or set(mapping) != set(signals)
        or any(not value for value in mapping.values())
    ):
        raise CiboCapitalManagementError(
            "sovereign ceiling epoch option mapping must cover exact signals"
        )
    if len(set(mapping.values())) != len(mapping):
        raise CiboCapitalManagementError(
            "sovereign ceiling epoch option ids must be unique"
        )
    if (
        not isinstance(regime_state, CiboCapitalRegimeState)
        or regime_state.opportunity_count != len(opportunities)
    ):
        raise CiboCapitalManagementError(
            "sovereign ceiling epoch regime/opportunity surface drift"
        )
    if (
        not isinstance(twin, CiboObservedEconomicTwin)
        or twin.captured_at != decision_at
    ):
        raise CiboCapitalManagementError(
            "sovereign ceiling epoch twin must match decision time"
        )
    if set(mapping.values()) != {
        item.option_id for item in twin.opportunities
    }:
        raise CiboCapitalManagementError(
            "sovereign ceiling epoch twin/option surface drift"
        )
    if bool(world_paths) != bool(option_schedules):
        raise CiboCapitalManagementError(
            "sovereign ceiling epoch MPC worlds/schedules must pair"
        )
    for name, value in (
        ("survival_capital_usd", survival_capital_usd),
        ("protected_capital_usd", protected_capital_usd),
    ):
        if (
            not isinstance(value, Decimal)
            or not value.is_finite()
            or value < 0
        ):
            raise CiboCapitalManagementError(
                f"sovereign ceiling epoch {name} invalid"
            )

    native_by_signal: dict[str, CiboNativeSovereignCapitalDecision] = {}
    opportunity_by_signal = {
        item.signal_fingerprint: item for item in opportunities
    }

    # Phase A: CIBO thinks about the complete simultaneous surface before Risk
    # serialization. Every target sees the exact same causal opportunity tuple.
    for opportunity in sorted(
        opportunities,
        key=lambda item: (
            mapping[item.signal_fingerprint],
            item.signal_fingerprint,
        ),
    ):
        signal = opportunity.signal_fingerprint
        native_by_signal[signal] = run_cibo_native_sovereign_capital_runtime(
            decision_id=f"{decision_epoch_id}:{signal}",
            option_id=mapping[signal],
            opportunity=opportunity,
            simultaneous_opportunities=opportunities,
            twin=twin,
            world_paths=world_paths,
            option_schedules=option_schedules,
            mission_policy=mission_policy,
            capital=capital,
            regime_state=regime_state,
            evidence_ref=evidence_ref,
            survival_capital_usd=survival_capital_usd,
            protected_capital_usd=protected_capital_usd,
            request_id=f"{decision_epoch_id}:{signal}:risk",
            requested_at=decision_at,
            expires_at=expires_at,
            lifecycle_requests=lifecycle_requests,
            ablation_mode=ablation_mode,
        )

    # Phase B: only Risk-ready requests enter QORE Risk. Submit the strongest
    # causal portfolio utility first so simultaneous rows do not acquire capital
    # merely because of arbitrary manifest order.
    risk_ready = [
        (signal, native)
        for signal, native in native_by_signal.items()
        if native.capital.risk_request is not None
    ]
    risk_ready.sort(
        key=lambda item: (
            -_risk_priority(item[1])[0],
            -_risk_priority(item[1])[1],
            -_risk_priority(item[1])[2],
            mapping[item[0]],
            item[0],
        )
    )

    authorization_by_signal: dict[str, RiskAuthorization] = {}
    risk_order: list[str] = []
    provider_cost_reserve = Decimal(0)
    for signal, native in risk_ready:
        request = native.capital.risk_request
        assert request is not None
        cost_per_volume = _provider_cost_per_volume(
            opportunity=opportunity_by_signal[signal],
            option_id=mapping[signal],
            twin=twin,
        )
        requested_cost = cost_per_volume * request.requested_volume
        total_cost_reserve = provider_cost_reserve + requested_cost
        available_for_stop_after_cost = max(
            Decimal(0),
            risk_snapshot.qore_authorizable_headroom
            - total_cost_reserve,
        )
        cost_reserved_snapshot = replace(
            risk_snapshot,
            equity=max(
                Decimal(0),
                risk_snapshot.equity - total_cost_reserve,
            ),
            free_margin=max(
                Decimal(0),
                risk_snapshot.free_margin - total_cost_reserve,
            ),
            qore_authorizable_headroom=available_for_stop_after_cost,
        )
        authorization = risk_engine.authorize(
            request,
            cost_reserved_snapshot,
            now=decision_at,
        )
        authorization_by_signal[signal] = authorization
        risk_order.append(signal)
        if authorization.decision in {
            RiskDecision.ALLOW,
            RiskDecision.REDUCE,
        }:
            provider_cost_reserve += (
                cost_per_volume * authorization.authorized_volume
            )

    receipts = tuple(
        decision_receipt_from_native_runtime(
            decision_epoch_id=decision_epoch_id,
            decided_at=decision_at,
            opportunity=opportunity,
            native_decision=native_by_signal[opportunity.signal_fingerprint],
            risk_authorization=authorization_by_signal.get(
                opportunity.signal_fingerprint
            ),
        )
        for opportunity in opportunities
    )
    native_decisions = tuple(
        native_by_signal[item.signal_fingerprint] for item in opportunities
    )
    authorizations = tuple(
        authorization_by_signal[signal] for signal in risk_order
    )

    return CiboSovereignCeilingEpochResult(
        decision_epoch_id=decision_epoch_id,
        decision_receipts=receipts,
        native_decisions=native_decisions,
        risk_authorizations=authorizations,
        risk_submission_order=tuple(risk_order),
        provider_cost_reserve_usd=provider_cost_reserve,
        full_simultaneous_surface_used=True,
        outcome_used_for_predecision=False,
        broker_mutation=False,
    )
