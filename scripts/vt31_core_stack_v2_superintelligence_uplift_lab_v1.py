"""VT31 x Shared Core V2 causal-memory uplift lab.

Research-only temporal benchmark against the exact certified
VT31_NAS100_STRUCTURAL_TARGET_V1 economics.

The lab does not rewrite VT31 setup/entry/stop/target. It simulates an
authority-free Shared Core suitability opinion and a specialist-side shadow
ABSTAIN counterfactual. Only outcomes from episodes already CLOSED before the
current signal may enter memory.

Project-level evidence is consumed (not fresh). Inside this new experiment the
final three years are a no-retune temporal evaluation interval.
"""
# ruff: noqa: E402, I001
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

os.environ["QORE_DD6_FRONTIER_ONLY"] = "1"
os.environ["QORE_EVAL_START_DATE"] = "2017-07-01"
os.environ["QORE_EVAL_END_EXCLUSIVE_DATE"] = "2022-07-01"
os.environ["QORE_INCLUDE_TRADE_ROWS"] = "1"

import vt31_nas100_capacity_selective_target_ladder_v1 as frontier
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_r5_alloc_g_regime_root_cause_forensics_v1 as regime
import vt31_nas100_residual_regime_forensics_v2 as residual
import vt31_nas100_structural_target_candidate_5y_validation_v1 as fivey
import vt31_nas100_structural_target_candidate_v1 as candidate

SCHEMA = "qore.core_stack_v2.vt31_superintelligence_uplift_lab.v1"
BASELINE_ID = "VT31_NAS100_STRUCTURAL_TARGET_V1"
SHARED_CORE_ID = "QORE_CORE_STACK_V2_CAUSAL_ANALOG_MEMORY_V1"

START = date(2017, 7, 1)
CALIBRATION_START = date(2018, 7, 1)
EVALUATION_START = date(2019, 7, 1)
END = date(2022, 7, 1)

BASE_FEATURES = (
    "tier",
    "entry_family",
    "side",
    "reference_volatility_state",
)
CONTEXT_FEATURES = BASE_FEATURES + (
    "prior_day_state",
    "premarket_state",
    "cash_open_state",
)
PATH_FEATURES = CONTEXT_FEATURES + (
    "last_structure_event_family",
    "current_path_bucket",
    "confirmation_latency_bucket",
)
FULL_FEATURES = PATH_FEATURES + (
    "risk_ref_bucket",
    "reclaim_age_bucket",
    "authorization_reason",
)

INTERACTIONS = (
    ("tier", "entry_family"),
    ("tier", "side"),
    ("entry_family", "side"),
    ("entry_family", "reference_volatility_state"),
    ("entry_family", "cash_open_state"),
    ("entry_family", "current_path_bucket"),
    ("tier", "entry_family", "reference_volatility_state"),
    ("tier", "entry_family", "cash_open_state"),
    ("tier", "entry_family", "current_path_bucket"),
    ("tier", "entry_family", "confirmation_latency_bucket"),
)


@dataclass(frozen=True, slots=True)
class Policy:
    feature_profile: str
    shrinkage: int
    threshold_r: Decimal
    minimum_evidence_groups: int

    @property
    def features(self) -> tuple[str, ...]:
        if self.feature_profile == "BASE":
            return BASE_FEATURES
        if self.feature_profile == "CONTEXT":
            return CONTEXT_FEATURES
        if self.feature_profile == "PATH":
            return PATH_FEATURES
        if self.feature_profile == "FULL":
            return FULL_FEATURES
        raise ValueError("unknown feature profile")

    def payload(self) -> dict[str, object]:
        return {
            "feature_profile": self.feature_profile,
            "features": self.features,
            "shrinkage": self.shrinkage,
            "threshold_r": format(self.threshold_r, "f"),
            "minimum_evidence_groups": self.minimum_evidence_groups,
        }


POLICIES = tuple(
    Policy(profile, shrinkage, threshold, min_groups)
    for profile in ("BASE", "CONTEXT", "PATH", "FULL")
    for shrinkage in (8, 16, 32)
    for threshold in (
        Decimal("-0.02"),
        Decimal("0"),
        Decimal("0.02"),
        Decimal("0.04"),
    )
    for min_groups in (3, 5)
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _dt(value: object) -> datetime:
    raw = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _local_date(row: dict[str, object]) -> date:
    return date.fromisoformat(cast(str, row["local_date"]))


def _decorate(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        regime._decorate(dict(row))
        for row in sorted(rows, key=lambda item: cast(str, item["signal_at"]))
    ]


def _metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    return residual._metrics(
        sorted(rows, key=lambda item: cast(str, item["signal_at"]))
    )


def _closed_history(
    rows: list[dict[str, object]],
    *,
    signal_at: datetime,
) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for row in rows:
        exit_at = row.get("exit_at")
        if exit_at is None:
            continue
        if _dt(exit_at) < signal_at:
            result.append(row)
    return result


def _group_mean(
    history: list[dict[str, object]],
    current: dict[str, object],
    fields: tuple[str, ...],
    *,
    global_mean: Decimal,
    shrinkage: int,
) -> tuple[Decimal, int] | None:
    values = tuple(str(current.get(field)) for field in fields)
    selected = [
        row
        for row in history
        if tuple(str(row.get(field)) for field in fields) == values
    ]
    if len(selected) < 3:
        return None
    total = sum(
        (_d(row["capital_weighted_net_r"]) for row in selected),
        Decimal(0),
    )
    n = Decimal(len(selected))
    alpha = Decimal(shrinkage)
    posterior = (total + alpha * global_mean) / (n + alpha)
    return posterior, len(selected)


def _score(
    history: list[dict[str, object]],
    current: dict[str, object],
    policy: Policy,
) -> tuple[Decimal | None, int, int]:
    if len(history) < 40:
        return None, 0, len(history)

    global_total = sum(
        (_d(row["capital_weighted_net_r"]) for row in history),
        Decimal(0),
    )
    global_mean = global_total / Decimal(len(history))

    estimates: list[tuple[Decimal, Decimal]] = []
    for field in policy.features:
        item = _group_mean(
            history,
            current,
            (field,),
            global_mean=global_mean,
            shrinkage=policy.shrinkage,
        )
        if item is not None:
            estimate, sample = item
            estimates.append((estimate, Decimal(sample).sqrt()))

    for fields in INTERACTIONS:
        if any(field not in policy.features for field in fields):
            continue
        item = _group_mean(
            history,
            current,
            fields,
            global_mean=global_mean,
            shrinkage=policy.shrinkage,
        )
        if item is not None:
            estimate, sample = item
            estimates.append(
                (estimate, Decimal(sample).sqrt() * Decimal("1.5"))
            )

    if len(estimates) < policy.minimum_evidence_groups:
        return None, len(estimates), len(history)

    weight = sum((item[1] for item in estimates), Decimal(0))
    score = sum(
        (estimate * item_weight for estimate, item_weight in estimates),
        Decimal(0),
    ) / weight
    return score, len(estimates), len(history)


def _apply(
    all_rows: list[dict[str, object]],
    selected_rows: list[dict[str, object]],
    *,
    policy: Policy,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    kept: list[dict[str, object]] = []
    abstained: list[dict[str, object]] = []
    scored = 0
    score_total = Decimal(0)
    group_total = 0

    for row in selected_rows:
        signal_at = _dt(row["signal_at"])
        history = _closed_history(all_rows, signal_at=signal_at)
        score, groups, _history_n = _score(history, row, policy)
        updated = dict(row)
        if score is None:
            updated["shared_core_action"] = "PASS_BASELINE"
            updated["shared_core_score_r"] = None
            updated["shared_core_evidence_groups"] = groups
            kept.append(updated)
            continue

        scored += 1
        score_total += score
        group_total += groups
        updated["shared_core_score_r"] = format(score, "f")
        updated["shared_core_evidence_groups"] = groups

        if score < policy.threshold_r:
            updated["shared_core_action"] = "ABSTAIN_SHADOW"
            abstained.append(updated)
        else:
            updated["shared_core_action"] = "PASS_BASELINE"
            kept.append(updated)

    losses_avoided = sum(
        1 for row in abstained if _d(row["capital_weighted_net_r"]) < 0
    )
    winners_sacrificed = sum(
        1 for row in abstained if _d(row["capital_weighted_net_r"]) > 0
    )
    flats_abstained = len(abstained) - losses_avoided - winners_sacrificed

    return kept, {
        "input_trades": len(selected_rows),
        "kept_trades": len(kept),
        "abstained_trades": len(abstained),
        "density_retained": (
            format(Decimal(len(kept)) / Decimal(len(selected_rows)), "f")
            if selected_rows
            else "0"
        ),
        "scored_trades": scored,
        "mean_score_r": (
            format(score_total / Decimal(scored), "f") if scored else None
        ),
        "mean_evidence_groups": (
            format(Decimal(group_total) / Decimal(scored), "f")
            if scored
            else None
        ),
        "losses_avoided": losses_avoided,
        "winners_sacrificed": winners_sacrificed,
        "flats_abstained": flats_abstained,
    }


def _period(
    rows: list[dict[str, object]],
    start: date,
    end: date,
) -> list[dict[str, object]]:
    return [row for row in rows if start <= _local_date(row) < end]


def _candidate_score(
    baseline_metrics: dict[str, object],
    candidate_metrics: dict[str, object],
    diag: dict[str, object],
) -> Decimal | None:
    density = _d(diag["density_retained"])
    abstained = int(diag["abstained_trades"])
    input_trades = int(diag["input_trades"])
    if input_trades <= 0:
        return None
    abstain_share = Decimal(abstained) / Decimal(input_trades)
    if density < Decimal("0.70") or density > Decimal("0.90"):
        return None
    if abstain_share < Decimal("0.10"):
        return None

    baseline_total = _d(baseline_metrics["total_r"])
    candidate_total = _d(candidate_metrics["total_r"])
    if baseline_total > 0 and candidate_total < baseline_total * Decimal("0.95"):
        return None

    baseline_pf_raw = baseline_metrics["profit_factor"]
    candidate_pf_raw = candidate_metrics["profit_factor"]
    if baseline_pf_raw is None or candidate_pf_raw is None:
        return None
    baseline_pf = _d(baseline_pf_raw)
    candidate_pf = _d(candidate_pf_raw)
    if candidate_pf < baseline_pf * Decimal("1.03"):
        return None

    baseline_dd = max(_d(baseline_metrics["max_drawdown_r"]), Decimal("0.000001"))
    candidate_dd = max(_d(candidate_metrics["max_drawdown_r"]), Decimal("0.000001"))
    if candidate_dd > baseline_dd:
        return None
    if int(candidate_metrics["max_losing_streak"]) > int(
        baseline_metrics["max_losing_streak"]
    ):
        return None

    return (
        (candidate_pf / baseline_pf)
        * (candidate_total / max(baseline_total, Decimal("0.000001")))
        * (baseline_dd / candidate_dd)
    )


def _annual(
    rows: list[dict[str, object]],
    *,
    start_year: int,
    end_year: int,
) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    for year in range(start_year, end_year):
        selected = _period(rows, date(year, 7, 1), date(year + 1, 7, 1))
        blocks.append(
            {
                "start": date(year, 7, 1).isoformat(),
                "end_exclusive": date(year + 1, 7, 1).isoformat(),
                "trade_count": len(selected),
                "metrics": _metrics(selected),
            }
        )
    return blocks


def run(*, r8: Path, r6: Path, r5: Path) -> dict[str, object]:
    (
        series,
        account,
        evidence_fingerprint,
        checked_at,
        software_sha,
        provider,
        records,
    ) = fivey._stitch((r8, r6, r5))

    def stitched_loader(
        _path: Path,
    ) -> tuple[
        tuple[object, ...],
        str,
        str,
        datetime,
        str,
        str,
    ]:
        return (
            series,
            account,
            evidence_fingerprint,
            checked_at,
            software_sha,
            provider,
        )

    original_residual_loader = residual.load_market_evidence
    original_frontier_loader = frontier.load_market_evidence
    residual.load_market_evidence = stitched_loader
    frontier.load_market_evidence = stitched_loader
    try:
        evaluation = candidate.evaluate(
            Path("STITCHED_IMMUTABLE_5Y_EVIDENCE"),
            partition="core_v2_uplift_lab",
            include_rows=True,
        )
    finally:
        residual.load_market_evidence = original_residual_loader
        frontier.load_market_evidence = original_frontier_loader

    if evaluation["contract_fingerprint"] != candidate.contract_fingerprint():
        raise AssertionError("VT31 certified candidate fingerprint drift")

    raw_rows = cast(list[dict[str, object]], evaluation["trade_rows"])
    rows = _decorate(_period(raw_rows, START, END))
    calibration = _period(rows, CALIBRATION_START, EVALUATION_START)
    evaluation_rows = _period(rows, EVALUATION_START, END)

    baseline_cal_metrics = _metrics(calibration)
    frontier_results: list[dict[str, object]] = []
    best: tuple[Decimal, Policy] | None = None

    for policy in POLICIES:
        kept, diag = _apply(rows, calibration, policy=policy)
        metrics = _metrics(kept)
        score = _candidate_score(baseline_cal_metrics, metrics, diag)
        frontier_results.append(
            {
                "policy": policy.payload(),
                "metrics": metrics,
                "diagnostics": diag,
                "selection_score": None if score is None else format(score, "f"),
            }
        )
        if score is not None and (best is None or score > best[0]):
            best = (score, policy)

    if best is None:
        frozen_policy = Policy("BASE", 16, Decimal("-999"), 3)
        selection_status = "NO_CALIBRATION_SURVIVOR_BASELINE_FALLBACK"
    else:
        frozen_policy = best[1]
        selection_status = "CALIBRATION_SURVIVOR_FROZEN_FOR_TEMPORAL_EVALUATION"

    baseline_eval_metrics = _metrics(evaluation_rows)
    candidate_eval_rows, eval_diag = _apply(
        rows,
        evaluation_rows,
        policy=frozen_policy,
    )
    candidate_eval_metrics = _metrics(candidate_eval_rows)

    baseline_mc = engine._monte_carlo(
        evaluation_rows,
        variant="CORE_V2_COMMON_RANDOM_EVAL",
    )
    candidate_mc = engine._monte_carlo(
        candidate_eval_rows,
        variant="CORE_V2_COMMON_RANDOM_EVAL",
    )

    baseline_pf = _d(cast(object, baseline_eval_metrics["profit_factor"]))
    candidate_pf = _d(cast(object, candidate_eval_metrics["profit_factor"]))
    baseline_dd = _d(baseline_eval_metrics["max_drawdown_r"])
    candidate_dd = _d(candidate_eval_metrics["max_drawdown_r"])
    baseline_total = _d(baseline_eval_metrics["total_r"])
    candidate_total = _d(candidate_eval_metrics["total_r"])
    baseline_mean = _d(baseline_eval_metrics["mean_r"])
    candidate_mean = _d(candidate_eval_metrics["mean_r"])

    def pct_delta(new: Decimal, old: Decimal) -> str | None:
        if old == 0:
            return None
        return format((new / old - Decimal(1)) * Decimal(100), "f")

    eval_annual_baseline = _annual(
        evaluation_rows,
        start_year=2019,
        end_year=2022,
    )
    eval_annual_candidate = _annual(
        candidate_eval_rows,
        start_year=2019,
        end_year=2022,
    )

    comparison = {
        "pf_delta_pct": pct_delta(candidate_pf, baseline_pf),
        "total_r_delta_pct": pct_delta(candidate_total, baseline_total),
        "mean_r_delta_pct": pct_delta(candidate_mean, baseline_mean),
        "dd_reduction_pct": (
            format(
                (Decimal(1) - candidate_dd / baseline_dd) * Decimal(100),
                "f",
            )
            if baseline_dd > 0
            else None
        ),
        "max_losing_streak_delta": (
            int(candidate_eval_metrics["max_losing_streak"])
            - int(baseline_eval_metrics["max_losing_streak"])
        ),
        "mc_p95_dd_reduction_pct": (
            format(
                (
                    Decimal(1)
                    - _d(candidate_mc["p95_max_drawdown_r"])
                    / _d(baseline_mc["p95_max_drawdown_r"])
                )
                * Decimal(100),
                "f",
            )
            if _d(baseline_mc["p95_max_drawdown_r"]) > 0
            else None
        ),
    }

    significant_gates = {
        "density_retained_ge_70pct": (
            _d(eval_diag["density_retained"]) >= Decimal("0.70")
        ),
        "pf_improvement_ge_15pct": (
            candidate_pf >= baseline_pf * Decimal("1.15")
        ),
        "dd_reduction_ge_20pct": (
            baseline_dd > 0
            and candidate_dd <= baseline_dd * Decimal("0.80")
        ),
        "total_r_at_least_95pct_of_baseline": (
            candidate_total >= baseline_total * Decimal("0.95")
        ),
        "losing_streak_not_worse": (
            int(candidate_eval_metrics["max_losing_streak"])
            <= int(baseline_eval_metrics["max_losing_streak"])
        ),
        "mc_p95_dd_not_worse": (
            _d(candidate_mc["p95_max_drawdown_r"])
            <= _d(baseline_mc["p95_max_drawdown_r"])
        ),
        "all_three_eval_years_positive": all(
            _d(cast(dict[str, object], block["metrics"])["total_r"]) > 0
            for block in eval_annual_candidate
        ),
    }

    return {
        "schema": SCHEMA,
        "baseline_id": BASELINE_ID,
        "shared_core_id": SHARED_CORE_ID,
        "contract_fingerprint": candidate.contract_fingerprint(),
        "evidence_status": {
            "project_level": "CONSUMED_EXTENDED_VALIDATION",
            "experiment_design": "TEMPORAL_TRAIN_CALIBRATION_EVALUATION",
            "memory_initialization": [START.isoformat(), CALIBRATION_START.isoformat()],
            "calibration": [
                CALIBRATION_START.isoformat(),
                EVALUATION_START.isoformat(),
            ],
            "no_retune_evaluation": [
                EVALUATION_START.isoformat(),
                END.isoformat(),
            ],
            "fresh_claimed": False,
            "source_records": records,
            "evidence_fingerprint": evidence_fingerprint,
        },
        "selection": {
            "status": selection_status,
            "policy": frozen_policy.payload(),
            "frontier_size": len(frontier_results),
            "frontier": frontier_results,
        },
        "certified_5y_baseline": {
            "trade_count": len(rows),
            "metrics": _metrics(rows),
        },
        "temporal_evaluation": {
            "baseline": {
                "trade_count": len(evaluation_rows),
                "metrics": baseline_eval_metrics,
                "monte_carlo": baseline_mc,
                "annual_blocks": eval_annual_baseline,
            },
            "shared_core_shadow": {
                "trade_count": len(candidate_eval_rows),
                "metrics": candidate_eval_metrics,
                "monte_carlo": candidate_mc,
                "annual_blocks": eval_annual_candidate,
                "diagnostics": eval_diag,
            },
            "comparison": comparison,
            "significant_difference_gates": significant_gates,
            "significant_difference": all(significant_gates.values()),
        },
        "governance": {
            "shared_core_order_authority": False,
            "shared_core_risk_authority": False,
            "vt31_methodology_mutated": False,
            "vt31_setup_mutated": False,
            "vt31_entry_mutated": False,
            "vt31_stop_mutated": False,
            "vt31_target_mutated": False,
            "shadow_abstain_counterfactual_only": True,
            "current_episode_future_outcome_used": False,
            "only_closed_prior_episodes_enter_memory": True,
            "calendar_identity_used_as_edge_feature": False,
            "fold_identity_used_as_edge_feature": False,
            "cross_market_intelligence_included": False,
            "cross_market_reason": (
                "this immutable certified 5Y package is NAS100-only; "
                "global synchronized market evidence is a separate expansion"
            ),
            "vt08_forex_touched": False,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8", required=True, type=Path)
    parser.add_argument("--r6", required=True, type=Path)
    parser.add_argument("--r5", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = run(r8=args.r8, r6=args.r6, r5=args.r5)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    evaluation = cast(dict[str, object], payload["temporal_evaluation"])
    print(
        json.dumps(
            {
                "selection": payload["selection"],
                "temporal_evaluation": evaluation,
                "governance": payload["governance"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
