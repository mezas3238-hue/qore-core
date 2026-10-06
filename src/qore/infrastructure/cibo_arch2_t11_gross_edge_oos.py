"""Fresh-OOS validator for the frozen T11 gross-edge model.

The model is exactly the Phase19 TRAIN median-of-means prior. Fresh outcomes
may validate or falsify it but can never refit it. The frozen prediction is
compared against a zero-edge baseline using squared structural-R error in four
chronological folds. Every fold must be non-worse; pooled rescue is forbidden.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_arch2_t11_nonlinear_input_freeze import (
    FROZEN_AT,
    GROSS_EDGE_MINIMUM_OUTCOMES_PER_LINEAGE,
    GROSS_EDGE_REQUIRED_FOLDS,
    GROSS_EDGE_REQUIRED_LINEAGES,
    REQUIRED_SYMBOLS,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    frozen_train_prior_for,
    prior_digest_sha256,
)


@dataclass(frozen=True, slots=True)
class T11GrossEdgeFreshObservation:
    evidence_id: str
    signal_fingerprint: str
    trader_id: TraderLineage
    qore_symbol: str
    observed_at: datetime
    structural_outcome_r: Decimal
    stop_risk_per_volume_usd: Decimal
    outcome_reconciled: bool
    provider_bound: bool
    holdout_receipt_authorized: bool
    model_refit_performed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.signal_fingerprint:
            raise CiboCapitalManagementError(
                "T11 gross-edge fresh observation identity required"
            )
        if type(self.trader_id) is not TraderLineage:
            raise CiboCapitalManagementError(
                "T11 gross-edge trader lineage invalid"
            )
        if self.qore_symbol not in REQUIRED_SYMBOLS:
            raise CiboCapitalManagementError(
                "T11 gross-edge symbol outside frozen execution universe"
            )
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "T11 gross-edge observed_at must be timezone-aware"
            )
        if self.observed_at <= FROZEN_AT:
            raise CiboCapitalManagementError(
                "T11 gross-edge fresh observation must postdate protocol freeze"
            )
        if (
            not isinstance(self.structural_outcome_r, Decimal)
            or not self.structural_outcome_r.is_finite()
        ):
            raise CiboCapitalManagementError(
                "T11 gross-edge structural outcome must be finite Decimal"
            )
        if (
            not isinstance(self.stop_risk_per_volume_usd, Decimal)
            or not self.stop_risk_per_volume_usd.is_finite()
            or self.stop_risk_per_volume_usd <= 0
        ):
            raise CiboCapitalManagementError(
                "T11 gross-edge stop risk per volume must be positive"
            )
        if (
            not self.outcome_reconciled
            or not self.provider_bound
            or not self.holdout_receipt_authorized
            or self.model_refit_performed
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "T11 gross-edge fresh observation governance incomplete"
            )

    @property
    def frozen_prediction_r(self) -> Decimal:
        return frozen_train_prior_for(self.trader_id).expected_structural_r

    @property
    def frozen_gross_edge_per_volume_usd(self) -> Decimal:
        return self.frozen_prediction_r * self.stop_risk_per_volume_usd


@dataclass(frozen=True, slots=True)
class T11GrossEdgeFoldResult:
    fold_index: int
    observations: int
    represented_lineages: tuple[str, ...]
    frozen_model_mse_r2: Decimal
    zero_edge_mse_r2: Decimal
    frozen_model_nonworse: bool


@dataclass(frozen=True, slots=True)
class T11GrossEdgeSymbolResult:
    qore_symbol: str
    observations: int
    frozen_gross_edge_per_volume_usd: Decimal


@dataclass(frozen=True, slots=True)
class T11GrossEdgeFreshOOSResult:
    train_prior_sha256: str
    observation_count: int
    represented_lineages: tuple[str, ...]
    minimum_outcomes_per_lineage: int
    symbols: tuple[T11GrossEdgeSymbolResult, ...]
    folds: tuple[T11GrossEdgeFoldResult, ...]
    four_of_four_nonworse: bool
    fresh_oos_validated: bool
    temporal_stability_validated: bool
    model_refit_performed: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.train_prior_sha256 != prior_digest_sha256():
            raise CiboCapitalManagementError(
                "T11 gross-edge result TRAIN prior lineage drift"
            )
        if len(self.represented_lineages) < GROSS_EDGE_REQUIRED_LINEAGES:
            raise CiboCapitalManagementError(
                "T11 gross-edge result lineage coverage incomplete"
            )
        if self.minimum_outcomes_per_lineage < (
            GROSS_EDGE_MINIMUM_OUTCOMES_PER_LINEAGE
        ):
            raise CiboCapitalManagementError(
                "T11 gross-edge result per-lineage coverage incomplete"
            )
        if tuple(item.qore_symbol for item in self.symbols) != REQUIRED_SYMBOLS:
            raise CiboCapitalManagementError(
                "T11 gross-edge result exact symbol coverage required"
            )
        if tuple(item.fold_index for item in self.folds) != (1, 2, 3, 4):
            raise CiboCapitalManagementError(
                "T11 gross-edge exact four folds required"
            )
        expected = all(item.frozen_model_nonworse for item in self.folds)
        if self.four_of_four_nonworse != expected:
            raise CiboCapitalManagementError(
                "T11 gross-edge four-fold result drift"
            )
        if (
            self.fresh_oos_validated != expected
            or self.temporal_stability_validated != expected
        ):
            raise CiboCapitalManagementError(
                "T11 gross-edge validation result drift"
            )
        if self.model_refit_performed or self.productive_authority:
            raise CiboCapitalManagementError(
                "T11 gross-edge result cannot refit/grant authority"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def evaluate_t11_gross_edge_fresh_oos(
    observations: tuple[T11GrossEdgeFreshObservation, ...],
) -> T11GrossEdgeFreshOOSResult:
    if not observations:
        raise CiboCapitalManagementError(
            "T11 gross-edge fresh population required"
        )
    ids = tuple(item.evidence_id for item in observations)
    if len(ids) != len(set(ids)):
        raise CiboCapitalManagementError(
            "T11 gross-edge evidence ids must be unique"
        )
    signals = tuple(item.signal_fingerprint for item in observations)
    if len(signals) != len(set(signals)):
        raise CiboCapitalManagementError(
            "T11 gross-edge fresh signals must be unique"
        )

    ordered = tuple(sorted(observations, key=lambda item: item.observed_at))
    lineage_counts: dict[TraderLineage, int] = {}
    for item in ordered:
        lineage_counts[item.trader_id] = lineage_counts.get(item.trader_id, 0) + 1
    represented = tuple(sorted(item.value for item in lineage_counts))
    if len(represented) < GROSS_EDGE_REQUIRED_LINEAGES:
        raise CiboCapitalManagementError(
            "T11 gross-edge requires all frozen Trader lineages"
        )
    minimum_per_lineage = min(lineage_counts.values())
    if minimum_per_lineage < GROSS_EDGE_MINIMUM_OUTCOMES_PER_LINEAGE:
        raise CiboCapitalManagementError(
            "T11 gross-edge per-lineage sample threshold not met"
        )
    if len(ordered) < FROZEN_PHASE20D_QUALIFICATION_PLAN.minimum_selected_outcomes:
        raise CiboCapitalManagementError(
            "T11 gross-edge global selected-outcome threshold not met"
        )

    symbols: list[T11GrossEdgeSymbolResult] = []
    for symbol in REQUIRED_SYMBOLS:
        rows = tuple(item for item in ordered if item.qore_symbol == symbol)
        if not rows:
            raise CiboCapitalManagementError(
                f"T11 gross-edge symbol population missing: {symbol}"
            )
        symbols.append(
            T11GrossEdgeSymbolResult(
                qore_symbol=symbol,
                observations=len(rows),
                frozen_gross_edge_per_volume_usd=(
                    sum(
                        (item.frozen_gross_edge_per_volume_usd for item in rows),
                        Decimal(0),
                    )
                    / Decimal(len(rows))
                ),
            )
        )

    folds = _folds(ordered)
    fold_results: list[T11GrossEdgeFoldResult] = []
    for index, fold in enumerate(folds, start=1):
        lineages = tuple(sorted({item.trader_id.value for item in fold}))
        if len(lineages) < FROZEN_PHASE20D_QUALIFICATION_PLAN.minimum_fold_lineages:
            raise CiboCapitalManagementError(
                f"T11 gross-edge fold {index} lineage coverage incomplete"
            )
        model_errors = tuple(
            (item.structural_outcome_r - item.frozen_prediction_r) ** 2
            for item in fold
        )
        zero_errors = tuple(item.structural_outcome_r**2 for item in fold)
        model_mse = _mean(model_errors)
        zero_mse = _mean(zero_errors)
        fold_results.append(
            T11GrossEdgeFoldResult(
                fold_index=index,
                observations=len(fold),
                represented_lineages=lineages,
                frozen_model_mse_r2=model_mse,
                zero_edge_mse_r2=zero_mse,
                frozen_model_nonworse=model_mse <= zero_mse,
            )
        )

    four = all(item.frozen_model_nonworse for item in fold_results)
    return T11GrossEdgeFreshOOSResult(
        train_prior_sha256=prior_digest_sha256(),
        observation_count=len(ordered),
        represented_lineages=represented,
        minimum_outcomes_per_lineage=minimum_per_lineage,
        symbols=tuple(symbols),
        folds=tuple(fold_results),
        four_of_four_nonworse=four,
        fresh_oos_validated=four,
        temporal_stability_validated=four,
        model_refit_performed=False,
        productive_authority=False,
    )


def _folds(
    observations: tuple[T11GrossEdgeFreshObservation, ...],
) -> tuple[tuple[T11GrossEdgeFreshObservation, ...], ...]:
    base = len(observations) // GROSS_EDGE_REQUIRED_FOLDS
    extra = len(observations) % GROSS_EDGE_REQUIRED_FOLDS
    rows: list[tuple[T11GrossEdgeFreshObservation, ...]] = []
    cursor = 0
    for index in range(GROSS_EDGE_REQUIRED_FOLDS):
        size = base + (1 if index < extra else 0)
        rows.append(observations[cursor : cursor + size])
        cursor += size
    return tuple(rows)


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    if not values:
        raise CiboCapitalManagementError(
            "T11 gross-edge mean requires observations"
        )
    return sum(values, Decimal(0)) / Decimal(len(values))
