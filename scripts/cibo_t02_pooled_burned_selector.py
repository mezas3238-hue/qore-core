#!/usr/bin/env python3
"""Train-select and independently validate a pooled causal T02 rule.

Research-only. The selector uses immutable burned Phase18 data, partitions every
lineage chronologically 60/40, chooses among a small preregistered causal family
using TRAIN only, freezes that choice, then evaluates the untouched VALIDATION.

No reused-holdout outcome participates in selection. No broker, LIVE,
Production, certification, merge, or real-capital authority is created.
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

SEED = 20261003
SIMS = 10000
TRAIN_FRACTION = Decimal("0.60")
MIN_OVERALL_TRAIN_ROWS = 100
MIN_LINEAGE_ROWS = 30
MAX_P95_LOSS_R = Decimal("1.10")

SOURCES = {
    "R38_GBPJPY": "phase18-gbpjpy-r38-bound-trades.jsonl",
    "R42_AUDJPY": "phase18-audjpy-r42-bound-trades.jsonl",
    "R43_GBPUSD": "phase18-gbpusd-r43-bound-trades.jsonl",
}

Rule = tuple[
    str,
    Decimal,
    Callable[[dict[str, str | None]], bool],
]


def _dec(value: object) -> Decimal:
    parsed = Decimal(str(value))
    if not parsed.is_finite():
        raise ValueError("non-finite T02 burned value")
    return parsed


def _context(row: dict[str, Any]) -> dict[str, str | None]:
    regime = row.get("regime")
    setup = row.get("setup_context")
    if not isinstance(regime, dict) or not isinstance(setup, dict):
        return {
            "side": str(row.get("side")),
            "session": None,
            "d1_range": None,
            "h4_range": None,
            "m5_vol": None,
            "reclaim": None,
        }
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
    }


def _base(context: dict[str, str | None]) -> bool:
    return context["side"] == "long"


def _non_asia(context: dict[str, str | None]) -> bool:
    return _base(context) and context["session"] not in {None, "asia"}


def _d1_non_extreme(context: dict[str, str | None]) -> bool:
    return _base(context) and context["d1_range"] not in {None, "extreme"}


def _d1_non_extreme_non_asia(
    context: dict[str, str | None],
) -> bool:
    return _d1_non_extreme(context) and context["session"] not in {
        None,
        "asia",
    }


def _h4_non_extreme(context: dict[str, str | None]) -> bool:
    return _d1_non_extreme_non_asia(context) and context["h4_range"] not in {
        None,
        "extreme",
    }


def _reclaim_le_15(context: dict[str, str | None]) -> bool:
    return _d1_non_extreme_non_asia(context) and context["reclaim"] in {
        "<=5m",
        "6-15m",
    }


def _m5_not_expanded(context: dict[str, str | None]) -> bool:
    return _d1_non_extreme_non_asia(context) and context["m5_vol"] not in {
        None,
        "expanded",
    }


def _h4_reclaim(context: dict[str, str | None]) -> bool:
    return _h4_non_extreme(context) and context["reclaim"] in {
        "<=5m",
        "6-15m",
    }


FAMILY: tuple[Rule, ...] = (
    ("ROR_0025_LONG", Decimal("0.025"), _base),
    ("ROR_0025_NON_ASIA", Decimal("0.025"), _non_asia),
    ("ROR_0025_D1_NOT_EXTREME", Decimal("0.025"), _d1_non_extreme),
    (
        "ROR_0025_D1_NOT_EXTREME_NON_ASIA",
        Decimal("0.025"),
        _d1_non_extreme_non_asia,
    ),
    ("ROR_0050_LONG", Decimal("0.05"), _base),
    ("ROR_0050_NON_ASIA", Decimal("0.05"), _non_asia),
    ("ROR_0050_D1_NOT_EXTREME", Decimal("0.05"), _d1_non_extreme),
    (
        "ROR_0050_D1_NOT_EXTREME_NON_ASIA",
        Decimal("0.05"),
        _d1_non_extreme_non_asia,
    ),
    (
        "ROR_0050_D1_NONEXT_NONASIA_H4_NONEXT",
        Decimal("0.05"),
        _h4_non_extreme,
    ),
    (
        "ROR_0050_D1_NONEXT_NONASIA_RECLAIM_LE15",
        Decimal("0.05"),
        _reclaim_le_15,
    ),
    (
        "ROR_0050_D1_NONEXT_NONASIA_M5_NOTEXP",
        Decimal("0.05"),
        _m5_not_expanded,
    ),
    (
        "ROR_0050_D1_NONEXT_NONASIA_H4_NONEXT_RECLAIM_LE15",
        Decimal("0.05"),
        _h4_reclaim,
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
        raise ValueError("burned T02 source must contain object rows")
    return sorted(rows, key=lambda row: str(row["entry_at"]))


def _split(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    index = int(Decimal(len(rows)) * TRAIN_FRACTION)
    if index <= 0 or index >= len(rows):
        raise ValueError("invalid burned TRAIN/VALIDATION split")
    return rows[:index], rows[index:]


def _prior_ror(lineage: str) -> Decimal:
    return frozen_train_prior_for(
        TraderLineage(lineage)
    ).expected_structural_r


def _selected(
    by_lineage: dict[str, list[dict[str, Any]]],
    *,
    threshold: Decimal,
    predicate: Callable[[dict[str, str | None]], bool],
) -> tuple[
    list[tuple[str, dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
]:
    pooled: list[tuple[str, dict[str, Any]]] = []
    per: dict[str, list[dict[str, Any]]] = {}
    for lineage, rows in sorted(by_lineage.items()):
        if _prior_ror(lineage) < threshold:
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
        "n": len(rows),
        "sum_r": format(total, "f"),
        "mean_r": format(total / Decimal(len(rows)), "f"),
        "stop_rate": format(
            Decimal(stopped) / Decimal(len(rows)),
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
        for _ in range(SIMS)
    )
    return Decimal(str(totals[int(0.05 * (SIMS - 1))]))


def _report_rule(
    by_lineage: dict[str, list[dict[str, Any]]],
    rule: Rule,
) -> dict[str, Any]:
    rule_id, threshold, predicate = rule
    pooled, per = _selected(
        by_lineage,
        threshold=threshold,
        predicate=predicate,
    )
    overall = _metrics([row for _, row in pooled])
    return {
        "rule_id": rule_id,
        "minimum_frozen_train_return_on_risk": format(threshold, "f"),
        "overall": overall,
        "bootstrap_p05_total_r": format(_bootstrap_p05(pooled), "f"),
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
    for metrics in row["lineages"].values():
        if (
            int(metrics["n"]) < MIN_LINEAGE_ROWS
            or _dec(metrics["sum_r"]) <= 0
        ):
            return False
    return True


def _rank_key(row: dict[str, Any]) -> tuple[Decimal, Decimal, int, str]:
    minimum_lineage_mean = min(
        _dec(metrics["mean_r"])
        for metrics in row["lineages"].values()
    )
    return (
        minimum_lineage_mean,
        _dec(row["overall"]["mean_r"]),
        int(row["overall"]["n"]),
        str(row["rule_id"]),
    )


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
        raise RuntimeError("no pooled T02 rule qualifies on TRAIN")
    selected_train = max(eligible, key=_rank_key)
    selected_id = str(selected_train["rule_id"])
    selected_rule = next(rule for rule in FAMILY if rule[0] == selected_id)
    validation_report = _report_rule(validation, selected_rule)

    baseline_rule = (
        "ROR_0050_LONG",
        Decimal("0.05"),
        _base,
    )
    validation_baseline = _report_rule(validation, baseline_rule)

    validation_pass = (
        _dec(validation_report["overall"]["sum_r"]) > 0
        and _dec(validation_report["bootstrap_p05_total_r"]) > 0
        and _dec(validation_report["overall"]["p95_loss_r"])
        <= _dec(validation_baseline["overall"]["p95_loss_r"])
        and _dec(validation_report["overall"]["stop_rate"])
        <= _dec(validation_baseline["overall"]["stop_rate"])
        and all(
            int(metrics["n"]) >= MIN_LINEAGE_ROWS
            and _dec(metrics["sum_r"]) > 0
            for metrics in validation_report["lineages"].values()
        )
    )

    return {
        "schema": "qore.cibo.t02.pooled-burned-selector.v1",
        "mode": "BURNED_PHASE18_TRAIN_VALIDATE_RESEARCH",
        "selection_policy": (
            "TRAIN_ONLY_MAXIMIN_LINEAGE_MEAN_THEN_OVERALL_MEAN_DENSITY"
        ),
        "train_fraction": format(TRAIN_FRACTION, "f"),
        "family_ids": [rule[0] for rule in FAMILY],
        "train_results": train_reports,
        "selected_rule_id": selected_id,
        "selected_train": selected_train,
        "selected_validation": validation_report,
        "validation_baseline": validation_baseline,
        "validation_pass": validation_pass,
        "promotion_authorized": False,
        "governance": {
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
        },
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
                "selected_rule_id": report["selected_rule_id"],
                "validation_pass": report["validation_pass"],
                "selected_validation": report["selected_validation"],
            },
            sort_keys=True,
        )
    )
    return 0 if report["validation_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
