"""Architect-2 terminal intake for the Phase22 V2 fresh-OOS result.

Architect-2 must never consume or rerun the one-shot holdout.  Terminalization
requires three independently validated objects:
1. the durable Phase22 consumption receipt;
2. the canonical Phase22 qualification report;
3. the Integrator cross-boundary receipt proving that the exact outcome bundle
   materialized the stores/artifact used by that qualification.

PASS -> COMPLETED_AND_PROVEN.
FAIL -> FALSIFIED_AND_CLOSED.
NOT_READY/INVALID -> remains non-terminal.

No pooled rescue, no threshold changes, no canonical-ledger mutation.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_arch2_fresh_oos_binding import (
    Phase22OutcomeQualificationBindingReceipt,
    phase22_report_fingerprint,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase22_qualification import (
    Phase22HoldoutQualificationReport,
    Phase22HoldoutQualificationStatus,
)
from qore.infrastructure.cibo_ce2i_phase22_qualification_plan import (
    phase22_holdout_qualification_plan_sha256,
)
from qore.infrastructure.cibo_phase22_consumption_ledger import (
    Phase22ExecutionConsumptionReceipt,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import (
    CANDIDATE_ID,
)

COMPLETED = "COMPLETED_AND_PROVEN"
FALSIFIED = "FALSIFIED_AND_CLOSED"
WAITING = "WAITING_ON_AUTHORIZED_PHASE22_V2_FRESH_OUTCOME_RECEIPT"


@dataclass(frozen=True, slots=True)
class Architect2FreshOOSTerminalIntake:
    candidate_id: str
    execution_manifest_sha256: str
    outcome_bundle_sha256: str
    holdout_evidence_store_sha256: str
    holdout_policy_store_sha256: str
    outcome_to_store_binding_sha256: str
    qualification_plan_sha256: str
    qualification_report_sha256: str
    qualification_artifact_sha256: str
    cross_boundary_binding_sha256: str
    qualification_status: str
    lineage_valid: bool
    fresh_oos_terminal_ready: bool
    terminal_recommendation: str | None
    rerun_authorized: bool = False
    canonical_ledger_modified: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.candidate_id != CANDIDATE_ID:
            raise CiboCapitalManagementError(
                "Fresh-OOS intake candidate identity drift"
            )
        for name in (
            "execution_manifest_sha256",
            "outcome_bundle_sha256",
            "holdout_evidence_store_sha256",
            "holdout_policy_store_sha256",
            "outcome_to_store_binding_sha256",
            "qualification_plan_sha256",
            "qualification_report_sha256",
            "qualification_artifact_sha256",
            "cross_boundary_binding_sha256",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or not value.startswith("sha256:")
                or len(value) != 71
                or any(char not in "0123456789abcdef" for char in value[7:])
            ):
                raise CiboCapitalManagementError(
                    f"Fresh-OOS intake {name} invalid"
                )
        if self.qualification_plan_sha256 != (
            phase22_holdout_qualification_plan_sha256()
        ):
            raise CiboCapitalManagementError(
                "Fresh-OOS intake qualification-plan lineage drift"
            )
        terminal_status = self.qualification_status in {
            Phase22HoldoutQualificationStatus.PASS.value,
            Phase22HoldoutQualificationStatus.FAIL.value,
        }
        expected_ready = terminal_status and self.lineage_valid
        if self.fresh_oos_terminal_ready != expected_ready:
            raise CiboCapitalManagementError(
                "Fresh-OOS intake terminal readiness drift"
            )
        expected_recommendation: str | None
        if (
            self.qualification_status
            == Phase22HoldoutQualificationStatus.PASS.value
            and self.lineage_valid
        ):
            expected_recommendation = COMPLETED
        elif (
            self.qualification_status
            == Phase22HoldoutQualificationStatus.FAIL.value
            and self.lineage_valid
        ):
            expected_recommendation = FALSIFIED
        else:
            expected_recommendation = None
        if self.terminal_recommendation != expected_recommendation:
            raise CiboCapitalManagementError(
                "Fresh-OOS intake terminal recommendation drift"
            )
        if (
            self.rerun_authorized
            or self.canonical_ledger_modified
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "Fresh-OOS intake exceeded Architect-2 authority"
            )


def build_arch2_fresh_oos_terminal_intake(
    *,
    consumption: Phase22ExecutionConsumptionReceipt,
    qualification: Phase22HoldoutQualificationReport,
    binding: Phase22OutcomeQualificationBindingReceipt,
) -> Architect2FreshOOSTerminalIntake:
    """Validate exact one-shot/output/qualification lineage without reopening it."""

    if not isinstance(consumption, Phase22ExecutionConsumptionReceipt):
        raise CiboCapitalManagementError(
            "Fresh-OOS intake requires canonical consumption receipt"
        )
    if not isinstance(qualification, Phase22HoldoutQualificationReport):
        raise CiboCapitalManagementError(
            "Fresh-OOS intake requires canonical Phase22 qualification report"
        )
    if not isinstance(binding, Phase22OutcomeQualificationBindingReceipt):
        raise CiboCapitalManagementError(
            "Fresh-OOS intake requires Integrator outcome/qualification binding"
        )
    if consumption.candidate_id != CANDIDATE_ID:
        raise CiboCapitalManagementError(
            "Fresh-OOS intake consumption candidate drift"
        )
    if not consumption.claim_committed:
        raise CiboCapitalManagementError(
            "Fresh-OOS intake requires durable prior one-shot claim"
        )
    if not consumption.outcomes_emitted:
        raise CiboCapitalManagementError(
            "Fresh-OOS intake requires emitted fresh outcomes"
        )
    if consumption.outcome_bundle_sha256 is None:
        raise CiboCapitalManagementError(
            "Fresh-OOS intake outcome bundle digest missing"
        )
    if qualification.plan_sha256 != phase22_holdout_qualification_plan_sha256():
        raise CiboCapitalManagementError(
            "Fresh-OOS intake qualification plan drift"
        )

    exact_pairs = (
        ("candidate_id", consumption.candidate_id, binding.candidate_id),
        (
            "execution_manifest_sha256",
            consumption.execution_manifest_sha256,
            binding.execution_manifest_sha256,
        ),
        (
            "claim_head_sha",
            consumption.claim_head_sha,
            binding.claim_head_sha,
        ),
        ("claim_run_id", consumption.claim_run_id, binding.claim_run_id),
        (
            "claim_run_attempt",
            consumption.claim_run_attempt,
            binding.claim_run_attempt,
        ),
        (
            "outcome_bundle_sha256",
            consumption.outcome_bundle_sha256,
            binding.outcome_bundle_sha256,
        ),
        (
            "qualification_plan_sha256",
            qualification.plan_sha256,
            binding.qualification_plan_sha256,
        ),
        (
            "qualification_status",
            qualification.status.value,
            binding.qualification_status,
        ),
        (
            "lineage_valid",
            qualification.lineage.lineage_valid,
            binding.lineage_valid,
        ),
        (
            "qualification_report_sha256",
            phase22_report_fingerprint(qualification),
            binding.qualification_report_sha256,
        ),
    )
    for name, observed, bound in exact_pairs:
        if observed != bound:
            raise CiboCapitalManagementError(
                f"Fresh-OOS cross-boundary binding drift: {name}"
            )

    status = qualification.status
    lineage_valid = qualification.lineage.lineage_valid
    if status is Phase22HoldoutQualificationStatus.PASS:
        if not qualification.economically_certified:
            raise CiboCapitalManagementError(
                "Fresh-OOS PASS is not economically certified"
            )
        recommendation: str | None = COMPLETED
        ready = True
    elif status is Phase22HoldoutQualificationStatus.FAIL:
        if not lineage_valid:
            raise CiboCapitalManagementError(
                "Fresh-OOS economic FAIL requires valid lineage"
            )
        recommendation = FALSIFIED
        ready = True
    else:
        recommendation = None
        ready = False

    return Architect2FreshOOSTerminalIntake(
        candidate_id=consumption.candidate_id,
        execution_manifest_sha256=consumption.execution_manifest_sha256,
        outcome_bundle_sha256=consumption.outcome_bundle_sha256,
        holdout_evidence_store_sha256=(
            binding.holdout_evidence_store_sha256
        ),
        holdout_policy_store_sha256=binding.holdout_policy_store_sha256,
        outcome_to_store_binding_sha256=(
            binding.outcome_to_store_binding_sha256
        ),
        qualification_plan_sha256=qualification.plan_sha256,
        qualification_report_sha256=binding.qualification_report_sha256,
        qualification_artifact_sha256=binding.qualification_artifact_sha256,
        cross_boundary_binding_sha256=binding.fingerprint(),
        qualification_status=status.value,
        lineage_valid=lineage_valid,
        fresh_oos_terminal_ready=ready,
        terminal_recommendation=recommendation,
        rerun_authorized=False,
        canonical_ledger_modified=False,
        productive_authority=False,
    )
