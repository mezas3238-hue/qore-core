"""Component-level provider-economics freeze for CIBO pre-holdout work.

The current cTrader DEMO terms may be frozen as a reproducible point-in-time
input while empirical slippage and the execution model remain explicitly open.
This module cannot activate the global pre-holdout freeze.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_provider_economics_evidence import (
    CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS,
    provider_economics_evidence_ref,
)
from qore.infrastructure.cibo_ce2i_provider_economics_provenance import (
    provider_economics_provenance_payload,
    provider_economics_provenance_sha256,
)
from qore.infrastructure.cibo_ce2i_provider_execution_calibration import (
    CiboProviderExecutionCalibration,
)
from qore.infrastructure.cibo_ce2i_provider_execution_stress_bound import (
    FROZEN_PROVIDER_EXECUTION_STRESS_PROFILE,
    PROVIDER_EXECUTION_STRESS_PROFILE_ID,
    provider_execution_stress_profile_sha256,
)
from qore.infrastructure.cibo_ce2i_provider_stress_bound_freeze import (
    CiboProviderStressBoundFreeze,
)

PROVIDER_ECONOMICS_COMPONENT_FREEZE_ID = (
    "CIBO_CTRADER_DEMO_PROVIDER_ECONOMICS_COMPONENT_FREEZE_V1"
)


@dataclass(frozen=True, slots=True)
class CiboProviderEconomicsComponentFreeze:
    freeze_id: str
    provider_key: str
    environment: str
    source_evidence_ref: str
    source_provenance_sha256: str
    source_observed_at: datetime
    frozen_at: datetime
    point_in_time_terms_frozen: bool
    spread_terms_frozen: bool
    commission_terms_frozen: bool
    expected_margin_terms_frozen: bool
    volume_contract_terms_frozen: bool
    empirical_slippage_frozen: bool
    execution_model_frozen: bool
    stress_bound_execution_model_frozen: bool
    execution_model_basis: str
    stress_profile_sha256: str | None
    historical_2017_exact_claimed: bool
    holdout_outcomes_used: bool
    target_aware: bool
    broker_mutation_performed: bool
    pre_holdout_provider_economics_ready: bool
    provider_deployment_ready: bool
    certification_lane: str
    blockers: tuple[str, ...]
    deployment_blockers: tuple[str, ...]
    execution_calibration_sha256: str | None = None
    provider_stress_bound_sha256: str | None = None
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.freeze_id != PROVIDER_ECONOMICS_COMPONENT_FREEZE_ID:
            raise CiboCapitalManagementError(
                "provider economics component freeze identity drift"
            )
        if self.provider_key != "ctrader-demo" or self.environment != "demo":
            raise CiboCapitalManagementError(
                "provider economics component freeze provider/environment drift"
            )
        if not self.source_evidence_ref:
            raise CiboCapitalManagementError(
                "provider economics component freeze evidence ref required"
            )
        if (
            len(self.source_provenance_sha256) != 64
            or any(
                char not in "0123456789abcdef"
                for char in self.source_provenance_sha256
            )
        ):
            raise CiboCapitalManagementError(
                "provider economics component provenance SHA invalid"
            )
        for name in ("source_observed_at", "frozen_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise CiboCapitalManagementError(
                    f"provider economics component {name} must be timezone-aware"
                )
        if self.frozen_at < self.source_observed_at:
            raise CiboCapitalManagementError(
                "provider economics component freeze cannot predate observation"
            )
        for name in (
            "point_in_time_terms_frozen",
            "spread_terms_frozen",
            "commission_terms_frozen",
            "expected_margin_terms_frozen",
            "volume_contract_terms_frozen",
            "empirical_slippage_frozen",
            "execution_model_frozen",
            "stress_bound_execution_model_frozen",
            "historical_2017_exact_claimed",
            "holdout_outcomes_used",
            "target_aware",
            "broker_mutation_performed",
            "pre_holdout_provider_economics_ready",
            "provider_deployment_ready",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"provider economics component {name} must be bool"
                )
        current_terms_complete = all(
            (
                self.point_in_time_terms_frozen,
                self.spread_terms_frozen,
                self.commission_terms_frozen,
                self.expected_margin_terms_frozen,
                self.volume_contract_terms_frozen,
            )
        )
        empirical_lane_ready = (
            self.empirical_slippage_frozen
            and self.execution_model_frozen
            and self.execution_calibration_sha256 is not None
        )
        stress_lane_ready = self.provider_stress_bound_sha256 is not None
        expected_ready = (
            current_terms_complete
            and (empirical_lane_ready or stress_lane_ready)
            and not self.historical_2017_exact_claimed
            and not self.holdout_outcomes_used
            and not self.target_aware
            and not self.broker_mutation_performed
            and not self.blockers
        )
        expected_deployment = (
            current_terms_complete
            and empirical_lane_ready
            and not self.historical_2017_exact_claimed
            and not self.holdout_outcomes_used
            and not self.target_aware
            and not self.broker_mutation_performed
            and not self.deployment_blockers
        )
        if self.pre_holdout_provider_economics_ready != expected_ready:
            raise CiboCapitalManagementError(
                "provider economics component readiness/blocker drift"
            )
        if self.provider_deployment_ready != expected_deployment:
            raise CiboCapitalManagementError(
                "provider economics deployment readiness drift"
            )
        if self.certification_lane not in {
            "EMPIRICAL_EXECUTION",
            "PREDECLARED_STRESS_BOUND",
            "NOT_READY",
        }:
            raise CiboCapitalManagementError(
                "provider economics certification lane invalid"
            )
        expected_lane = (
            "EMPIRICAL_EXECUTION"
            if empirical_lane_ready
            else (
                "PREDECLARED_STRESS_BOUND"
                if stress_lane_ready
                else "NOT_READY"
            )
        )
        if self.certification_lane != expected_lane:
            raise CiboCapitalManagementError(
                "provider economics certification lane drift"
            )
        if self.execution_calibration_sha256 is not None:
            value = self.execution_calibration_sha256
            if (
                not value.startswith("sha256:")
                or len(value) != 71
                or any(
                    char not in "0123456789abcdef"
                    for char in value[7:]
                )
            ):
                raise CiboCapitalManagementError(
                    "provider economics execution calibration SHA invalid"
                )
        if self.provider_stress_bound_sha256 is not None:
            value = self.provider_stress_bound_sha256
            if (
                not value.startswith("sha256:")
                or len(value) != 71
                or any(
                    char not in "0123456789abcdef"
                    for char in value[7:]
                )
            ):
                raise CiboCapitalManagementError(
                    "provider economics stress-bound SHA invalid"
                )
        if (
            self.empirical_slippage_frozen
            and self.execution_calibration_sha256 is None
        ):
            raise CiboCapitalManagementError(
                "provider economics empirical execution requires calibration SHA"
            )
        if (
            self.stress_bound_execution_model_frozen
            and self.stress_profile_sha256 is None
        ):
            raise CiboCapitalManagementError(
                "provider economics stress execution requires profile SHA"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "provider economics component freeze has no productive authority"
            )

    def fingerprint(self) -> str:
        raw = json.dumps(
            _canonical(asdict(self)),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def freeze_current_ctrader_demo_provider_economics(
    *,
    frozen_at: datetime,
    execution_calibration: CiboProviderExecutionCalibration | None = None,
    stress_bound: CiboProviderStressBoundFreeze | None = None,
) -> CiboProviderEconomicsComponentFreeze:
    """Freeze proven current terms while keeping unsupported components open."""

    evidence = CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS
    provenance = provider_economics_provenance_payload()
    observed_at = datetime.fromisoformat(evidence.observed_at)
    if frozen_at.tzinfo is None or frozen_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "provider economics component frozen_at must be timezone-aware"
        )
    if evidence.provider_key != provenance["provider"]:
        raise CiboCapitalManagementError(
            "provider economics evidence/provenance provider drift"
        )
    if tuple(provenance["symbols"]) != evidence.symbols:
        raise CiboCapitalManagementError(
            "provider economics evidence/provenance symbol drift"
        )
    if (
        evidence.workflow_run_id != provenance["workflow_run_id"]
        or evidence.artifact_id != provenance["artifact_id"]
        or evidence.artifact_sha256 != provenance["artifact_zip_sha256"]
        or evidence.source_git_sha != provenance["git_sha"]
        or evidence.observed_at != provenance["observed_at"]
    ):
        raise CiboCapitalManagementError(
            "provider economics evidence/provenance lineage drift"
        )

    current_terms = bool(
        evidence.provider_terms_ready
        and provenance["current_provider_terms_ready"] is True
    )
    slippage = bool(
        evidence.slippage_empirically_calibrated
        and provenance["slippage_empirically_calibrated"] is True
    )
    execution_model = bool(
        evidence.execution_model_ready
        and provenance["execution_model_ready"] is True
    )
    execution_calibration_sha256: str | None = None
    if execution_calibration is not None:
        if not isinstance(
            execution_calibration,
            CiboProviderExecutionCalibration,
        ):
            raise CiboCapitalManagementError(
                "provider economics execution calibration is invalid"
            )
        if execution_calibration.provider_key != evidence.provider_key:
            raise CiboCapitalManagementError(
                "provider economics execution calibration provider drift"
            )
        if frozen_at < execution_calibration.frozen_at:
            raise CiboCapitalManagementError(
                "provider economics freeze cannot predate execution calibration"
            )
        slippage = (
            slippage
            or execution_calibration.empirical_slippage_calibrated
        )
        execution_model = (
            execution_model
            or execution_calibration.execution_model_ready
        )
        execution_calibration_sha256 = execution_calibration.fingerprint()
    stress_bound_sha256: str | None = None
    stress_lane_ready = False
    deployment_blockers: list[str] = []
    if stress_bound is not None:
        if not isinstance(stress_bound, CiboProviderStressBoundFreeze):
            raise CiboCapitalManagementError(
                "provider economics stress-bound evidence is invalid"
            )
        if stress_bound.provider_key != evidence.provider_key:
            raise CiboCapitalManagementError(
                "provider economics stress-bound provider drift"
            )
        if frozen_at < stress_bound.frozen_at:
            raise CiboCapitalManagementError(
                "provider economics freeze cannot predate stress bound"
            )
        stress_lane_ready = stress_bound.core_pre_holdout_ready
        stress_bound_sha256 = stress_bound.fingerprint()
        deployment_blockers.extend(stress_bound.deployment_blockers)

    blockers: list[str] = []
    if not current_terms:
        blockers.append("CURRENT_PROVIDER_TERMS_NOT_FROZEN")
    if not (slippage and execution_model) and not stress_lane_ready:
        if not slippage:
            blockers.append("EMPIRICAL_SLIPPAGE_NOT_FROZEN")
        if not execution_model:
            blockers.append("EXECUTION_MODEL_NOT_FROZEN")
        blockers.append("PROVIDER_STRESS_BOUND_NOT_FROZEN")

    empirical_lane_ready = slippage and execution_model
    if not empirical_lane_ready:
        deployment_blockers.extend(
            (
                "PROVIDER_DEPLOYMENT_EMPIRICAL_SLIPPAGE_REQUIRED",
                "PROVIDER_DEPLOYMENT_EXECUTION_MODEL_REQUIRED",
            )
        )
    deployment_blockers = list(dict.fromkeys(deployment_blockers))

    return CiboProviderEconomicsComponentFreeze(
        freeze_id=PROVIDER_ECONOMICS_COMPONENT_FREEZE_ID,
        provider_key=evidence.provider_key,
        environment=str(provenance["environment"]),
        source_evidence_ref=provider_economics_evidence_ref(),
        source_provenance_sha256=provider_economics_provenance_sha256(),
        source_observed_at=observed_at,
        frozen_at=frozen_at,
        point_in_time_terms_frozen=current_terms,
        spread_terms_frozen=bool(provenance["spread_native_ready"]),
        commission_terms_frozen=bool(provenance["commission_native_ready"]),
        expected_margin_terms_frozen=bool(
            provenance["expected_margin_native_ready"]
        ),
        volume_contract_terms_frozen=bool(
            provenance["volume_and_contract_terms_ready"]
        ),
        empirical_slippage_frozen=slippage,
        execution_model_frozen=execution_model,
        stress_bound_execution_model_frozen=False,
        execution_model_basis=(
            "EMPIRICAL" if slippage and execution_model else "UNAVAILABLE"
        ),
        stress_profile_sha256=None,
        historical_2017_exact_claimed=evidence.historical_exact_claimed,
        holdout_outcomes_used=evidence.holdout_outcomes_used,
        target_aware=evidence.target_aware,
        broker_mutation_performed=evidence.broker_mutation_performed,
        pre_holdout_provider_economics_ready=(
            current_terms
            and (empirical_lane_ready or stress_lane_ready)
            and not evidence.historical_exact_claimed
            and not evidence.holdout_outcomes_used
            and not evidence.target_aware
            and not evidence.broker_mutation_performed
            and not blockers
        ),
        provider_deployment_ready=(
            current_terms
            and empirical_lane_ready
            and not evidence.historical_exact_claimed
            and not evidence.holdout_outcomes_used
            and not evidence.target_aware
            and not evidence.broker_mutation_performed
            and not deployment_blockers
        ),
        certification_lane=(
            "EMPIRICAL_EXECUTION"
            if empirical_lane_ready
            else (
                "PREDECLARED_STRESS_BOUND"
                if stress_lane_ready
                else "NOT_READY"
            )
        ),
        blockers=tuple(blockers),
        deployment_blockers=tuple(deployment_blockers),
        execution_calibration_sha256=execution_calibration_sha256,
        provider_stress_bound_sha256=stress_bound_sha256,
        productive_authority=False,
    )


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



def freeze_current_ctrader_demo_provider_economics_stress_bound(
    *,
    frozen_at: datetime,
) -> CiboProviderEconomicsComponentFreeze:
    """Freeze current provider terms with the predeclared stress-bound model.

    This path is intentionally distinct from empirical execution calibration.
    It is admissible for pre-holdout certification only because every stress
    scenario is frozen before the fresh holdout is opened.
    """

    evidence = CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS
    provenance = provider_economics_provenance_payload()
    observed_at = datetime.fromisoformat(evidence.observed_at)
    if frozen_at.tzinfo is None or frozen_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "provider economics stress-bound frozen_at must be timezone-aware"
        )
    if frozen_at < max(
        observed_at,
        FROZEN_PROVIDER_EXECUTION_STRESS_PROFILE.frozen_at,
    ):
        raise CiboCapitalManagementError(
            "provider economics stress-bound freeze predates its evidence"
        )
    if (
        evidence.provider_key != provenance["provider"]
        or tuple(provenance["symbols"]) != evidence.symbols
    ):
        raise CiboCapitalManagementError(
            "provider economics stress-bound evidence/provenance drift"
        )
    current_terms = bool(
        evidence.provider_terms_ready
        and provenance["current_provider_terms_ready"] is True
        and provenance["spread_native_ready"] is True
        and provenance["commission_native_ready"] is True
        and provenance["expected_margin_native_ready"] is True
        and provenance["volume_and_contract_terms_ready"] is True
    )
    blockers: list[str] = []
    if not current_terms:
        blockers.append("CURRENT_PROVIDER_TERMS_NOT_FROZEN")

    return CiboProviderEconomicsComponentFreeze(
        freeze_id=PROVIDER_ECONOMICS_COMPONENT_FREEZE_ID,
        provider_key=evidence.provider_key,
        environment=str(provenance["environment"]),
        source_evidence_ref=provider_economics_evidence_ref(),
        source_provenance_sha256=provider_economics_provenance_sha256(),
        source_observed_at=observed_at,
        frozen_at=frozen_at,
        point_in_time_terms_frozen=current_terms,
        spread_terms_frozen=bool(provenance["spread_native_ready"]),
        commission_terms_frozen=bool(provenance["commission_native_ready"]),
        expected_margin_terms_frozen=bool(
            provenance["expected_margin_native_ready"]
        ),
        volume_contract_terms_frozen=bool(
            provenance["volume_and_contract_terms_ready"]
        ),
        empirical_slippage_frozen=False,
        execution_model_frozen=current_terms,
        stress_bound_execution_model_frozen=current_terms,
        execution_model_basis=(
            "STRESS_BOUND" if current_terms else "UNAVAILABLE"
        ),
        stress_profile_sha256=(
            provider_execution_stress_profile_sha256()
            if current_terms
            else None
        ),
        historical_2017_exact_claimed=False,
        holdout_outcomes_used=False,
        target_aware=False,
        broker_mutation_performed=False,
        pre_holdout_provider_economics_ready=(
            current_terms and not blockers
        ),
        blockers=tuple(blockers),
        execution_calibration_sha256=None,
        productive_authority=False,
    )
