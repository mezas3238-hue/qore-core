"""Fast Trader Lab downside-governor research for CE2I T02.

Stage V3 starts from the TRAIN-selected positive/stable NON_ASIA family and asks
one narrower question: can a causal predecision governor reduce tail/stop
exposure without destroying temporal edge?

Selection is TRAIN-only. VALIDATION is opened only after one candidate passes
TRAIN density, 4/4 folds, bootstrap, lineage, and downside gates.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import cibo_t02_fast_stability_lab as base

IDENTITY = "CIBO_T02_FAST_DOWNSIDE_LAB_V3"

Context = dict[str, object]
Predicate = Callable[[Context], bool]
Rule = tuple[str, Predicate]


def _context(row: dict[str, Any]) -> Context:
    regime = row.get("regime")
    setup = row.get("setup_context")
    if not isinstance(regime, dict):
        regime = {}
    if not isinstance(setup, dict):
        setup = {}
    fragility_raw = row.get("fragility_flag_count")
    try:
        fragility = None if fragility_raw is None else int(fragility_raw)
    except (TypeError, ValueError):
        fragility = None
    return {
        "side": str(row.get("side")),
        "session": (
            None if setup.get("session") is None else str(setup["session"])
        ),
        "d1_range": (
            None
            if regime.get("d1_range_state") is None
            else str(regime["d1_range_state"])
        ),
        "h4_range": (
            None
            if regime.get("h4_range_state") is None
            else str(regime["h4_range_state"])
        ),
        "m5_vol": (
            None
            if regime.get("m5_volatility_state") is None
            else str(regime["m5_volatility_state"])
        ),
        "reclaim": (
            None
            if setup.get("reclaim_latency_bucket") is None
            else str(setup["reclaim_latency_bucket"])
        ),
        "fragility": fragility,
    }


def _non_asia(context: Context) -> bool:
    return (
        context["side"] == "long"
        and context["session"] not in {None, "asia"}
    )


def _h4_non_extreme(context: Context) -> bool:
    return (
        _non_asia(context)
        and context["h4_range"] not in {None, "extreme"}
    )


def _m5_not_expanded(context: Context) -> bool:
    return (
        _non_asia(context)
        and context["m5_vol"] not in {None, "expanded"}
    )


def _fragility_le(context: Context, maximum: int) -> bool:
    value = context["fragility"]
    return (
        _non_asia(context)
        and isinstance(value, int)
        and value <= maximum
    )


def _h4_frag1(context: Context) -> bool:
    return _h4_non_extreme(context) and _fragility_le(context, 1)


def _m5_frag1(context: Context) -> bool:
    return _m5_not_expanded(context) and _fragility_le(context, 1)


def _h4_m5(context: Context) -> bool:
    return _h4_non_extreme(context) and _m5_not_expanded(context)


def _d1_h4(context: Context) -> bool:
    return (
        _h4_non_extreme(context)
        and context["d1_range"] not in {None, "extreme"}
    )


def _reclaim5_frag1(context: Context) -> bool:
    return (
        _fragility_le(context, 1)
        and context["reclaim"] == "<=5m"
    )


def _d1_reclaim5_frag1(context: Context) -> bool:
    return (
        _reclaim5_frag1(context)
        and context["d1_range"] not in {None, "extreme"}
    )


CONTROL: Rule = ("ROR_0050_NON_ASIA", _non_asia)
FAMILY: tuple[Rule, ...] = (
    ("ROR_0050_NON_ASIA_H4_NOT_EXTREME", _h4_non_extreme),
    ("ROR_0050_NON_ASIA_M5_NOT_EXPANDED", _m5_not_expanded),
    (
        "ROR_0050_NON_ASIA_FRAGILITY_LE1",
        lambda context: _fragility_le(context, 1),
    ),
    (
        "ROR_0050_NON_ASIA_FRAGILITY_LE2",
        lambda context: _fragility_le(context, 2),
    ),
    ("ROR_0050_NON_ASIA_H4_NONEXT_FRAG_LE1", _h4_frag1),
    ("ROR_0050_NON_ASIA_M5_NOTEXP_FRAG_LE1", _m5_frag1),
    ("ROR_0050_NON_ASIA_H4_NONEXT_M5_NOTEXP", _h4_m5),
    ("ROR_0050_D1_H4_NONEXT_NON_ASIA", _d1_h4),
    ("ROR_0050_NON_ASIA_RECLAIM_LE5_FRAG_LE1", _reclaim5_frag1),
    (
        "ROR_0050_D1_NONEXT_NONASIA_RECLAIM_LE5_FRAG_LE1",
        _d1_reclaim5_frag1,
    ),
)


def _selected(
    by_lineage: dict[str, list[dict[str, Any]]],
    predicate: Predicate,
) -> tuple[
    list[tuple[str, dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
]:
    pooled: list[tuple[str, dict[str, Any]]] = []
    per: dict[str, list[dict[str, Any]]] = {}
    for lineage, rows in sorted(by_lineage.items()):
        if (
            base._prior_ror(lineage)
            < base.MINIMUM_FROZEN_TRAIN_RETURN_ON_RISK
        ):
            continue
        chosen = [row for row in rows if predicate(_context(row))]
        per[lineage] = chosen
        pooled.extend((lineage, row) for row in chosen)
    pooled.sort(key=lambda item: str(item[1]["entry_at"]))
    return pooled, per


def _report_rule(
    by_lineage: dict[str, list[dict[str, Any]]],
    rule: Rule,
) -> dict[str, Any]:
    rule_id, predicate = rule
    pooled, per = _selected(by_lineage, predicate)
    folds = base._folds(pooled)
    return {
        "rule_id": rule_id,
        "minimum_frozen_train_return_on_risk": format(
            base.MINIMUM_FROZEN_TRAIN_RETURN_ON_RISK,
            "f",
        ),
        "overall": base._metrics([row for _, row in pooled]),
        "bootstrap_p05_total_r": format(
            base._bootstrap_p05(pooled),
            "f",
        ),
        "chronological_folds": folds,
        "four_of_four_folds_positive": (
            len(folds) == base.FOLD_COUNT
            and all(base._dec(row["sum_r"]) > 0 for row in folds)
        ),
        "lineages": {
            lineage: base._metrics(rows)
            for lineage, rows in sorted(per.items())
        },
    }


def _train_eligible(
    row: dict[str, Any],
    control: dict[str, Any],
) -> bool:
    overall = row["overall"]
    control_overall = control["overall"]
    if int(overall["n"]) < base.MIN_OVERALL_TRAIN_ROWS:
        return False
    if row["four_of_four_folds_positive"] is not True:
        return False
    if base._dec(row["bootstrap_p05_total_r"]) <= 0:
        return False
    if base._dec(overall["p95_loss_r"]) > base._dec(
        control_overall["p95_loss_r"]
    ):
        return False
    if base._dec(overall["stop_rate"]) > base._dec(
        control_overall["stop_rate"]
    ):
        return False
    for metrics in row["lineages"].values():
        if (
            int(metrics["n"]) < base.MIN_TRAIN_LINEAGE_ROWS
            or base._dec(metrics["sum_r"]) <= 0
        ):
            return False
    return True


def _rank_key(
    row: dict[str, Any],
) -> tuple[Decimal, Decimal, Decimal, Decimal, int, str]:
    minimum_fold_mean = min(
        base._dec(item["mean_r"])
        for item in row["chronological_folds"]
    )
    minimum_lineage_mean = min(
        base._dec(metrics["mean_r"])
        for metrics in row["lineages"].values()
    )
    stop_rate = base._dec(row["overall"]["stop_rate"])
    return (
        minimum_fold_mean,
        -stop_rate,
        minimum_lineage_mean,
        base._dec(row["overall"]["mean_r"]),
        int(row["overall"]["n"]),
        str(row["rule_id"]),
    )


def _validation_pass(
    candidate: dict[str, Any],
    long_baseline: dict[str, Any],
) -> bool:
    overall = candidate["overall"]
    baseline = long_baseline["overall"]
    if int(overall["n"]) < base.MIN_OVERALL_VALIDATION_ROWS:
        return False
    if base._dec(overall["sum_r"]) <= 0:
        return False
    if base._dec(candidate["bootstrap_p05_total_r"]) <= 0:
        return False
    if candidate["four_of_four_folds_positive"] is not True:
        return False
    if base._dec(overall["p95_loss_r"]) > base._dec(
        baseline["p95_loss_r"]
    ):
        return False
    if base._dec(overall["stop_rate"]) > base._dec(
        baseline["stop_rate"]
    ):
        return False
    for metrics in candidate["lineages"].values():
        if (
            int(metrics["n"]) < base.MIN_VALIDATION_LINEAGE_ROWS
            or base._dec(metrics["sum_r"]) <= 0
        ):
            return False
    return True


def build_report(paths: dict[str, Path]) -> dict[str, Any]:
    all_rows = {
        lineage: base._rows(paths[lineage], base.SOURCES[lineage])
        for lineage in base.SOURCES
    }
    split = {
        lineage: base._split(rows)
        for lineage, rows in all_rows.items()
    }
    train = {lineage: parts[0] for lineage, parts in split.items()}
    validation = {lineage: parts[1] for lineage, parts in split.items()}

    train_control = _report_rule(train, CONTROL)
    train_reports = [_report_rule(train, rule) for rule in FAMILY]
    eligible = [
        row
        for row in train_reports
        if _train_eligible(row, train_control)
    ]
    if not eligible:
        return _result_without_validation(
            train_control=train_control,
            train_reports=train_reports,
        )

    selected_train = max(eligible, key=_rank_key)
    selected_id = str(selected_train["rule_id"])
    selected_rule = next(rule for rule in FAMILY if rule[0] == selected_id)
    selected_validation = _report_rule(validation, selected_rule)
    validation_long_baseline = base._report_rule(
        validation,
        ("ROR_0050_LONG", base._long),
    )
    validation_control = _report_rule(validation, CONTROL)
    passed = _validation_pass(
        selected_validation,
        validation_long_baseline,
    )
    return {
        "schema": "qore.trader-lab.cibo-t02-fast-downside.v3",
        "identity": IDENTITY,
        "mode": "BURNED_PHASE18_FAST_DOWNSIDE_RESEARCH",
        "selection_policy": (
            "TRAIN_ONLY_4OF4_BOOTSTRAP_LINEAGE_POSITIVE_AND_"
            "NO_WORSE_DOWNSIDE_THAN_NON_ASIA_CONTROL"
        ),
        "family_ids": [rule[0] for rule in FAMILY],
        "train_control": train_control,
        "train_results": train_reports,
        "selected_rule_id": selected_id,
        "selected_train": selected_train,
        "validation_opened": True,
        "selected_validation": selected_validation,
        "validation_control": validation_control,
        "validation_long_baseline": validation_long_baseline,
        "validation_pass": passed,
        "promotion_authorized": False,
        "governance": base._governance(),
    }


def _result_without_validation(
    *,
    train_control: dict[str, Any],
    train_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": "qore.trader-lab.cibo-t02-fast-downside.v3",
        "identity": IDENTITY,
        "mode": "BURNED_PHASE18_FAST_DOWNSIDE_RESEARCH",
        "selection_policy": (
            "TRAIN_ONLY_4OF4_BOOTSTRAP_LINEAGE_POSITIVE_AND_"
            "NO_WORSE_DOWNSIDE_THAN_NON_ASIA_CONTROL"
        ),
        "family_ids": [rule[0] for rule in FAMILY],
        "train_control": train_control,
        "train_results": train_reports,
        "selected_rule_id": None,
        "validation_opened": False,
        "validation_pass": False,
        "promotion_authorized": False,
        "governance": base._governance(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r38-gbpjpy", type=Path, required=True)
    parser.add_argument("--r42-audjpy", type=Path, required=True)
    parser.add_argument("--r43-gbpusd", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        {
            "R38_GBPJPY": args.r38_gbpjpy,
            "R42_AUDJPY": args.r42_audjpy,
            "R43_GBPUSD": args.r43_gbpusd,
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "selected_rule_id": report.get("selected_rule_id"),
                "validation_opened": report["validation_opened"],
                "validation_pass": report["validation_pass"],
            },
            sort_keys=True,
        )
    )
    return 0 if report["validation_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
