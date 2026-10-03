"""Fast integrated Trader Lab for CE2I T02 opportunity admission.

This laboratory works on the exact T02-enabled P0 surface. It derives a
one-provider-step incremental label from already-settled research executions,
while every candidate rule consumes only predecision fields. Selection uses the
first chronological 60% only; the final 40% stays sealed until one rule passes
TRAIN gates.

Research-only. No Fresh OOS, certification, LIVE, Production, broker mutation,
real capital, Risk authority, sizing-policy authority, or merge authority.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

IDENTITY = "CIBO_T02_INTEGRATED_FAST_LAB_V1"
SEED = 20261003
SIMULATIONS = 10000
TRAIN_FRACTION = Decimal("0.60")
FOLD_COUNT = 4
MIN_TRAIN_ROWS = 8
MIN_VALIDATION_ROWS = 6

Row = dict[str, Any]
Predicate = Callable[[Row], bool]
Rule = tuple[str, Predicate]


def _dec(value: object) -> Decimal:
    parsed = Decimal(str(value))
    if not parsed.is_finite():
        raise ValueError("T02 integrated fast lab requires finite Decimal")
    return parsed


def _context(row: Row) -> dict[str, str]:
    opportunity = row["trader_opportunity"]
    return {
        str(key): str(value)
        for key, value in opportunity.get("decision_context", [])
    }


def _research_row(row: Row) -> Row:
    cma = row["cma"]
    risk = row["qore_risk"]
    settlement = row["settlement"]
    opportunity = row["trader_opportunity"]
    expectation = row["expectation"]
    if not all(
        isinstance(item, dict)
        for item in (cma, risk, settlement, opportunity, expectation)
    ):
        raise ValueError("T02 integrated lab row missing economic record")

    baseline_risk = _dec(cma["pre_ce2i_stop_risk_usd"])
    authorized_risk = _dec(risk["authorized_stop_risk_usd"])
    if baseline_risk <= 0 or authorized_risk <= 0:
        raise ValueError("T02 integrated lab risk must be positive")

    incremental_risk = (
        _dec(opportunity["volume_step"])
        * _dec(opportunity["stop_loss_per_volume"])
    )
    if incremental_risk <= 0:
        raise ValueError("T02 integrated lab incremental risk must be positive")

    realized = _dec(settlement["realized_net_pnl_usd"])
    incremental_pnl = realized * incremental_risk / authorized_risk
    expected_net = _dec(expectation["expected_net_value_usd"])
    return {
        "market_decision_at": str(row["market_decision_at"]),
        "signal_fingerprint": str(row["signal_fingerprint"]),
        "side": str(opportunity["side"]),
        "entry_type": str(opportunity["entry_type"]),
        "expected_return_on_risk": expected_net / baseline_risk,
        "expected_capital_minutes": _dec(
            expectation["expected_capital_minutes"]
        ),
        "incremental_risk_usd": incremental_risk,
        "incremental_pnl_usd": incremental_pnl,
        "incremental_r": incremental_pnl / incremental_risk,
        "context": _context(row),
    }


def _surface(trace: dict[str, Any]) -> list[Row]:
    opportunities = trace.get("opportunities")
    if not isinstance(opportunities, list):
        raise ValueError("decision trace opportunities must be list")
    selected: list[Row] = []
    for raw in opportunities:
        if not isinstance(raw, dict):
            raise ValueError("decision trace opportunity must be object")
        enabled = raw.get("ce2i", {}).get("enabled_tools", [])
        if "T02" not in enabled:
            continue
        if not isinstance(raw.get("settlement"), dict):
            continue
        selected.append(_research_row(raw))
    selected.sort(
        key=lambda row: (
            row["market_decision_at"],
            row["signal_fingerprint"],
        )
    )
    if len(selected) < 20:
        raise ValueError("T02 integrated lab requires material enabled surface")
    return selected


def _ror05_long(row: Row) -> bool:
    return (
        row["side"] == "long"
        and row["expected_return_on_risk"] >= Decimal("0.05")
    )


def _ror05_long_minutes(row: Row, maximum: Decimal) -> bool:
    return (
        _ror05_long(row)
        and row["expected_capital_minutes"] <= maximum
    )


FAMILY: tuple[Rule, ...] = (
    ("ROR05_LONG", _ror05_long),
    (
        "ROR05_LONG_MINUTES_LE45",
        lambda row: _ror05_long_minutes(row, Decimal("45")),
    ),
    (
        "ROR05_LONG_MINUTES_LE60",
        lambda row: _ror05_long_minutes(row, Decimal("60")),
    ),
    (
        "ROR05_LONG_MINUTES_LE75",
        lambda row: _ror05_long_minutes(row, Decimal("75")),
    ),
    (
        "ROR05_LONG_MINUTES_LE90",
        lambda row: _ror05_long_minutes(row, Decimal("90")),
    ),
)


def _metrics(rows: list[Row]) -> dict[str, Any]:
    if not rows:
        return {
            "n": 0,
            "sum_incremental_pnl_usd": "0",
            "mean_incremental_pnl_usd": None,
            "negative_rate": None,
            "p95_loss_usd": None,
        }
    values = [row["incremental_pnl_usd"] for row in rows]
    losses = sorted(abs(value) for value in values if value < 0)
    p95 = Decimal(0)
    if losses:
        rank = max(1, math.ceil(Decimal("0.95") * len(losses)))
        p95 = losses[rank - 1]
    total = sum(values, Decimal(0))
    negatives = sum(value < 0 for value in values)
    return {
        "n": len(values),
        "sum_incremental_pnl_usd": format(total, "f"),
        "mean_incremental_pnl_usd": format(
            total / Decimal(len(values)),
            "f",
        ),
        "negative_rate": format(
            Decimal(negatives) / Decimal(len(values)),
            "f",
        ),
        "p95_loss_usd": format(p95, "f"),
    }


def _folds(rows: list[Row]) -> list[dict[str, Any]]:
    rows = sorted(
        rows,
        key=lambda row: (
            row["market_decision_at"],
            row["signal_fingerprint"],
        ),
    )
    if len(rows) < FOLD_COUNT:
        return []
    result: list[dict[str, Any]] = []
    for index in range(FOLD_COUNT):
        start = index * len(rows) // FOLD_COUNT
        end = (index + 1) * len(rows) // FOLD_COUNT
        fold = rows[start:end]
        total = sum(
            (row["incremental_pnl_usd"] for row in fold),
            Decimal(0),
        )
        result.append(
            {
                "fold": index + 1,
                "n": len(fold),
                "incremental_pnl_usd": format(total, "f"),
            }
        )
    return result


def _bootstrap_p05(rows: list[Row]) -> Decimal:
    values = [float(row["incremental_pnl_usd"]) for row in rows]
    if not values:
        return Decimal(0)
    rng = random.Random(SEED)
    totals = sorted(
        sum(rng.choice(values) for _ in values)
        for _ in range(SIMULATIONS)
    )
    return Decimal(str(totals[int(Decimal("0.05") * (SIMULATIONS - 1))]))


def _report(rows: list[Row], rule: Rule) -> dict[str, Any]:
    rule_id, predicate = rule
    chosen = [row for row in rows if predicate(row)]
    folds = _folds(chosen)
    return {
        "rule_id": rule_id,
        "metrics": _metrics(chosen),
        "bootstrap_p05_incremental_pnl_usd": format(
            _bootstrap_p05(chosen),
            "f",
        ),
        "chronological_folds": folds,
        "four_of_four_folds_positive": (
            len(folds) == FOLD_COUNT
            and all(
                _dec(item["incremental_pnl_usd"]) > 0
                for item in folds
            )
        ),
    }


def _train_eligible(row: dict[str, Any]) -> bool:
    return (
        int(row["metrics"]["n"]) >= MIN_TRAIN_ROWS
        and _dec(row["metrics"]["sum_incremental_pnl_usd"]) > 0
        and _dec(row["bootstrap_p05_incremental_pnl_usd"]) > 0
        and row["four_of_four_folds_positive"] is True
    )


def _rank(
    row: dict[str, Any],
) -> tuple[Decimal, Decimal, int, str]:
    minimum_fold = min(
        _dec(item["incremental_pnl_usd"])
        for item in row["chronological_folds"]
    )
    return (
        minimum_fold,
        _dec(row["bootstrap_p05_incremental_pnl_usd"]),
        int(row["metrics"]["n"]),
        str(row["rule_id"]),
    )


def _validation_pass(
    candidate: dict[str, Any],
    baseline: dict[str, Any],
) -> bool:
    c = candidate["metrics"]
    b = baseline["metrics"]
    return (
        int(c["n"]) >= MIN_VALIDATION_ROWS
        and _dec(c["sum_incremental_pnl_usd"]) > 0
        and _dec(candidate["bootstrap_p05_incremental_pnl_usd"]) > 0
        and candidate["four_of_four_folds_positive"] is True
        and _dec(c["negative_rate"]) <= _dec(b["negative_rate"])
        and _dec(c["p95_loss_usd"]) <= _dec(b["p95_loss_usd"])
    )


def build_report(trace: dict[str, Any]) -> dict[str, Any]:
    surface = _surface(trace)
    split = int(Decimal(len(surface)) * TRAIN_FRACTION)
    train = surface[:split]
    validation = surface[split:]
    train_results = [_report(train, rule) for rule in FAMILY]
    eligible = [row for row in train_results if _train_eligible(row)]

    result: dict[str, Any] = {
        "schema": "qore.trader-lab.cibo-t02-integrated-fast.v1",
        "identity": IDENTITY,
        "mode": "NON_CERTIFYING_REUSED_HOLDOUT_INTEGRATED_FAST_RESEARCH",
        "source_trace_sha256": trace.get("trace_sha256"),
        "t02_enabled_surface_count": len(surface),
        "train_count": len(train),
        "validation_count": len(validation),
        "family_ids": [rule[0] for rule in FAMILY],
        "train_results": train_results,
        "promotion_authorized": False,
        "governance": {
            "selection_used_validation_outcomes": False,
            "candidate_inputs_predecision_only": True,
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
    selected_validation = _report(validation, selected_rule)
    validation_baseline = _report(validation, ("ROR05_LONG", _ror05_long))
    result.update(
        selected_rule_id=selected_id,
        selected_train=selected_train,
        validation_opened=True,
        selected_validation=selected_validation,
        validation_baseline=validation_baseline,
        validation_pass=_validation_pass(
            selected_validation,
            validation_baseline,
        ),
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision-trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    trace = json.loads(args.decision_trace.read_text(encoding="utf-8"))
    if not isinstance(trace, dict):
        raise ValueError("decision trace root must be object")
    report = build_report(trace)
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
