"""GEN-C2 causal economic gate for profit graduation into protected floor.

GEN-C2 asks whether graduating already-realized Core profit into a protected
capital floor improves robust capital preservation without paying for it with
worse economic output or safety.

The A2-owned Compound engine supplies historical-replay realized-profit lineage
through the explicit A1 dependency admission. This gate does not create lots,
broker identifiers, floor tranches, or runtime authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_a1_phase22_historical_compound_dependency import (
    A1HistoricalCompoundDependencyAdmission,
)
from qore.infrastructure.cibo_a1_phase22_scientific_consumption import (
    A1Phase22ScientificConsumptionManifest,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError

GATE_ID = "CIBO_A1_GENC2_PHASE22_PROFIT_GRADUATION_ECONOMIC_GATE_V1"
_CANONICAL_FOLDS = ("WF1", "WF2", "WF3", "WF4")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class Genc2EconomicRole(StrEnum):
    CONTROL = "CONTROL"
    TREATMENT = "TREATMENT"


class Genc2EconomicStatus(StrEnum):
    CONTROL = "CONTROL"
    ELIGIBLE_FOR_FURTHER_RESEARCH = "ELIGIBLE_FOR_FURTHER_RESEARCH"
    REJECTED_SAFETY_DETERIORATION = "REJECTED_SAFETY_DETERIORATION"
    REJECTED_NOT_STRICT_4_OF_4 = "REJECTED_NOT_STRICT_4_OF_4"


@dataclass(frozen=True, slots=True)
class Genc2ProfitGraduationFoldObservation:
    candidate_id: str
    role: Genc2EconomicRole
    fold_id: str
    population_sha256: str
    compound_dependency_receipt_sha256: str
    provider_surface_sha256: str
    protocol_binding_sha256: str
    realized_net_delta_usd: Decimal
    ending_realized_capital_usd: Decimal
    ending_protected_floor_usd: Decimal
    minimum_base_capital_usd: Decimal
    maximum_drawdown_usd: Decimal
    p99_drawdown_usd: Decimal
    peak_plausible_loss_usd: Decimal
    provider_cost_usd: Decimal
    provider_failure_count: int
    minimum_liquid_reserve_usd: Decimal
    minimum_optionality_usd: Decimal
    capital_risk_time_productivity: Decimal
    source_realized_profit_usd: Decimal
    graduated_realized_profit_usd: Decimal
    capital_conservation_breach_count: int
    causal_effect_identified: bool
    treatment_preregistered_before_outcomes: bool
    double_spend_detected: bool = False
    floating_pnl_used_as_capital: bool = False
    base_capital_relabelled_as_profit: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise CiboCompoundCapitalError(
                "GEN-C2 economic candidate identity required"
            )
        if type(self.role) is not Genc2EconomicRole:
            raise CiboCompoundCapitalError(
                "GEN-C2 economic role invalid"
            )
        if self.fold_id not in _CANONICAL_FOLDS:
            raise CiboCompoundCapitalError(
                "GEN-C2 economic fold must be WF1..WF4"
            )
        for name in (
            "population_sha256",
            "compound_dependency_receipt_sha256",
            "provider_surface_sha256",
            "protocol_binding_sha256",
        ):
            _sha(getattr(self, name), name)

        for name in (
            "ending_realized_capital_usd",
            "ending_protected_floor_usd",
            "minimum_base_capital_usd",
            "maximum_drawdown_usd",
            "p99_drawdown_usd",
            "peak_plausible_loss_usd",
            "provider_cost_usd",
            "minimum_liquid_reserve_usd",
            "minimum_optionality_usd",
            "source_realized_profit_usd",
            "graduated_realized_profit_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"GEN-C2 economic {name} must be finite non-negative"
                )
        for name in (
            "realized_net_delta_usd",
            "capital_risk_time_productivity",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCompoundCapitalError(
                    f"GEN-C2 economic {name} must be finite Decimal"
                )
        for name in (
            "provider_failure_count",
            "capital_conservation_breach_count",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise CiboCompoundCapitalError(
                    f"GEN-C2 economic {name} must be non-negative int"
                )

        if self.role is Genc2EconomicRole.CONTROL:
            if self.graduated_realized_profit_usd != 0:
                raise CiboCompoundCapitalError(
                    "GEN-C2 control cannot graduate profit"
                )
        else:
            if self.graduated_realized_profit_usd <= 0:
                raise CiboCompoundCapitalError(
                    "GEN-C2 treatment requires positive profit graduation"
                )
            if (
                self.graduated_realized_profit_usd
                > self.source_realized_profit_usd
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C2 cannot graduate more than realized source profit"
                )

        if (
            not self.causal_effect_identified
            or not self.treatment_preregistered_before_outcomes
            or self.double_spend_detected
            or self.floating_pnl_used_as_capital
            or self.base_capital_relabelled_as_profit
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "GEN-C2 economic observation governance/causal drift"
            )


@dataclass(frozen=True, slots=True)
class Genc2CandidateVerdict:
    candidate_id: str
    status: Genc2EconomicStatus
    passed_fold_ids: tuple[str, ...]
    failed_fold_ids: tuple[str, ...]
    failed_dimensions: tuple[str, ...]
    production_promotion: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id or type(self.status) is not Genc2EconomicStatus:
            raise CiboCompoundCapitalError(
                "GEN-C2 verdict identity/status drift"
            )
        if self.status is Genc2EconomicStatus.CONTROL:
            if (
                self.passed_fold_ids != _CANONICAL_FOLDS
                or self.failed_fold_ids
                or self.failed_dimensions
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C2 control verdict fold drift"
                )
        else:
            if set(self.passed_fold_ids) | set(self.failed_fold_ids) != set(
                _CANONICAL_FOLDS
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C2 treatment verdict requires complete WF1..WF4"
                )
            expected = (
                Genc2EconomicStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
                if self.passed_fold_ids == _CANONICAL_FOLDS
                else (
                    Genc2EconomicStatus.REJECTED_SAFETY_DETERIORATION
                    if any(
                        ":SAFETY:" in item
                        for item in self.failed_dimensions
                    )
                    else Genc2EconomicStatus.REJECTED_NOT_STRICT_4_OF_4
                )
            )
            if self.status is not expected:
                raise CiboCompoundCapitalError(
                    "GEN-C2 verdict status/fold drift"
                )
        if self.production_promotion or self.certification_ready:
            raise CiboCompoundCapitalError(
                "GEN-C2 verdict grants no promotion/certification authority"
            )


@dataclass(frozen=True, slots=True)
class Genc2Phase22EconomicGateReport:
    gate_id: str
    manifest_sha256: str
    compound_dependency_receipt_sha256: str
    control_candidate_id: str
    verdicts: tuple[Genc2CandidateVerdict, ...]
    all_four_folds_required: bool = True
    weighted_score_used: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != GATE_ID:
            raise CiboCompoundCapitalError(
                "GEN-C2 gate identity drift"
            )
        _sha(self.manifest_sha256, "manifest_sha256")
        _sha(
            self.compound_dependency_receipt_sha256,
            "compound_dependency_receipt_sha256",
        )
        if (
            not self.control_candidate_id
            or not self.verdicts
            or len({item.candidate_id for item in self.verdicts})
            != len(self.verdicts)
        ):
            raise CiboCompoundCapitalError(
                "GEN-C2 gate candidate surface invalid"
            )
        controls = tuple(
            item for item in self.verdicts
            if item.status is Genc2EconomicStatus.CONTROL
        )
        if (
            len(controls) != 1
            or controls[0].candidate_id != self.control_candidate_id
        ):
            raise CiboCompoundCapitalError(
                "GEN-C2 gate control verdict drift"
            )
        if (
            not self.all_four_folds_required
            or self.weighted_score_used
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "GEN-C2 gate governance drift"
            )


def evaluate_genc2_phase22_profit_graduation(
    *,
    manifest: A1Phase22ScientificConsumptionManifest,
    compound_dependency: A1HistoricalCompoundDependencyAdmission,
    observations: tuple[Genc2ProfitGraduationFoldObservation, ...],
) -> Genc2Phase22EconomicGateReport:
    """Require non-compensatory GEN-C2 utility independently in WF1..WF4."""

    if not isinstance(manifest, A1Phase22ScientificConsumptionManifest):
        raise CiboCompoundCapitalError(
            "GEN-C2 requires canonical Phase22 manifest"
        )
    if not isinstance(
        compound_dependency,
        A1HistoricalCompoundDependencyAdmission,
    ):
        raise CiboCompoundCapitalError(
            "GEN-C2 requires admitted historical Compound dependency"
        )
    if compound_dependency.manifest_sha256 != manifest.fingerprint():
        raise CiboCompoundCapitalError(
            "GEN-C2 Compound admission/manifest drift"
        )
    if not observations:
        raise CiboCompoundCapitalError(
            "GEN-C2 economic observations required"
        )

    fold_population = {
        item.fold_id: item.population_sha256 for item in manifest.folds
    }
    receipt_sha = compound_dependency.receipt_sha256
    for item in observations:
        if item.population_sha256 != fold_population[item.fold_id]:
            raise CiboCompoundCapitalError(
                "GEN-C2 observation population differs from Phase22 fold"
            )
        if item.compound_dependency_receipt_sha256 != receipt_sha:
            raise CiboCompoundCapitalError(
                "GEN-C2 observation Compound dependency receipt drift"
            )

    control_ids = {
        item.candidate_id
        for item in observations
        if item.role is Genc2EconomicRole.CONTROL
    }
    if len(control_ids) != 1:
        raise CiboCompoundCapitalError(
            "GEN-C2 gate requires exactly one control candidate"
        )
    control_id = next(iter(control_ids))
    control_rows = _rows_by_fold(observations, control_id)
    treatment_ids = sorted(
        {
            item.candidate_id
            for item in observations
            if item.role is Genc2EconomicRole.TREATMENT
        }
    )
    if not treatment_ids:
        raise CiboCompoundCapitalError(
            "GEN-C2 gate requires treatment candidate"
        )

    verdicts: list[Genc2CandidateVerdict] = [
        Genc2CandidateVerdict(
            candidate_id=control_id,
            status=Genc2EconomicStatus.CONTROL,
            passed_fold_ids=_CANONICAL_FOLDS,
            failed_fold_ids=(),
            failed_dimensions=(),
        )
    ]
    for candidate_id in treatment_ids:
        treatment_rows = _rows_by_fold(observations, candidate_id)
        passed: list[str] = []
        failed: list[str] = []
        failed_dimensions: list[str] = []
        for fold_id in _CANONICAL_FOLDS:
            control = control_rows[fold_id]
            treatment = treatment_rows[fold_id]
            _comparable(control, treatment)

            dimensions: list[str] = []
            for name in (
                "maximum_drawdown_usd",
                "p99_drawdown_usd",
                "peak_plausible_loss_usd",
                "provider_cost_usd",
                "provider_failure_count",
                "capital_conservation_breach_count",
            ):
                if getattr(treatment, name) > getattr(control, name):
                    dimensions.append(name)
            for name in (
                "realized_net_delta_usd",
                "ending_realized_capital_usd",
                "minimum_base_capital_usd",
                "minimum_liquid_reserve_usd",
                "minimum_optionality_usd",
            ):
                if getattr(treatment, name) < getattr(control, name):
                    dimensions.append(name)

            if dimensions:
                failed.append(fold_id)
                failed_dimensions.extend(
                    f"{fold_id}:SAFETY:{name}" for name in dimensions
                )
                continue

            strict = any(
                (
                    treatment.ending_protected_floor_usd
                    > control.ending_protected_floor_usd,
                    treatment.minimum_base_capital_usd
                    > control.minimum_base_capital_usd,
                    treatment.maximum_drawdown_usd
                    < control.maximum_drawdown_usd,
                    treatment.p99_drawdown_usd
                    < control.p99_drawdown_usd,
                    treatment.peak_plausible_loss_usd
                    < control.peak_plausible_loss_usd,
                    treatment.minimum_optionality_usd
                    > control.minimum_optionality_usd,
                    treatment.capital_risk_time_productivity
                    > control.capital_risk_time_productivity,
                )
            )
            if strict:
                passed.append(fold_id)
            else:
                failed.append(fold_id)
                failed_dimensions.append(
                    f"{fold_id}:NO_STRICT_IMPROVEMENT"
                )

        passed_tuple = tuple(passed)
        failed_tuple = tuple(failed)
        if passed_tuple == _CANONICAL_FOLDS:
            status = Genc2EconomicStatus.ELIGIBLE_FOR_FURTHER_RESEARCH
        elif any(":SAFETY:" in item for item in failed_dimensions):
            status = Genc2EconomicStatus.REJECTED_SAFETY_DETERIORATION
        else:
            status = Genc2EconomicStatus.REJECTED_NOT_STRICT_4_OF_4
        verdicts.append(
            Genc2CandidateVerdict(
                candidate_id=candidate_id,
                status=status,
                passed_fold_ids=passed_tuple,
                failed_fold_ids=failed_tuple,
                failed_dimensions=tuple(failed_dimensions),
            )
        )

    return Genc2Phase22EconomicGateReport(
        gate_id=GATE_ID,
        manifest_sha256=manifest.fingerprint(),
        compound_dependency_receipt_sha256=receipt_sha,
        control_candidate_id=control_id,
        verdicts=tuple(verdicts),
    )


def _rows_by_fold(
    observations: tuple[Genc2ProfitGraduationFoldObservation, ...],
    candidate_id: str,
) -> dict[str, Genc2ProfitGraduationFoldObservation]:
    rows = tuple(
        item for item in observations if item.candidate_id == candidate_id
    )
    by_fold = {item.fold_id: item for item in rows}
    if len(rows) != 4 or set(by_fold) != set(_CANONICAL_FOLDS):
        raise CiboCompoundCapitalError(
            "GEN-C2 candidate requires exactly WF1..WF4"
        )
    return by_fold


def _comparable(
    control: Genc2ProfitGraduationFoldObservation,
    treatment: Genc2ProfitGraduationFoldObservation,
) -> None:
    if (
        control.fold_id != treatment.fold_id
        or control.population_sha256 != treatment.population_sha256
        or control.compound_dependency_receipt_sha256
        != treatment.compound_dependency_receipt_sha256
        or control.provider_surface_sha256 != treatment.provider_surface_sha256
        or control.protocol_binding_sha256 != treatment.protocol_binding_sha256
    ):
        raise CiboCompoundCapitalError(
            "GEN-C2 requires identical causal comparison surface"
        )


def _sha(value: str, name: str) -> None:
    if _SHA256_RE.fullmatch(value) is None:
        raise CiboCompoundCapitalError(
            f"GEN-C2 {name} must be canonical SHA-256"
        )
