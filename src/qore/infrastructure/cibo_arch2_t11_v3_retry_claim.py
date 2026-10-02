"""Immutable retry lineage for T11 V3 after a pre-broker quality failure.

The first V3 workflow run failed during static quality checks.  Credentials,
fresh containment preflight, broker mutation and evidence publication were all
skipped.  A single technical retry is admissible because no provider outcome
was observed or consumed and the frozen scientific protocol is unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_arch2_t11_post_containment_cycle_v3 import (
    CYCLE_ID,
    T11_POST_CONTAINMENT_CYCLE_V3,
)

CLAIM_ID = "CIBO_ARCH2_T11_V3_TECHNICAL_RETRY_R1"
FAILED_RUN_ID = 36948338513
FAILED_HEAD_SHA = "02e5a2872fe4cc9fa6d7c3ca8977fd0ad2557a6b"
RETRY_REASON = "PRE_BROKER_RUFF_IMPORT_ORDER_ONLY"
RETRY_TOKEN = "QUALITY_ONLY_R1"


@dataclass(frozen=True, slots=True)
class T11V3TechnicalRetryClaim:
    claim_id: str
    cycle_id: str
    failed_run_id: int
    failed_head_sha: str
    failed_before_credentials: bool
    failed_before_containment_preflight: bool
    failed_before_broker_mutation: bool
    terminal_artifact_count: int
    provider_outcomes_observed: bool
    provider_outcomes_consumed: bool
    retry_reason: str
    retry_token: str
    scientific_model_changed: bool
    thresholds_changed: bool
    experiment_plan_changed: bool
    outcome_aware_change: bool
    one_retry_allowed: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.claim_id != CLAIM_ID:
            raise ValueError("T11 V3 retry claim identity drift")
        if self.cycle_id != CYCLE_ID:
            raise ValueError("T11 V3 retry cycle lineage drift")
        if self.failed_run_id != FAILED_RUN_ID:
            raise ValueError("T11 V3 failed run lineage drift")
        if self.failed_head_sha != FAILED_HEAD_SHA:
            raise ValueError("T11 V3 failed HEAD lineage drift")
        if not all(
            (
                self.failed_before_credentials,
                self.failed_before_containment_preflight,
                self.failed_before_broker_mutation,
            )
        ):
            raise ValueError("T11 V3 retry requires pre-broker failure")
        if self.terminal_artifact_count != 0:
            raise ValueError("T11 V3 failed run must have zero terminal artifacts")
        if self.provider_outcomes_observed or self.provider_outcomes_consumed:
            raise ValueError("T11 V3 retry cannot consume provider outcomes")
        if self.retry_reason != RETRY_REASON or self.retry_token != RETRY_TOKEN:
            raise ValueError("T11 V3 retry reason/token drift")
        if (
            self.scientific_model_changed
            or self.thresholds_changed
            or self.experiment_plan_changed
            or self.outcome_aware_change
        ):
            raise ValueError("T11 V3 retry scientific contract changed")
        if not self.one_retry_allowed:
            raise ValueError("T11 V3 technical retry must be explicitly admitted")
        if not T11_POST_CONTAINMENT_CYCLE_V3.ready_for_versioned_execution:
            raise ValueError("T11 V3 base cycle is not ready")
        if self.productive_authority:
            raise ValueError("T11 V3 retry claim grants no productive authority")


T11_V3_TECHNICAL_RETRY_CLAIM = T11V3TechnicalRetryClaim(
    claim_id=CLAIM_ID,
    cycle_id=CYCLE_ID,
    failed_run_id=FAILED_RUN_ID,
    failed_head_sha=FAILED_HEAD_SHA,
    failed_before_credentials=True,
    failed_before_containment_preflight=True,
    failed_before_broker_mutation=True,
    terminal_artifact_count=0,
    provider_outcomes_observed=False,
    provider_outcomes_consumed=False,
    retry_reason=RETRY_REASON,
    retry_token=RETRY_TOKEN,
    scientific_model_changed=False,
    thresholds_changed=False,
    experiment_plan_changed=False,
    outcome_aware_change=False,
    one_retry_allowed=True,
    productive_authority=False,
)
