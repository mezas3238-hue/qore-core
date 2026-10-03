"""Fast Trader Lab for CE2I T02 structural-leverage stability research.

Research-only. This laboratory is deliberately separate from the canonical T02
runtime policy. It consumes immutable burned Phase18 corpora, performs all rule
selection on chronological TRAIN only, requires positive TRAIN stability across
four folds, freezes one rule, and then opens VALIDATION exactly once.

No reused-holdout outcome participates in selection. No Trader/symbol blacklist,
broker mutation, LIVE, Production, certification, real-capital, Risk, sizing
policy, or merge authority is created.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import zipfile
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    frozen_train_prior_for,
)

IDENTITY = "CIBO_T02_FAST_STABILITY_LAB_V2"
SEED = 20261003
SIMULATIONS = 10000
TRAIN_FRACTION = Decimal("0.60")
FOLD_COUNT = 4
MIN_OVERALL_TRAIN_ROWS = 100
MIN_TRAIN_LINEAGE_ROWS = 30
MIN_OVERALL_VALIDATION_ROWS = 60
MIN_VALIDATION_LINEAGE_ROWS = 20
MAX_P95_LOSS_R = Decimal("1.10")
MINIMUM_FROZEN_TRAIN_RETURN_ON_RISK = Decimal("0.05")

SOURCES = {
    "R38_GBPJPY": "phase18-gbpjpy-r38-bound-trades.jsonl",
    "R42_AUDJPY": "phase18-audjpy-r42-bound-trades.jsonl",
    "R43_GBPUSD": "phase18-gbpusd-r43-bound-trades.jsonl",
}

Context = dict[str, str | None]
Predicate = Callable[[Context], bool]
Rule = tuple[str, Predicate]


def _dec(value: object) -> Decimal:
    parsed = Decimal(str(value))
    if not parsed.is_finite():
        raise ValueError("T02 fast lab requires finite Decimal values")
    return parsed


def _context(row: dict[str, Any]) -> Context:
    regime = row.get("regime")
    setup = row.get("setup_context")
    if not isinstance(regime, dict):
        regime = {}
    if not isinstance(setup, dict):
        setup = {}
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
        "reclaim": (
            None
            if setup.get("reclaim_latency_bucket") is None
            else str(setup["reclaim_latency_bucket"])
        ),
    }


def _long(context: Context) -> bool:
    return context["side"] == "long"


def _non_asia(context: Context) -> bool:
    return _long(context) and context["session"] not in {None, "asia"}


def _d1_non_extreme(context: Context) -> bool:
    return _long(context) and context["d1_range"] not in {None, "extreme"}


def _d1_non_extreme_non_asia(context: Context) -> bool:
    return _d1_non_extreme(context) and context["session"] not in {
        None,
        "asia",
    }


def _non_asia_reclaim_le_5(context: Context) -> bool:
    return _non_asia(context) and context["reclaim"] == "<=5m"


def _d1_non_extreme_non_asia_reclaim_le_5(context: Context) -> bool:
    return (
        _d1_non_extreme_non_asia(context)
        and context["reclaim"] == "<=5m"
    )


FAMILY: tuple[Rule, ...] = (
    ("ROR_0050_LONG", _long),
    ("ROR_0050_NON_ASIA", _non_asia),
    ("ROR_0050_D1_NOT_EXTREME", _d1_non_extreme),
    (
        "ROR_0050_D1_NOT_EXTREME_NON_ASIA",
        _d1_non_extreme_non_asia,
    ),
    (
        "ROR_0050_NON_ASIA_RECLAIM_LE_5M",
        _non_asia_reclaim_le_5,
    ),
    (
        "ROR_0050_D1_NOT_EXTREME_NON_ASIA_RECLAIM_LE_5M",
        _d1_non_extreme_non_asia_reclaim_le_5,
    ),
)


def _rows(path: Path, member: str) -> list[dict[str, Any]]:
    with zipfile.ZipFile(path) as archive:
        rows = [
            json.loads(line)
            for line in archive.read(member).decode().splitlines()
            if line.strip()
        ]
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise ValueError("T02 fast-lab source must contain object rows")
    return sorted(rows, key=lambda row: str(row["entry_at"]))


def _split(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    index = int(Decimal(len(rows)) * TRAIN_FRACTION)
    if index <= 0 or index >= len(rows):
        raise ValueError("T02 fast-lab TRAIN/VALIDATION split invalid")
    return rows[:index], rows[index:]


def _prior_ror(lineage: str) -> Decimal:
    return frozen_train_prior_for(
        TraderLineage(lineage)
    ).expected_structural_r


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
        if _prior_ror(lineage) < MINIMUM_FROZEN_TRAIN_RETURN_ON_RISK:
            continue
        chosen = [row for row in rows if predicate(_context(row))]
        per[lineage] = chosen
        pooled.extend((lineage, row) for row in chosen)
    pooled.sort(key=lambda item: str(item[1]["entry_at"]))
    return pooled, per


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = [_dec(row["raw_net_010_r"]) for row in rows]
    if not values:
        return {
            "n": 0,
            "sum_r": "0",
            "mean_r": None,
            "stop_rate": None,
            "p95_loss_r": None,
        }
    stopped = sum(
        1
        for row in rows
        if "stop" in str(row.get("exit_reason", "")).lower()
    )
    losses = sorted(abs(value) for value in values if value < 0)
    p95 = Decimal(0)
    if losses:
        rank = max(1, math.ceil(0.95 * len(losses)))
        p95 = losses[rank - 1]
    total = sum(values, Decimal(0))
    return {
        "n": len(values),
        "sum_r": format(total, "f"),
        "mean_r": format(total / Decimal(len(values)), "f"),
        "stop_rate": format(
            Decimal(stopped) / Decimal(len(values)),
            "f",
        ),
        "p95_loss_r": format(p95, "f"),
    }


def _bootstrap_p05(
    pooled: list[tuple[str, dict[str, Any]]],
) -> Decimal:
    values = [float(_dec(row["raw_net_010_r"])) for _, row in pooled]
    if not values:
        return Decimal(0)
    rng = random.Random(SEED)
    totals = sorted(
        sum(rng.choice(values) for _ in values)
        for _ in range(SIMULATIONS)
    )
    return Decimal(str(totals[int(0.05 * (SIMULATIONS - 1))]))


def _folds(
    pooled: list[tuple[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    if len(pooled) < FOLD_COUNT:
        return []
    rows: list[dict[str, Any]] = []
    for index in range(FOLD_COUNT):
        start = index * len(pooled) // FOLD_COUNT
        end = (index + 1) * len(pooled) // FOLD_COUNT
        values = [
            _dec(row["raw_net_010_r"])
            for _, row in pooled[start:end]
        ]
        if not values:
            return []
        total = sum(values, Decimal(0))
        rows.append(
            {
                "fold": index + 1,
                "n": len(values),
                "sum_r": format(total, "f"),
                "mean_r": format(total / Decimal(len(values)), "f"),
            }
        )
    return rows


def _report_rule(
    by_lineage: dict[str, list[dict[str, Any]]],
    rule: Rule,
) -> dict[str, Any]:
    rule_id, predicate = rule
    pooled, per = _selected(by_lineage, predicate)
    folds = _folds(pooled)
    return {
        "rule_id": rule_id,
        "minimum_frozen_train_return_on_risk": format(
            MINIMUM_FROZEN_TRAIN_RETURN_ON_RISK,
            "f",
        ),
        "overall": _metrics([row for _, row in pooled]),
        "bootstrap_p05_total_r": format(_bootstrap_p05(pooled), "f"),
        "chronological_folds": folds,
        "four_of_four_folds_positive": (
            len(folds) == FOLD_COUNT
            and all(_dec(row["sum_r"]) > 0 for row in folds)
        ),
        "lineages": {
            lineage: _metrics(rows)
            for lineage, rows in sorted(per.items())
        },
    }


def _train_eligible(row: dict[str, Any]) -> bool:
    overall = row["overall"]
    if int(overall["n"]) < MIN_OVERALL_TRAIN_ROWS:
        return False
    if _dec(overall["p95_loss_r"]) > MAX_P95_LOSS_R:
        return False
    if _dec(row["bootstrap_p05_total_r"]) <= 0:
        return False
    if row["four_of_four_folds_positive"] is not True:
        return False
    for metrics in row["lineages"].values():
        if (
            int(metrics["n"]) < MIN_TRAIN_LINEAGE_ROWS
            or _dec(metrics["sum_r"]) <= 0
        ):
            return False
    return True


def _rank_key(
    row: dict[str, Any],
) -> tuple[Decimal, Decimal, Decimal, int, str]:
    minimum_fold_mean = min(
        _dec(item["mean_r"]) for item in row["chronological_folds"]
    )
    minimum_lineage_mean = min(
        _dec(metrics["mean_r"])
        for metrics in row["lineages"].values()
    )
    return (
        minimum_fold_mean,
        minimum_lineage_mean,
        _dec(row["overall"]["mean_r"]),
        int(row["overall"]["n"]),
        str(row["rule_id"]),
    )


def _validation_pass(
    candidate: dict[str, Any],
    baseline: dict[str, Any],
) -> bool:
    overall = candidate["overall"]
    if int(overall["n"]) < MIN_OVERALL_VALIDATION_ROWS:
        return False
    if _dec(overall["sum_r"]) <= 0:
        return False
    if _dec(candidate["bootstrap_p05_total_r"]) <= 0:
        return False
    if candidate["four_of_four_folds_positive"] is not True:
        return False
    if _dec(overall["p95_loss_r"]) > _dec(
        baseline["overall"]["p95_loss_r"]
    ):
        return False
    if _dec(overall["stop_rate"]) > _dec(
        baseline["overall"]["stop_rate"]
    ):
        return False
    for metrics in candidate["lineages"].values():
        if (
            int(metrics["n"]) < MIN_VALIDATION_LINEAGE_ROWS
            or _dec(metrics["sum_r"]) <= 0
        ):
            return False
    return True


def build_report(paths: dict[str, Path]) -> dict[str, Any]:
    all_rows = {
        lineage: _rows(paths[lineage], SOURCES[lineage])
        for lineage in SOURCES
    }
    split = {
        lineage: _split(rows)
        for lineage, rows in all_rows.items()
    }
    train = {lineage: parts[0] for lineage, parts in split.items()}
    validation = {lineage: parts[1] for lineage, parts in split.items()}

    train_reports = [_report_rule(train, rule) for rule in FAMILY]
    eligible = [row for row in train_reports if _train_eligible(row)]
    if not eligible:
        return {
            "schema": "qore.trader-lab.cibo-t02-fast-stability.v2",
            "identity": IDENTITY,
            "mode": "BURNED_PHASE18_FAST_STABILITY_RESEARCH",
            "selection_policy": (
                "TRAIN_ONLY_REQUIRE_4OF4_POSITIVE_FOLDS_THEN_"
                "MAXIMIN_FOLD_MEAN_LINEAGE_MEAN_OVERALL_MEAN_DENSITY"
            ),
            "family_ids": [rule[0] for rule in FAMILY],
            "train_results": train_reports,
            "selected_rule_id": None,
            "validation_opened": False,
            "validation_pass": False,
            "promotion_authorized": False,
            "governance": _governance(),
        }

    selected_train = max(eligible, key=_rank_key)
    selected_id = str(selected_train["rule_id"])
    selected_rule = next(rule for rule in FAMILY if rule[0] == selected_id)
    selected_validation = _report_rule(validation, selected_rule)
    validation_baseline = _report_rule(
        validation,
        ("ROR_0050_LONG", _long),
    )
    passed = _validation_pass(
        selected_validation,
        validation_baseline,
    )
    return {
        "schema": "qore.trader-lab.cibo-t02-fast-stability.v2",
        "identity": IDENTITY,
        "mode": "BURNED_PHASE18_FAST_STABILITY_RESEARCH",
        "selection_policy": (
            "TRAIN_ONLY_REQUIRE_4OF4_POSITIVE_FOLDS_THEN_"
            "MAXIMIN_FOLD_MEAN_LINEAGE_MEAN_OVERALL_MEAN_DENSITY"
        ),
        "train_fraction": format(TRAIN_FRACTION, "f"),
        "fold_count": FOLD_COUNT,
        "family_ids": [rule[0] for rule in FAMILY],
        "train_results": train_reports,
        "selected_rule_id": selected_id,
        "selected_train": selected_train,
        "validation_opened": True,
        "selected_validation": selected_validation,
        "validation_baseline": validation_baseline,
        "validation_pass": passed,
        "promotion_authorized": False,
        "governance": _governance(),
    }


def _governance() -> dict[str, bool]:
    return {
        "selection_used_validation_outcomes": False,
        "selection_used_reused_holdout_outcomes": False,
        "symbol_or_trader_blacklist": False,
        "fresh_oos_claimed": False,
        "certification_claimed": False,
        "broker_mutation": False,
        "live": False,
        "production": False,
        "real_capital": False,
        "merge_authority": False,
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
