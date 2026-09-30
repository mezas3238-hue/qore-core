"""Causal loss-memory resolution falsification for Capitalizer 2Y.

Consumes the frozen failure-fingerprint audit and the unchanged 1R control ledger.
It compares several deterministic memory semantics using only outcomes that were
already CLOSED before each later candidate arrived.

The variants are diagnostics, not runtime policies:
- PERSISTENT_ANY_PRIOR_LOSS: any prior closed loss with same fingerprint remains unresolved.
- LAST_SAME_FINGERPRINT_LOSS: a later non-loss with the same fingerprint resolves memory.
- LATEST_SAME_SYMBOL_STATE_LOSS: memory survives only while the latest closed state
  for that symbol is the same fingerprint and is a loss.
- SAME_DAY_ANY_PRIOR_LOSS: failure memory resets at the operating-day boundary.

Both structural and contextual fingerprint families are measured independently.
No variant is promoted by this consumed-window study.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_evidence_binding_audit_2y_v1 as binding_v1,
)
from qore.infrastructure.trader_lab.capitalizer_cognitive_failure_fingerprint_audit_2y_v1 import (
    IDENTITY as FINGERPRINT_IDENTITY,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_LOSS_MEMORY_RESOLUTION_ATLAS_2Y_V1"
SOURCE_FINGERPRINT_RUN_ID = 36066153534
SOURCE_FINGERPRINT_SHA = "e6bf614578b52bde0928268c43a2b57bdd547139"
SOURCE_TARGET_RUN_ID = 36055792484
SOURCE_TARGET_SHA = "a66ab11c22efbefb61756db3f0062c3c51a2a825"

SEMANTICS = (
    "PERSISTENT_ANY_PRIOR_LOSS",
    "LAST_SAME_FINGERPRINT_LOSS",
    "LATEST_SAME_SYMBOL_STATE_LOSS",
    "SAME_DAY_ANY_PRIOR_LOSS",
)
FINGERPRINT_FAMILIES = ("STRUCTURAL", "CONTEXTUAL")


@dataclass(frozen=True, slots=True)
class MemoryVariantResult:
    fingerprint_family: str
    semantics: str
    blocked_trades: int
    blocked_losses: int
    blocked_stops: int
    blocked_wins: int
    kept_trades: int
    kept_metrics: dict[str, Any]
    blocked_metrics: dict[str, Any]
    stop_capture_rate: str
    winner_sacrifice_rate: str
    density_retention: str


def _aware(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def _load_fingerprints(root: Path) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    report_paths = sorted(
        root.rglob("capitalizer-cognitive-failure-fingerprint-audit-2y-v1.json")
    )
    row_paths = sorted(
        root.rglob("capitalizer-cognitive-failure-fingerprint-audit-2y-v1-rows.jsonl")
    )
    if len(report_paths) != 1 or len(row_paths) != 1:
        raise ValueError("resolution atlas requires one fingerprint artifact")
    report = json.loads(report_paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != FINGERPRINT_IDENTITY:
        raise ValueError("unexpected fingerprint audit identity")
    if report.get("current_outcome_used_to_build_fingerprint") is not False:
        raise ValueError("resolution atlas requires outcome-free fingerprints")
    rows: list[dict[str, Any]] = []
    with row_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("fingerprint row must be object")
                rows.append(raw)
    if len(rows) != int(report.get("control_trades", -1)):
        raise ValueError("fingerprint artifact population mismatch")
    return report, tuple(rows)


def _join_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["symbol"]), str(row["entry_at"])


def _metrics(rows: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    values = tuple(Decimal(str(row["realized_gross_r"])) for row in rows)
    gp = sum((value for value in values if value > 0), Decimal("0"))
    gl = -sum((value for value in values if value < 0), Decimal("0"))
    equity = Decimal("0")
    peak = Decimal("0")
    max_dd = Decimal("0")
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "trades": len(rows),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "stops": sum(str(row["exit_reason"]) == "STOP" for row in rows),
        "total_r": str(sum(values, Decimal("0"))),
        "profit_factor": None if gl == 0 else str(gp / gl),
        "max_drawdown_r": str(max_dd),
        "max_losing_streak": max_streak,
    }


def _fingerprint(row: dict[str, Any], family: str) -> str:
    key = (
        "structural_fingerprint"
        if family == "STRUCTURAL"
        else "contextual_fingerprint"
    )
    value = row.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError("missing fingerprint")
    return value


def _is_loss(row: dict[str, Any]) -> bool:
    return Decimal(str(row["realized_gross_r"])) < 0


def _blocked(
    *,
    current: dict[str, Any],
    prior_closed: tuple[dict[str, Any], ...],
    fp_by_key: dict[tuple[str, str], dict[str, Any]],
    family: str,
    semantics: str,
) -> bool:
    current_fp = _fingerprint(fp_by_key[_join_key(current)], family)
    same_fp = tuple(
        row
        for row in prior_closed
        if _fingerprint(fp_by_key[_join_key(row)], family) == current_fp
    )

    if semantics == "PERSISTENT_ANY_PRIOR_LOSS":
        return any(_is_loss(row) for row in same_fp)

    if semantics == "LAST_SAME_FINGERPRINT_LOSS":
        if not same_fp:
            return False
        latest = max(same_fp, key=lambda row: _aware(row["exit_at"]))
        return _is_loss(latest)

    if semantics == "LATEST_SAME_SYMBOL_STATE_LOSS":
        same_symbol = tuple(
            row for row in prior_closed if str(row["symbol"]) == str(current["symbol"])
        )
        if not same_symbol:
            return False
        latest = max(same_symbol, key=lambda row: _aware(row["exit_at"]))
        latest_fp = _fingerprint(fp_by_key[_join_key(latest)], family)
        return latest_fp == current_fp and _is_loss(latest)

    if semantics == "SAME_DAY_ANY_PRIOR_LOSS":
        return any(
            _is_loss(row)
            and str(row["operating_date"]) == str(current["operating_date"])
            for row in same_fp
        )

    raise ValueError(f"unknown semantics: {semantics}")


def _variant(
    *,
    control: tuple[dict[str, Any], ...],
    fp_by_key: dict[tuple[str, str], dict[str, Any]],
    family: str,
    semantics: str,
) -> MemoryVariantResult:
    blocked_rows: list[dict[str, Any]] = []
    kept_rows: list[dict[str, Any]] = []

    for current in control:
        entry_at = _aware(current["entry_at"])
        prior_closed = tuple(
            row
            for row in control
            if _aware(row["entry_at"]) < entry_at
            and _aware(row["exit_at"]) <= entry_at
        )
        if _blocked(
            current=current,
            prior_closed=prior_closed,
            fp_by_key=fp_by_key,
            family=family,
            semantics=semantics,
        ):
            blocked_rows.append(current)
        else:
            kept_rows.append(current)

    blocked = tuple(blocked_rows)
    kept = tuple(kept_rows)
    total_stops = sum(str(row["exit_reason"]) == "STOP" for row in control)
    total_wins = sum(Decimal(str(row["realized_gross_r"])) > 0 for row in control)
    blocked_stops = sum(str(row["exit_reason"]) == "STOP" for row in blocked)
    blocked_wins = sum(Decimal(str(row["realized_gross_r"])) > 0 for row in blocked)
    return MemoryVariantResult(
        fingerprint_family=family,
        semantics=semantics,
        blocked_trades=len(blocked),
        blocked_losses=sum(_is_loss(row) for row in blocked),
        blocked_stops=blocked_stops,
        blocked_wins=blocked_wins,
        kept_trades=len(kept),
        kept_metrics=_metrics(kept),
        blocked_metrics=_metrics(blocked),
        stop_capture_rate=(
            "0" if total_stops == 0 else str(Decimal(blocked_stops) / Decimal(total_stops))
        ),
        winner_sacrifice_rate=(
            "0" if total_wins == 0 else str(Decimal(blocked_wins) / Decimal(total_wins))
        ),
        density_retention=str(Decimal(len(kept)) / Decimal(len(control))),
    )


def build_report(
    fingerprint_root: Path,
    target_root: Path,
) -> dict[str, Any]:
    fingerprint_report, fp_rows = _load_fingerprints(fingerprint_root)
    control = binding_v1._load_control(target_root)
    if len(control) != len(fp_rows):
        raise ValueError("resolution atlas population mismatch")

    fp_by_key = {_join_key(row): row for row in fp_rows}
    if len(fp_by_key) != len(fp_rows):
        raise ValueError("fingerprint join identity not unique")
    if {_join_key(row) for row in control} != set(fp_by_key):
        raise ValueError("control/fingerprint identities differ")

    variants = tuple(
        _variant(
            control=control,
            fp_by_key=fp_by_key,
            family=family,
            semantics=semantics,
        )
        for family in FINGERPRINT_FAMILIES
        for semantics in SEMANTICS
    )

    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for variant in variants:
        by_family[variant.fingerprint_family].append(
            {
                "semantics": variant.semantics,
                "blocked_trades": variant.blocked_trades,
                "blocked_losses": variant.blocked_losses,
                "blocked_stops": variant.blocked_stops,
                "blocked_wins": variant.blocked_wins,
                "kept_trades": variant.kept_trades,
                "kept_metrics": variant.kept_metrics,
                "blocked_metrics": variant.blocked_metrics,
                "stop_capture_rate": variant.stop_capture_rate,
                "winner_sacrifice_rate": variant.winner_sacrifice_rate,
                "density_retention": variant.density_retention,
            }
        )

    return {
        "identity": IDENTITY,
        "source_fingerprint_run_id": SOURCE_FINGERPRINT_RUN_ID,
        "source_fingerprint_sha": SOURCE_FINGERPRINT_SHA,
        "source_target_run_id": SOURCE_TARGET_RUN_ID,
        "source_target_sha": SOURCE_TARGET_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "control_trades": len(control),
        "control_metrics": _metrics(control),
        "fingerprint_control_reproduced": len(control)
        == int(fingerprint_report["control_trades"]),
        "semantics": SEMANTICS,
        "fingerprint_families": FINGERPRINT_FAMILIES,
        "variants": {
            family: sorted(rows, key=lambda row: str(row["semantics"]))
            for family, rows in sorted(by_family.items())
        },
        "prior_closed_outcomes_only": True,
        "current_trade_outcome_visible_to_memory_decision": False,
        "current_trade_outcome_used_for_post_audit_metrics": True,
        "numeric_market_thresholds_added": False,
        "semantic_variant_selected": False,
        "runtime_enforcement_allowed": False,
        "strategy_rules_changed": False,
        "cognitive_rules_changed": False,
        "entry_changed": False,
        "stop_changed": False,
        "target_changed": False,
        "max3_changed": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": "COMPARE_MEMORY_INFORMATION_VALUE_WITH_OTHER_COGNITIVE_BLOCKERS",
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output / "capitalizer-cognitive-loss-memory-resolution-atlas-2y-v1.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fingerprint_root", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_report(args.fingerprint_root, args.target_root)
    write_report(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
