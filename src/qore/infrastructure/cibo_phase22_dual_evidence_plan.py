"""Pre-outcome Phase22 dual-evidence qualification amendment.

This contract does not activate or consume the holdout. It records the only
scientifically honest route for combining a historical untouched market
holdout with real current provider execution evidence:

1. historical holdout outcomes remain historical market evidence only;
2. provider fills/slippage/latency are measured on real cTrader DEMO now;
3. no historical order/deal/settlement identity may be fabricated;
4. provider cost application to the holdout must be a predeclared model/bound,
   never represented as an observed historical fill;
5. both evidence planes are mandatory before any certification claim.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase22_qualification_plan import (
    FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN,
    phase22_holdout_qualification_plan_sha256,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import (
    CANDIDATE_ID,
    phase22_v2_holdout_source_receipt_sha256,
)
from qore.infrastructure.cibo_phase22_provider_execution_calibration_receipt import (
    PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT,
)

DUAL_EVIDENCE_PLAN_ID = "CIBO_PHASE22_DUAL_EVIDENCE_QUALIFICATION_PLAN_V2"


@dataclass(frozen=True, slots=True)
class Phase22DualEvidencePlan:
    plan_id: str
    candidate_id: str
    source_receipt_sha256: str
    superseded_plan_id: str
    superseded_plan_sha256: str
    provider_execution_calibration_sha256: str
    protocol_frozen_before_holdout_outcomes: bool
    require_historical_holdout_market_plane: bool
    require_real_current_demo_execution_plane: bool
    require_empirical_causal_quote_slippage: bool
    require_predeclared_provider_cost_application: bool
    forbid_historical_provider_fill_claims: bool
    forbid_historical_provider_order_refs: bool
    forbid_historical_provider_deal_refs: bool
    forbid_historical_provider_settlement_claims: bool
    forbid_synthetic_fill_evidence: bool
    forbid_holdout_mining: bool
    require_both_planes_for_certification: bool
    execution_population_ready: bool
    empirical_provider_calibration_ready: bool
    activation_ready: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.plan_id != DUAL_EVIDENCE_PLAN_ID:
            raise CiboCapitalManagementError(
                "Phase22 dual-evidence plan id drift"
            )
        if self.candidate_id != CANDIDATE_ID:
            raise CiboCapitalManagementError(
                "Phase22 dual-evidence candidate drift"
            )
        if self.source_receipt_sha256 != (
            phase22_v2_holdout_source_receipt_sha256()
        ):
            raise CiboCapitalManagementError(
                "Phase22 dual-evidence source receipt drift"
            )
        if self.superseded_plan_id != (
            FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN.plan_id
        ):
            raise CiboCapitalManagementError(
                "Phase22 dual-evidence superseded plan id drift"
            )
        if self.superseded_plan_sha256 != phase22_holdout_qualification_plan_sha256():
            raise CiboCapitalManagementError(
                "Phase22 dual-evidence superseded plan digest drift"
            )
        if self.provider_execution_calibration_sha256 != (
            PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.fingerprint()
        ):
            raise CiboCapitalManagementError(
                "Phase22 dual-evidence provider calibration receipt drift"
            )
        required_true = (
            self.protocol_frozen_before_holdout_outcomes,
            self.require_historical_holdout_market_plane,
            self.require_real_current_demo_execution_plane,
            self.require_empirical_causal_quote_slippage,
            self.require_predeclared_provider_cost_application,
            self.forbid_historical_provider_fill_claims,
            self.forbid_historical_provider_order_refs,
            self.forbid_historical_provider_deal_refs,
            self.forbid_historical_provider_settlement_claims,
            self.forbid_synthetic_fill_evidence,
            self.forbid_holdout_mining,
            self.require_both_planes_for_certification,
            self.execution_population_ready,
        )
        if not all(required_true):
            raise CiboCapitalManagementError(
                "Phase22 dual-evidence plan cannot weaken evidence gates"
            )
        expected_activation = (
            self.execution_population_ready
            and self.empirical_provider_calibration_ready
        )
        if self.activation_ready != expected_activation:
            raise CiboCapitalManagementError(
                "Phase22 dual-evidence activation readiness drift"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "Phase22 dual-evidence plan has no productive authority"
            )

    def fingerprint(self) -> str:
        raw = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


PHASE22_DUAL_EVIDENCE_PLAN = Phase22DualEvidencePlan(
    plan_id=DUAL_EVIDENCE_PLAN_ID,
    candidate_id=CANDIDATE_ID,
    source_receipt_sha256=phase22_v2_holdout_source_receipt_sha256(),
    superseded_plan_id=FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN.plan_id,
    superseded_plan_sha256=phase22_holdout_qualification_plan_sha256(),
    provider_execution_calibration_sha256=(
        PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.fingerprint()
    ),
    protocol_frozen_before_holdout_outcomes=True,
    require_historical_holdout_market_plane=True,
    require_real_current_demo_execution_plane=True,
    require_empirical_causal_quote_slippage=True,
    require_predeclared_provider_cost_application=True,
    forbid_historical_provider_fill_claims=True,
    forbid_historical_provider_order_refs=True,
    forbid_historical_provider_deal_refs=True,
    forbid_historical_provider_settlement_claims=True,
    forbid_synthetic_fill_evidence=True,
    forbid_holdout_mining=True,
    require_both_planes_for_certification=True,
    execution_population_ready=(
        PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.execution_population_ready
    ),
    empirical_provider_calibration_ready=(
        PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.empirical_slippage_calibrated
        and PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.execution_model_ready
        and PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.created_positions_closed
        and PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.minimum_volume_only
        and not PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.blockers
    ),
    activation_ready=True,
)


def phase22_dual_evidence_plan_payload() -> dict[str, object]:
    plan = PHASE22_DUAL_EVIDENCE_PLAN
    return {
        "schema": "qore.cibo.phase22.dual-evidence-plan.v2",
        **asdict(plan),
        "plan_sha256": plan.fingerprint(),
        "holdout_consumed": False,
        "activation_disposition": (
            "READY_TO_ACTIVATE"
            if plan.activation_ready
            else "WAITING_FOR_EMPIRICAL_PROVIDER_CALIBRATION"
        ),
    }
