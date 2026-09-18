"""Economic replay of the frozen R11 XAUUSD structural-validity candidate.

This is a consumed-evidence research launch, not fresh validation.

Eligibility is NOT re-fit here. The exact 31 pre-entry candidate episode IDs
are read from the immutable R11 Situation Recognition artifact. Economic
outcomes are then joined to the reproduced frozen R3 routed trades.

This separation prevents the economic replay from changing the candidate after
seeing PnL. It also makes outlier dependence explicit.
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r3_causal_regime_forensics as causal,
)
from qore.infrastructure.trader_lab.turtle_soup_xauusd_r11_positive_validity_candidate_contract import (
    IDENTITY as CANDIDATE_IDENTITY,
)

IDENTITY = "TURTLE_SOUP_XAUUSD_R12_FROZEN_CANDIDATE_TRADER_REPLAY_V1"
EVIDENCE_STATUS = "CONSUMED_10Y_ECONOMIC_REPLAY_NOT_FRESH_HOLDOUT"
EXPECTED_CANDIDATES = 31
PRIMARY_FRICTION_R = Decimal("0.05")


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _load_r11_candidates(recognition_root: Path) -> list[dict[str, Any]]:
    path = recognition_root / "recognized-cases.json"
    if not path.exists():
        matches = list(recognition_root.rglob("recognized-cases.json"))
        if len(matches) != 1:
            raise ValueError(
                f"expected exactly one recognized-cases.json, got {len(matches)}"
            )
        path = matches[0]

    rows = json.loads(path.read_text())
    if not isinstance(rows, list):
        raise ValueError("recognized-cases.json must contain a list")

    candidates = [
        cast(dict[str, Any], row)
        for row in rows
        if isinstance(row, dict)
        and row.get("recognized_state") == "STRUCTURALLY_VALID_CANDIDATE"
    ]
    if len(candidates) != EXPECTED_CANDIDATES:
        raise ValueError(
            f"R11 frozen candidate count drift: {len(candidates)} != "
            f"{EXPECTED_CANDIDATES}"
        )

    episode_ids = [str(row["episode_id"]) for row in candidates]
    if len(set(episode_ids)) != len(episode_ids):
        raise ValueError("R11 candidate episode IDs are not unique")
    return candidates


def _max_dd(values: Sequence[Decimal]) -> Decimal:
    equity = Decimal(0)
    peak = Decimal(0)
    maximum = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        maximum = max(maximum, peak - equity)
    return maximum


def _max_losing_streak(values: Sequence[Decimal]) -> int:
    maximum = 0
    current = 0
    for value in values:
        if value < 0:
            current += 1
            maximum = max(maximum, current)
        else:
            current = 0
    return maximum


def _metrics(
    rows: Sequence[Mapping[str, Any]],
    *,
    extra_friction_r: Decimal = Decimal(0),
) -> dict[str, Any]:
    values = [
        _d(row["primary_net_r"]) - extra_friction_r
        for row in rows
    ]
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    flats = [value for value in values if value == 0]
    gross_profit = sum(wins, Decimal(0))
    gross_loss = -sum(losses, Decimal(0))
    total = sum(values, Decimal(0))
    target_exits = sum(
        1 for row in rows if "TARGET" in str(row["exit_reason"]).upper()
    )
    stop_exits = sum(
        1 for row in rows if "STOP" in str(row["exit_reason"]).upper()
    )
    lifecycle_exits = len(rows) - target_exits - stop_exits
    return {
        "trades": len(rows),
        "wins": len(wins),
        "losses": len(losses),
        "flats": len(flats),
        "win_rate": (
            str(Decimal(len(wins)) / Decimal(len(rows))) if rows else None
        ),
        "total_r": str(total),
        "mean_r": str(total / Decimal(len(rows))) if rows else None,
        "median_r": (
            str(statistics.median(values)) if values else None
        ),
        "profit_factor": (
            str(gross_profit / gross_loss) if gross_loss > 0 else None
        ),
        "max_drawdown_r": str(_max_dd(values)),
        "max_losing_streak": _max_losing_streak(values),
        "target_exits": target_exits,
        "stop_exits": stop_exits,
        "lifecycle_other_exits": lifecycle_exits,
        "target_rate": (
            str(Decimal(target_exits) / Decimal(len(rows))) if rows else None
        ),
        "stop_rate": (
            str(Decimal(stop_exits) / Decimal(len(rows))) if rows else None
        ),
    }


def _pack(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "primary_0p05R": _metrics(rows),
        "stress_0p10R": _metrics(rows, extra_friction_r=Decimal("0.05")),
        "stress_0p15R": _metrics(rows, extra_friction_r=Decimal("0.10")),
    }


def _group(
    rows: Sequence[dict[str, Any]],
    key: str,
) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(key))].append(row)
    return {
        name: _pack(items)
        for name, items in sorted(groups.items())
    }


def _yearly(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[int(row["year"])].append(row)
    return {
        str(year): _pack(groups[year])
        for year in sorted(groups)
    }


def _outlier_sensitivity(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "largest_winner": None,
            "leave_largest_winner_out": _pack([]),
        }

    winner = max(rows, key=lambda row: _d(row["primary_net_r"]))
    remaining = [row for row in rows if row is not winner]
    total = sum((_d(row["primary_net_r"]) for row in rows), Decimal(0))
    winner_r = _d(winner["primary_net_r"])
    return {
        "largest_winner": {
            "episode_id": winner["episode_id"],
            "entry_at": winner["entry_at"],
            "side": winner["side"],
            "source_timeframe": winner["source_timeframe"],
            "entry_mode": winner["entry_mode"],
            "target_route": winner["target_route"],
            "exit_reason": winner["exit_reason"],
            "primary_net_r": str(winner_r),
            "share_of_total_r": (
                str(winner_r / total) if total != 0 else None
            ),
        },
        "leave_largest_winner_out": _pack(remaining),
    }


def run(
    source_root: Path,
    target_root: Path,
    recognition_root: Path,
    output: Path,
) -> dict[str, Any]:
    candidates = _load_r11_candidates(recognition_root)
    candidate_by_episode = {
        str(row["episode_id"]): row for row in candidates
    }

    evidence, selected, reproduction = causal._reproduce_selected(
        source_root, target_root
    )
    opens = tuple(bar.opened_at for bar in evidence.bars)

    economic_rows = [
        causal._record(setup, trade, evidence.bars, opens)
        for setup, trade in selected
    ]
    if len(economic_rows) != 5885:
        raise ValueError(
            f"R3 reproduction drift: {len(economic_rows)} != 5885"
        )

    trade_by_episode = {
        str(row["episode_id"]): row for row in economic_rows
    }
    missing = sorted(set(candidate_by_episode) - set(trade_by_episode))
    if missing:
        raise ValueError(
            f"candidate economic join missing {len(missing)} episode IDs"
        )

    trader_rows: list[dict[str, Any]] = []
    for episode_id, recognition in candidate_by_episode.items():
        raw = dict(trade_by_episode[episode_id])
        raw["recognized_state"] = recognition["recognized_state"]
        raw["mechanism_code"] = recognition["mechanism_code"]
        raw["evidence_grade"] = recognition["evidence_grade"]
        raw["matched_signal_codes"] = recognition["matched_signal_codes"]
        raw["outcome_class"] = recognition["outcome_class"]
        raw["journey_failure_stage"] = recognition["journey_failure_stage"]
        trader_rows.append(raw)

    trader_rows.sort(key=lambda row: str(row["entry_at"]))
    if len(trader_rows) != EXPECTED_CANDIDATES:
        raise ValueError(
            f"candidate economic rows drift: {len(trader_rows)} != "
            f"{EXPECTED_CANDIDATES}"
        )

    baseline_ids = {str(row["episode_id"]) for row in economic_rows}
    if not all(str(row["episode_id"]) in baseline_ids for row in trader_rows):
        raise ValueError("candidate replay contains non-R3-selected trade")

    binary_capacity = [
        row
        for row in trader_rows
        if row["outcome_class"]
        in {"TOUCHED_ANY_ACTIVE_DOL", "INVALIDATED_BEFORE_ANY_ACTIVE_DOL"}
    ]
    if len(binary_capacity) != 30:
        raise ValueError(
            f"binary capacity count drift: {len(binary_capacity)} != 30"
        )

    payload = {
        "schema": "qore.turtle_soup_xauusd_r12.frozen_candidate_trader_replay.v1",
        "identity": IDENTITY,
        "candidate_identity": CANDIDATE_IDENTITY,
        "evidence_status": EVIDENCE_STATUS,
        "reproduction": {
            **reproduction,
            "r3_selected_trades": len(economic_rows),
            "frozen_candidate_trades": len(trader_rows),
            "binary_capacity_labeled": len(binary_capacity),
        },
        "launch_contract": {
            "eligibility_source": (
                "IMMUTABLE_R11_RECOGNITION_ARTIFACT_EPISODE_IDS"
            ),
            "candidate_definition_retrained": False,
            "thresholds_changed": False,
            "calendar_year_used_as_rule": False,
            "pnl_used_for_eligibility": False,
            "fresh_holdout_used": False,
            "research_replay_only": True,
        },
        "performance": _pack(trader_rows),
        "by_year": _yearly(trader_rows),
        "by_side": _group(trader_rows, "side"),
        "by_source_timeframe": _group(trader_rows, "source_timeframe"),
        "by_entry_mode": _group(trader_rows, "entry_mode"),
        "by_target_route": _group(trader_rows, "target_route"),
        "capacity_labels": {
            "dol_capable": sum(
                1
                for row in binary_capacity
                if row["outcome_class"] == "TOUCHED_ANY_ACTIVE_DOL"
            ),
            "invalidated_before_any_active_dol": sum(
                1
                for row in binary_capacity
                if row["outcome_class"]
                == "INVALIDATED_BEFORE_ANY_ACTIVE_DOL"
            ),
            "other_diagnostic": len(trader_rows) - len(binary_capacity),
        },
        "outlier_sensitivity": _outlier_sensitivity(trader_rows),
        "governance": {
            "candidate_promoted_to_operating_rule": False,
            "fresh_holdout_consumed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "candidate-trader-replay-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "candidate-trades.json").write_text(
        json.dumps(trader_rows, indent=2, sort_keys=True) + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit(
            "usage: module SOURCE_ROOT TARGET_ROOT R11_RECOGNITION_ROOT OUTPUT_DIR"
        )
    print(
        json.dumps(
            run(
                Path(sys.argv[1]),
                Path(sys.argv[2]),
                Path(sys.argv[3]),
                Path(sys.argv[4]),
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
