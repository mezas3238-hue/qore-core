"""Fast Trader Lab V5 tail governor for CE2I T02.

The family is frozen from burned TRAIN tail forensics only. Every rule starts
from the V4 FVG-confirmed opportunity family and removes one causal adverse
microstructure state. Selection is TRAIN-only; VALIDATION is not opened until
one rule passes 4/4 folds, bootstrap, density, lineage, stop-rate and p95 gates.

Research-only. No symbol/Trader blacklist and no execution authority.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import cibo_t02_fast_stability_lab as base

IDENTITY = "CIBO_T02_FAST_TAIL_LAB_V5"
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
        "m5_efficiency": (
            None
            if regime.get("m5_efficiency_state") is None
            else str(regime["m5_efficiency_state"])
        ),
        "wick": (
            None
            if setup.get("rejection_wick_bucket") is None
            else str(setup["rejection_wick_bucket"])
        ),
        "protected_risk": (
            None
            if setup.get("protected_risk_range_bucket") is None
            else str(setup["protected_risk_range_bucket"])
        ),
        "close_location": (
            None
            if setup.get("close_location_bucket") is None
            else str(setup["close_location_bucket"])
        ),
    }


def _fvg(context: Context) -> bool:
    return (
        context["side"] == "long"
        and context["session"] not in {None, "asia"}
        and context["fvg"] == "yes"
    )


def _low_large_wick(context: Context) -> bool:
    return (
        context["m5_efficiency"] == "low"
        and context["wick"] == "q4:>0.50"
    )


def _rule_low_large_wick(context: Context) -> bool:
    return _fvg(context) and not _low_large_wick(context)


def _rule_low_large_wick_risk(context: Context) -> bool:
    hazard = (
        _low_large_wick(context)
        and context["protected_risk"] == "q3:<=1.0"
    )
    return _fvg(context) and not hazard


def _rule_ny_low_large_wick(context: Context) -> bool:
    hazard = (
        context["session"] == "new-york"
        and _low_large_wick(context)
    )
    return _fvg(context) and not hazard


def _rule_ny_low_large_wick_risk(context: Context) -> bool:
    hazard = (
        context["session"] == "new-york"
        and _low_large_wick(context)
        and context["protected_risk"] == "q3:<=1.0"
    )
    return _fvg(context) and not hazard


def _rule_low_close_extreme(context: Context) -> bool:
    hazard = (
        context["m5_efficiency"] == "low"
        and context["close_location"] == "q4:>0.75"
    )
    return _fvg(context) and not hazard


FAMILY: tuple[Rule, ...] = (
    ("FVG_EXCLUDE_LOW_EFF_LARGE_WICK", _rule_low_large_wick),
    (
        "FVG_EXCLUDE_LOW_EFF_LARGE_WICK_RISK_Q3",
        _rule_low_large_wick_risk,
    ),
    (
        "FVG_EXCLUDE_NY_LOW_EFF_LARGE_WICK",
        _rule_ny_low_large_wick,
    ),
    (
        "FVG_EXCLUDE_NY_LOW_EFF_LARGE_WICK_RISK_Q3",
        _rule_ny_low_large_wick_risk,
    ),
    ("FVG_EXCLUDE_LOW_EFF_CLOSE_Q4", _rule_low_close_extreme),
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


def _report(
    by_lineage: dict[str, list[dict[str, Any]]],
    rule: Rule,
) -> dict[str, Any]:
    rule_id, predicate = rule
    pooled, per = _selected(by_lineage, predicate)
    folds = base._folds(pooled)
    return {
        "rule_id": rule_id,
        "overall": base._metrics([row for _, row in pooled]),
        "bootstrap_p05_total_r": format(base._bootstrap_p05(pooled), "f"),
        "chronological_folds": folds,
        "four_of_four_folds_positive": (
            len(folds) == base.FOLD_COUNT
            and all(base._dec(item["sum_r"]) > 0 for item in folds)
        ),
        "lineages": {
            lineage: base._metrics(rows) for lineage, rows in sorted(per.items())
        },
    }


def _eligible(candidate: dict[str, Any], control: dict[str, Any]) -> bool:
    c = candidate["overall"]
    b = control["overall"]
    return (
        int(c["n"]) >= base.MIN_OVERALL_TRAIN_ROWS
        and candidate["four_of_four_folds_positive"] is True
        and base._dec(candidate["bootstrap_p05_total_r"]) > 0
        and base._dec(c["p95_loss_r"]) <= base._dec(b["p95_loss_r"])
        and base._dec(c["stop_rate"]) <= base._dec(b["stop_rate"])
        and all(
            int(metrics["n"]) >= base.MIN_TRAIN_LINEAGE_ROWS
            and base._dec(metrics["sum_r"]) > 0
            for metrics in candidate["lineages"].values()
        )
    )


def _rank(candidate: dict[str, Any]) -> tuple[Decimal, Decimal, Decimal, int, str]:
    min_fold = min(
        base._dec(item["sum_r"]) for item in candidate["chronological_folds"]
    )
    min_lineage = min(
        base._dec(metrics["mean_r"])
        for metrics in candidate["lineages"].values()
    )
    return (
        min_fold,
        base._dec(candidate["bootstrap_p05_total_r"]),
        min_lineage,
        int(candidate["overall"]["n"]),
        str(candidate["rule_id"]),
    )


def _validation_pass(candidate: dict[str, Any], baseline: dict[str, Any]) -> bool:
    c = candidate["overall"]
    b = baseline["overall"]
    return (
        int(c["n"]) >= base.MIN_OVERALL_VALIDATION_ROWS
        and base._dec(c["sum_r"]) > 0
        and base._dec(candidate["bootstrap_p05_total_r"]) > 0
        and candidate["four_of_four_folds_positive"] is True
        and base._dec(c["p95_loss_r"]) <= base._dec(b["p95_loss_r"])
        and base._dec(c["stop_rate"]) <= base._dec(b["stop_rate"])
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

    control = _report(train, ("FVG_CONTROL", _fvg))
    train_results = [_report(train, rule) for rule in FAMILY]
    eligible = [row for row in train_results if _eligible(row, control)]

    result: dict[str, Any] = {
        "schema": "qore.trader-lab.cibo-t02-fast-tail.v5",
        "identity": IDENTITY,
        "mode": "BURNED_PHASE18_FAST_TAIL_RESEARCH",
        "selection_policy": (
            "TRAIN_ONLY_FVG_TAIL_GOVERNOR_4OF4_BOOTSTRAP_LINEAGE_"
            "NO_WORSE_STOP_OR_P95"
        ),
        "family_ids": [rule[0] for rule in FAMILY],
        "train_control": control,
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
    validation = _report(validation, selected_rule)
    baseline = base._report_rule(
        {lineage: parts[1] for lineage, parts in split.items()},
        ("ROR_0050_LONG", base._long),
    )
    result.update(
        selected_rule_id=selected_id,
        selected_train=selected_train,
        validation_opened=True,
        selected_validation=validation,
        validation_baseline=baseline,
        validation_pass=_validation_pass(validation, baseline),
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
