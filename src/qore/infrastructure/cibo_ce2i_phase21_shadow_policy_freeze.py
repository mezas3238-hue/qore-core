"""Sealed Phase21 policy freeze for the owner-authorized shadow lane.

This freeze binds the successful post-TRAIN historical-shadow empirical screen
to the already frozen Phase20 V3 policy.  It never relabels historical evidence
as live/forward execution, never invents provider USD economics and never reads
the final 2017H1 holdout.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    prior_digest_sha256,
)

PHASE21_SHADOW_POLICY_FREEZE_ID = "CIBO_PHASE21_SHADOW_POLICY_FREEZE_V1"
PHASE21_SHADOW_SOURCE_RUN_ID = 36865828999
PHASE21_SHADOW_SOURCE_ARTIFACT_ID = 11164600745
PHASE21_SHADOW_SOURCE_ARTIFACT_DIGEST = (
    "sha256:0b3d0b892207ec3f5873240175eb08dc15cebd31c23d8621472933e691a2990c"
)
PHASE21_SHADOW_SOURCE_HEAD = "072b6b7494eed0ed0a2d881b6526bdeb779e28f7"


@dataclass(frozen=True, slots=True)
class CiboPhase21ShadowPolicyFreeze:
    freeze_id: str
    frozen_at: datetime
    candidate_id: str
    candidate_code_sha: str
    candidate_parameter_sha256: str
    train_prior_sha256: str
    source_run_id: int
    source_artifact_id: int
    source_artifact_digest: str
    source_head_sha: str
    validation_rows: int
    selected_outcomes: int
    represented_lineages: int
    monte_carlo_simulations: int
    sealed: bool
    historical_shadow_only: bool
    provider_economics_claimed: bool
    holdout_2017h1_read: bool
    policy_retuned_after_outcomes: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.freeze_id != PHASE21_SHADOW_POLICY_FREEZE_ID:
            raise CiboCapitalManagementError("Phase21 shadow freeze identity drift")
        if self.frozen_at.tzinfo is None or self.frozen_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "Phase21 shadow freeze timestamp must be timezone-aware"
            )
        candidate = FROZEN_PHASE20_POLICY_CANDIDATE
        if (
            self.candidate_id != candidate.candidate_id
            or self.candidate_code_sha != candidate.code_sha
            or self.candidate_parameter_sha256 != candidate.parameter_sha256()
        ):
            raise CiboCapitalManagementError(
                "Phase21 shadow freeze candidate lineage drift"
            )
        if self.train_prior_sha256 != prior_digest_sha256():
            raise CiboCapitalManagementError(
                "Phase21 shadow freeze TRAIN prior digest drift"
            )
        if (
            self.source_run_id != PHASE21_SHADOW_SOURCE_RUN_ID
            or self.source_artifact_id != PHASE21_SHADOW_SOURCE_ARTIFACT_ID
            or self.source_artifact_digest
            != PHASE21_SHADOW_SOURCE_ARTIFACT_DIGEST
            or self.source_head_sha != PHASE21_SHADOW_SOURCE_HEAD
        ):
            raise CiboCapitalManagementError(
                "Phase21 shadow freeze source evidence drift"
            )
        if (
            self.validation_rows != 332
            or self.selected_outcomes != 256
            or self.represented_lineages != 7
            or self.monte_carlo_simulations != 1000
        ):
            raise CiboCapitalManagementError(
                "Phase21 shadow freeze empirical population drift"
            )
        if (
            not self.sealed
            or not self.historical_shadow_only
            or self.provider_economics_claimed
            or self.holdout_2017h1_read
            or self.policy_retuned_after_outcomes
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "Phase21 shadow freeze governance drift"
            )

    def fingerprint(self) -> str:
        raw = json.dumps(
            _canonical(asdict(self)),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_phase21_shadow_policy_freeze(
    *,
    screen: dict[str, Any],
    frozen_at: datetime,
) -> CiboPhase21ShadowPolicyFreeze:
    """Validate the successful screen and seal the frozen V3 research policy."""

    if screen.get("schema") != "qore.cibo.phase21.historical-shadow-screen.v1":
        raise CiboCapitalManagementError("Phase21 shadow screen schema mismatch")
    if screen.get("status") != "PASS":
        raise CiboCapitalManagementError("Phase21 shadow screen is not PASS")

    candidate = FROZEN_PHASE20_POLICY_CANDIDATE
    if (
        screen.get("candidate_id") != candidate.candidate_id
        or screen.get("candidate_code_sha") != candidate.code_sha
        or screen.get("candidate_parameter_sha256") != candidate.parameter_sha256()
        or screen.get("train_prior_sha256") != prior_digest_sha256()
    ):
        raise CiboCapitalManagementError(
            "Phase21 shadow screen frozen-policy lineage mismatch"
        )

    source = _mapping(screen.get("source_population"), "source_population")
    metrics = _mapping(screen.get("screen"), "screen")
    policy = _mapping(metrics.get("policy"), "policy")
    baseline = _mapping(metrics.get("baseline"), "baseline")
    mc = _mapping(metrics.get("monte_carlo"), "monte_carlo")
    governance = _mapping(screen.get("governance"), "governance")

    validation_rows = _integer(metrics, "validation_rows")
    selected_outcomes = _integer(metrics, "selected_outcomes")
    represented_lineages = _integer(metrics, "represented_lineages")
    decision_epochs = _integer(metrics, "decision_epochs")
    distinct_days = _integer(metrics, "distinct_trading_days")
    simulations = _integer(mc, "simulation_count")

    if source.get("validation_rows") != 332 or source.get(
        "historical_provider_usd_economics"
    ) is not False:
        raise CiboCapitalManagementError(
            "Phase21 shadow source population provenance mismatch"
        )
    if metrics.get("passed") is not True:
        raise CiboCapitalManagementError("Phase21 shadow empirical gate not passed")
    if (
        validation_rows != 332
        or selected_outcomes != 256
        or represented_lineages != 7
        or decision_epochs < 80
        or distinct_days < 20
        or simulations != 1000
    ):
        raise CiboCapitalManagementError(
            "Phase21 shadow empirical thresholds not satisfied"
        )

    folds = metrics.get("folds")
    if not isinstance(folds, list) or len(folds) != 4:
        raise CiboCapitalManagementError("Phase21 shadow fold coverage incomplete")
    for fold in folds:
        row = _mapping(fold, "fold")
        if (
            _integer(row, "baseline_outcomes") < 40
            or _integer(row, "represented_lineages") != 7
        ):
            raise CiboCapitalManagementError(
                "Phase21 shadow fold population threshold failed"
            )

    policy_delta = _decimal(policy, "realized_delta_ncu")
    baseline_delta = _decimal(baseline, "realized_delta_ncu")
    policy_dd = _decimal(policy, "max_drawdown_ncu")
    baseline_dd = _decimal(baseline, "max_drawdown_ncu")
    policy_productivity = _decimal(
        policy, "capital_productivity_ncu_per_risk_minute"
    )
    baseline_productivity = _decimal(
        baseline, "capital_productivity_ncu_per_risk_minute"
    )
    if (
        policy_delta <= 0
        or policy_delta < baseline_delta
        or policy_dd > baseline_dd
        or policy_productivity <= baseline_productivity
    ):
        raise CiboCapitalManagementError(
            "Phase21 shadow aggregate economic screen failed"
        )

    if (
        _decimal(mc, "policy_median_ending_delta_ncu")
        < _decimal(mc, "baseline_median_ending_delta_ncu")
        or _decimal(mc, "policy_p95_drawdown_ncu")
        > _decimal(mc, "baseline_p95_drawdown_ncu")
        or _integer(mc, "policy_capacity_breach_paths") != 0
        or _integer(mc, "baseline_capacity_breach_paths") != 0
    ):
        raise CiboCapitalManagementError(
            "Phase21 shadow Monte Carlo screen failed"
        )

    if (
        governance.get("policy_retuned_from_shadow_outcomes") is not False
        or governance.get("historical_usd_claimed") is not False
        or governance.get("historical_provider_economics_claimed") is not False
        or governance.get("final_holdout_2017h1_read") is not False
        or governance.get("final_holdout_2017h1_status") != "SEALED_UNTOUCHED"
    ):
        raise CiboCapitalManagementError(
            "Phase21 shadow governance evidence failed"
        )

    return CiboPhase21ShadowPolicyFreeze(
        freeze_id=PHASE21_SHADOW_POLICY_FREEZE_ID,
        frozen_at=frozen_at,
        candidate_id=candidate.candidate_id,
        candidate_code_sha=candidate.code_sha,
        candidate_parameter_sha256=candidate.parameter_sha256(),
        train_prior_sha256=prior_digest_sha256(),
        source_run_id=PHASE21_SHADOW_SOURCE_RUN_ID,
        source_artifact_id=PHASE21_SHADOW_SOURCE_ARTIFACT_ID,
        source_artifact_digest=PHASE21_SHADOW_SOURCE_ARTIFACT_DIGEST,
        source_head_sha=PHASE21_SHADOW_SOURCE_HEAD,
        validation_rows=validation_rows,
        selected_outcomes=selected_outcomes,
        represented_lineages=represented_lineages,
        monte_carlo_simulations=simulations,
        sealed=True,
        historical_shadow_only=True,
        provider_economics_claimed=False,
        holdout_2017h1_read=False,
        policy_retuned_after_outcomes=False,
        productive_authority=False,
    )


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CiboCapitalManagementError(f"Phase21 shadow {name} must be object")
    return value


def _integer(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if type(value) is not int:
        raise CiboCapitalManagementError(
            f"Phase21 shadow metric must be int: {key}"
        )
    return value


def _decimal(payload: dict[str, Any], key: str) -> Decimal:
    try:
        value = Decimal(str(payload[key]))
    except (KeyError, ValueError) as error:
        raise CiboCapitalManagementError(
            f"Phase21 shadow decimal metric invalid: {key}"
        ) from error
    if not value.is_finite():
        raise CiboCapitalManagementError(
            f"Phase21 shadow decimal metric non-finite: {key}"
        )
    return value


def _canonical(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return value
