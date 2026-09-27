"""Phase 20D forward-evidence contract for CIBO policy qualification.

Decision evidence is sealed before any realized outcome is attached. Synthetic
contract fixtures are explicitly ineligible for Phase 20D qualification.

Research-only: no sizing, QORE Risk, order, execution, DEMO, LIVE or real-capital
authority is granted here.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum, StrEnum
from hashlib import sha256
from typing import Any

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    CiboCapitalMissionPolicy,
    derive_cibo_capital_mission,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_causal_expectation import (
    CausalExpectationBasis,
)
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
)
from qore.infrastructure.cibo_ce2i_phase20_mpc import (
    Phase20MpcCapacityPlan,
    Phase20MpcKnownOption,
    plan_phase20i_receding_horizon_capacity,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_robust_allocator import (
    Phase20RobustAllocatorDecision,
    propose_phase20h_robust_allocation,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CiboRegimeToolSelection,
    select_ce2i_tools_for_regime,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
    normalize_provider_economics,
)

_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class Phase20ForwardEvidenceKind(StrEnum):
    SYNTHETIC_CONTRACT = "SYNTHETIC_CONTRACT"
    FORWARD_OBSERVED = "FORWARD_OBSERVED"


@dataclass(frozen=True, slots=True)
class Phase20PolicyCandidateLineage:
    candidate_id: str
    code_sha: str
    parameter_sha256: str
    frozen_at: datetime
    phase19j_burned_validation_reused: bool = False
    policy_certified: bool = False
    demo_execution_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    merge_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise CiboCapitalManagementError("Phase20D candidate_id is required")
        if _SHA1_RE.fullmatch(self.code_sha) is None:
            raise CiboCapitalManagementError(
                "Phase20D code_sha must be a lowercase 40-hex Git SHA"
            )
        if _SHA256_RE.fullmatch(self.parameter_sha256) is None:
            raise CiboCapitalManagementError(
                "Phase20D parameter_sha256 must use sha256:<64 lowercase hex>"
            )
        _aware(self.frozen_at, name="frozen_at")
        if (
            self.phase19j_burned_validation_reused
            or self.policy_certified
            or self.demo_execution_authorized
            or self.live_authorized
            or self.real_capital_authorized
            or self.merge_authorized
        ):
            raise CiboCapitalManagementError("Phase20D candidate governance drift")


@dataclass(frozen=True, slots=True)
class Phase20ForwardCandidateEvidence:
    provider_evidence_id: str
    opportunity: TraderOpportunityEnvelope
    provider_observation: ProviderEconomicObservation
    candidate: CapitalOpportunityCandidate

    def __post_init__(self) -> None:
        if not self.provider_evidence_id:
            raise CiboCapitalManagementError(
                "Phase20D provider evidence identity is required"
            )
        if not isinstance(self.opportunity, TraderOpportunityEnvelope):
            raise CiboCapitalManagementError(
                "Phase20D opportunity must be TraderOpportunityEnvelope"
            )
        if not isinstance(self.provider_observation, ProviderEconomicObservation):
            raise CiboCapitalManagementError(
                "Phase20D provider observation must be canonical"
            )
        if not isinstance(self.candidate, CapitalOpportunityCandidate):
            raise CiboCapitalManagementError(
                "Phase20D candidate must be CapitalOpportunityCandidate"
            )
        if self.candidate.signal_fingerprint != self.opportunity.signal_fingerprint:
            raise CiboCapitalManagementError("Phase20D candidate signal mismatch")
        if self.candidate.trader_id is not self.opportunity.trader_id:
            raise CiboCapitalManagementError("Phase20D candidate Trader mismatch")
        if self.candidate.qore_symbol != self.opportunity.qore_symbol:
            raise CiboCapitalManagementError("Phase20D candidate QORE symbol mismatch")
        if self.candidate.provider_symbol != self.opportunity.provider_symbol:
            raise CiboCapitalManagementError(
                "Phase20D candidate provider symbol mismatch"
            )
        if self.provider_observation.qore_symbol != self.opportunity.qore_symbol:
            raise CiboCapitalManagementError("Phase20D provider QORE symbol mismatch")
        if (
            self.provider_observation.provider_symbol
            != self.opportunity.provider_symbol
        ):
            raise CiboCapitalManagementError("Phase20D provider symbol mismatch")
        if self.provider_observation.observed_at > self.candidate.decision_as_of:
            raise CiboCapitalManagementError(
                "Phase20D provider observation cannot postdate capital decision"
            )

        normalized = normalize_provider_economics(
            opportunity=self.opportunity,
            observation=self.provider_observation,
        )
        if self.candidate.stop_risk_usd < normalized.minimum_stop_risk_usd:
            raise CiboCapitalManagementError(
                "Phase20D candidate understates provider minimum stop risk"
            )
        if self.candidate.margin_usd < normalized.minimum_margin_usd:
            raise CiboCapitalManagementError(
                "Phase20D candidate understates provider minimum margin"
            )


@dataclass(frozen=True, slots=True)
class Phase20ForwardKnownOptionEvidence:
    evidence_id: str
    option: Phase20MpcKnownOption
    known_as_of: datetime
    active_at_decision: bool
    expires_at: datetime | None = None
    cancelled_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.evidence_id:
            raise CiboCapitalManagementError(
                "Phase20D known-option evidence_id is required"
            )
        if not isinstance(self.option, Phase20MpcKnownOption):
            raise CiboCapitalManagementError(
                "Phase20D known option must be Phase20MpcKnownOption"
            )
        _aware(self.known_as_of, name="known_as_of")
        if type(self.active_at_decision) is not bool:
            raise CiboCapitalManagementError(
                "Phase20D active_at_decision must be bool"
            )
        for name in ("expires_at", "cancelled_at"):
            value = getattr(self, name)
            if value is not None:
                _aware(value, name=name)
                if value < self.known_as_of:
                    raise CiboCapitalManagementError(
                        f"Phase20D {name} cannot predate known_as_of"
                    )

    def validate_at(self, decision_at: datetime) -> None:
        _aware(decision_at, name="decision_at")
        if self.known_as_of > decision_at:
            raise CiboCapitalManagementError(
                "Phase20D known option cannot be discovered after decision"
            )
        if not self.active_at_decision:
            raise CiboCapitalManagementError(
                "Phase20D known option must be active at decision"
            )
        if self.expires_at is not None and self.expires_at <= decision_at:
            raise CiboCapitalManagementError(
                "Phase20D expired option cannot enter MPC horizon"
            )
        if self.cancelled_at is not None and self.cancelled_at <= decision_at:
            raise CiboCapitalManagementError(
                "Phase20D cancelled option cannot enter MPC horizon"
            )


@dataclass(frozen=True, slots=True)
class Phase20ForwardDecisionEvidence:
    evidence_id: str
    evidence_kind: Phase20ForwardEvidenceKind
    decision_at: datetime
    lineage: Phase20PolicyCandidateLineage
    account_identity: CiboAccountCapitalIdentity
    mission: CiboCapitalMissionPolicy
    capital_snapshot_id: str
    capital_snapshot_observed_at: datetime
    risk_snapshot_id: str
    risk_snapshot_observed_at: datetime
    hard_risk_headroom_usd: Decimal
    margin_headroom_usd: Decimal
    concentration_limit_by_group: tuple[tuple[str, Decimal], ...]
    regime_state: CiboCapitalRegimeState
    current_step: int
    horizon_steps: int
    candidates: tuple[Phase20ForwardCandidateEvidence, ...]
    known_options: tuple[Phase20ForwardKnownOptionEvidence, ...] = ()
    outcome_present: bool = False
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.capital_snapshot_id or not self.risk_snapshot_id:
            raise CiboCapitalManagementError(
                "Phase20D evidence/capital/risk snapshot identities are required"
            )
        _fresh_snapshot(
            decision_at=self.decision_at,
            observed_at=self.capital_snapshot_observed_at,
            max_age_seconds=FROZEN_PHASE20_POLICY_CANDIDATE.snapshot_max_age_seconds,
            name="capital snapshot",
        )
        _fresh_snapshot(
            decision_at=self.decision_at,
            observed_at=self.risk_snapshot_observed_at,
            max_age_seconds=FROZEN_PHASE20_POLICY_CANDIDATE.snapshot_max_age_seconds,
            name="Risk snapshot",
        )
        if type(self.evidence_kind) is not Phase20ForwardEvidenceKind:
            raise CiboCapitalManagementError(
                "Phase20D evidence_kind must use canonical enum"
            )
        _aware(self.decision_at, name="decision_at")
        if not isinstance(self.lineage, Phase20PolicyCandidateLineage):
            raise CiboCapitalManagementError("Phase20D lineage is invalid")
        if self.decision_at < self.lineage.frozen_at:
            raise CiboCapitalManagementError(
                "Phase20D decision cannot predate policy freeze"
            )
        frozen = FROZEN_PHASE20_POLICY_CANDIDATE
        if (
            self.lineage.candidate_id != frozen.candidate_id
            or self.lineage.code_sha != frozen.code_sha
            or self.lineage.parameter_sha256 != frozen.parameter_sha256()
            or self.lineage.frozen_at != frozen.frozen_at
        ):
            raise CiboCapitalManagementError(
                "Phase20D lineage does not match frozen policy candidate"
            )
        if not isinstance(self.account_identity, CiboAccountCapitalIdentity):
            raise CiboCapitalManagementError("Phase20D account identity is invalid")
        if not isinstance(self.mission, CiboCapitalMissionPolicy):
            raise CiboCapitalManagementError("Phase20D mission is invalid")
        if derive_cibo_capital_mission(self.account_identity) != self.mission:
            raise CiboCapitalManagementError(
                "Phase20D mission must derive from authoritative account identity"
            )
        _nonnegative(self.hard_risk_headroom_usd, name="hard_risk_headroom_usd")
        _nonnegative(self.margin_headroom_usd, name="margin_headroom_usd")
        if not isinstance(self.regime_state, CiboCapitalRegimeState):
            raise CiboCapitalManagementError("Phase20D regime state is invalid")
        if type(self.current_step) is not int or self.current_step < 0:
            raise CiboCapitalManagementError(
                "Phase20D current_step must be non-negative int"
            )
        if type(self.horizon_steps) is not int or self.horizon_steps <= 0:
            raise CiboCapitalManagementError(
                "Phase20D horizon_steps must be positive int"
            )
        if (
            self.horizon_steps
            != FROZEN_PHASE20_POLICY_CANDIDATE.mpc_horizon_steps
        ):
            raise CiboCapitalManagementError(
                "Phase20D horizon_steps drift from frozen policy candidate"
            )
        if self.regime_state.opportunity_count != len(self.candidates):
            raise CiboCapitalManagementError(
                "Phase20D regime opportunity_count must equal sealed candidate count"
            )
        fingerprints = tuple(
            item.candidate.signal_fingerprint for item in self.candidates
        )
        if len(fingerprints) != len(set(fingerprints)):
            raise CiboCapitalManagementError(
                "Phase20D decision candidates must have unique fingerprints"
            )
        for candidate_evidence in self.candidates:
            if candidate_evidence.candidate.decision_as_of != self.decision_at:
                raise CiboCapitalManagementError(
                    "Phase20D candidate decision timestamp must equal sealed decision_at"
                )
            _fresh_snapshot(
                decision_at=self.decision_at,
                observed_at=candidate_evidence.provider_observation.observed_at,
                max_age_seconds=(
                    FROZEN_PHASE20_POLICY_CANDIDATE.snapshot_max_age_seconds
                ),
                name="provider snapshot",
            )
            expectation = candidate_evidence.candidate.expectation
            if expectation.basis in {
                CausalExpectationBasis.CAUSAL_MODEL_FORECAST,
                CausalExpectationBasis.CURRENT_STATE_FORECAST,
            }:
                _fresh_snapshot(
                    decision_at=self.decision_at,
                    observed_at=expectation.as_of,
                    max_age_seconds=(
                        FROZEN_PHASE20_POLICY_CANDIDATE
                        .current_forecast_max_age_seconds
                    ),
                    name="current causal expectation",
                )
        option_ids = tuple(item.option.opportunity_id for item in self.known_options)
        if len(option_ids) != len(set(option_ids)):
            raise CiboCapitalManagementError(
                "Phase20D known options must have unique opportunity ids"
            )
        for option_evidence in self.known_options:
            option_evidence.validate_at(self.decision_at)
        groups = tuple(name for name, _ in self.concentration_limit_by_group)
        if len(groups) != len(set(groups)):
            raise CiboCapitalManagementError(
                "Phase20D concentration groups must be unique"
            )
        for name, limit in self.concentration_limit_by_group:
            if not name:
                raise CiboCapitalManagementError(
                    "Phase20D concentration group name is required"
                )
            _nonnegative(limit, name="concentration_limit")
        if (
            self.outcome_present
            or self.allocation_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCapitalManagementError(
                "Phase20D pre-decision evidence cannot contain outcome or authority"
            )


@dataclass(frozen=True, slots=True)
class Phase20ForwardDecisionRecord:
    evidence_sha256: str
    regime: CiboRegimeToolSelection
    mpc_plan: Phase20MpcCapacityPlan
    allocator_input_stop_risk_headroom_usd: Decimal
    allocator_input_margin_headroom_usd: Decimal
    allocator_decision: Phase20RobustAllocatorDecision
    mpc_reserve_applied_before_allocator: bool = True
    phase20d_qualified: bool = False

    def __post_init__(self) -> None:
        if _SHA256_RE.fullmatch(self.evidence_sha256) is None:
            raise CiboCapitalManagementError(
                "Phase20D decision digest must use sha256:<64 lowercase hex>"
            )
        if not isinstance(self.regime, CiboRegimeToolSelection):
            raise CiboCapitalManagementError("Phase20D regime selection is invalid")
        if not isinstance(self.mpc_plan, Phase20MpcCapacityPlan):
            raise CiboCapitalManagementError("Phase20D MPC plan is invalid")
        for name in (
            "allocator_input_stop_risk_headroom_usd",
            "allocator_input_margin_headroom_usd",
        ):
            _nonnegative(getattr(self, name), name=name)
        if (
            self.allocator_input_stop_risk_headroom_usd
            != self.mpc_plan.deployable_stop_risk_usd
            or self.allocator_input_margin_headroom_usd
            != self.mpc_plan.deployable_margin_usd
        ):
            raise CiboCapitalManagementError(
                "Phase20D allocator input must equal MPC deployable headroom"
            )
        if not isinstance(
            self.allocator_decision,
            Phase20RobustAllocatorDecision,
        ):
            raise CiboCapitalManagementError(
                "Phase20D allocator decision is invalid"
            )
        if type(self.mpc_reserve_applied_before_allocator) is not bool:
            raise CiboCapitalManagementError(
                "Phase20D MPC composition flag must be bool"
            )
        if not self.mpc_reserve_applied_before_allocator:
            raise CiboCapitalManagementError(
                "Phase20D policy candidate must reserve MPC capacity first"
            )
        if self.phase20d_qualified:
            raise CiboCapitalManagementError(
                "Phase20D decision alone cannot be qualified before outcome"
            )


@dataclass(frozen=True, slots=True)
class Phase20ForwardOutcomeEvidence:
    evidence_id: str
    decision_evidence_sha256: str
    signal_fingerprint: str
    observed_at: datetime
    realized_structural_outcome_r: Decimal
    outcome_reconciled: bool
    future_data_used_for_decision: bool = False
    decision_rewritten_after_outcome: bool = False

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.signal_fingerprint:
            raise CiboCapitalManagementError(
                "Phase20D outcome identity/signal is required"
            )
        if _SHA256_RE.fullmatch(self.decision_evidence_sha256) is None:
            raise CiboCapitalManagementError(
                "Phase20D outcome must bind canonical decision SHA256"
            )
        _aware(self.observed_at, name="outcome observed_at")
        if (
            not isinstance(self.realized_structural_outcome_r, Decimal)
            or not self.realized_structural_outcome_r.is_finite()
        ):
            raise CiboCapitalManagementError(
                "Phase20D realized structural outcome must be finite Decimal"
            )
        for name in (
            "outcome_reconciled",
            "future_data_used_for_decision",
            "decision_rewritten_after_outcome",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(f"Phase20D {name} must be bool")
        if self.future_data_used_for_decision or self.decision_rewritten_after_outcome:
            raise CiboCapitalManagementError(
                "Phase20D outcome evidence reports causal contamination"
            )


@dataclass(frozen=True, slots=True)
class Phase20ForwardQualification:
    eligible: bool
    reasons: tuple[str, ...]


def build_phase20_forward_decision_record(
    evidence: Phase20ForwardDecisionEvidence,
) -> Phase20ForwardDecisionRecord:
    """Evaluate 20H and 20I from one sealed pre-decision evidence object."""

    if not isinstance(evidence, Phase20ForwardDecisionEvidence):
        raise CiboCapitalManagementError(
            "Phase20D decision evidence must be canonical"
        )
    regime = select_ce2i_tools_for_regime(
        mission=evidence.mission,
        state=evidence.regime_state,
    )
    mpc_plan = plan_phase20i_receding_horizon_capacity(
        current_step=evidence.current_step,
        horizon_steps=evidence.horizon_steps,
        posture=regime.posture,
        hard_risk_headroom_usd=evidence.hard_risk_headroom_usd,
        margin_headroom_usd=evidence.margin_headroom_usd,
        known_options=tuple(item.option for item in evidence.known_options),
    )
    allocator = propose_phase20h_robust_allocation(
        mission=evidence.mission,
        regime=regime,
        hard_risk_headroom_usd=mpc_plan.deployable_stop_risk_usd,
        margin_headroom_usd=mpc_plan.deployable_margin_usd,
        concentration_limit_by_group=evidence.concentration_limit_by_group,
        candidates=tuple(item.candidate for item in evidence.candidates),
        known_options=(),
    )
    return Phase20ForwardDecisionRecord(
        evidence_sha256=phase20_forward_evidence_sha256(evidence),
        regime=regime,
        mpc_plan=mpc_plan,
        allocator_input_stop_risk_headroom_usd=(
            mpc_plan.deployable_stop_risk_usd
        ),
        allocator_input_margin_headroom_usd=mpc_plan.deployable_margin_usd,
        allocator_decision=allocator,
        mpc_reserve_applied_before_allocator=True,
        phase20d_qualified=False,
    )


def assess_phase20d_forward_qualification(
    *,
    decision: Phase20ForwardDecisionEvidence,
    outcome: Phase20ForwardOutcomeEvidence,
) -> Phase20ForwardQualification:
    """Check whether one sealed decision/outcome pair is genuine fresh evidence."""

    if not isinstance(decision, Phase20ForwardDecisionEvidence):
        raise CiboCapitalManagementError("Phase20D decision evidence is invalid")
    if not isinstance(outcome, Phase20ForwardOutcomeEvidence):
        raise CiboCapitalManagementError("Phase20D outcome evidence is invalid")

    reasons: list[str] = []
    decision_digest = phase20_forward_evidence_sha256(decision)
    if decision.evidence_kind is not Phase20ForwardEvidenceKind.FORWARD_OBSERVED:
        reasons.append("DECISION_NOT_FORWARD_OBSERVED")
    if outcome.decision_evidence_sha256 != decision_digest:
        reasons.append("OUTCOME_DECISION_DIGEST_MISMATCH")
    if outcome.observed_at <= decision.decision_at:
        reasons.append("OUTCOME_NOT_STRICTLY_AFTER_DECISION")
    fingerprints = {
        item.candidate.signal_fingerprint for item in decision.candidates
    }
    if outcome.signal_fingerprint not in fingerprints:
        reasons.append("OUTCOME_SIGNAL_NOT_IN_SEALED_CANDIDATES")
    if not outcome.outcome_reconciled:
        reasons.append("OUTCOME_NOT_RECONCILED")

    return Phase20ForwardQualification(
        eligible=not reasons,
        reasons=tuple(reasons),
    )


def phase20_forward_evidence_json(
    evidence: Phase20ForwardDecisionEvidence,
) -> str:
    if not isinstance(evidence, Phase20ForwardDecisionEvidence):
        raise CiboCapitalManagementError(
            "Phase20D canonical payload requires decision evidence"
        )
    return json.dumps(
        _canonicalize(evidence),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def phase20_forward_evidence_sha256(
    evidence: Phase20ForwardDecisionEvidence,
) -> str:
    payload = phase20_forward_evidence_json(evidence).encode("utf-8")
    return f"sha256:{sha256(payload).hexdigest()}"


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _canonicalize(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, tuple):
        return [_canonicalize(item) for item in value]
    if isinstance(value, list):
        return [_canonicalize(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _canonicalize(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return value


def _fresh_snapshot(
    *,
    decision_at: datetime,
    observed_at: datetime,
    max_age_seconds: Decimal,
    name: str,
) -> None:
    _aware(decision_at, name="decision_at")
    _aware(observed_at, name=name)
    if observed_at > decision_at:
        raise CiboCapitalManagementError(
            f"Phase20D {name} cannot postdate decision"
        )
    delta = decision_at - observed_at
    age_seconds = (
        Decimal(delta.days * 86400 + delta.seconds)
        + Decimal(delta.microseconds) / Decimal(1000000)
    )
    if age_seconds > max_age_seconds:
        raise CiboCapitalManagementError(
            f"Phase20D {name} exceeds frozen freshness bound"
        )


def _aware(value: datetime, *, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"Phase20D {name} must be timezone-aware"
        )


def _nonnegative(value: Decimal, *, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise CiboCapitalManagementError(
            f"Phase20D {name} must be finite non-negative Decimal"
        )
