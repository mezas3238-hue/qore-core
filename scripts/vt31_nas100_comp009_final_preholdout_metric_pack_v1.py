"""VT31 NAS100 Comparator-009 final pre-holdout metric pack V1.

Consumed development evidence only. Fresh Holdout is never opened here.

The economic policy is frozen as:
    VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR

Metric conventions are frozen in:
    docs/research/VT31_ARCH2_FINAL_PREHOLDOUT_METRIC_CONVENTIONS_001.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from decimal import Decimal, localcontext
from pathlib import Path
from typing import cast

import vt31_nas100_breaker_mixed_weak_efficiency_adverse_exit_v1 as weak
import vt31_nas100_bullish_h1_mid_confirmation_conflict_admission_v1 as mid
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.comp009.final_preholdout_metric_pack.v1"
COMPARATOR_ID = "VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR"
SOURCE_WORKFLOW_RUN_ID = 37513693408
SOURCE_HEAD = "c6b6377f345b8a61eebd47b144378efc97849e41"

BASELINE_FRICTION_R = Decimal("0.05")
DEGRADED_FRICTION_R = Decimal("0.10")
SEVERE_FRICTIONS_R = (Decimal("0.15"), Decimal("0.20"))
ANNUALIZATION_PERIODS = Decimal(252)
SHARPE_MIN = Decimal("1.50")
SORTINO_MIN = Decimal("2.00")
PAYOFF_MIN = Decimal("1.20")
ERA_PF_MIN = Decimal("1.50")
COMBINED_PF_MIN = Decimal("1.70")
MC_POSITIVE_MIN = Decimal("0.90")
MC_P95_DD_MAX = Decimal("15")
OBSERVED_DD_MAX = Decimal("6")

FROZEN_BINDINGS = {
    "r5": {
        "sample": 34,
        "profit_factor": "4.897915350564525410057976405",
        "mean_r": "2.197817857591424783557903568",
        "max_drawdown_r": "5.00990309477810209617480854",
    },
    "r6": {
        "sample": 23,
        "profit_factor": "5.250938817386014467844845488",
        "mean_r": "2.718914734671640619052067000",
        "max_drawdown_r": "5.39444444444444444444444444",
    },
    "r8": {
        "sample": 21,
        "profit_factor": "6.951578883233516655108940627",
        "mean_r": "3.120336625473599133524780162",
        "max_drawdown_r": "5.06612612612612612612612612",
    },
    "consumed": {
        "sample": 31,
        "profit_factor": "2.499511583184046817088854793",
        "mean_r": "0.9513652139433809187776428974",
        "max_drawdown_r": "5.139752370303072658233745661",
    },
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _policy_payload() -> dict[str, object]:
    return {
        "comparator_id": COMPARATOR_ID,
        "source_workflow_run_id": SOURCE_WORKFLOW_RUN_ID,
        "source_head": SOURCE_HEAD,
        "admission_stack": [
            "A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M",
            "BREAKER_SHORT_ROTATION_COMPRESSED_EXCEPT_BULLISH_RECOVERY",
            "FVG_SHORT_COMPRESSED_FRESH_LT8M_FAST_LE5M",
            "BREAKER_SHORT_PRIOR_BEARISH_COMPRESSED_H1_BULLISH",
            "RAPID_BREAKER_CONFLICT_A",
            "RAPID_BREAKER_CONFLICT_B",
            "BULLISH_H1_BREAKER_SHORT_MID_6_10M_CONFLICT",
        ],
        "position_stack": [
            "H3_FULL_COGNITION_POST1R",
            "W5_SOFT_DOL1",
            "COGNITION_SELECTED_DOL2",
            "POST_ACCEPTANCE_PS2",
            "CAUSAL_CURRENT_OPEN_R",
            "CAUTIOUS_ADVERSE_EXIT",
            "STALE_MIXED_EXIT",
            "RESIDUAL_ADVERSE_CONTEXT_EXITS",
            "BREAKER_MIXED_WEAK_EFFICIENCY_ADVERSE_EXIT",
        ],
        "material_adverse_r": "-0.50",
        "weak_efficiency_max": "0.30",
        "baseline_friction_r": "0.05",
        "capital_engineering": False,
    }


def policy_fingerprint() -> str:
    encoded = json.dumps(
        _policy_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _candidate_rows(evidence_path: Path) -> list[dict[str, object]]:
    _, weak_rows = weak._build_candidate_rows(evidence_path)
    return [row for row in weak_rows if not mid._conflict(row)]


def _eligible_dates(evidence_path: Path) -> tuple[list[str], dict[str, object]]:
    series, account, evidence, checked, evidence_sha, provider = (
        specialist.load_market_evidence(evidence_path)
    )
    by_day: dict[object, list[object]] = defaultdict(list)
    for bar in series:
        by_day[specialist._day(getattr(bar, "opened_at"))].append(bar)
    eligible = []
    for day in sorted(by_day):
        bars = tuple(
            sorted(
                by_day[day],
                key=lambda bar: getattr(bar, "opened_at"),
            )
        )
        if specialist._admitted_day(bars):
            eligible.append(day.isoformat())
    metadata = {
        "account_fingerprint": account,
        "evidence_fingerprint": evidence,
        "evidence_software_sha": evidence_sha,
        "provider_symbol_name": provider,
        "checked_at": checked.isoformat(),
        "bar_count": len(series),
        "file_sha256": hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
    }
    return eligible, metadata


def _minimal_rows(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    return [
        {
            "signal_at": row["signal_at"],
            "local_date": row["local_date"],
            "entry_family": row.get("entry_family"),
            "side": row.get("side"),
            "exit_reason": row.get("exit_reason"),
            "r_multiple": row["r_multiple"],
            "reference_volatility_state": cast(
                dict[str, object],
                row.get("entry_context", {}),
            ).get("reference_volatility_state"),
        }
        for row in rows
    ]


def _stressed_values(
    rows: list[dict[str, object]],
    friction: Decimal,
) -> list[Decimal]:
    return [_d(row["r_multiple"]) - friction for row in rows]


def _payoff(
    rows: list[dict[str, object]],
    friction: Decimal,
) -> Decimal | None:
    values = _stressed_values(rows, friction)
    wins = [value for value in values if value > 0]
    losses = [-value for value in values if value < 0]
    if not wins or not losses:
        return None
    with localcontext() as ctx:
        ctx.prec = 34
        average_win = sum(wins, Decimal(0)) / Decimal(len(wins))
        average_loss = sum(losses, Decimal(0)) / Decimal(len(losses))
        return average_win / average_loss


def _daily_series(
    rows: list[dict[str, object]],
    eligible_dates: list[str],
) -> list[dict[str, str]]:
    eligible = set(eligible_dates)
    totals: dict[str, Decimal] = defaultdict(Decimal)
    for row in rows:
        day = str(row["local_date"])
        if day not in eligible:
            raise AssertionError(
                f"candidate trade {row['signal_at']} lies outside eligible day"
            )
        totals[day] += _d(row["r_multiple"]) - BASELINE_FRICTION_R
    return [
        {
            "local_date": day,
            "daily_r": format(totals.get(day, Decimal(0)), "f"),
        }
        for day in eligible_dates
    ]


def _risk_adjusted(
    daily: list[dict[str, str]],
) -> dict[str, object]:
    values = [_d(item["daily_r"]) for item in daily]
    n = len(values)
    if n < 2:
        return {
            "eligible_session_count": n,
            "no_trade_eligible_session_count": sum(value == 0 for value in values),
            "mean_daily_r": None,
            "sample_stddev_daily_r": None,
            "downside_deviation_daily_r": None,
            "daily_sharpe": None,
            "annualized_sharpe": None,
            "daily_sortino": None,
            "annualized_sortino": None,
            "annualization_periods": "252",
        }
    with localcontext() as ctx:
        ctx.prec = 34
        mean = sum(values, Decimal(0)) / Decimal(n)
        variance = sum(
            ((value - mean) * (value - mean) for value in values),
            Decimal(0),
        ) / Decimal(n - 1)
        stddev = variance.sqrt()
        downside_variance = sum(
            (
                min(Decimal(0), value) * min(Decimal(0), value)
                for value in values
            ),
            Decimal(0),
        ) / Decimal(n)
        downside = downside_variance.sqrt()
        root_252 = ANNUALIZATION_PERIODS.sqrt()
        daily_sharpe = None if stddev == 0 else mean / stddev
        daily_sortino = None if downside == 0 else mean / downside
        annual_sharpe = (
            None if daily_sharpe is None else daily_sharpe * root_252
        )
        annual_sortino = (
            None if daily_sortino is None else daily_sortino * root_252
        )
    return {
        "eligible_session_count": n,
        "no_trade_eligible_session_count": sum(value == 0 for value in values),
        "mean_daily_r": format(mean, "f"),
        "sample_stddev_daily_r": format(stddev, "f"),
        "downside_deviation_daily_r": format(downside, "f"),
        "daily_sharpe": (
            None if daily_sharpe is None else format(daily_sharpe, "f")
        ),
        "annualized_sharpe": (
            None if annual_sharpe is None else format(annual_sharpe, "f")
        ),
        "daily_sortino": (
            None if daily_sortino is None else format(daily_sortino, "f")
        ),
        "annualized_sortino": (
            None if annual_sortino is None else format(annual_sortino, "f")
        ),
        "annualization_periods": "252",
        "risk_free_r_per_day": "0",
        "minimum_acceptable_return_r_per_day": "0",
    }


def _year_totals(
    rows: list[dict[str, object]],
) -> dict[str, str]:
    result: dict[str, Decimal] = defaultdict(Decimal)
    for row in rows:
        year = str(row["local_date"])[:4]
        result[year] += _d(row["r_multiple"]) - BASELINE_FRICTION_R
    return {
        key: format(value, "f")
        for key, value in sorted(result.items())
    }


def _regime_report(
    rows: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get("reference_volatility_state"))].append(row)
    return {
        key: specialist._metrics(group, friction=BASELINE_FRICTION_R)
        for key, group in sorted(groups.items())
    }


def _cost_stress(
    rows: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    levels = (
        BASELINE_FRICTION_R,
        DEGRADED_FRICTION_R,
        *SEVERE_FRICTIONS_R,
    )
    return {
        format(level, "f"): specialist._metrics(rows, friction=level)
        for level in levels
    }


def _pf_pass(metrics: dict[str, object], threshold: Decimal) -> bool:
    value = metrics.get("profit_factor")
    return value is not None and _d(value) >= threshold


def _pf_gt(metrics: dict[str, object], threshold: Decimal) -> bool:
    value = metrics.get("profit_factor")
    return value is not None and _d(value) > threshold


def _binding_matches(
    partition: str,
    metrics: dict[str, object],
) -> bool:
    expected = FROZEN_BINDINGS[partition]
    return all(
        str(metrics[key]) == str(value)
        for key, value in expected.items()
    )


def partition_report(
    evidence_path: Path,
    partition: str,
) -> dict[str, object]:
    if partition not in FROZEN_BINDINGS:
        raise ValueError(f"unsupported partition: {partition}")
    rows = _candidate_rows(evidence_path)
    metrics = specialist._metrics(rows, friction=BASELINE_FRICTION_R)
    if not _binding_matches(partition, metrics):
        raise AssertionError(
            f"Comparator-009 development binding drift in {partition}: {metrics}"
        )
    eligible_dates, evidence = _eligible_dates(evidence_path)
    daily = _daily_series(rows, eligible_dates)
    risk = _risk_adjusted(daily)
    payoff = _payoff(rows, BASELINE_FRICTION_R)
    stress = _cost_stress(rows)
    mc = specialist._monte_carlo(rows)
    years = _year_totals(rows)
    halfyears = specialist._block_metrics(rows, halfyear=True)

    gates = {
        "development_binding_exact": True,
        "era_pf_at_least_1_50": _pf_pass(metrics, ERA_PF_MIN),
        "expectancy_positive": _d(metrics["mean_r"]) > 0,
        "observed_dd_at_most_6r": (
            _d(metrics["max_drawdown_r"]) <= OBSERVED_DD_MAX
        ),
        "payoff_at_least_1_20": (
            payoff is not None and payoff >= PAYOFF_MIN
        ),
        "annualized_sharpe_at_least_1_50": (
            risk["annualized_sharpe"] is not None
            and _d(risk["annualized_sharpe"]) >= SHARPE_MIN
        ),
        "annualized_sortino_at_least_2_00": (
            risk["annualized_sortino"] is not None
            and _d(risk["annualized_sortino"]) >= SORTINO_MIN
        ),
        "mc_positive_at_least_0_90": (
            _d(mc["positive_terminal_probability"]) >= MC_POSITIVE_MIN
        ),
        "mc_p95_dd_at_most_15r": (
            _d(mc["p95_max_drawdown_r"]) <= MC_P95_DD_MAX
        ),
        "degraded_0_10r_pf_gt_1": _pf_gt(
            stress["0.10"],
            Decimal(1),
        ),
        "all_calendar_year_totals_positive": (
            bool(years) and all(_d(value) > 0 for value in years.values())
        ),
    }
    return {
        "schema": SCHEMA,
        "mode": "partition",
        "partition": partition,
        "comparator_id": COMPARATOR_ID,
        "policy_fingerprint": policy_fingerprint(),
        "policy": _policy_payload(),
        "evidence": evidence,
        "candidate_rows": _minimal_rows(rows),
        "eligible_dates": eligible_dates,
        "daily_series": daily,
        "metrics": metrics,
        "payoff_ratio": None if payoff is None else format(payoff, "f"),
        "risk_adjusted": risk,
        "monte_carlo": mc,
        "cost_stress": stress,
        "year_total_r": years,
        "halfyear_stress": halfyears,
        "reference_volatility_regimes": _regime_report(_minimal_rows(rows)),
        "gates": gates,
        "partition_pack_pass": all(gates.values()),
        "governance": {
            "consumed_evidence_only": True,
            "fresh_holdout_opened": False,
            "metric_conventions_frozen_before_holdout": True,
            "equal_r_edge_only": True,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "portfolio_weighting_used": False,
            "capital_weighting_used": False,
            "candidate_certified": False,
            "live_authorized": False,
        },
    }


def aggregate_reports(
    reports: list[dict[str, object]],
) -> dict[str, object]:
    by_partition = {
        str(report["partition"]): report
        for report in reports
    }
    if set(by_partition) != set(FROZEN_BINDINGS):
        raise ValueError(
            f"expected partitions {sorted(FROZEN_BINDINGS)}, "
            f"got {sorted(by_partition)}"
        )
    fingerprints = {
        str(report["policy_fingerprint"])
        for report in reports
    }
    if fingerprints != {policy_fingerprint()}:
        raise AssertionError("policy fingerprint drift across partitions")

    rows = [
        cast(dict[str, object], row)
        for partition in ("r5", "r6", "r8", "consumed")
        for row in cast(
            list[dict[str, object]],
            by_partition[partition]["candidate_rows"],
        )
    ]
    rows.sort(key=lambda row: str(row["signal_at"]))
    signal_ids = [str(row["signal_at"]) for row in rows]
    if len(signal_ids) != len(set(signal_ids)):
        raise AssertionError("candidate signal identities overlap across folds")

    daily = [
        cast(dict[str, str], item)
        for partition in ("r5", "r6", "r8", "consumed")
        for item in cast(
            list[dict[str, str]],
            by_partition[partition]["daily_series"],
        )
    ]
    daily.sort(key=lambda item: item["local_date"])
    daily_dates = [item["local_date"] for item in daily]
    if len(daily_dates) != len(set(daily_dates)):
        raise AssertionError("eligible session dates overlap across folds")

    metrics = specialist._metrics(rows, friction=BASELINE_FRICTION_R)
    payoff = _payoff(rows, BASELINE_FRICTION_R)
    risk = _risk_adjusted(daily)
    mc = specialist._monte_carlo(rows)
    stress = _cost_stress(rows)
    years = _year_totals(rows)
    fold_pf = all(
        cast(dict[str, bool], by_partition[name]["gates"])[
            "era_pf_at_least_1_50"
        ]
        for name in FROZEN_BINDINGS
    )
    fold_dd = all(
        cast(dict[str, bool], by_partition[name]["gates"])[
            "observed_dd_at_most_6r"
        ]
        for name in FROZEN_BINDINGS
    )

    gates = {
        "all_partition_development_bindings_exact": all(
            cast(dict[str, bool], report["gates"])[
                "development_binding_exact"
            ]
            for report in reports
        ),
        "no_signal_overlap_across_folds": True,
        "no_eligible_session_overlap_across_folds": True,
        "all_fold_pf_at_least_1_50": fold_pf,
        "all_fold_observed_dd_at_most_6r": fold_dd,
        "combined_pf_at_least_1_70": _pf_pass(metrics, COMBINED_PF_MIN),
        "combined_expectancy_positive": _d(metrics["mean_r"]) > 0,
        "combined_expectancy_at_least_0_15r_direction": (
            _d(metrics["mean_r"]) >= Decimal("0.15")
        ),
        "payoff_at_least_1_20": (
            payoff is not None and payoff >= PAYOFF_MIN
        ),
        "annualized_sharpe_at_least_1_50": (
            risk["annualized_sharpe"] is not None
            and _d(risk["annualized_sharpe"]) >= SHARPE_MIN
        ),
        "annualized_sortino_at_least_2_00": (
            risk["annualized_sortino"] is not None
            and _d(risk["annualized_sortino"]) >= SORTINO_MIN
        ),
        "mc_positive_at_least_0_90": (
            _d(mc["positive_terminal_probability"]) >= MC_POSITIVE_MIN
        ),
        "mc_p95_dd_at_most_15r": (
            _d(mc["p95_max_drawdown_r"]) <= MC_P95_DD_MAX
        ),
        "degraded_0_10r_pf_gt_1": _pf_gt(
            stress["0.10"],
            Decimal(1),
        ),
        "all_calendar_year_totals_positive": (
            bool(years) and all(_d(value) > 0 for value in years.values())
        ),
    }
    partition_results = {
        name: {
            "partition_pack_pass": by_partition[name]["partition_pack_pass"],
            "metrics": by_partition[name]["metrics"],
            "payoff_ratio": by_partition[name]["payoff_ratio"],
            "risk_adjusted": by_partition[name]["risk_adjusted"],
            "monte_carlo": by_partition[name]["monte_carlo"],
            "cost_stress": by_partition[name]["cost_stress"],
            "year_total_r": by_partition[name]["year_total_r"],
        }
        for name in ("r5", "r6", "r8", "consumed")
    }
    return {
        "schema": SCHEMA,
        "mode": "aggregate",
        "comparator_id": COMPARATOR_ID,
        "source_workflow_run_id": SOURCE_WORKFLOW_RUN_ID,
        "source_head": SOURCE_HEAD,
        "policy_fingerprint": policy_fingerprint(),
        "metric_convention": {
            "basis": "eligible-NY-session-daily-R",
            "baseline_friction_r_per_trade": "0.05",
            "no_trade_eligible_session_r": "0",
            "risk_free_r_per_day": "0",
            "minimum_acceptable_return_r_per_day": "0",
            "sharpe_dispersion": "sample-stddev-N-minus-1",
            "sortino_downside_denominator": "all-eligible-sessions-N",
            "annualization": "sqrt(252)",
        },
        "partitions": partition_results,
        "combined": {
            "trade_count": len(rows),
            "metrics": metrics,
            "payoff_ratio": (
                None if payoff is None else format(payoff, "f")
            ),
            "risk_adjusted": risk,
            "monte_carlo": mc,
            "cost_stress": stress,
            "year_total_r": years,
            "reference_volatility_regimes": _regime_report(rows),
        },
        "gates": gates,
        "preholdout_metric_pack_pass": all(gates.values()),
        "remaining_nonmetric_blockers": [
            "REPLAY_RUNTIME_SEMANTIC_PARITY",
            "MAXIMUM_INTELLIGENCE_RUNTIME_ACCOUNTING",
            "CATEGORICAL_SEMANTIC_PARSER_AUDIT",
            "CAUSAL_NO_LEAKAGE_AUDIT",
            "EXACT_CODE_CONFIG_MEMORY_EVIDENCE_FREEZE",
            "FINAL_CANDIDATE_CONTRACT_FREEZE",
        ],
        "governance": {
            "consumed_evidence_only": True,
            "fresh_holdout_opened": False,
            "further_discretionary_optimization_authorized": False,
            "metric_retuning_after_holdout_authorized": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "portfolio_weighting_used": False,
            "capital_weighting_used": False,
            "candidate_frozen": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    one = sub.add_parser("partition")
    one.add_argument("evidence", type=Path)
    one.add_argument(
        "--partition",
        required=True,
        choices=tuple(FROZEN_BINDINGS),
    )
    one.add_argument("--output", required=True, type=Path)

    agg = sub.add_parser("aggregate")
    for name in ("r5", "r6", "r8", "consumed"):
        agg.add_argument(
            f"--{name}",
            required=True,
            type=Path,
        )
    agg.add_argument("--output", required=True, type=Path)

    args = parser.parse_args()
    if args.command == "partition":
        payload = partition_report(args.evidence, args.partition)
    else:
        paths = [args.r5, args.r6, args.r8, args.consumed]
        reports = [
            cast(
                dict[str, object],
                json.loads(path.read_text(encoding="utf-8")),
            )
            for path in paths
        ]
        payload = aggregate_reports(reports)
    _write(args.output, payload)
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
