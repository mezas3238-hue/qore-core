"""Consumed-evidence counterfactual lab for one frozen structural abstention hypothesis."""
from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_causal_regime_forensics as causal
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r5_regime_journey_validity_forensics as r5

IDENTITY = "TURTLE_SOUP_XAUUSD_R7_STRUCTURAL_ABSTENTION_LAB_V1"
EVIDENCE_STATUS = "CONSUMED_CIBO_10Y_STRUCTURAL_ABSTENTION_COUNTERFACTUAL_NOT_FRESH_HOLDOUT"
STRESS_EXTRA_R = Decimal("0.05")

FROZEN_INVALID = {
    "raid_depth_range_bucket": "q4:<=0.50",
    "cisd_progress_bucket": "q4:>0.75",
    "reclaim_latency_bucket": "<=5m",
    "protected_risk_range_bucket": "q3:<=1.0",
}


def _d(v: Any) -> Decimal:
    return Decimal(str(v))


def _is_abstain(row: dict[str, Any]) -> bool:
    return all(str(row[k]) == v for k, v in FROZEN_INVALID.items())


def _max_dd(values: Sequence[Decimal]) -> Decimal:
    equity = Decimal(0)
    peak = Decimal(0)
    dd = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    return dd


def _max_losing_streak(values: Sequence[Decimal]) -> int:
    best = 0
    current = 0
    for value in values:
        if value < 0:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def _metrics(rows: Sequence[dict[str, Any]], *, stress: bool = False) -> dict[str, Any]:
    values = [
        _d(row["primary_net_r"]) - (STRESS_EXTRA_R if stress else Decimal(0))
        for row in rows
    ]
    gross_profit = sum((value for value in values if value > 0), Decimal(0))
    gross_loss = -sum((value for value in values if value < 0), Decimal(0))
    total = sum(values, Decimal(0))
    targets = sum(1 for row in rows if "TARGET" in str(row["exit_reason"]).upper())
    stops = sum(1 for row in rows if "STOP" in str(row["exit_reason"]).upper())
    return {
        "trades": len(rows),
        "total_r": str(total),
        "mean_r": str(total / len(rows)) if rows else None,
        "profit_factor": str(gross_profit / gross_loss) if gross_loss > 0 else None,
        "max_drawdown_r": str(_max_dd(values)),
        "max_losing_streak": _max_losing_streak(values),
        "target_rate": str(Decimal(targets) / len(rows)) if rows else None,
        "stop_rate": str(Decimal(stops) / len(rows)) if rows else None,
    }


def _slice(rows: Sequence[dict[str, Any]], years: set[int]) -> list[dict[str, Any]]:
    return [row for row in rows if int(row["year"]) in years]


def _pack(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "primary": _metrics(rows),
        "stress_0p10R": _metrics(rows, stress=True),
    }


def run(source_root: Path, target_root: Path, output: Path) -> dict[str, Any]:
    evidence, selected, reproduction = causal._reproduce_selected(source_root, target_root)
    opens = tuple(bar.opened_at for bar in evidence.bars)
    base = [causal._record(setup, trade, evidence.bars, opens) for setup, trade in selected]
    if len(base) != 5885:
        raise ValueError(f"R3 reproduction drift: {len(base)}")

    d1 = r5._aggregate(evidence.bars, "D1")
    h4 = r5._aggregate(evidence.bars, "H4")
    rows: list[dict[str, Any]] = []
    for raw in base:
        row = dict(raw)
        row.update(r5._regime_features(row, d1, h4))
        rows.append(row)

    removed = [row for row in rows if _is_abstain(row)]
    kept = [row for row in rows if not _is_abstain(row)]
    if len(removed) != 273:
        raise ValueError(f"frozen invalid state drift: expected 273, got {len(removed)}")

    periods = {
        "full_2016_2026": set(range(2016, 2027)),
        "early_2016_2020": set(range(2016, 2021)),
        "transition_2021_2023": {2021, 2022, 2023},
        "recent_2024_2026": {2024, 2025, 2026},
        "2024": {2024},
        "2025": {2025},
        "2026": {2026},
    }
    comparison: dict[str, Any] = {}
    for name, years in periods.items():
        baseline_rows = _slice(rows, years)
        kept_rows = _slice(kept, years)
        removed_rows = _slice(removed, years)
        comparison[name] = {
            "r3_baseline": _pack(baseline_rows),
            "r7_abstention": _pack(kept_rows),
            "removed_invalid": _pack(removed_rows),
            "trade_reduction": len(baseline_rows) - len(kept_rows),
        }

    payload = {
        "schema": "qore.turtle_soup_xauusd_r7.structural_abstention_lab.v1",
        "identity": IDENTITY,
        "evidence_status": EVIDENCE_STATUS,
        "reproduction": reproduction,
        "frozen_abstention_state": FROZEN_INVALID,
        "baseline_trades": len(rows),
        "removed_trades": len(removed),
        "retained_trades": len(kept),
        "comparison": comparison,
        "governance": {
            "counterfactual_only": True,
            "single_pre_frozen_abstention_family": True,
            "year_or_date_allowed_as_rule": False,
            "post_entry_leakage_allowed": False,
            "fresh_holdout_consumed": False,
            "rules_promoted": False,
            "automatic_candidate_promotion": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "structural-abstention-lab.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "retained-trades.json").write_text(json.dumps(kept, indent=2, sort_keys=True) + "\n")
    (output / "removed-invalid-trades.json").write_text(
        json.dumps(removed, indent=2, sort_keys=True) + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: module SOURCE_ROOT TARGET_ROOT OUTPUT_DIR")
    print(json.dumps(run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])), sort_keys=True))


if __name__ == "__main__":
    main()
