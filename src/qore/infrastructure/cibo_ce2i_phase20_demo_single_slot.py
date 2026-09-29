"""Single-slot cTrader DEMO forward observer for VT31 and VT08.

VT31 NAS100 and VT08 FOREX do not share the five-market M5 decision epoch.
This adapter preserves their sovereign clocks by sealing one Trader/symbol slot
per genuine decision boundary into the common Phase20D evidence/policy stores.

Because a single-slot boundary does not itself provide trustworthy cross-market
volatility/correlation evidence, the frozen regime adapter is deliberately
conservative: unknown cross-market context is represented as ELEVATED
volatility + CONCENTRATED correlation, yielding WATCH (or stricter if current
Risk/provider state requires it). It never invents a NORMAL regime.

Research-only. No sizing, Risk authorization or broker-mutation authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.account_wide_risk_ledger import (
    DurableAccountWideRiskEngine,
)
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_capital_source_ledger_store import (
    VersionedCapitalSourceLedger,
)
from qore.infrastructure.cibo_ce2i_advanced_evidence import (
    AdvancedCe2iEvidenceSnapshot,
)
from qore.infrastructure.cibo_ce2i_phase20_demo_shadow_risk import (
    build_demo_capability_risk_snapshot,
    observe_demo_capability_constraints,
)
from qore.infrastructure.cibo_ce2i_phase20_epoch_aggregator import (
    Phase20DecisionEpochAggregator,
    Phase20DecisionEpochSlot,
)
from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    VersionedPhase20ExecutedRiskBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_epoch import (
    Phase20ForwardCollectedEpoch,
    Phase20ForwardEpochResult,
    Phase20ForwardObservedOpportunity,
    seal_phase20_forward_observed_epoch_from_snapshots,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardKnownOptionEvidence,
    Phase20ForwardPopulationDisposition,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    DurablePhase20ForwardPolicyStore,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_snapshots import (
    build_phase20_forward_snapshot_bundle,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    DurablePhase20ForwardEvidenceStore,
)
from qore.infrastructure.cibo_ce2i_phase20_mpc import (
    Phase20MpcKnownOption,
)
from qore.infrastructure.cibo_ce2i_phase20_shadow_observer import (
    Phase20ForwardShadowObservation,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_runtime_shadow import (
    Phase20T13RuntimeShadowSeal,
    seal_phase20_t13_runtime_shadow,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_store import (
    DurableT13ShadowDecisionStore,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_treatment_store import (
    DurableT13ShadowTreatmentStore,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ctrader_demo_economic_observation,
    normalize_provider_economics,
)
from qore.infrastructure.ctrader_demo_compat import (
    CTraderDemoAccountState,
    CTraderDemoSymbolSpecification,
)

PHASE20_DEMO_SINGLE_SLOT_REGIME_ID = (
    "CIBO_PHASE20D_DEMO_SINGLE_SLOT_REGIME_V1"
)
_MAX_PROVIDER_AGE_SECONDS = Decimal("2")
_THIN_SPREAD_TO_STOP = Decimal("0.10")
_STRESSED_SPREAD_TO_STOP = Decimal("0.25")


@dataclass(frozen=True, slots=True)
class Phase20DemoSingleSlotTerminal:
    trader_id: TraderLineage
    qore_symbol: str
    observed_at: datetime
    disposition: Phase20ForwardPopulationDisposition
    reason: str
    opportunity: Phase20ForwardObservedOpportunity | None = None

    def __post_init__(self) -> None:
        if type(self.trader_id) is not TraderLineage:
            raise CiboCapitalManagementError(
                "Phase20D single-slot Trader identity must be canonical"
            )
        if not self.qore_symbol or not self.reason:
            raise CiboCapitalManagementError(
                "Phase20D single-slot symbol/reason are required"
            )
        _aware(self.observed_at, name="terminal observed_at")
        if type(self.disposition) is not Phase20ForwardPopulationDisposition:
            raise CiboCapitalManagementError(
                "Phase20D single-slot disposition must be canonical"
            )
        if self.disposition is Phase20ForwardPopulationDisposition.CANDIDATE:
            if not isinstance(
                self.opportunity,
                Phase20ForwardObservedOpportunity,
            ):
                raise CiboCapitalManagementError(
                    "Phase20D single-slot candidate requires observed opportunity"
                )
            envelope = self.opportunity.opportunity
            if (
                envelope.trader_id is not self.trader_id
                or envelope.qore_symbol != self.qore_symbol
            ):
                raise CiboCapitalManagementError(
                    "Phase20D single-slot candidate identity mismatch"
                )
        elif self.opportunity is not None:
            raise CiboCapitalManagementError(
                "Phase20D single-slot non-candidate cannot carry opportunity"
            )


@dataclass(frozen=True, slots=True)
class Phase20DemoSingleSlotPrepared:
    result: Phase20ForwardEpochResult
    regime_policy_id: str
    regime_policy_sha256: str
    broker_mutation_performed: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.result, Phase20ForwardEpochResult):
            raise CiboCapitalManagementError(
                "Phase20D single-slot prepared result must be canonical"
            )
        if self.regime_policy_id != PHASE20_DEMO_SINGLE_SLOT_REGIME_ID:
            raise CiboCapitalManagementError(
                "Phase20D single-slot regime policy drift"
            )
        if (
            not self.regime_policy_sha256.startswith("sha256:")
            or len(self.regime_policy_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "Phase20D single-slot regime digest invalid"
            )
        if self.broker_mutation_performed or self.execution_authority:
            raise CiboCapitalManagementError(
                "Phase20D single-slot observer cannot mutate execution"
            )


@dataclass(frozen=True, slots=True)
class Phase20DemoSingleSlotObservation:
    observation: Phase20ForwardShadowObservation
    regime_policy_id: str
    regime_policy_sha256: str
    t13_shadow: Phase20T13RuntimeShadowSeal | None = None
    broker_mutation_performed: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.observation, Phase20ForwardShadowObservation):
            raise CiboCapitalManagementError(
                "Phase20D single-slot observation must be canonical"
            )
        if self.regime_policy_id != PHASE20_DEMO_SINGLE_SLOT_REGIME_ID:
            raise CiboCapitalManagementError(
                "Phase20D single-slot finalized regime policy drift"
            )
        if self.t13_shadow is not None:
            if not isinstance(
                self.t13_shadow,
                Phase20T13RuntimeShadowSeal,
            ):
                raise CiboCapitalManagementError(
                    "Phase20D single-slot T13 shadow must be canonical"
                )
            if (
                self.t13_shadow.decision_evidence_sha256
                != self.observation.collected.result.decision_record.evidence_sha256
            ):
                raise CiboCapitalManagementError(
                    "Phase20D single-slot T13 evidence binding drift"
                )
        if self.broker_mutation_performed or self.execution_authority:
            raise CiboCapitalManagementError(
                "Phase20D single-slot finalized observer cannot mutate execution"
            )


def phase20_demo_single_slot_regime_sha256() -> str:
    payload = {
        "policy_id": PHASE20_DEMO_SINGLE_SLOT_REGIME_ID,
        "max_provider_age_seconds": format(
            _MAX_PROVIDER_AGE_SECONDS,
            "f",
        ),
        "thin_spread_to_stop": format(_THIN_SPREAD_TO_STOP, "f"),
        "stressed_spread_to_stop": format(
            _STRESSED_SPREAD_TO_STOP,
            "f",
        ),
        "unknown_cross_market_volatility": VolatilityState.ELEVATED.value,
        "unknown_cross_market_correlation": CorrelationState.CONCENTRATED.value,
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"sha256:{sha256(raw).hexdigest()}"


def build_ctrader_demo_single_slot_observed_opportunity(
    *,
    opportunity: TraderOpportunityEnvelope,
    provider_spec: CTraderDemoSymbolSpecification,
    observed_at: datetime,
) -> Phase20ForwardObservedOpportunity:
    """Bind a Trader-owned opportunity to contemporaneous cTrader economics."""

    if not isinstance(opportunity, TraderOpportunityEnvelope):
        raise CiboCapitalManagementError(
            "Phase20D single-slot opportunity must be TraderOpportunityEnvelope"
        )
    if not isinstance(provider_spec, CTraderDemoSymbolSpecification):
        raise CiboCapitalManagementError(
            "Phase20D single-slot provider spec must be canonical"
        )
    _aware(observed_at, name="opportunity observed_at")
    if provider_spec.observed_at > observed_at:
        raise CiboCapitalManagementError(
            "Phase20D single-slot provider evidence cannot postdate terminal"
        )
    provider = ctrader_demo_economic_observation(
        qore_symbol=opportunity.qore_symbol,
        provider_key="ctrader-demo",
        spec=provider_spec,
    )
    normalized = normalize_provider_economics(
        opportunity=opportunity,
        observation=provider,
    )
    return Phase20ForwardObservedOpportunity(
        provider_evidence_id=_provider_evidence_id(
            opportunity=opportunity,
            spec=provider_spec,
        ),
        opportunity=opportunity,
        provider_observation=provider,
        concentration_group=f"SYMBOL:{opportunity.qore_symbol}",
        concentration_risk_usd=normalized.minimum_stop_risk_usd,
    )


def build_ctrader_demo_single_slot_known_option(
    *,
    opportunity: TraderOpportunityEnvelope,
    provider_spec: CTraderDemoSymbolSpecification,
    known_as_of: datetime,
    decision_step: int,
    expires_at: datetime | None = None,
) -> Phase20ForwardKnownOptionEvidence:
    """Bind one currently-known contingent option to provider minimum economics."""

    if not isinstance(opportunity, TraderOpportunityEnvelope):
        raise CiboCapitalManagementError(
            "Phase20D single-slot known option must be TraderOpportunityEnvelope"
        )
    if not isinstance(provider_spec, CTraderDemoSymbolSpecification):
        raise CiboCapitalManagementError(
            "Phase20D single-slot known option provider spec must be canonical"
        )
    _aware(known_as_of, name="known option known_as_of")
    if expires_at is not None:
        _aware(expires_at, name="known option expires_at")
        if expires_at <= known_as_of:
            raise CiboCapitalManagementError(
                "Phase20D single-slot known option expiry must follow observation"
            )
    if provider_spec.observed_at > known_as_of:
        raise CiboCapitalManagementError(
            "Phase20D single-slot known option provider evidence postdates observation"
        )
    if type(decision_step) is not int or decision_step < 0:
        raise CiboCapitalManagementError(
            "Phase20D single-slot known option decision_step invalid"
        )
    provider = ctrader_demo_economic_observation(
        qore_symbol=opportunity.qore_symbol,
        provider_key="ctrader-demo",
        spec=provider_spec,
    )
    normalized = normalize_provider_economics(
        opportunity=opportunity,
        observation=provider,
    )
    evidence_id = _known_option_evidence_id(
        opportunity=opportunity,
        spec=provider_spec,
        known_as_of=known_as_of,
        decision_step=decision_step,
    )
    return Phase20ForwardKnownOptionEvidence(
        evidence_id=evidence_id,
        option=Phase20MpcKnownOption(
            opportunity_id=(
                f"known-option:{opportunity.trader_id.value}:"
                f"{opportunity.signal_fingerprint}"
            ),
            decision_step=decision_step,
            minimum_stop_risk_usd=normalized.minimum_stop_risk_usd,
            minimum_margin_usd=normalized.minimum_margin_usd,
        ),
        known_as_of=known_as_of,
        active_at_decision=True,
        expires_at=expires_at,
    )


def prepare_ctrader_demo_single_slot_phase20_epoch(
    *,
    epoch_scope: str,
    opened_at: datetime,
    deadline_at: datetime,
    decision_at: datetime,
    terminal: Phase20DemoSingleSlotTerminal,
    provider_spec: CTraderDemoSymbolSpecification | None,
    evidence_store: DurablePhase20ForwardEvidenceStore,
    account_identity: CiboAccountCapitalIdentity,
    account_state: CTraderDemoAccountState,
    risk: DurableAccountWideRiskEngine,
    executed_risk_book: VersionedPhase20ExecutedRiskBook,
    open_position_ids: tuple[int, ...],
    pending_broker_worst_case_loss_usd: Decimal,
    capital_state: VersionedCapitalSourceLedger,
    highest_closed_balance: Decimal,
    current_step: int,
    advanced_evidence_snapshot: AdvancedCe2iEvidenceSnapshot | None = None,
    known_options: tuple[Phase20ForwardKnownOptionEvidence, ...] = (),
    collector_git_sha: str | None = None,
) -> Phase20DemoSingleSlotPrepared:
    """Seal one sovereign Trader boundary into the common forward evidence book."""

    _aware(opened_at, name="opened_at")
    _aware(deadline_at, name="deadline_at")
    _aware(decision_at, name="decision_at")
    if not isinstance(terminal, Phase20DemoSingleSlotTerminal):
        raise CiboCapitalManagementError(
            "Phase20D single-slot terminal must be canonical"
        )
    if terminal.observed_at < opened_at:
        raise CiboCapitalManagementError(
            "Phase20D single-slot terminal cannot predate epoch open"
        )
    if terminal.disposition is Phase20ForwardPopulationDisposition.CANDIDATE:
        if provider_spec is None:
            raise CiboCapitalManagementError(
                "Phase20D candidate single-slot epoch requires provider evidence"
            )
        assert terminal.opportunity is not None
        if (
            terminal.opportunity.provider_observation.observed_at
            != provider_spec.observed_at
        ):
            raise CiboCapitalManagementError(
                "Phase20D single-slot provider observation drift"
            )

    slot = Phase20DecisionEpochSlot(
        slot_id=f"{terminal.trader_id.value}|{terminal.qore_symbol}",
        trader_id=terminal.trader_id,
        qore_symbol=terminal.qore_symbol,
    )
    aggregator = Phase20DecisionEpochAggregator(
        epoch_scope=epoch_scope,
        opened_at=opened_at,
        deadline_at=deadline_at,
        expected_slots=(slot,),
    )
    if terminal.observed_at <= deadline_at:
        if (
            terminal.disposition
            is Phase20ForwardPopulationDisposition.CANDIDATE
        ):
            assert terminal.opportunity is not None
            aggregator.record_candidate(
                slot_id=slot.slot_id,
                opportunity=terminal.opportunity,
                observed_at=terminal.observed_at,
                reason=terminal.reason,
            )
        else:
            aggregator.record_non_candidate(
                slot_id=slot.slot_id,
                disposition=terminal.disposition,
                observed_at=terminal.observed_at,
                reason=terminal.reason,
            )
    batch = aggregator.seal(decision_at=decision_at)

    open_ids = set(open_position_ids)
    open_risks = tuple(
        item
        for item in executed_risk_book.evidences
        if item.position_id in open_ids
    )
    risk_snapshot = build_demo_capability_risk_snapshot(
        account_binding_id=account_identity.account_ref,
        account_state=account_state,
        open_position_ids=open_position_ids,
        open_executed_risks=open_risks,
        pending_broker_worst_case_loss_usd=(
            pending_broker_worst_case_loss_usd
        ),
    )
    if risk.recovery_required:
        risk.complete_boot_reconciliation(
            risk_snapshot,
            now=batch.decision_at,
            max_snapshot_age=timedelta(seconds=2),
        )
    constraints = observe_demo_capability_constraints(
        risk=risk,
        snapshot=risk_snapshot,
        observed_at=batch.decision_at,
    )
    regime = _single_slot_regime(
        decision_at=batch.decision_at,
        opportunity=(
            None
            if terminal.opportunity is None
            else terminal.opportunity.opportunity
        ),
        provider_spec=provider_spec,
        account_state=account_state,
        aggregate_pre_order_worst_case_usd=(
            constraints.aggregate_pre_order_worst_case_usd
        ),
        highest_closed_balance=highest_closed_balance,
        opportunity_count=len(batch.opportunities),
    )
    snapshots = build_phase20_forward_snapshot_bundle(
        account_snapshot=risk_snapshot,
        risk_constraints=constraints,
        capital_state=capital_state,
        captured_at=account_state.observed_at,
    )
    result = seal_phase20_forward_observed_epoch_from_snapshots(
        store=evidence_store,
        decision_epoch_id=batch.decision_epoch_id,
        decision_at=batch.decision_at,
        account_identity=account_identity,
        snapshots=snapshots,
        concentration_limit_by_group=(),
        regime_state=regime,
        current_step=current_step,
        population_slots=batch.population_slots,
        opportunities=batch.opportunities,
        advanced_evidence_snapshot=advanced_evidence_snapshot,
        seal_deadline_at=batch.deadline_at,
        known_options=known_options,
        collector_git_sha=collector_git_sha,
    )
    return Phase20DemoSingleSlotPrepared(
        result=result,
        regime_policy_id=PHASE20_DEMO_SINGLE_SLOT_REGIME_ID,
        regime_policy_sha256=phase20_demo_single_slot_regime_sha256(),
    )


def finalize_ctrader_demo_single_slot_phase20_policy(
    *,
    prepared: Phase20DemoSingleSlotPrepared,
    evidence_store: DurablePhase20ForwardEvidenceStore,
    policy_store: DurablePhase20ForwardPolicyStore,
    t13_recommendation_store: DurableT13ShadowDecisionStore | None = None,
    t13_treatment_store: DurableT13ShadowTreatmentStore | None = None,
) -> Phase20DemoSingleSlotObservation:
    """Persist a precomputed single-slot policy record without rereading outcomes."""

    if not isinstance(prepared, Phase20DemoSingleSlotPrepared):
        raise CiboCapitalManagementError(
            "Phase20D single-slot finalization requires prepared evidence"
        )
    if (t13_recommendation_store is None) != (
        t13_treatment_store is None
    ):
        raise CiboCapitalManagementError(
            "Phase20D T13 runtime stores must be provided together"
        )
    current = policy_store.load()
    policy_book = policy_store.seal_policy_decision(
        prepared.result.decision_record,
        evidence_store=evidence_store,
        expected_generation=current.generation,
    )
    t13_shadow = None
    if (
        t13_recommendation_store is not None
        and t13_treatment_store is not None
    ):
        t13_shadow = seal_phase20_t13_runtime_shadow(
            evidence=prepared.result.evidence,
            decision_record=prepared.result.decision_record,
            evidence_book=evidence_store.load(),
            policy_book=policy_book,
            recommendation_store=t13_recommendation_store,
            treatment_store=t13_treatment_store,
        )
    collected = Phase20ForwardCollectedEpoch(
        evidence_generation=prepared.result.sealed_generation,
        policy_generation=policy_book.generation,
        result=prepared.result,
    )
    return Phase20DemoSingleSlotObservation(
        observation=Phase20ForwardShadowObservation(collected=collected),
        regime_policy_id=prepared.regime_policy_id,
        regime_policy_sha256=prepared.regime_policy_sha256,
        t13_shadow=t13_shadow,
    )


def _single_slot_regime(
    *,
    decision_at: datetime,
    opportunity: TraderOpportunityEnvelope | None,
    provider_spec: CTraderDemoSymbolSpecification | None,
    account_state: CTraderDemoAccountState,
    aggregate_pre_order_worst_case_usd: Decimal,
    highest_closed_balance: Decimal,
    opportunity_count: int,
) -> CiboCapitalRegimeState:
    provider_condition = ProviderCondition.UNAVAILABLE
    stale = provider_spec is None
    if provider_spec is not None:
        if provider_spec.observed_at > decision_at:
            raise CiboCapitalManagementError(
                "Phase20D single-slot provider evidence postdates decision"
            )
        age = Decimal(
            str((decision_at - provider_spec.observed_at).total_seconds())
        )
        stale = age > _MAX_PROVIDER_AGE_SECONDS
        if not provider_spec.trade_enabled or not provider_spec.session_open:
            provider_condition = ProviderCondition.DEGRADED
        elif stale:
            provider_condition = ProviderCondition.DEGRADED
        else:
            provider_condition = ProviderCondition.HEALTHY

    liquidity = LiquidityState.THIN
    if opportunity is not None and provider_spec is not None:
        stop_distance = abs(
            opportunity.intended_entry - opportunity.stop_loss
        )
        spread = provider_spec.ask - provider_spec.bid
        if stop_distance <= 0:
            raise CiboCapitalManagementError(
                "Phase20D single-slot stop distance invalid"
            )
        spread_to_stop = spread / stop_distance
        if spread_to_stop >= _STRESSED_SPREAD_TO_STOP:
            liquidity = LiquidityState.STRESSED
        elif spread_to_stop >= _THIN_SPREAD_TO_STOP:
            liquidity = LiquidityState.THIN
        else:
            liquidity = LiquidityState.NORMAL
    elif provider_spec is None:
        liquidity = LiquidityState.STRESSED

    if (
        not isinstance(highest_closed_balance, Decimal)
        or not highest_closed_balance.is_finite()
        or highest_closed_balance <= 0
    ):
        raise CiboCapitalManagementError(
            "Phase20D single-slot highest balance must be finite positive"
        )
    risk_utilization = _bounded_ratio(
        max(Decimal(0), aggregate_pre_order_worst_case_usd),
        account_state.equity,
    )
    margin_utilization = _bounded_ratio(
        account_state.margin,
        account_state.margin + account_state.free_margin,
    )
    drawdown_utilization = _bounded_ratio(
        max(Decimal(0), highest_closed_balance - account_state.equity),
        highest_closed_balance,
    )
    return CiboCapitalRegimeState(
        liquidity=liquidity,
        volatility=VolatilityState.ELEVATED,
        correlation=CorrelationState.CONCENTRATED,
        provider_condition=provider_condition,
        risk_utilization=risk_utilization,
        margin_utilization=margin_utilization,
        drawdown_utilization=drawdown_utilization,
        opportunity_count=opportunity_count,
        evidence_stale=stale,
    )


def _known_option_evidence_id(
    *,
    opportunity: TraderOpportunityEnvelope,
    spec: CTraderDemoSymbolSpecification,
    known_as_of: datetime,
    decision_step: int,
) -> str:
    payload = {
        "kind": "PHASE20D_SINGLE_SLOT_KNOWN_OPTION",
        "trader": opportunity.trader_id.value,
        "qore_symbol": opportunity.qore_symbol,
        "provider_symbol": opportunity.provider_symbol,
        "signal_fingerprint": opportunity.signal_fingerprint,
        "known_as_of": known_as_of.isoformat(),
        "provider_observed_at": spec.observed_at.isoformat(),
        "decision_step": decision_step,
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"phase20d-known-option:{sha256(raw).hexdigest()}"


def _provider_evidence_id(
    *,
    opportunity: TraderOpportunityEnvelope,
    spec: CTraderDemoSymbolSpecification,
) -> str:
    payload = {
        "provider_key": "ctrader-demo",
        "signal_fingerprint": opportunity.signal_fingerprint,
        "qore_symbol": opportunity.qore_symbol,
        "provider_symbol": opportunity.provider_symbol,
        "bid": format(spec.bid, "f"),
        "ask": format(spec.ask, "f"),
        "tick_size": format(spec.tick_size, "f"),
        "tick_value": format(spec.tick_value, "f"),
        "minimum_volume": format(spec.minimum_volume, "f"),
        "maximum_volume": format(spec.maximum_volume, "f"),
        "volume_step": format(spec.volume_step, "f"),
        "margin_per_volume": format(spec.margin_per_volume, "f"),
        "observed_at": spec.observed_at.isoformat(),
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"ctrader-demo-single-slot-provider:{sha256(raw).hexdigest()}"


def _bounded_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= 0:
        return Decimal(1)
    return min(
        Decimal(1),
        max(Decimal(0), numerator / denominator),
    )


def _aware(value: datetime, *, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"Phase20D single-slot {name} must be timezone-aware"
        )
