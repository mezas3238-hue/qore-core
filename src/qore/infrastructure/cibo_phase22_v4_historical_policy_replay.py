"""Counterfactual historical policy replay for Phase22 V4.

The market clock (2015-2016) and the replay/qualification clock (post-freeze)
are deliberately separate. This module reuses the frozen CE2I full surface,
forecastless MPC and robust allocator without pretending the 2026 policy or
provider calibration existed in 2015.

Provider-specific economics must already be normalized into each
TraderOpportunityEnvelope by a separately artifact-bound Phase22 provider model.
QORE Risk remains downstream and independent.
"""
# ruff: noqa: I001, E402

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    derive_cibo_capital_mission,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_economic_effects import (
    AdvancedCe2iEconomicApplication,
    apply_advanced_ce2i_economic_effects,
)
from qore.infrastructure.cibo_ce2i_full_surface import (
    AdvancedPortfolioEvidence,
    FullCe2iSurfaceAssessment,
    evaluate_full_ce2i_surface,
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
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    build_frozen_train_expectation,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
)
from qore.infrastructure.cibo_profitability_lab_economic_consultation import (
    CiboEconomicConsultationReceipt,
    consult_cibo_economic_faculties,
)
from qore.infrastructure.cibo_phase22_v4_governance import (
    V4_CANDIDATE_ID,
)
from qore.infrastructure.cibo_next_policy_advanced_scientific_eligibility import (
    NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class Phase22HistoricalCapitalInput:
    opportunity: TraderOpportunityEnvelope
    minimum_stop_risk_usd: Decimal
    minimum_margin_usd: Decimal
    concentration_group: str
    concentration_risk_usd: Decimal
    provider_model_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.opportunity, TraderOpportunityEnvelope):
            raise CiboCapitalManagementError(
                "Phase22 historical capital input opportunity invalid"
            )
        for name in (
            "minimum_stop_risk_usd",
            "minimum_margin_usd",
            "concentration_risk_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase22 historical capital input {name} invalid"
                )
        expected_min_risk = (
            self.opportunity.minimum_volume
            * Decimal(self.opportunity.minimum_execution_steps)
            * self.opportunity.stop_loss_per_volume
        )
        expected_min_margin = (
            self.opportunity.minimum_volume
            * Decimal(self.opportunity.minimum_execution_steps)
            * self.opportunity.margin_per_volume
        )
        if self.minimum_stop_risk_usd != expected_min_risk:
            raise CiboCapitalManagementError(
                "Phase22 historical minimum stop-risk identity drift"
            )
        if self.minimum_margin_usd != expected_min_margin:
            raise CiboCapitalManagementError(
                "Phase22 historical minimum margin identity drift"
            )
        if (
            self.concentration_risk_usd > self.minimum_stop_risk_usd
            or not self.concentration_group
        ):
            raise CiboCapitalManagementError(
                "Phase22 historical concentration input invalid"
            )
        if _SHA256_RE.fullmatch(self.provider_model_sha256) is None:
            raise CiboCapitalManagementError(
                "Phase22 historical provider model digest invalid"
            )


@dataclass(frozen=True, slots=True)
class Phase22HistoricalPolicyDecisionRecord:
    candidate_id: str
    market_decision_at: datetime
    replay_sealed_at: datetime
    account_identity: CiboAccountCapitalIdentity
    provider_model_sha256: str
    hard_risk_headroom_usd: Decimal
    margin_headroom_usd: Decimal
    concentration_limit_by_group: tuple[tuple[str, Decimal], ...]
    economic_consultation: CiboEconomicConsultationReceipt
    full_surface: FullCe2iSurfaceAssessment
    advanced_economic_application: AdvancedCe2iEconomicApplication
    mpc_plan: Phase20MpcCapacityPlan
    allocator_decision: Phase20RobustAllocatorDecision
    counterfactual_historical_replay: bool = True
    policy_changed: bool = False
    thresholds_changed: bool = False
    outcome_aware: bool = False
    risk_authority: bool = False
    execution_authority: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.candidate_id != V4_CANDIDATE_ID:
            raise CiboCapitalManagementError(
                "Phase22 historical policy candidate drift"
            )
        for name, value in (
            ("market_decision_at", self.market_decision_at),
            ("replay_sealed_at", self.replay_sealed_at),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise CiboCapitalManagementError(
                    f"Phase22 historical policy {name} must be timezone-aware"
                )
        if self.replay_sealed_at <= FROZEN_PHASE20_POLICY_CANDIDATE.frozen_at:
            raise CiboCapitalManagementError(
                "Phase22 historical replay must be sealed after policy freeze"
            )
        if self.market_decision_at >= FROZEN_PHASE20_POLICY_CANDIDATE.frozen_at:
            raise CiboCapitalManagementError(
                "Phase22 historical market clock must predate policy freeze"
            )
        if (
            self.account_identity.environment is not MarketRuntimeEnvironment.DEMO
            or self.account_identity.provider_key != "ctrader-demo"
        ):
            raise CiboCapitalManagementError(
                "Phase22 historical policy requires cTrader DEMO mission"
            )
        if _SHA256_RE.fullmatch(self.provider_model_sha256) is None:
            raise CiboCapitalManagementError(
                "Phase22 historical policy provider digest invalid"
            )
        for name in ("hard_risk_headroom_usd", "margin_headroom_usd"):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase22 historical policy {name} invalid"
                )
        if (
            not self.counterfactual_historical_replay
            or self.policy_changed
            or self.thresholds_changed
            or self.outcome_aware
            or self.risk_authority
            or self.execution_authority
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "Phase22 historical policy governance contamination"
            )

    def fingerprint(self) -> str:
        payload = {
            "candidate_id": self.candidate_id,
            "market_decision_at": self.market_decision_at.isoformat(),
            "replay_sealed_at": self.replay_sealed_at.isoformat(),
            "account_identity": asdict(self.account_identity),
            "provider_model_sha256": self.provider_model_sha256,
            "hard_risk_headroom_usd": format(
                self.hard_risk_headroom_usd,
                "f",
            ),
            "margin_headroom_usd": format(self.margin_headroom_usd, "f"),
            "concentration_limit_by_group": [
                [name, format(value, "f")]
                for name, value in self.concentration_limit_by_group
            ],
            "economic_consultation": {
                "consultation_id": self.economic_consultation.consultation_id,
                "consulted_faculties": list(
                    self.economic_consultation.consulted_faculties
                ),
                "coordination_disposition": (
                    self.economic_consultation.coordination_disposition
                ),
                "coordination_request_code": (
                    self.economic_consultation.coordination_request_code
                ),
                "causal_predecision": self.economic_consultation.causal_predecision,
                "outcome_used": self.economic_consultation.outcome_used,
            },
            "regime_posture": self.full_surface.regime.posture.value,
            "advanced_economic_application": {
                "effective_hard_risk_headroom_usd": format(
                    self.advanced_economic_application.effective_hard_risk_headroom_usd,
                    "f",
                ),
                "effective_margin_headroom_usd": format(
                    self.advanced_economic_application.effective_margin_headroom_usd,
                    "f",
                ),
                "conservative_portfolio_credit_usd": format(
                    self.advanced_economic_application.conservative_portfolio_credit_usd,
                    "f",
                ),
                "candidate_effects": [
                    {
                        "signal_fingerprint": item.signal_fingerprint,
                        "tool_code": item.tool_code,
                        "field_name": item.field_name,
                        "before_usd": format(item.before_usd, "f"),
                        "after_usd": format(item.after_usd, "f"),
                    }
                    for item in self.advanced_economic_application.candidate_effects
                ],
                "portfolio_effects": [
                    {
                        "tool_code": item.tool_code,
                        "released_risk_capacity_usd": format(
                            item.released_risk_capacity_usd,
                            "f",
                        ),
                    }
                    for item in self.advanced_economic_application.portfolio_effects
                ],
            },
            "allocator_disposition": self.allocator_decision.disposition.value,
            "selected_signal_fingerprints": (
                []
                if self.allocator_decision.allocation is None
                else list(
                    self.allocator_decision
                    .allocation
                    .selected_signal_fingerprints
                )
            ),
            "counterfactual_historical_replay": True,
            "policy_changed": False,
            "thresholds_changed": False,
            "outcome_aware": False,
            "risk_authority": False,
            "execution_authority": False,
            "productive_authority": False,
        }
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode()
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def evaluate_phase22_historical_policy(
    *,
    market_decision_at: datetime,
    replay_sealed_at: datetime,
    account_identity: CiboAccountCapitalIdentity,
    inputs: tuple[Phase22HistoricalCapitalInput, ...],
    regime_state: CiboCapitalRegimeState,
    hard_risk_headroom_usd: Decimal,
    margin_headroom_usd: Decimal,
    concentration_limit_by_group: tuple[tuple[str, Decimal], ...],
    current_step: int,
    advanced_evidence: AdvancedPortfolioEvidence | None = None,
    known_options: tuple[Phase20MpcKnownOption, ...] = (),
    lab_allow_nonpositive_expectation: bool = False,
    lab_cibo_free_tool_choice: bool = False,
) -> Phase22HistoricalPolicyDecisionRecord:
    """Evaluate frozen V4 composition without falsifying historical timestamps."""

    if type(lab_allow_nonpositive_expectation) is not bool:
        raise CiboCapitalManagementError(
            "lab_allow_nonpositive_expectation must be bool"
        )
    if type(lab_cibo_free_tool_choice) is not bool:
        raise CiboCapitalManagementError(
            "lab_cibo_free_tool_choice must be bool"
        )
    if not inputs:
        raise CiboCapitalManagementError(
            "Phase22 historical policy requires at least one candidate"
        )
    if advanced_evidence is None:
        advanced_evidence = AdvancedPortfolioEvidence()
    provider_digests = {item.provider_model_sha256 for item in inputs}
    if len(provider_digests) != 1:
        raise CiboCapitalManagementError(
            "Phase22 historical policy requires one provider model identity"
        )
    fingerprints = tuple(
        item.opportunity.signal_fingerprint for item in inputs
    )
    if len(fingerprints) != len(set(fingerprints)):
        raise CiboCapitalManagementError(
            "Phase22 historical policy duplicate signal fingerprint"
        )
    if regime_state.opportunity_count != len(inputs):
        raise CiboCapitalManagementError(
            "Phase22 historical regime opportunity count drift"
        )

    mission = derive_cibo_capital_mission(account_identity)
    candidates = tuple(
        CapitalOpportunityCandidate(
            signal_fingerprint=item.opportunity.signal_fingerprint,
            trader_id=item.opportunity.trader_id,
            qore_symbol=item.opportunity.qore_symbol,
            provider_symbol=item.opportunity.provider_symbol,
            decision_as_of=market_decision_at,
            expectation=build_frozen_train_expectation(
                trader_id=item.opportunity.trader_id,
                stop_risk_usd=item.minimum_stop_risk_usd,
                as_of=market_decision_at,
            ),
            stop_risk_usd=item.minimum_stop_risk_usd,
            margin_usd=item.minimum_margin_usd,
            concentration_group=item.concentration_group,
            concentration_risk_usd=item.concentration_risk_usd,
        )
        for item in inputs
    )
    opportunities = tuple(item.opportunity for item in inputs)
    economic_consultation = consult_cibo_economic_faculties(
        decision_at=market_decision_at,
        opportunities=opportunities,
        regime_state=regime_state,
    )
    full_surface = evaluate_full_ce2i_surface(
        mission=mission,
        regime_state=regime_state,
        opportunities=opportunities,
        advanced_evidence=advanced_evidence,
        decision_at=market_decision_at,
        scientific_eligibility=(
            None
            if lab_cibo_free_tool_choice
            else NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY
        ),
    )
    advanced_application = apply_advanced_ce2i_economic_effects(
        candidates=candidates,
        full_surface=full_surface,
        hard_risk_headroom_usd=(
            advanced_application.effective_hard_risk_headroom_usd
        ),
        margin_headroom_usd=(
            advanced_application.effective_margin_headroom_usd
        ),
    )
    mpc = plan_phase20i_receding_horizon_capacity(
        current_step=current_step,
        horizon_steps=FROZEN_PHASE20_POLICY_CANDIDATE.mpc_horizon_steps,
        posture=full_surface.regime.posture,
        hard_risk_headroom_usd=hard_risk_headroom_usd,
        margin_headroom_usd=margin_headroom_usd,
        known_options=known_options,
    )
    allocator = propose_phase20h_robust_allocation(
        mission=mission,
        regime=full_surface.regime,
        hard_risk_headroom_usd=mpc.deployable_stop_risk_usd,
        margin_headroom_usd=mpc.deployable_margin_usd,
        concentration_limit_by_group=concentration_limit_by_group,
        candidates=advanced_application.candidates,
        known_options=(),
        lab_allow_nonpositive_expectation=lab_allow_nonpositive_expectation,
    )
    return Phase22HistoricalPolicyDecisionRecord(
        candidate_id=V4_CANDIDATE_ID,
        market_decision_at=market_decision_at,
        replay_sealed_at=replay_sealed_at,
        account_identity=account_identity,
        provider_model_sha256=next(iter(provider_digests)),
        hard_risk_headroom_usd=hard_risk_headroom_usd,
        margin_headroom_usd=margin_headroom_usd,
        concentration_limit_by_group=concentration_limit_by_group,
        economic_consultation=economic_consultation,
        full_surface=full_surface,
        advanced_economic_application=advanced_application,
        mpc_plan=mpc,
        allocator_decision=allocator,
    )
