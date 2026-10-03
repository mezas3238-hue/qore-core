"""Fast Trader Lab V4 for CE2I T02 FVG-confirmed structural leverage.

This is research-only. The hypothesis family was formulated from burned TRAIN
only after diagnosing temporal instability. Selection remains TRAIN-only and
VALIDATION stays sealed until one candidate passes all TRAIN gates.

No reused-holdout outcome is used for selection. No Trader/symbol blacklist,
broker mutation, LIVE, Production, real-capital, certification, Risk, sizing
policy, or merge authority is created.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import cibo_t02_fast_stability_lab as base

IDENTITY = "CIBO_T02_FAST_FVG_LAB_V4"

Context = dict[str, str | None]
Predicate = Callable[[Context], bool]
Rule = tuple[str, Predicate]


def _context(row: dict[str, Any]) -> Context:
    regime = row.get("regime")
    setup = row.get("setup_context")
    if not isinstance(regime, dict):
        regime = {}
    if not isinstance(setup, dict):
        setup = {}
    return {
        "side": str(row.get("side")),
        "session": None if setup.get("session") is None else str(setup["session"]),
        "fvg": None if setup.get("fvg_before_entry") is None else str(setup["fvg_before_entry"]),
        "d1_range": None if regime.get("d1_range_state") is None else str(regime["d1_range_state"]),
        "h4_range": None if regime.get("h4_range_state") is None else str(regime["h4_range_state"]),
        "m5_vol": None if regime.get("m5_volatility_state") is None else str(regime["m5_volatility_state"]),
        "reclaim": None if setup.get("reclaim_latency_bucket") is None else str(setup["reclaim_latency_bucket"]),
    }


def _base_fvg(context: Context) -> bool:
    return (
        context["side"] == "long"
        and context["session"] not in {None, "asia"}
        and context["fvg"] == "yes"
    )


def _fvg_d1(context: Context) -> bool:
    return _base_fvg(context) and context["d1_range"] not in {None, "extreme"}


def _fvg_h4(context: Context) -> bool:
    return _base_fvg(context) and context["h4_range"] not in {None, "extreme"}


def _fvg_m5(context: Context) -> bool:
    return _base_fvg(context) and context["m5_vol"] not in {None, "expanded"}


def _fvg_reclaim15(context: Context) -> bool:
    return _base_fvg(context) and context["reclaim"] in {"<=5m", "6-15m"}


def _fvg_d1_m5(context: Context) -> bool:
    return _fvg_d1(context) and context["m5_vol"] not in {None, "expanded"}


FAMILY: tuple[Rule, ...] = (
    ("ROR_0050_NON_ASIA_FVG_YES", _base_fvg),
    ("ROR_0050_NON_ASIA_FVG_YES_D1_NOT_EXTREME", _fvg_d1),
    ("ROR_0050_NON_ASIA_FVG_YES_H4_NOT_EXTREME", _fvg_h4),
    ("ROR_0050_NON_ASIA_FVG_YES_M5_NOT_EXPANDED", _fvg_m5),
    ("ROR_0050_NON_ASIA_FVG_YES_RECLAIM_LE15", _fvg_reclaim15),
    ("ROR_0050_NON_ASIA_FVG_YES_D1_NONEXT_M5_NOTEXP", _fvg_d1_m5),
)


def _selected(
    by_lineage: dict[str, list[dict[str, Any]]],
    predicate: Predicate,
) -> tuple[list[tuple[str, dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    pooled: list[tuple[str, dict[str, Any]]] = []
    per: dict[str, list[dict[str, Any]]] = {}
    for lineage, rows in sorted(by_lineage.items()):
        if base._prior_ror(lineage) < base.MINIMUM_FROZEN_TRAIN_RETURN_ON_RISK:
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
            base.MINIMUM_FROZEN_TRAIN_RETURN_ON_RISK, "f"
        ),
        "overall": base._metrics([row for _, row in pooled]),
        "bootstrap_p05_total_r": format(base._bootstrap_p05(pooled), "f"),
        "chronological_folds": folds,
        "four_of_four_folds_positive": (
            len(folds) == base.FOLD_COUNT
            and all(base._dec(row["sum_r"]) > 0 for row in folds)
        ),
        "lineages": {
            lineage: base._metrics(rows) for lineage, rows in sorted(per.items())
        },
    }


def _eligible(row: dict[str, Any], control: dict[str, Any]) -> bool:
    overall = row["overall"]
    control_overall = control["overall"]
    if int(overall["n"]) < base.MIN_OVERALL_TRAIN_ROWS:
        return False
    if row["four_of_four_folds_positive"] is not True:
        return False
    if base._dec(row["bootstrap_p05_total_r"]) <= 0:
        return False
    if base._dec(overall["p95_loss_r"]) > base._dec(control_overall["p95_loss_r"]):
        return False
    if base._dec(overall["stop_rate"]) > base._dec(control_overall["stop_rate"]):
        return False
    return all(
        int(metrics["n"]) >= base.MIN_TRAIN_LINEAGE_ROWS
        and base._dec(metrics["sum_r"]) > 0
        for metrics in row["lineages"].values()
    )


def _rank(row: dict[str, Any]) -> tuple[Decimal, Decimal, Decimal, int, str]:
    min_fold = min(base._dec(item["sum_r"]) for item in row["chronological_folds"])
    min_lineage = min(
        base._dec(metrics["mean_r"]) for metrics in row["lineages"].values()
    )
    return (
        min_fold,
        base._dec(row["bootstrap_p05_total_r"]),
        min_lineage,
        int(row["overall"]["n"]),
        str(row["rule_id"]),
    )


def _validation_pass(candidate: dict[str, Any], baseline: dict[str, Any]) -> bool:
    overall = candidate["overall"]
    baseline_overall = baseline["overall"]
    return (
        int(overall["n"]) >= base.MIN_OVERALL_VALIDATION_ROWS
        and base._dec(overall["sum_r"]) > 0
        and base._dec(candidate["bootstrap_p05_total_r"]) > 0
        and candidate["four_of_four_folds_positive"] is True
        and base._dec(overall["p95_loss_r"]) <= base._dec(baseline_overall["p95_loss_r"])
        and base._dec(overall["stop_rate"]) <= base._dec(baseline_overall["stop_rate"])
        and all(
            int(metrics["n"]) >= base.MIN_VALIDATION_LINEAGE_ROWS
            and base._dec(metrics["sum_r"]) > 0
            for metrics in candidate["lineages"].values()
        )
    )


def build_report(paths: dict[str, Path]) -> dict[str, Any]:
    all_rows = {
        lineage: base._rows(paths[lineage], base.SOURCES[lineage])
        for lineage in base.SOURCES
    }
    split = {lineage: base._split(rows) for lineage, rows in all_rows.items()}
    train = {lineage: parts[0] for lineage, parts in split.items()}
    validation = {lineage: parts[1] for lineage, parts in split.items()}

    train_control = base._report_rule(
        train, ("ROR_0050_NON_ASIA", base._non_asia)
    )
    train_results = [_report_rule(train, rule) for rule in FAMILY]
    eligible = [row for row in train_results if _eligible(row, train_control)]
    result: dict[str, Any] = {
        "schema": "qore.trader-lab.cibo-t02-fast-fvg.v4",
        "identity": IDENTITY,
        "mode": "BURNED_PHASE18_FAST_FVG_RESEARCH",
        "selection_policy": (
            "TRAIN_ONLY_FVG_FAMILY_REQUIRE_4OF4_BOOTSTRAP_LINEAGE_"
            "AND_NO_WORSE_DOWNSIDE"
        ),
        "family_ids": [rule[0] for rule in FAMILY],
        "train_control": train_control,
        "train_results": train_results,
        "promotion_authorized": False,
        "governance": base._governance(),
    }
    if not eligible:
        result.update(
            selected_rule_id=None,
            validation_opened=False,
            validation_pass=False,
        )
        return result

    selected_train = max(eligible, key=_rank)
    selected_id = str(selected_train["rule_id"])
    selected_rule = next(rule for rule in FAMILY if rule[0] == selected_id)
    selected_validation = _report_rule(validation, selected_rule)
    validation_baseline = base._report_rule(
        validation, ("ROR_0050_LONG", base._long)
    )
    result.update(
        selected_rule_id=selected_id,
        selected_train=selected_train,
        validation_opened=True,
        selected_validation=selected_validation,
        validation_baseline=validation_baseline,
        validation_pass=_validation_pass(
            selected_validation, validation_baseline
        ),
    )
    return result


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
