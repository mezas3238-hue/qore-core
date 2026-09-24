"""Decision-time Journey atlas for Capitalizer third-slot candidates.

The frozen MAX3 contract is a ceiling, never a quota. This consumed-window
diagnostic isolates the 40 candidates that entered with two earlier selected
trades already assigned to the same session and reconstructs only what was
known at the candidate timestamp:

- whether each of the two earlier trades was still OPEN or already closed;
- WIN / LOSS / FLAT labels only for trades already closed before the candidate;
- realized session R and operating-day R known at that moment;
- active-position count.

The current candidate outcome is attached only after the causal Journey cell is
constructed. No third-slot rule is selected or promoted here.
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
    capitalizer_cognitive_evidence_binding_audit_2y_v1 as binding_v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_evidence_binding_audit_2y_v2 as binding_v2,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_THIRD_SLOT_JOURNEY_ATLAS_2Y_V1"
SOURCE_BINDING_RUN_ID = 36065651404
SOURCE_BINDING_SHA = "1d910f5c3550ac481c28390671a86ceb011597e3"
SOURCE_TARGET_RUN_ID = 36055792484
SOURCE_TARGET_SHA = "a66ab11c22efbefb61756db3f0062c3c51a2a825"


def _aware(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def _join_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["symbol"]), str(row["entry_at"])


def _load_binding(root: Path) -> tuple[dict[str, Any], ...]:
    report_paths = sorted(
        root.rglob("capitalizer-cognitive-evidence-binding-audit-2y-v2.json")
    )
    row_paths = sorted(
        root.rglob("capitalizer-cognitive-evidence-binding-audit-2y-v2-rows.jsonl")
    )
    if len(report_paths) != 1 or len(row_paths) != 1:
        raise ValueError("third-slot atlas requires one V2 binding artifact")
    report = json.loads(report_paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != binding_v2.IDENTITY:
        raise ValueError("unexpected V2 binding identity")
    if int(report.get("future_evidence_violations", -1)) != 0:
        raise ValueError("third-slot atlas rejects future evidence")
    rows: list[dict[str, Any]] = []
    with row_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("binding row must be object")
                rows.append(raw)
    return tuple(rows)


def _metrics(rows: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    values = tuple(Decimal(str(row["realized_gross_r"])) for row in rows)
    gp = sum((value for value in values if value > 0), Decimal("0"))
    gl = -sum((value for value in values if value < 0), Decimal("0"))
    equity = Decimal("0")
    peak = Decimal("0")
    dd = Decimal("0")
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
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
        "max_drawdown_r": str(dd),
        "max_losing_streak": max_streak,
    }


def _sign(value: Decimal) -> str:
    if value > 0:
        return "POSITIVE"
    if value < 0:
        return "NEGATIVE"
    return "ZERO"


def _known_state(row: dict[str, Any], *, decision_at: datetime) -> str:
    if _aware(row["exit_at"]) > decision_at:
        return "OPEN"
    value = Decimal(str(row["realized_gross_r"]))
    if value > 0:
        return "WIN"
    if value < 0:
        return "LOSS"
    return "FLAT"


def _causal_cells(
    *,
    candidate: dict[str, Any],
    binding: dict[str, Any],
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
        raise ValueError("third-slot candidate must have exactly two earlier session selections")

    states = tuple(
        _known_state(row, decision_at=decision_at)
        for row in same_session_prior
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
    active = int(binding["baseline_active_positions"])
    if active != sum(state == "OPEN" for state in states):
        raise ValueError("third-slot active-position state disagrees with binding")

    return (
        ("PRIOR_TWO_STATE", ">".join(states)),
        ("PRIOR_SESSION_REALIZED_SIGN", _sign(session_r)),
        ("PRIOR_DAY_REALIZED_SIGN", _sign(day_r)),
        ("PRIOR_SESSION_CLOSED_COUNT", str(len(closed_session))),
        ("MOST_RECENT_CLOSED_SESSION_OUTCOME", most_recent_closed),
        ("ACTIVE_POSITION_COUNT", str(active)),
    )


def build_report(binding_root: Path, target_root: Path) -> dict[str, Any]:
    bindings = _load_binding(binding_root)
    control = binding_v1._load_control(target_root)
    binding_by_key = {_join_key(row): row for row in bindings}
    if {_join_key(row) for row in control} != set(binding_by_key):
        raise ValueError("third-slot binding/control identities differ")

    third = tuple(
        row
        for row in control
        if int(binding_by_key[_join_key(row)]["prior_same_session_selected"]) == 2
    )
    if len(third) != 40:
        raise ValueError(f"expected frozen 40 third-slot trades, got {len(third)}")

    members: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for candidate in third:
        binding = binding_by_key[_join_key(candidate)]
        for cell in _causal_cells(
            candidate=candidate,
            binding=binding,
            control=control,
        ):
            members[cell].append(candidate)

    cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (feature, value), selected in members.items():
        blocked = tuple(selected)
        blocked_keys = {_join_key(row) for row in blocked}
        kept_full = tuple(
            row for row in control if _join_key(row) not in blocked_keys
        )
        cells[feature].append(
            {
                "value": value,
                "third_slot_trades": len(blocked),
                "third_slot_metrics": _metrics(blocked),
                "full_portfolio_if_abstained_metrics": _metrics(kept_full),
                "full_portfolio_trades_if_abstained": len(kept_full),
            }
        )

    return {
        "identity": IDENTITY,
        "source_binding_run_id": SOURCE_BINDING_RUN_ID,
        "source_binding_sha": SOURCE_BINDING_SHA,
        "source_target_run_id": SOURCE_TARGET_RUN_ID,
        "source_target_sha": SOURCE_TARGET_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "control_metrics": _metrics(control),
        "control_trades": len(control),
        "third_slot_trades": len(third),
        "third_slot_metrics": _metrics(third),
        "journey_cells": {
            feature: sorted(rows, key=lambda row: str(row["value"]))
            for feature, rows in sorted(cells.items())
        },
        "journey_feature_count": len(cells),
        "prior_trade_outcome_visible_only_after_prior_trade_closed": True,
        "current_candidate_outcome_visible_to_journey_cell": False,
        "current_candidate_outcome_used_for_post_cell_metrics": True,
        "positive_session_pnl_is_not_stop_condition": True,
        "third_slot_rule_selected": False,
        "loss_cluster_semantics_selected": False,
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
        "next_phase": "FREEZE_THIRD_SLOT_COGNITIVE_PRESSURE_HYPOTHESIS_IF_CAUSAL_CELL_IS_INFORMATIVE",
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output / "capitalizer-cognitive-third-slot-journey-atlas-2y-v1.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("binding_root", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_report(args.binding_root, args.target_root)
    write_report(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
