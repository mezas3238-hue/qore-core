"""Frozen provider-bound economic ablation for CE2I T02 Structural Leverage.

This gate is intentionally downstream of the explicit structural-stop forward
audit. It does not discover leverage settings. It only evaluates whether the
already-frozen T02 treatment adds economic value when compared with the exact
same opportunity under baseline sizing.

No outcome-aware pairing, pooled rescue or post-freeze retuning is allowed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

PROTOCOL_ID = "CIBO_ARCH2_T02_PROVIDER_BOUND_ECONOMIC_ABLATION_V1"
FROZEN_AT = datetime(2026, 10, 1, 23, 28, tzinfo=UTC)
REQUIRED_FOLDS = 4
MINIMUM_PAIRS_PER_FOLD = 8


@dataclass(frozen=True, slots=True)
class T02EconomicAblationPair:
    fold_index: int
    signal_fingerprint: str
    trader_id: TraderLineage
    observed_at: datetime
    provider_evidence_id: str
    structural_evidence_id: str
    baseline_volume: Decimal
    treatment_volume: Decimal
    stop_loss_per_volume_usd: Decimal
    baseline_margin_usd: Decimal
    treatment_margin_usd: Decimal
    baseline_net_pnl_usd: Decimal
    treatment_net_pnl_usd: Decimal
    baseline_max_adverse_r: Decimal
    treatment_max_adverse_r: Decimal
    stop_geometry_unchanged: bool
    provider_bound: bool
    risk_authorized: bool
    outcome_pair_predeclared: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.fold_index not in range(1, REQUIRED_FOLDS + 1):
            raise CiboCapitalManagementError("T02 ablation fold index invalid")
        if not self.signal_fingerprint:
            raise CiboCapitalManagementError("T02 ablation signal identity required")
        if type(self.trader_id) is not TraderLineage:
            raise CiboCapitalManagementError("T02 ablation trader lineage invalid")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise CiboCapitalManagementError("T02 ablation observed_at must be aware")
        if self.observed_at <= FROZEN_AT:
            raise CiboCapitalManagementError(
                "T02 ablation observation must postdate frozen protocol"
            )
        if not self.provider_evidence_id or not self.structural_evidence_id:
            raise CiboCapitalManagementError("T02 ablation evidence lineage required")
        for name in (
            "baseline_volume",
            "treatment_volume",
            "stop_loss_per_volume_usd",
            "baseline_margin_usd",
            "treatment_margin_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"T02 ablation {name} must be positive finite Decimal"
                )
        for name in (
            "baseline_net_pnl_usd",
            "treatment_net_pnl_usd",
            "baseline_max_adverse_r",
            "treatment_max_adverse_r",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"T02 ablation {name} must be finite Decimal"
                )
        if self.treatment_volume <= self.baseline_volume:
            raise CiboCapitalManagementError(
                "T02 ablation treatment must express additional exposure"
            )
        required = (
            self.stop_geometry_unchanged,
            self.provider_bound,
            self.risk_authorized,
            self.outcome_pair_predeclared,
        )
        if not all(required) or self.productive_authority:
            raise CiboCapitalManagementError(
                "T02 ablation causal/provider governance incomplete"
            )

    @property
    def baseline_stop_risk_usd(self) -> Decimal:
        return self.stop_loss_per_volume_usd * self.baseline_volume

    @property
    def treatment_stop_risk_usd(self) -> Decimal:
        return self.stop_loss_per_volume_usd * self.treatment_volume

    @property
    def incremental_stop_risk_usd(self) -> Decimal:
        return self.treatment_stop_risk_usd - self.baseline_stop_risk_usd

    @property
    def incremental_net_pnl_usd(self) -> Decimal:
        return self.treatment_net_pnl_usd - self.baseline_net_pnl_usd

    @property
    def incremental_return_on_risk(self) -> Decimal:
        return self.incremental_net_pnl_usd / self.incremental_stop_risk_usd


@dataclass(frozen=True, slots=True)
class T02EconomicFoldResult:
    fold_index: int
    pair_count: int
    incremental_net_pnl_usd: Decimal
    incremental_stop_risk_usd: Decimal
    incremental_return_on_risk: Decimal
    baseline_p95_adverse_r: Decimal
    treatment_p95_adverse_r: Decimal
    economic_value_positive: bool
    normalized_tail_nonworse: bool
    pass_gate: bool


@dataclass(frozen=True, slots=True)
class T02EconomicAblationResult:
    protocol_id: str
    fold_results: tuple[T02EconomicFoldResult, ...]
    four_of_four_pass: bool
    provider_bound_economic_value_proven: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.protocol_id != PROTOCOL_ID:
            raise CiboCapitalManagementError("T02 ablation protocol identity drift")
        if tuple(item.fold_index for item in self.fold_results) != (1, 2, 3, 4):
            raise CiboCapitalManagementError("T02 ablation exact fold surface required")
        expected = all(item.pass_gate for item in self.fold_results)
        if self.four_of_four_pass != expected:
            raise CiboCapitalManagementError("T02 ablation 4/4 result drift")
        if self.provider_bound_economic_value_proven != expected:
            raise CiboCapitalManagementError("T02 ablation terminal result drift")
        if self.productive_authority:
            raise CiboCapitalManagementError("T02 ablation grants no authority")


def evaluate_t02_provider_bound_economic_ablation(
    pairs: tuple[T02EconomicAblationPair, ...],
) -> T02EconomicAblationResult:
    if not pairs:
        raise CiboCapitalManagementError("T02 ablation population required")
    keys = tuple((item.fold_index, item.signal_fingerprint) for item in pairs)
    if len(keys) != len(set(keys)):
        raise CiboCapitalManagementError("T02 ablation duplicate fold/signal pair")

    fold_results: list[T02EconomicFoldResult] = []
    for fold_index in range(1, REQUIRED_FOLDS + 1):
        fold = tuple(item for item in pairs if item.fold_index == fold_index)
        if len(fold) < MINIMUM_PAIRS_PER_FOLD:
            raise CiboCapitalManagementError(
                f"T02 ablation fold {fold_index} minimum sample not met"
            )
        incremental_pnl = sum(
            (item.incremental_net_pnl_usd for item in fold), Decimal(0)
        )
        incremental_risk = sum(
            (item.incremental_stop_risk_usd for item in fold), Decimal(0)
        )
        if incremental_risk <= 0:
            raise CiboCapitalManagementError(
                "T02 ablation incremental risk must be positive"
            )
        return_on_risk = incremental_pnl / incremental_risk
        baseline_p95 = _p95(tuple(item.baseline_max_adverse_r for item in fold))
        treatment_p95 = _p95(tuple(item.treatment_max_adverse_r for item in fold))
        economic_positive = incremental_pnl > 0 and return_on_risk > 0
        tail_nonworse = treatment_p95 <= baseline_p95
        fold_results.append(
            T02EconomicFoldResult(
                fold_index=fold_index,
                pair_count=len(fold),
                incremental_net_pnl_usd=incremental_pnl,
                incremental_stop_risk_usd=incremental_risk,
                incremental_return_on_risk=return_on_risk,
                baseline_p95_adverse_r=baseline_p95,
                treatment_p95_adverse_r=treatment_p95,
                economic_value_positive=economic_positive,
                normalized_tail_nonworse=tail_nonworse,
                pass_gate=economic_positive and tail_nonworse,
            )
        )

    four = all(item.pass_gate for item in fold_results)
    return T02EconomicAblationResult(
        protocol_id=PROTOCOL_ID,
        fold_results=tuple(fold_results),
        four_of_four_pass=four,
        provider_bound_economic_value_proven=four,
        productive_authority=False,
    )


def _p95(values: tuple[Decimal, ...]) -> Decimal:
    if not values:
        raise CiboCapitalManagementError("T02 ablation p95 requires observations")
    ordered = tuple(sorted(values))
    index = max(0, ((95 * len(ordered) + 99) // 100) - 1)
    return ordered[index]
