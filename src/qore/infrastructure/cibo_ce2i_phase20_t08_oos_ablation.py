"""Fresh OOS shadow-ablation contract for CE2I T08 portfolio netting.

The treatment policy must be sealed before outcomes are known. The evaluator
compares a gross-risk baseline against factor-netting selection over contiguous
forward folds. It requires incremental capital utility, no worse realized
settlement drawdown, and pathwise peak loss staying inside the treatment's
netted risk authorization.

Passing this contract demonstrates OOS utility only. It does not independently
certify the signed factor-risk mapping or correlation estimator; those evidence
identities remain separately bound and must be certified before runtime credit.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

T08_OOS_ABLATION_CONTRACT_ID = "CIBO_T08_FRESH_OOS_NETTING_ABLATION_V1"

_MAX_NETTING_CREDIT_FRACTION = Decimal("0.50")


@dataclass(frozen=True, slots=True)
class T08NettingShadowEpoch:
    epoch_id: str
    decision_at: datetime
    shadow_sealed_at: datetime
    outcome_observed_at: datetime
    baseline_selected_count: int
    treatment_selected_count: int
    baseline_realized_net_pnl_usd: Decimal
    treatment_realized_net_pnl_usd: Decimal
    baseline_peak_loss_usd: Decimal
    treatment_peak_loss_usd: Decimal
    treatment_gross_stop_risk_usd: Decimal
    treatment_netted_risk_usd: Decimal
    netting_credit_usd: Decimal
    risk_mapping_evidence_id: str
    correlation_evidence_id: str
    outcome_evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.epoch_id:
            raise CiboCapitalManagementError(
                "T08 shadow epoch identity is required"
            )
        for name in (
            "decision_at",
            "shadow_sealed_at",
            "outcome_observed_at",
        ):
            _aware(getattr(self, name), f"T08 shadow {name}")
        if self.shadow_sealed_at < self.decision_at:
            raise CiboCapitalManagementError(
                "T08 shadow policy cannot seal before decision"
            )
        if self.outcome_observed_at <= self.shadow_sealed_at:
            raise CiboCapitalManagementError(
                "T08 shadow outcomes must postdate sealed treatment policy"
            )
        for name in (
            "baseline_selected_count",
            "treatment_selected_count",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"T08 shadow {name} must be non-negative int"
                )
        for name in (
            "baseline_realized_net_pnl_usd",
            "treatment_realized_net_pnl_usd",
        ):
            _finite(getattr(self, name), f"T08 shadow {name}")
        for name in (
            "baseline_peak_loss_usd",
            "treatment_peak_loss_usd",
            "treatment_gross_stop_risk_usd",
            "treatment_netted_risk_usd",
            "netting_credit_usd",
        ):
            _non_negative(getattr(self, name), f"T08 shadow {name}")
        if self.treatment_gross_stop_risk_usd <= 0:
            raise CiboCapitalManagementError(
                "T08 shadow treatment gross stop risk must be positive"
            )
        if self.treatment_netted_risk_usd <= 0:
            raise CiboCapitalManagementError(
                "T08 shadow treatment netted risk must be positive"
            )
        if self.treatment_netted_risk_usd > self.treatment_gross_stop_risk_usd:
            raise CiboCapitalManagementError(
                "T08 shadow netted risk cannot exceed gross stop risk"
            )
        if (
            self.treatment_gross_stop_risk_usd
            - self.treatment_netted_risk_usd
            != self.netting_credit_usd
        ):
            raise CiboCapitalManagementError(
                "T08 shadow netting-credit accounting mismatch"
            )
        if (
            self.netting_credit_usd
            / self.treatment_gross_stop_risk_usd
            > _MAX_NETTING_CREDIT_FRACTION
        ):
            raise CiboCapitalManagementError(
                "T08 shadow netting credit exceeds frozen 50% ceiling"
            )
        if not self.risk_mapping_evidence_id:
            raise CiboCapitalManagementError(
                "T08 shadow risk-mapping evidence id is required"
            )
        if not self.correlation_evidence_id:
            raise CiboCapitalManagementError(
                "T08 shadow correlation evidence id is required"
            )
        if (
            not self.outcome_evidence_ids
            or len(self.outcome_evidence_ids)
            != len(set(self.outcome_evidence_ids))
            or any(not item for item in self.outcome_evidence_ids)
        ):
            raise CiboCapitalManagementError(
                "T08 shadow outcome evidence ids must be unique/non-empty"
            )


@dataclass(frozen=True, slots=True)
class T08NettingOosFold:
    fold_index: int
    epoch_count: int
    baseline_selected_count: int
    treatment_selected_count: int
    baseline_total_pnl_usd: Decimal
    treatment_total_pnl_usd: Decimal
    baseline_max_drawdown_usd: Decimal
    treatment_max_drawdown_usd: Decimal
    treatment_peak_loss_within_authorization: bool
    non_worse_drawdown: bool
    non_worse_pnl: bool

    def __post_init__(self) -> None:
        if self.fold_index < 0 or self.epoch_count < 2:
            raise CiboCapitalManagementError(
                "T08 OOS fold identity/sample invalid"
            )
        for name in (
            "baseline_selected_count",
            "treatment_selected_count",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"T08 OOS fold {name} invalid"
                )
        for name in (
            "baseline_total_pnl_usd",
            "treatment_total_pnl_usd",
            "baseline_max_drawdown_usd",
            "treatment_max_drawdown_usd",
        ):
            _finite(getattr(self, name), f"T08 OOS fold {name}")
        if (
            self.baseline_max_drawdown_usd < 0
            or self.treatment_max_drawdown_usd < 0
        ):
            raise CiboCapitalManagementError(
                "T08 OOS fold drawdown cannot be negative"
            )


@dataclass(frozen=True, slots=True)
class T08NettingOosAblationReport:
    sample_size: int
    minimum_epochs: int
    required_folds: int
    folds: tuple[T08NettingOosFold, ...]
    baseline_selected_count: int
    treatment_selected_count: int
    incremental_selected_count: int
    baseline_total_pnl_usd: Decimal
    treatment_total_pnl_usd: Decimal
    baseline_max_drawdown_usd: Decimal
    treatment_max_drawdown_usd: Decimal
    mapping_evidence_bound: bool
    correlation_evidence_bound: bool
    pathwise_authorization_respected: bool
    fresh_oos_utility_demonstrated: bool
    risk_mapping_verified: bool
    correlation_state_verified: bool
    netting_credit_authorized: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "sample_size",
            "minimum_epochs",
            "required_folds",
            "baseline_selected_count",
            "treatment_selected_count",
            "incremental_selected_count",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"T08 OOS report {name} invalid"
                )
        if self.minimum_epochs < 2 or self.required_folds != 4:
            raise CiboCapitalManagementError(
                "T08 OOS report requires exactly four temporal folds"
            )
        for name in (
            "baseline_total_pnl_usd",
            "treatment_total_pnl_usd",
            "baseline_max_drawdown_usd",
            "treatment_max_drawdown_usd",
        ):
            _finite(getattr(self, name), f"T08 OOS report {name}")
        if (
            self.baseline_max_drawdown_usd < 0
            or self.treatment_max_drawdown_usd < 0
        ):
            raise CiboCapitalManagementError(
                "T08 OOS report drawdown cannot be negative"
            )
        if self.risk_mapping_verified or self.correlation_state_verified:
            raise CiboCapitalManagementError(
                "T08 OOS utility contract cannot independently certify mapping/correlation"
            )
        if self.netting_credit_authorized:
            raise CiboCapitalManagementError(
                "T08 OOS utility contract cannot authorize runtime netting"
            )


def assess_t08_fresh_oos_netting_ablation(
    epochs: tuple[T08NettingShadowEpoch, ...],
    *,
    minimum_epochs: int = 30,
    required_folds: int = 4,
) -> T08NettingOosAblationReport:
    """Evaluate a sealed gross-vs-netting shadow comparison on fresh evidence."""

    if minimum_epochs < 2:
        raise CiboCapitalManagementError(
            "T08 OOS minimum_epochs must be at least two"
        )
    if required_folds != 4:
        raise CiboCapitalManagementError(
            "T08 OOS required_folds must be exactly four"
        )
    if not epochs:
        return _empty_report(
            minimum_epochs=minimum_epochs,
            required_folds=required_folds,
        )

    ordered = tuple(
        sorted(
            epochs,
            key=lambda item: (item.decision_at, item.epoch_id),
        )
    )
    epoch_ids = tuple(item.epoch_id for item in ordered)
    if len(epoch_ids) != len(set(epoch_ids)):
        raise CiboCapitalManagementError(
            "T08 OOS shadow epoch ids must be unique"
        )
    if any(
        current.decision_at <= previous.decision_at
        for previous, current in zip(ordered, ordered[1:], strict=False)
    ):
        raise CiboCapitalManagementError(
            "T08 OOS shadow decisions must advance strictly in time"
        )

    folds = _build_folds(ordered, required_folds=required_folds)
    baseline_selected = sum(item.baseline_selected_count for item in ordered)
    treatment_selected = sum(item.treatment_selected_count for item in ordered)
    incremental_selected = treatment_selected - baseline_selected
    baseline_pnl = sum(
        (item.baseline_realized_net_pnl_usd for item in ordered),
        Decimal(0),
    )
    treatment_pnl = sum(
        (item.treatment_realized_net_pnl_usd for item in ordered),
        Decimal(0),
    )
    baseline_dd = _max_drawdown(
        tuple(item.baseline_realized_net_pnl_usd for item in ordered)
    )
    treatment_dd = _max_drawdown(
        tuple(item.treatment_realized_net_pnl_usd for item in ordered)
    )
    mapping_bound = all(item.risk_mapping_evidence_id for item in ordered)
    correlation_bound = all(item.correlation_evidence_id for item in ordered)
    pathwise_authorization = all(
        item.treatment_peak_loss_usd <= item.treatment_netted_risk_usd
        for item in ordered
    )

    sample_ready = len(ordered) >= minimum_epochs
    folds_ready = len(folds) == required_folds
    all_folds_safe = folds_ready and all(
        fold.treatment_peak_loss_within_authorization
        and fold.non_worse_drawdown
        and fold.non_worse_pnl
        for fold in folds
    )
    utility = (
        sample_ready
        and folds_ready
        and mapping_bound
        and correlation_bound
        and pathwise_authorization
        and incremental_selected > 0
        and treatment_pnl >= baseline_pnl
        and treatment_dd <= baseline_dd
        and all_folds_safe
    )

    blockers: list[str] = []
    if not sample_ready:
        blockers.append(
            f"T08_OOS_MINIMUM_EPOCHS_NOT_MET:{len(ordered)}/{minimum_epochs}"
        )
    if not folds_ready:
        blockers.append(
            f"T08_OOS_FOLD_COVERAGE_NOT_MET:{len(folds)}/{required_folds}"
        )
    if not mapping_bound:
        blockers.append("T08_OOS_RISK_MAPPING_EVIDENCE_NOT_BOUND")
    if not correlation_bound:
        blockers.append("T08_OOS_CORRELATION_EVIDENCE_NOT_BOUND")
    if incremental_selected <= 0:
        blockers.append("T08_OOS_NO_INCREMENTAL_CAPITAL_UTILITY")
    if treatment_pnl < baseline_pnl:
        blockers.append("T08_OOS_TREATMENT_PNL_WORSE_THAN_BASELINE")
    if treatment_dd > baseline_dd:
        blockers.append("T08_OOS_TREATMENT_DRAWDOWN_WORSE_THAN_BASELINE")
    if not pathwise_authorization:
        blockers.append("T08_OOS_NETTED_RISK_AUTHORIZATION_BREACHED")
    if folds_ready and not all_folds_safe:
        blockers.append("T08_OOS_FOLD_SAFETY_OR_UTILITY_NOT_ROBUST")
    if utility:
        blockers.extend(
            (
                "SIGNED_FACTOR_RISK_MAP_REQUIRES_INDEPENDENT_CERTIFICATION",
                "CORRELATION_STATE_REQUIRES_INDEPENDENT_CERTIFICATION",
            )
        )
    else:
        blockers.append("FRESH_OOS_NETTING_UTILITY_NOT_DEMONSTRATED")

    return T08NettingOosAblationReport(
        sample_size=len(ordered),
        minimum_epochs=minimum_epochs,
        required_folds=required_folds,
        folds=folds,
        baseline_selected_count=baseline_selected,
        treatment_selected_count=treatment_selected,
        incremental_selected_count=incremental_selected,
        baseline_total_pnl_usd=baseline_pnl,
        treatment_total_pnl_usd=treatment_pnl,
        baseline_max_drawdown_usd=baseline_dd,
        treatment_max_drawdown_usd=treatment_dd,
        mapping_evidence_bound=mapping_bound,
        correlation_evidence_bound=correlation_bound,
        pathwise_authorization_respected=pathwise_authorization,
        fresh_oos_utility_demonstrated=utility,
        risk_mapping_verified=False,
        correlation_state_verified=False,
        netting_credit_authorized=False,
        blockers=tuple(blockers),
    )


def _build_folds(
    epochs: tuple[T08NettingShadowEpoch, ...],
    *,
    required_folds: int,
) -> tuple[T08NettingOosFold, ...]:
    if len(epochs) < required_folds * 2:
        return ()
    base = len(epochs) // required_folds
    extra = len(epochs) % required_folds
    folds: list[T08NettingOosFold] = []
    cursor = 0
    for fold_index in range(required_folds):
        size = base + (1 if fold_index < extra else 0)
        subset = epochs[cursor : cursor + size]
        cursor += size
        baseline_pnl = tuple(
            item.baseline_realized_net_pnl_usd for item in subset
        )
        treatment_pnl = tuple(
            item.treatment_realized_net_pnl_usd for item in subset
        )
        baseline_total = sum(baseline_pnl, Decimal(0))
        treatment_total = sum(treatment_pnl, Decimal(0))
        baseline_dd = _max_drawdown(baseline_pnl)
        treatment_dd = _max_drawdown(treatment_pnl)
        folds.append(
            T08NettingOosFold(
                fold_index=fold_index,
                epoch_count=len(subset),
                baseline_selected_count=sum(
                    item.baseline_selected_count for item in subset
                ),
                treatment_selected_count=sum(
                    item.treatment_selected_count for item in subset
                ),
                baseline_total_pnl_usd=baseline_total,
                treatment_total_pnl_usd=treatment_total,
                baseline_max_drawdown_usd=baseline_dd,
                treatment_max_drawdown_usd=treatment_dd,
                treatment_peak_loss_within_authorization=all(
                    item.treatment_peak_loss_usd
                    <= item.treatment_netted_risk_usd
                    for item in subset
                ),
                non_worse_drawdown=treatment_dd <= baseline_dd,
                non_worse_pnl=treatment_total >= baseline_total,
            )
        )
    return tuple(folds)


def _max_drawdown(pnl_path: tuple[Decimal, ...]) -> Decimal:
    cumulative = Decimal(0)
    peak = Decimal(0)
    maximum = Decimal(0)
    for pnl in pnl_path:
        cumulative += pnl
        peak = max(peak, cumulative)
        maximum = max(maximum, peak - cumulative)
    return maximum


def _empty_report(
    *,
    minimum_epochs: int,
    required_folds: int,
) -> T08NettingOosAblationReport:
    return T08NettingOosAblationReport(
        sample_size=0,
        minimum_epochs=minimum_epochs,
        required_folds=required_folds,
        folds=(),
        baseline_selected_count=0,
        treatment_selected_count=0,
        incremental_selected_count=0,
        baseline_total_pnl_usd=Decimal(0),
        treatment_total_pnl_usd=Decimal(0),
        baseline_max_drawdown_usd=Decimal(0),
        treatment_max_drawdown_usd=Decimal(0),
        mapping_evidence_bound=False,
        correlation_evidence_bound=False,
        pathwise_authorization_respected=False,
        fresh_oos_utility_demonstrated=False,
        risk_mapping_verified=False,
        correlation_state_verified=False,
        netting_credit_authorized=False,
        blockers=(
            f"T08_OOS_MINIMUM_EPOCHS_NOT_MET:0/{minimum_epochs}",
            f"T08_OOS_FOLD_COVERAGE_NOT_MET:0/{required_folds}",
            "T08_OOS_RISK_MAPPING_EVIDENCE_NOT_BOUND",
            "T08_OOS_CORRELATION_EVIDENCE_NOT_BOUND",
            "T08_OOS_NO_INCREMENTAL_CAPITAL_UTILITY",
            "FRESH_OOS_NETTING_UTILITY_NOT_DEMONSTRATED",
        ),
    )


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(f"{name} must be timezone-aware")


def _finite(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboCapitalManagementError(f"{name} must be finite Decimal")


def _non_negative(value: Decimal, name: str) -> None:
    _finite(value, name)
    if value < 0:
        raise CiboCapitalManagementError(
            f"{name} must be non-negative Decimal"
        )
