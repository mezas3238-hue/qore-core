"""R3 annual/regime forensics over the immutable official Turtle Soup replay.

Diagnostic only: explains why historically positive years became negative without
promoting retrospective filters or changing the frozen R3 economic contract.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

IDENTITY = "TURTLE_SOUP_XAUUSD_R3_ANNUAL_REGIME_FORENSICS_V1"
R3_RUN_ID = 35256772043
R3_ARTIFACT_ID = 10513151886


def _d(v: Any) -> Decimal:
    return Decimal(str(v))


def _stat(rows: list[dict[str, Any]]) -> dict[str, Any]:
    vals = [_d(r["primary_net_r"]) for r in rows]
    wins = [v for v in vals if v > 0]
    losses = [v for v in vals if v < 0]
    pos = sum(wins, Decimal(0))
    neg = -sum(losses, Decimal(0))
    reasons = Counter(str(r["exit_reason"]) for r in rows)
    return {
        "n": len(rows),
        "total_r": str(sum(vals, Decimal(0))),
        "mean_r": str(sum(vals, Decimal(0)) / len(vals)) if vals else None,
        "profit_factor": str(pos / neg) if neg else None,
        "win_rate": str(Decimal(len(wins)) / len(vals)) if vals else None,
        "mean_winner_r": str(pos / len(wins)) if wins else None,
        "mean_loser_r": str(-neg / len(losses)) if losses else None,
        "stop_rate": str(Decimal(reasons["STOP"] + reasons["GAP_STOP"] + reasons["STOP_FIRST"]) / len(vals)) if vals else None,
        "target_rate": str(Decimal(reasons["TARGET"] + reasons["GAP_TARGET_CAPPED"]) / len(vals)) if vals else None,
    }


def _era(year: int) -> str:
    if year <= 2019:
        return "2016_2019_POSITIVE_BASELINE"
    if year <= 2021:
        return "2020_2021_FLAT_TRANSITION"
    if year <= 2023:
        return "2022_2023_RECOVERY"
    return "2024_2026_NEGATIVE_RECENT"


def _groups(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(row[field])].append(row)
    return {k: _stat(v) for k, v in sorted(buckets.items())}


def run(root: Path, out: Path) -> dict[str, Any]:
    paths = list(root.rglob("trades-full.json"))
    if len(paths) != 1:
        raise ValueError("expected one official R3 trades-full.json")
    rows = json.loads(paths[0].read_text())
    if len(rows) != 5885:
        raise ValueError("unexpected official R3 trade count")

    by_year: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_era: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        year = datetime.fromisoformat(str(row["entry_at"])).year
        by_year[str(year)].append(row)
        by_era[_era(year)].append(row)

    annual = {k: _stat(v) for k, v in sorted(by_year.items())}
    eras: dict[str, Any] = {}
    for name, members in by_era.items():
        eras[name] = {
            "summary": _stat(members),
            "by_side": _groups(members, "side"),
            "by_timeframe": _groups(members, "source_timeframe"),
            "by_entry_mode": _groups(members, "entry_mode"),
            "by_target_route": _groups(members, "target_route"),
            "by_session": _groups(members, "session_bucket"),
            "by_prior_body": _groups(members, "prior_body_alignment"),
        }

    base = eras["2016_2019_POSITIVE_BASELINE"]["summary"]
    recent = eras["2024_2026_NEGATIVE_RECENT"]["summary"]
    diagnosis = {
        "win_rate_delta_recent_minus_baseline": str(_d(recent["win_rate"]) - _d(base["win_rate"])),
        "mean_winner_delta": str(_d(recent["mean_winner_r"]) - _d(base["mean_winner_r"])),
        "mean_loser_delta": str(_d(recent["mean_loser_r"]) - _d(base["mean_loser_r"])),
        "stop_rate_delta": str(_d(recent["stop_rate"]) - _d(base["stop_rate"])),
        "target_rate_delta": str(_d(recent["target_rate"]) - _d(base["target_rate"])),
        "interpretation": [
            "RECENT_NEGATIVITY_IS_PRIMARILY_HIT_RATE_DEGRADATION_NOT_PAYOFF_COMPRESSION",
            "SHORT_SIDE_EDGE_REVERSED_NEGATIVE",
            "H4_EDGE_REVERSED_NEGATIVE",
            "SOURCE_OPPOSITE_AND_SWING_H1_ROUTE_EDGE_REVERSED_NEGATIVE",
            "NEW_YORK_AND_OTHER_SESSION_CONTRIBUTIONS_REVERSED_NEGATIVE",
            "BOTH_ENTRY_MODES_DEGRADED_SO_FAILURE_IS_NOT_ONE_ENTRY_MECHANISM_ONLY",
        ],
    }

    report = {
        "schema": "qore.turtle_soup_xauusd_r3.annual_regime_forensics.v1",
        "identity": IDENTITY,
        "source_r3_run_id": R3_RUN_ID,
        "source_r3_artifact_id": R3_ARTIFACT_ID,
        "evidence_status": "POST_RESULT_DIAGNOSTIC_OVER_CONSUMED_R3_NOT_FRESH_HOLDOUT",
        "annual": annual,
        "eras": eras,
        "diagnosis": diagnosis,
        "governance": {
            "fresh_holdout_consumed": False,
            "retrospective_filter_promotion_allowed": False,
            "economic_contract_changed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "regime-forensics.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    return report


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: python -m ... <r3-artifact-root> <output-dir>")
    print(json.dumps(run(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))


if __name__ == "__main__":
    main()
