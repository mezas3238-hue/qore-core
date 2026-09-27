"""Phase 20D causal decision-epoch collector for CIBO forward qualification.

This module turns the complete set of currently-valid Trader opportunities into
one deterministic, portfolio-aware, pre-outcome evidence object. It deliberately
seals that evidence durably before Phase20I/Phase20H are evaluated.

Research-only: it has no sizing authority, no QORE Risk authority, no execution
authority and never mutates broker state.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from hashlib import sha256

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    derive_cibo_capital_mission,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardCandidateEvidence,
    Phase20ForwardDecisionEvidence,
    Phase20ForwardDecisionRecord,
    Phase20ForwardEvidenceKind,
    Phase20ForwardKnownOptionEvidence,
    Phase20PolicyCandidateLineage,
    build_phase20_forward_decision_record,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    DurablePhase20ForwardEvidenceStore,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    build_frozen_train_expectation,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
    normalize_provider_economics,
)


@dataclass(frozen=True, slots=True)
class Phase20ForwardObservedOpportunity:
    """One contemporaneous opportunity plus its provider/concentration evidence."""

    provider_evidence_id: str
    opportunity: TraderOpportunityEnvelope
    provider_observation: ProviderEconomicObservation
    concentration_group: str
    concentration_risk_usd: Decimal
    optionality_cost_usd: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        if not self.provider_evidence_id or not self.concentration_group:
            raise CiboCapitalManagementError(
                "Phase20D observed opportunity evidence/group is required"
            )
        if not isinstance(self.opportunity, TraderOpportunityEnvelope):
            raise CiboCapitalManagementError(
                "Phase20D observed opportunity must be canonical"
            )
        if not isinstance(self.provider_observation, ProviderEconomicObservation):
            raise CiboCapitalManagementError(
                "Phase20D observed provider economics must be canonical"
            )
        for name in ("concentration_risk_usd", "optionality_cost_usd"):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"Phase20D {name} must be finite Decimal"
                )
        if self.concentration_risk_usd <= 0:
            raise CiboCapitalManagementError(
                "Phase20D concentration_risk_usd must be positive"
            )
        if self.optionality_cost_usd < 0:
            raise CiboCapitalManagementError(
                "Phase20D optionality_cost_usd must be non-negative"
            )


@dataclass(frozen=True, slots=True)
class Phase20ForwardEpochResult:
    """Durably sealed epoch plus the observational V2 policy decision."""

    evidence: Phase20ForwardDecisionEvidence
    sealed_generation: int
    decision_record: Phase20ForwardDecisionRecord

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, Phase20ForwardDecisionEvidence):
            raise CiboCapitalManagementError(
                "Phase20D epoch result evidence must be canonical"
            )
        if (
            not isinstance(self.sealed_generation, int)
            or isinstance(self.sealed_generation, bool)
            or self.sealed_generation < 1
        ):
            raise CiboCapitalManagementError(
                "Phase20D sealed generation must be positive int"
            )
        if not isinstance(self.decision_record, Phase20ForwardDecisionRecord):
            raise CiboCapitalManagementError(
                "Phase20D epoch result record must be canonical"
            )


def seal_phase20_forward_observed_epoch(
    *,
    store: DurablePhase20ForwardEvidenceStore,
    decision_at: datetime,
    account_identity: CiboAccountCapitalIdentity,
    capital_snapshot_id: str,
    capital_snapshot_observed_at: datetime,
    risk_snapshot_id: str,
    risk_snapshot_observed_at: datetime,
    hard_risk_headroom_usd: Decimal,
    margin_headroom_usd: Decimal,
    concentration_limit_by_group: tuple[tuple[str, Decimal], ...],
    regime_state: CiboCapitalRegimeState,
    current_step: int,
    opportunities: tuple[Phase20ForwardObservedOpportunity, ...],
    known_options: tuple[Phase20ForwardKnownOptionEvidence, ...] = (),
) -> Phase20ForwardEpochResult:
    """Seal a complete causal epoch, then evaluate V2 observationally.

    The durable write happens before Phase20I/Phase20H evaluation. A concurrent
    writer therefore fails through the store's generation CAS rather than
    allowing two mutable views of the same capital decision epoch.
    """

    if not isinstance(store, DurablePhase20ForwardEvidenceStore):
        raise CiboCapitalManagementError(
            "Phase20D forward store must be durable canonical store"
        )
    if not opportunities:
        raise CiboCapitalManagementError(
            "Phase20D forward epoch requires at least one valid opportunity"
        )
    if not isinstance(regime_state, CiboCapitalRegimeState):
        raise CiboCapitalManagementError(
            "Phase20D forward epoch regime state must be canonical"
        )
    if regime_state.opportunity_count != len(opportunities):
        raise CiboCapitalManagementError(
            "Phase20D regime opportunity_count must equal epoch population"
        )

    ordered_observations = tuple(
        sorted(
            opportunities,
            key=lambda item: (
                item.opportunity.trader_id.value,
                item.opportunity.qore_symbol,
                item.opportunity.provider_symbol,
                item.opportunity.signal_fingerprint,
                item.provider_evidence_id,
            ),
        )
    )
    fingerprints = tuple(
        item.opportunity.signal_fingerprint for item in ordered_observations
    )
    if len(fingerprints) != len(set(fingerprints)):
        raise CiboCapitalManagementError(
            "Phase20D forward epoch signal fingerprints must be unique"
        )
    provider_ids = tuple(
        item.provider_evidence_id for item in ordered_observations
    )
    if len(provider_ids) != len(set(provider_ids)):
        raise CiboCapitalManagementError(
            "Phase20D forward epoch provider evidence ids must be unique"
        )
    if any(
        item.provider_observation.provider_key != account_identity.provider_key
        for item in ordered_observations
    ):
        raise CiboCapitalManagementError(
            "Phase20D provider observation must match account provider"
        )

    candidates = tuple(
        _candidate_evidence(
            item=item,
            decision_at=decision_at,
        )
        for item in ordered_observations
    )
    ordered_options = tuple(
        sorted(
            known_options,
            key=lambda item: (
                item.option.decision_step,
                item.option.opportunity_id,
                item.evidence_id,
            ),
        )
    )
    ordered_limits = tuple(sorted(concentration_limit_by_group))
    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    lineage = Phase20PolicyCandidateLineage(
        candidate_id=frozen.candidate_id,
        code_sha=frozen.code_sha,
        parameter_sha256=frozen.parameter_sha256(),
        frozen_at=frozen.frozen_at,
    )
    evidence = Phase20ForwardDecisionEvidence(
        evidence_id=_epoch_evidence_id(
            decision_at=decision_at,
            account_identity=account_identity,
            capital_snapshot_id=capital_snapshot_id,
            risk_snapshot_id=risk_snapshot_id,
            candidate_evidence=candidates,
            known_options=ordered_options,
            current_step=current_step,
        ),
        evidence_kind=Phase20ForwardEvidenceKind.FORWARD_OBSERVED,
        decision_at=decision_at,
        lineage=lineage,
        account_identity=account_identity,
        mission=derive_cibo_capital_mission(account_identity),
        capital_snapshot_id=capital_snapshot_id,
        capital_snapshot_observed_at=capital_snapshot_observed_at,
        risk_snapshot_id=risk_snapshot_id,
        risk_snapshot_observed_at=risk_snapshot_observed_at,
        hard_risk_headroom_usd=hard_risk_headroom_usd,
        margin_headroom_usd=margin_headroom_usd,
        concentration_limit_by_group=ordered_limits,
        regime_state=regime_state,
        current_step=current_step,
        horizon_steps=frozen.mpc_horizon_steps,
        candidates=candidates,
        known_options=ordered_options,
    )

    current = store.load()
    sealed = store.seal_decision(
        evidence,
        expected_generation=current.generation,
    )
    decision_record = build_phase20_forward_decision_record(evidence)
    return Phase20ForwardEpochResult(
        evidence=evidence,
        sealed_generation=sealed.generation,
        decision_record=decision_record,
    )


def _candidate_evidence(
    *,
    item: Phase20ForwardObservedOpportunity,
    decision_at: datetime,
) -> Phase20ForwardCandidateEvidence:
    normalized = normalize_provider_economics(
        opportunity=item.opportunity,
        observation=item.provider_observation,
    )
    if item.concentration_risk_usd > normalized.minimum_stop_risk_usd:
        raise CiboCapitalManagementError(
            "Phase20D concentration risk cannot exceed minimum seed stop risk"
        )
    expectation = build_frozen_train_expectation(
        trader_id=item.opportunity.trader_id,
        stop_risk_usd=normalized.minimum_stop_risk_usd,
        as_of=decision_at,
    )
    candidate = CapitalOpportunityCandidate(
        signal_fingerprint=item.opportunity.signal_fingerprint,
        trader_id=item.opportunity.trader_id,
        qore_symbol=item.opportunity.qore_symbol,
        provider_symbol=item.opportunity.provider_symbol,
        decision_as_of=decision_at,
        expectation=expectation,
        stop_risk_usd=normalized.minimum_stop_risk_usd,
        margin_usd=normalized.minimum_margin_usd,
        concentration_group=item.concentration_group,
        concentration_risk_usd=item.concentration_risk_usd,
        optionality_cost_usd=item.optionality_cost_usd,
    )
    return Phase20ForwardCandidateEvidence(
        provider_evidence_id=item.provider_evidence_id,
        opportunity=item.opportunity,
        provider_observation=item.provider_observation,
        candidate=candidate,
    )


def _epoch_evidence_id(
    *,
    decision_at: datetime,
    account_identity: CiboAccountCapitalIdentity,
    capital_snapshot_id: str,
    risk_snapshot_id: str,
    candidate_evidence: tuple[Phase20ForwardCandidateEvidence, ...],
    known_options: tuple[Phase20ForwardKnownOptionEvidence, ...],
    current_step: int,
) -> str:
    payload = {
        "candidate_id": FROZEN_PHASE20_POLICY_CANDIDATE.candidate_id,
        "decision_at": decision_at.isoformat(),
        "account": {
            "provider_key": account_identity.provider_key,
            "account_ref": account_identity.account_ref,
            "environment": account_identity.environment.value,
            "provider_program": account_identity.provider_program,
        },
        "capital_snapshot_id": capital_snapshot_id,
        "risk_snapshot_id": risk_snapshot_id,
        "current_step": current_step,
        "candidates": [
            {
                "signal_fingerprint": item.opportunity.signal_fingerprint,
                "trader_id": item.opportunity.trader_id.value,
            }
            for item in candidate_evidence
        ],
        "known_options": [
            {
                "opportunity_id": item.option.opportunity_id,
                "decision_step": item.option.decision_step,
            }
            for item in known_options
        ],
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"phase20d-forward-epoch:{sha256(raw).hexdigest()}"
