"""Materialize the provider-valid AS-IS economic baseline for Architect A.

This adapter consumes, but never mutates, the frozen Phase20D qualification
report and the strict forward Compound binding. It accepts economically PASS or
FAIL populations when causal readiness is complete; NOT_READY and INVALID fail
closed. No missing value is synthesized.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_ce2i_phase20_qualification import (
    Phase20QualificationReport,
    Phase20QualificationStatus,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_compound_real_population_binding import (
    ForwardCompoundEconomicRecord,
)

AS_IS_CONTROL_ID = "CIBO_GENERATION_CURRENT_CONTROL_V1"
AS_IS_CONTROL_GIT_SHA = "87d98ced8d56b275823c4472392923ba6a11d769"
_CANONICAL_FOLDS = ("WF1", "WF2", "WF3", "WF4")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class AsIsEconomicBaselineState(StrEnum):
    MATERIALIZED = "MATERIALIZED"


@dataclass(frozen=True, slots=True)
class AsIsEconomicBaselineMeasurement:
    state: AsIsEconomicBaselineState
    control_id: str
    control_git_sha: str
    phase20_plan_id: str
    phase20_plan_sha256: str
    candidate_id: str
    qualification_status: Phase20QualificationStatus
    qualification_failures: tuple[str, ...]
    account_identity_fingerprint: str
    source_manifest_sha256: str
    phase20_population_sha256: str
    compound_population_sha256: str
    decision_epoch_count: int
    candidate_row_count: int
    fold_ids: tuple[str, ...]
    policy_net_delta_usd: Decimal
    baseline_net_delta_usd: Decimal
    policy_settlement_cash_drawdown_usd: Decimal
    baseline_settlement_cash_drawdown_usd: Decimal
    policy_capital_productivity: Decimal
    baseline_capital_productivity: Decimal
    policy_acceptance_rate: Decimal
    baseline_acceptance_rate: Decimal
    policy_selected_outcome_coverage: Decimal
    baseline_selected_outcome_coverage: Decimal
    candidate_outcome_coverage: Decimal
    capital_utilization: Decimal
    capital_starvation_rate: Decimal
    mpc_reserve_efficiency: Decimal
    optionality_preserved_rate: Decimal
    concentration_utilization: Decimal
    provider_failure_incidence: Decimal
    evidence_missingness: Decimal
    compound_episode_count: int
    gross_compound_deployment_usd: Decimal
    compound_realized_net_pnl_usd: Decimal
    compound_protected_floor_graduation_usd: Decimal
    compound_capital_minutes_usd: Decimal
    compound_stop_risk_minutes_usd: Decimal
    compound_margin_minutes_usd: Decimal
    max_source_generation: int
    synthetic_values_used: bool = False
    treatment_effect_claimed: bool = False
    certification_ready: bool = False


def materialize_as_is_economic_baseline(
    *,
    report: Phase20QualificationReport,
    compound_records: tuple[ForwardCompoundEconomicRecord, ...],
) -> AsIsEconomicBaselineMeasurement:
    """Materialize the AS-IS population without retuning or counterfactual claims."""

    if not isinstance(report, Phase20QualificationReport):
        raise CiboCompoundCapitalError(
            "AS-IS baseline requires canonical Phase20 qualification report"
        )
    if report.status in {
        Phase20QualificationStatus.NOT_READY,
        Phase20QualificationStatus.INVALID,
    }:
        raise CiboCompoundCapitalError(
            "AS-IS baseline requires causally ready non-invalid population"
        )
    if not report.readiness.ready:
        raise CiboCompoundCapitalError(
            "AS-IS baseline readiness must be true"
        )
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    if (
        report.plan_id != plan.plan_id
        or report.plan_sha256 != phase20d_qualification_plan_sha256()
        or report.candidate_id != plan.candidate_id
    ):
        raise CiboCompoundCapitalError(
            "AS-IS baseline Phase20 frozen lineage drift"
        )
    fold_ids = tuple(item.fold_id for item in report.folds)
    if fold_ids != _CANONICAL_FOLDS:
        raise CiboCompoundCapitalError(
            "AS-IS baseline requires ordered WF1..WF4"
        )
    if not report.rows:
        raise CiboCompoundCapitalError(
            "AS-IS baseline Phase20 population cannot be empty"
        )
    decision_epoch_count = len(
        {item.decision_epoch_id for item in report.rows}
    )
    observed_rows = tuple(
        item for item in report.rows
        if item.realized_net_pnl_usd is not None
    )
    candidate_outcomes = len(observed_rows)
    selected_rows = tuple(item for item in report.rows if item.policy_selected)
    selected_outcomes = sum(
        1 for item in selected_rows if item.realized_net_pnl_usd is not None
    )
    decision_dates = tuple(item.decision_at.date() for item in report.rows)
    calendar_span_days = (
        (max(decision_dates) - min(decision_dates)).days + 1
        if decision_dates
        else 0
    )
    distinct_trading_days = len(set(decision_dates))
    lineage_counts: dict[str, int] = {}
    for item in observed_rows:
        lineage_counts[item.trader_id] = lineage_counts.get(item.trader_id, 0) + 1
    represented_lineages = len(lineage_counts)
    minimum_outcomes_any_lineage = (
        min(lineage_counts.values()) if lineage_counts else 0
    )
    if (
        report.readiness.pre_freeze_decisions != 0
        or report.readiness.missing_policy_decisions != 0
        or report.readiness.decision_epochs != decision_epoch_count
        or report.readiness.candidate_instances != len(report.rows)
        or report.readiness.candidate_outcomes != candidate_outcomes
        or report.readiness.selected_instances != len(selected_rows)
        or report.readiness.selected_outcomes != selected_outcomes
        or report.readiness.calendar_span_days != calendar_span_days
        or report.readiness.distinct_trading_days != distinct_trading_days
        or report.readiness.represented_lineages != represented_lineages
        or report.readiness.minimum_outcomes_any_lineage
        != minimum_outcomes_any_lineage
        or report.readiness.candidate_outcome_coverage
        != report.candidate_outcome_coverage
        or report.readiness.selected_outcome_coverage
        != report.policy_selected_outcome_coverage
    ):
        raise CiboCompoundCapitalError(
            "AS-IS baseline readiness/report consistency drift"
        )
    if (
        decision_epoch_count < plan.minimum_decision_epochs
        or report.readiness.candidate_outcomes < plan.minimum_candidate_outcomes
        or report.readiness.selected_outcomes < plan.minimum_selected_outcomes
        or report.readiness.calendar_span_days < plan.minimum_calendar_span_days
        or report.readiness.distinct_trading_days
        < plan.minimum_distinct_trading_days
        or report.readiness.represented_lineages < plan.minimum_global_lineages
        or report.readiness.minimum_outcomes_any_lineage
        < plan.minimum_outcomes_per_lineage
        or report.readiness.minimum_fold_candidate_outcomes
        < plan.minimum_fold_candidate_outcomes
        or report.readiness.minimum_fold_lineages < plan.minimum_fold_lineages
        or report.candidate_outcome_coverage
        < plan.minimum_candidate_outcome_coverage
        or report.policy_selected_outcome_coverage
        < plan.required_selected_outcome_coverage
        or report.baseline_selected_outcome_coverage
        < plan.required_baseline_selected_outcome_coverage
    ):
        raise CiboCompoundCapitalError(
            "AS-IS baseline frozen qualification thresholds not met"
        )
    if sum(item.decision_epoch_count for item in report.folds) != decision_epoch_count:
        raise CiboCompoundCapitalError(
            "AS-IS baseline temporal fold population count drift"
        )
    if (
        not isinstance(compound_records, tuple)
        or not compound_records
        or any(
            not isinstance(item, ForwardCompoundEconomicRecord)
            for item in compound_records
        )
    ):
        raise CiboCompoundCapitalError(
            "AS-IS baseline requires real forward Compound records"
        )

    manifests = {item.source_manifest_sha256 for item in compound_records}
    accounts = {item.account_identity_fingerprint for item in compound_records}
    if len(manifests) != 1 or len(accounts) != 1:
        raise CiboCompoundCapitalError(
            "AS-IS baseline Compound source/account lineage drift"
        )
    source_manifest_sha256 = next(iter(manifests))
    account_identity_fingerprint = next(iter(accounts))
    _sha(source_manifest_sha256, "source_manifest_sha256")

    rows = {
        (item.decision_epoch_id, item.signal_fingerprint): item
        for item in report.rows
    }
    if len(rows) != len(report.rows):
        raise CiboCompoundCapitalError(
            "AS-IS baseline Phase20 row identity must be unique"
        )
    for item in compound_records:
        row = rows.get((item.decision_id, item.signal_fingerprint))
        if row is None:
            raise CiboCompoundCapitalError(
                "AS-IS baseline Compound decision missing from Phase20 population"
            )
        if not row.policy_selected:
            raise CiboCompoundCapitalError(
                "AS-IS baseline Compound deployment was not policy-selected"
            )
        if row.decision_at != item.decision_at:
            raise CiboCompoundCapitalError(
                "AS-IS baseline decision timestamp lineage drift"
            )
        if row.realized_net_pnl_usd is None:
            raise CiboCompoundCapitalError(
                "AS-IS baseline Compound deployment lacks realized outcome"
            )
        if row.realized_net_pnl_usd != item.realized_pnl_usd:
            raise CiboCompoundCapitalError(
                "AS-IS baseline realized PnL lineage drift"
            )
        if item.frozen_candidate_id != report.candidate_id:
            raise CiboCompoundCapitalError(
                "AS-IS baseline candidate identity drift"
            )

    capital_minutes = Decimal(0)
    stop_risk_minutes = Decimal(0)
    margin_minutes = Decimal(0)
    for item in compound_records:
        duration = _minutes(item.settled_at - item.deployed_at)
        capital_minutes += item.deployed_capital_usd * duration
        stop_risk_minutes += item.stop_risk_usd * duration
        margin_minutes += item.margin_usd * duration

    return AsIsEconomicBaselineMeasurement(
        state=AsIsEconomicBaselineState.MATERIALIZED,
        control_id=AS_IS_CONTROL_ID,
        control_git_sha=AS_IS_CONTROL_GIT_SHA,
        phase20_plan_id=report.plan_id,
        phase20_plan_sha256=report.plan_sha256,
        candidate_id=report.candidate_id,
        qualification_status=report.status,
        qualification_failures=report.failures,
        account_identity_fingerprint=account_identity_fingerprint,
        source_manifest_sha256=source_manifest_sha256,
        phase20_population_sha256=_phase20_population_sha256(report),
        compound_population_sha256=_compound_population_sha256(compound_records),
        decision_epoch_count=decision_epoch_count,
        candidate_row_count=len(report.rows),
        fold_ids=fold_ids,
        policy_net_delta_usd=report.policy_net_delta_usd,
        baseline_net_delta_usd=report.baseline_net_delta_usd,
        policy_settlement_cash_drawdown_usd=(
            report.policy_settlement_cash_drawdown_usd
        ),
        baseline_settlement_cash_drawdown_usd=(
            report.baseline_settlement_cash_drawdown_usd
        ),
        policy_capital_productivity=report.policy_capital_productivity,
        baseline_capital_productivity=report.baseline_capital_productivity,
        policy_acceptance_rate=report.policy_acceptance_rate,
        baseline_acceptance_rate=report.baseline_acceptance_rate,
        policy_selected_outcome_coverage=report.policy_selected_outcome_coverage,
        baseline_selected_outcome_coverage=(
            report.baseline_selected_outcome_coverage
        ),
        candidate_outcome_coverage=report.candidate_outcome_coverage,
        capital_utilization=report.capital_utilization,
        capital_starvation_rate=report.capital_starvation_rate,
        mpc_reserve_efficiency=report.mpc_reserve_efficiency,
        optionality_preserved_rate=report.optionality_preserved_rate,
        concentration_utilization=report.concentration_utilization,
        provider_failure_incidence=report.provider_failure_incidence,
        evidence_missingness=report.evidence_missingness,
        compound_episode_count=len(compound_records),
        gross_compound_deployment_usd=sum(
            (item.deployed_capital_usd for item in compound_records),
            Decimal(0),
        ),
        compound_realized_net_pnl_usd=sum(
            (item.realized_pnl_usd for item in compound_records),
            Decimal(0),
        ),
        compound_protected_floor_graduation_usd=sum(
            (item.protected_floor_graduation_usd for item in compound_records),
            Decimal(0),
        ),
        compound_capital_minutes_usd=capital_minutes,
        compound_stop_risk_minutes_usd=stop_risk_minutes,
        compound_margin_minutes_usd=margin_minutes,
        max_source_generation=max(
            item.source_generation for item in compound_records
        ),
    )


def as_is_economic_baseline_sha256(
    measurement: AsIsEconomicBaselineMeasurement,
) -> str:
    if not isinstance(measurement, AsIsEconomicBaselineMeasurement):
        raise CiboCompoundCapitalError(
            "AS-IS baseline digest requires canonical measurement"
        )
    payload = {
        name: _json_value(getattr(measurement, name))
        for name in measurement.__dataclass_fields__
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _phase20_population_sha256(report: Phase20QualificationReport) -> str:
    payload = [
        {
            "decision_epoch_id": item.decision_epoch_id,
            "decision_evidence_sha256": item.decision_evidence_sha256,
            "decision_at": item.decision_at.isoformat(),
            "signal_fingerprint": item.signal_fingerprint,
            "trader_id": item.trader_id,
            "stop_risk_usd": str(item.stop_risk_usd),
            "margin_usd": str(item.margin_usd),
            "expected_capital_minutes": str(item.expected_capital_minutes),
            "provider_cost_proxy_usd": str(item.provider_cost_proxy_usd),
            "policy_selected": item.policy_selected,
            "baseline_selected": item.baseline_selected,
            "realized_net_pnl_usd": _json_value(item.realized_net_pnl_usd),
            "capital_minutes": _json_value(item.capital_minutes),
            "outcome_observed_at": _json_value(item.outcome_observed_at),
        }
        for item in report.rows
    ]
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _compound_population_sha256(
    records: tuple[ForwardCompoundEconomicRecord, ...],
) -> str:
    payload = [
        {
            "episode_id": item.episode_id,
            "deployment_id": item.deployment_id,
            "decision_id": item.decision_id,
            "signal_fingerprint": item.signal_fingerprint,
            "decision_at": item.decision_at.isoformat(),
            "deployed_at": item.deployed_at.isoformat(),
            "settled_at": item.settled_at.isoformat(),
            "source_generation": item.source_generation,
            "deployed_capital_usd": str(item.deployed_capital_usd),
            "stop_risk_usd": str(item.stop_risk_usd),
            "margin_usd": str(item.margin_usd),
            "realized_pnl_usd": str(item.realized_pnl_usd),
            "protected_floor_graduation_usd": str(
                item.protected_floor_graduation_usd
            ),
            "source_manifest_sha256": item.source_manifest_sha256,
        }
        for item in compound_records_sorted(records)
    ]
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def compound_records_sorted(
    records: tuple[ForwardCompoundEconomicRecord, ...],
) -> tuple[ForwardCompoundEconomicRecord, ...]:
    return tuple(
        sorted(
            records,
            key=lambda item: (
                item.decision_at,
                item.signal_fingerprint,
                item.episode_id,
            ),
        )
    )


def _minutes(delta) -> Decimal:
    seconds = (
        Decimal(delta.days * 86400 + delta.seconds)
        + Decimal(delta.microseconds) / Decimal(1_000_000)
    )
    return seconds / Decimal(60)


def _json_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    return value


def _sha(value: str, name: str) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise CiboCompoundCapitalError(
            f"AS-IS baseline {name} must be canonical SHA-256"
        )
