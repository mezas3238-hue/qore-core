"""Decision-time Journey atlas for true-2R Capitalizer third-slot candidates.

Consumes the true-2R cognitive economic rebase. The 40 third-slot selections are
unchanged, but prior-trade OPEN/WIN/LOSS state is reconstructed from the true 2R
exit lifecycle rather than the superseded 1R target experiment.

Current candidate outcome is attached only after the Journey cell is built.
No third-slot rule is selected or promoted.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_economic_rebase_2r_v1 as rebase,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_preentry_stop_risk_atlas_2r_v1 as stoprisk_2r,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_THIRD_SLOT_JOURNEY_ATLAS_2R_V1"
SOURCE_REBASE_RUN_ID = 36078677895
SOURCE_REBASE_SHA = "cfc04849c8bbfd6565310d89456f5e367ea880f7"


def _aware(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def _join_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["symbol"]), str(row["entry_at"])


def _load_rebase(root: Path) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    report_paths = sorted(
        root.rglob("capitalizer-cognitive-economic-rebase-2r-v1.json")
    )
    row_paths = sorted(
        root.rglob("capitalizer-cognitive-economic-rebase-2r-v1-rows.jsonl")
    )
    if len(report_paths) != 1 or len(row_paths) != 1:
        raise ValueError("2R third-slot atlas requires one rebase artifact")
    report = json.loads(report_paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != rebase.IDENTITY:
        raise ValueError("unexpected 2R rebase identity")

    rows: list[dict[str, Any]] = []
    with row_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("2R rebase row must be object")
                rows.append(raw)
    if len(rows) != rebase.EXPECTED_TRADES:
        raise ValueError("2R third-slot population mismatch")
    return report, tuple(rows)


def _trade(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": str(row["symbol"]),
        "session": str(row["session"]),
        "operating_date": str(row["operating_date"]),
        "side": str(row["side"]),
        "entry_at": str(row["entry_at"]),
        "exit_at": str(row["post_audit_exit_at"]),
        "realized_gross_r": str(row["post_audit_realized_gross_r"]),
        "exit_reason": str(row["post_audit_exit_reason"]),
    }


def _known_state(row: dict[str, Any], *, decision_at: datetime) -> str:
    if _aware(row["exit_at"]) > decision_at:
        return "OPEN"
    value = Decimal(str(row["realized_gross_r"]))
    if value > 0:
        return "WIN"
    if value < 0:
        return "LOSS"
    return "FLAT"


def _sign(value: Decimal) -> str:
    if value > 0:
        return "POSITIVE"
    if value < 0:
        return "NEGATIVE"
    return "ZERO"


def _causal_cells(
    *,
    candidate: dict[str, Any],
    rebase_row: dict[str, Any],
    control: tuple[dict[str, Any], ...],
) -> tuple[tuple[str, str], ...]:
    decision_at = _aware(candidate["entry_at"])
    same_session_prior = tuple(
        sorted(
            (
                row
                for row in control
                if str(row["operating_date"]) == str(candidate["operating_date"])
                and str(row["session"]) == str(candidate["session"])
                and _aware(row["entry_at"]) < decision_at
            ),
            key=lambda row: _aware(row["entry_at"]),
        )
    )
    if len(same_session_prior) != 2:
        raise ValueError("2R third-slot candidate must have two prior selections")

    states = tuple(
        _known_state(row, decision_at=decision_at) for row in same_session_prior
    )
    closed_session = tuple(
        row for row in same_session_prior if _aware(row["exit_at"]) <= decision_at
    )
    prior_day = tuple(
        row
        for row in control
        if str(row["operating_date"]) == str(candidate["operating_date"])
        and _aware(row["entry_at"]) < decision_at
        and _aware(row["exit_at"]) <= decision_at
    )
    session_r = sum(
        (Decimal(str(row["realized_gross_r"])) for row in closed_session),
        Decimal("0"),
    )
    day_r = sum(
        (Decimal(str(row["realized_gross_r"])) for row in prior_day),
        Decimal("0"),
    )
    most_recent_closed = (
        "NONE"
        if not closed_session
        else _known_state(
            max(closed_session, key=lambda row: _aware(row["exit_at"])),
            decision_at=decision_at,
        )
    )
    active = int(rebase_row["baseline_active_positions"])
    if active != sum(state == "OPEN" for state in states):
        raise ValueError("2R Journey/rebase active-position mismatch")

    return (
        ("PRIOR_TWO_STATE", ">".join(states)),
        ("PRIOR_SESSION_REALIZED_SIGN", _sign(session_r)),
        ("PRIOR_DAY_REALIZED_SIGN", _sign(day_r)),
        ("PRIOR_SESSION_CLOSED_COUNT", str(len(closed_session))),
        ("MOST_RECENT_CLOSED_SESSION_OUTCOME", most_recent_closed),
        ("ACTIVE_POSITION_COUNT", str(active)),
    )


def build_report(root: Path) -> dict[str, Any]:
    rebase_report, rows = _load_rebase(root)
    control = tuple(_trade(row) for row in rows)
    rebase_by_key = {_join_key(row): row for row in rows}
    if len(rebase_by_key) != len(rows):
        raise ValueError("2R third-slot rebase identity not unique")

    third = tuple(
        trade
        for trade in control
        if int(rebase_by_key[_join_key(trade)]["prior_same_session_selected"]) == 2
    )
    if len(third) != 40:
        raise ValueError(f"expected frozen 40 third-slot trades, got {len(third)}")

    members: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for candidate in third:
        rebase_row = rebase_by_key[_join_key(candidate)]
        for cell in _causal_cells(
            candidate=candidate,
            rebase_row=rebase_row,
            control=control,
        ):
            members[cell].append(candidate)

    cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (feature, value), selected in members.items():
        blocked = tuple(selected)
        blocked_keys = {_join_key(row) for row in blocked}
        kept = tuple(
            row for row in control if _join_key(row) not in blocked_keys
        )
        cells[feature].append(
            {
                "value": value,
                "third_slot_trades": len(blocked),
                "third_slot_metrics": stoprisk_2r._metrics(blocked),
                "full_portfolio_if_abstained_metrics": stoprisk_2r._metrics(kept),
                "full_portfolio_trades_if_abstained": len(kept),
            }
        )

    active_distribution = defaultdict(int)
    for candidate in third:
        active_distribution[
            str(rebase_by_key[_join_key(candidate)]["baseline_active_positions"])
        ] += 1

    return {
        "identity": IDENTITY,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": "2.00",
        "control_trades": len(control),
        "control_metrics": stoprisk_2r._metrics(control),
        "third_slot_trades": len(third),
        "third_slot_metrics": stoprisk_2r._metrics(third),
        "third_slot_active_position_distribution": dict(
            sorted(active_distribution.items())
        ),
        "journey_cells": {
            feature: sorted(value, key=lambda row: str(row["value"]))
            for feature, value in sorted(cells.items())
        },
        "journey_feature_count": len(cells),
        "dynamic_state_from_true_2r_rebase": True,
        "prior_trade_outcome_visible_only_after_prior_trade_closed": True,
        "current_candidate_outcome_visible_to_journey_cell": False,
        "current_candidate_outcome_used_for_post_cell_metrics": True,
        "positive_session_pnl_is_not_stop_condition": True,
        "third_slot_rule_selected": False,
        "loss_cluster_semantics_selected": False,
        "rebase_control_reproduced": (
            int(rebase_report["control_trades"]) == len(control)
        ),
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
        "next_phase": "CROSS_FALSIFY_TRUE_2R_THIRD_SLOT_WITH_PREENTRY_STATE",
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output / "capitalizer-cognitive-third-slot-journey-atlas-2r-v1.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rebase_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_report(args.rebase_root)
    write_report(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
