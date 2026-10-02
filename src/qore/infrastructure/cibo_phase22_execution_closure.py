"""Terminal one-shot execution closure for Phase22 V2.

This stage does not decide whether the holdout "should" pass. It persists the
five create-once stores, runs the frozen qualification protocol, records the
actual status, and marks the already-burned one-shot consumption as CONSUMED.

A scientifically valid FAIL/NOT_READY/INVALID is never converted into PASS and
never authorizes a second fresh execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase22_qualification import (
    Phase22HoldoutQualificationReport,
    run_phase22_holdout_qualification,
)
from qore.infrastructure.cibo_phase21_shadow_qualification_lineage import (
    PHASE21_SHADOW_QUALIFICATION_LINEAGE_RECEIPT,
)
from qore.infrastructure.cibo_phase22_chronological_execution import (
    Phase22HistoricalExecutionReport,
    execute_phase22_chronological_replay,
)
from qore.infrastructure.cibo_phase22_chronological_replay_plan import (
    build_phase22_chronological_replay_plan,
)
from qore.infrastructure.cibo_phase22_consumption_ledger import (
    Phase22ExecutionConsumptionReceipt,
)
from qore.infrastructure.cibo_phase22_execution_inputs import (
    Phase22SealedFreshBatchInput,
    Phase22SealedProviderNumericInput,
    project_phase22_execution_inputs,
)
from qore.infrastructure.cibo_phase22_git_durable_claim import (
    Phase22GitDurableClaimEvidence,
)
from qore.infrastructure.cibo_phase22_historical_regime import (
    build_phase22_historical_regime_evidence,
)
from qore.infrastructure.cibo_phase22_historical_replay_stores import (
    persist_phase22_historical_store_set,
)
from qore.infrastructure.cibo_phase22_one_shot_batch import (
    Phase22OneShotBatchCompletionReceipt,
    Phase22OneShotClaimReceipt,
)
from qore.infrastructure.cibo_phase22_store_contract import (
    PHASE22_STORE_IDENTITIES,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Evidence,
)

PHASE22_SOVEREIGN_BRANCH = "agent/cibo-integrator-ab-001"


@dataclass(frozen=True, slots=True)
class Phase22ExecutionClosure:
    durable_claim_evidence: Phase22GitDurableClaimEvidence
    execution: Phase22HistoricalExecutionReport
    qualification: Phase22HoldoutQualificationReport
    completion: Phase22OneShotBatchCompletionReceipt
    consumed: Phase22ExecutionConsumptionReceipt
    store_sha256s: tuple[tuple[str, str], ...]
    qualification_recorded_without_override: bool = True
    second_fresh_execution_authorized: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if (
            self.durable_claim_evidence.branch_name
            != PHASE22_SOVEREIGN_BRANCH
            or not self.durable_claim_evidence.durable_claim_proven
        ):
            raise CiboCapitalManagementError(
                "Phase22 closure requires sovereign remote-durable claim proof"
            )
        if (
            self.durable_claim_evidence.claim_receipt_sha256
            != self.completion.claim_receipt_sha256
        ):
            raise CiboCapitalManagementError(
                "Phase22 closure durable claim/completion lineage drift"
            )
        expected_roles = tuple(item.name for item in PHASE22_STORE_IDENTITIES)
        if tuple(name for name, _ in self.store_sha256s) != expected_roles:
            raise CiboCapitalManagementError(
                "Phase22 closure store digest surface drift"
            )
        if self.completion.store_sha256s != self.store_sha256s:
            raise CiboCapitalManagementError(
                "Phase22 closure completion/store digest drift"
            )
        if (
            not self.consumed.claim_committed
            or not self.consumed.outcomes_emitted
            or self.consumed.outcome_bundle_sha256
            != self.completion.fingerprint()
        ):
            raise CiboCapitalManagementError(
                "Phase22 closure consumed receipt drift"
            )
        if (
            not self.qualification_recorded_without_override
            or self.second_fresh_execution_authorized
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "Phase22 closure governance contamination"
            )


def close_phase22_one_shot_execution(
    *,
    fresh: Phase22SealedFreshBatchInput,
    provider: Phase22SealedProviderNumericInput,
    provider_numeric_freeze_sha256: str,
    corpora: tuple[Evidence, ...],
    store_root: Path,
    replay_started_at: datetime,
    completed_at: datetime | None,
    claim: Phase22OneShotClaimReceipt,
    consumption_claim: Phase22ExecutionConsumptionReceipt,
    durable_claim_evidence: Phase22GitDurableClaimEvidence,
    execution_run_id: int,
    execution_run_attempt: int,
) -> Phase22ExecutionClosure:
    """Persist actual Phase22 evidence and record qualification without override."""

    if (
        not isinstance(execution_run_id, int)
        or isinstance(execution_run_id, bool)
        or execution_run_id <= 0
        or not isinstance(execution_run_attempt, int)
        or isinstance(execution_run_attempt, bool)
        or execution_run_attempt <= 0
    ):
        raise CiboCapitalManagementError(
            "Phase22 closure execution lease values invalid"
        )
    if (
        claim.run_id != execution_run_id
        or claim.run_attempt != execution_run_attempt
    ):
        raise CiboCapitalManagementError(
            "Phase22 closure execution lease mismatch"
        )
    if not isinstance(durable_claim_evidence, Phase22GitDurableClaimEvidence):
        raise CiboCapitalManagementError(
            "Phase22 closure requires canonical durable claim evidence"
        )
    if durable_claim_evidence.branch_name != PHASE22_SOVEREIGN_BRANCH:
        raise CiboCapitalManagementError(
            "Phase22 closure durable claim branch is not sovereign"
        )
    if (
        durable_claim_evidence.source_head_sha != claim.runner_git_sha
        or durable_claim_evidence.source_head_sha != consumption_claim.claim_head_sha
        or durable_claim_evidence.claim_receipt_sha256 != claim.fingerprint()
    ):
        raise CiboCapitalManagementError(
            "Phase22 closure durable claim lineage mismatch"
        )
    if claim.consumption_claim() != consumption_claim:
        raise CiboCapitalManagementError(
            "Phase22 closure claim/consumption lineage mismatch"
        )
    if consumption_claim.outcomes_emitted:
        raise CiboCapitalManagementError(
            "Phase22 closure cannot rerun consumed holdout"
        )
    if completed_at is not None and completed_at < replay_started_at:
        raise CiboCapitalManagementError(
            "Phase22 closure completion cannot predate replay start"
        )

    projections = project_phase22_execution_inputs(
        fresh=fresh,
        provider=provider,
        provider_numeric_freeze_sha256=provider_numeric_freeze_sha256,
    )
    replay_plan = build_phase22_chronological_replay_plan(
        fresh=fresh,
        projections=projections,
    )
    regimes = build_phase22_historical_regime_evidence(
        plan=replay_plan,
        provider=provider,
        provider_numeric_freeze_sha256=provider_numeric_freeze_sha256,
        corpora=corpora,
    )
    execution = execute_phase22_chronological_replay(
        plan=replay_plan,
        regime_evidence=regimes,
        replay_started_at=replay_started_at,
    )
    raw_store_sha256s = persist_phase22_historical_store_set(
        root=store_root,
        books=execution.books,
    )
    roles = tuple(item.name for item in PHASE22_STORE_IDENTITIES)
    if len(raw_store_sha256s) != len(roles):
        raise CiboCapitalManagementError(
            "Phase22 closure store persistence count drift"
        )
    store_sha256s = tuple(zip(roles, raw_store_sha256s, strict=True))

    by_role = dict(store_sha256s)
    qualification = run_phase22_holdout_qualification(
        phase21_manifest=PHASE21_SHADOW_QUALIFICATION_LINEAGE_RECEIPT,
        qualification_evidence_book=None,
        holdout_evidence_book=execution.books.holdout_evidence,
        holdout_policy_book=execution.books.holdout_policy,
        qualification_evidence_store_sha256=None,
        qualification_policy_store_sha256=None,
        holdout_evidence_store_sha256=by_role["HOLDOUT_FORWARD_EVIDENCE"],
        holdout_policy_store_sha256=by_role["HOLDOUT_POLICY"],
    )

    trader_sha256s = tuple(
        (item.trader_id, item.source_artifact_sha256)
        for item in fresh.batch.traders
    )
    resolved_completed_at = (
        datetime.now(UTC) if completed_at is None else completed_at
    )
    if resolved_completed_at < replay_started_at:
        raise CiboCapitalManagementError(
            "Phase22 closure completion cannot predate replay start"
        )
    completion = Phase22OneShotBatchCompletionReceipt(
        claim_receipt_sha256=claim.fingerprint(),
        trader_artifact_sha256s=trader_sha256s,
        store_sha256s=store_sha256s,
        completed_at=resolved_completed_at,
        all_traders_completed=True,
        all_stores_sealed=True,
        fresh_outcomes_emitted=True,
        productive_authority=False,
    )
    consumed = completion.consumed_receipt(claim=consumption_claim)
    return Phase22ExecutionClosure(
        durable_claim_evidence=durable_claim_evidence,
        execution=execution,
        qualification=qualification,
        completion=completion,
        consumed=consumed,
        store_sha256s=store_sha256s,
    )
