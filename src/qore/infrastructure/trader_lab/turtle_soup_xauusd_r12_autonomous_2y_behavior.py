"""R12: observe the intelligent Turtle Soup trader autonomously for two years.

This is a consumed-evidence behaviour experiment, not a fresh holdout.
The trader is not externally restricted to the 31 R11 positive-candidate cases.
R3 CIBO routing remains responsible for entry/stop/target execution while R11
recognition is recorded for every routed trade so behaviour can be diagnosed.

Window is fixed before execution: [2024-09-17, 2026-09-17), exactly two years.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r11_situation_recognition_lab as r11lab
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r11_situation_recognition_engine as r11

IDENTITY = "TURTLE_SOUP_XAUUSD_R12_AUTONOMOUS_2Y_BEHAVIOR_V1"
OPEN = datetime(2024, 9, 17, tzinfo=UTC)
CLOSE = datetime(2026, 9, 17, tzinfo=UTC)


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rs = [_d(row["primary_net_r"]) for row in rows]
    gross = [_d(row["gross_r"]) for row in rows]
    if not rs:
        return {"trades": 0}
    wins = sum(x > 0 for x in rs)
    losses = sum(x < 0 for x in rs)
    total = sum(rs, Decimal(0))
    peak = Decimal(0)
    equity = Decimal(0)
    dd = Decimal(0)
    for value in rs:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    gross_profit = sum((x for x in rs if x > 0), Decimal(0))
    gross_loss = -sum((x for x in rs if x < 0), Decimal(0))
    stop_dist = [abs(_d(row["entry"]) - _d(row["stop"])) for row in rows]
    target_dist = [abs(_d(row["target"]) - _d(row["entry"])) for row in rows]
    planned_rr = [
        target / stop for target, stop in zip(target_dist, stop_dist, strict=True)
        if stop > 0
    ]
    return {
        "trades": len(rows),
        "wins": wins,
        "losses": losses,
        "flats": len(rows) - wins - losses,
        "win_rate": str(Decimal(wins) / Decimal(len(rows))),
        "total_primary_r": str(total),
        "mean_primary_r": str(total / Decimal(len(rows))),
        "profit_factor": None if gross_loss == 0 else str(gross_profit / gross_loss),
        "max_drawdown_r": str(dd),
        "gross_total_r": str(sum(gross, Decimal(0))),
        "median_stop_price_distance": str(sorted(stop_dist)[len(stop_dist)//2]),
        "median_target_price_distance": str(sorted(target_dist)[len(target_dist)//2]),
        "median_planned_rr": (
            None if not planned_rr else str(sorted(planned_rr)[len(planned_rr)//2])
        ),
    }


def _group(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row[key])].append(row)
    return {name: _stats(items) for name, items in sorted(groups.items())}


def run(source_root: Path, target_root: Path, output: Path) -> dict[str, Any]:
    # Reuse the canonical R3 trader execution, then independently reconstruct
    # R11 causal recognition features for state attribution.
    r3_out = output / "r3"
    r3_payload = r3.run(source_root, target_root, r3_out)
    trades = json.loads((r3_out / "trades-full.json").read_text())
    two_year = [
        row for row in trades
        if OPEN <= datetime.fromisoformat(str(row["entry_at"])) < CLOSE
    ]

    # Build recognition ledger from the same immutable consumed corpus.
    recognition_out = output / "recognition"
    r11lab.run(source_root, target_root, recognition_out)
    recognized = json.loads((recognition_out / "recognized-cases.json").read_text())

    # R11 ledger is keyed by episode. Multiple executions can share an episode;
    # state is setup knowledge and is therefore stable for that episode.
    state_by_episode: dict[str, dict[str, Any]] = {}
    for row in recognized:
        episode = str(row["episode_id"])
        previous = state_by_episode.get(episode)
        if previous is not None and previous["recognized_state"] != row["recognized_state"]:
            raise ValueError(f"ambiguous R11 state for episode {episode}")
        state_by_episode[episode] = row

    enriched: list[dict[str, Any]] = []
    unmatched = 0
    for trade in two_year:
        state = state_by_episode.get(str(trade["episode_id"]))
        if state is None:
            unmatched += 1
            recognized_state = r11.SituationState.UNKNOWN.value
            mechanism = "UNMATCHED_RECOGNITION"
            directive = r11.SituationDirective.NO_DECISION.value
        else:
            recognized_state = str(state["recognized_state"])
            mechanism = str(state["mechanism_code"])
            directive = str(state["directive"])
        enriched.append({
            **trade,
            "r11_state": recognized_state,
            "r11_mechanism": mechanism,
            "r11_directive": directive,
        })

    payload = {
        "schema": "qore.turtle_soup_xauusd_r12.autonomous_2y_behavior.v1",
        "identity": IDENTITY,
        "window": {"open": OPEN.isoformat(), "close": CLOSE.isoformat(), "years": 2},
        "evidence_status": "CONSUMED_2Y_AUTONOMOUS_BEHAVIOR_NOT_FRESH_HOLDOUT",
        "freedom_contract": {
            "restricted_to_r11_positive_candidates": False,
            "external_year_filter_inside_window": False,
            "external_side_filter": False,
            "external_timeframe_filter": False,
            "external_session_filter": False,
            "entry_owner": "R3_CIBO_JOURNEY_ROUTER",
            "stop_owner": "CAUSAL_CISD_PROTECTED_SWING",
            "target_owner": "R3_ACTIVE_CIBO_DOL_ROUTER",
            "r11_role": "OBSERVE_AND_ATTRIBUTE_INTELLIGENCE_STATE_FOR_THIS_BEHAVIOR_RUN",
            "single_position_constraint": True,
        },
        "source_r3": {
            "identity": r3_payload["identity"],
            "full_executed_trades": r3_payload["executed_trades"],
        },
        "two_year": {
            "executed_trades": len(enriched),
            "r11_unmatched": unmatched,
            "overall": _stats(enriched),
            "by_r11_state": _group(enriched, "r11_state"),
            "by_r11_mechanism": _group(enriched, "r11_mechanism"),
            "by_side": _group(enriched, "side"),
            "by_source_timeframe": _group(enriched, "source_timeframe"),
            "by_entry_mode": _group(enriched, "entry_mode"),
            "by_target_route": _group(enriched, "target_route"),
            "by_exit_reason": dict(Counter(row["exit_reason"] for row in enriched)),
            "by_session": _group(enriched, "session_bucket"),
        },
        "governance": {
            "fresh_holdout_consumed": False,
            "candidate_promoted": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "r12-autonomous-2y-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "r12-autonomous-2y-trades.json").write_text(
        json.dumps(enriched, indent=2, sort_keys=True) + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: module SOURCE_ROOT TARGET_ROOT OUTPUT_DIR")
    print(json.dumps(run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])), sort_keys=True))


if __name__ == "__main__":
    main()
