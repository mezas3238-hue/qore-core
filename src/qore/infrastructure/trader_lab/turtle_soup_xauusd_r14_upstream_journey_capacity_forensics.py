"""R14: upstream journey-capacity geometry forensics for XAUUSD.

Consumed evidence only. Compares UNKNOWN winning trades against UNKNOWN losses
whose journey failed before touching any active CIBO DOL. All measurements use
information available at entry plus outcome labels only for cohort assignment.

No threshold, timeframe, side, session, target family, or geometry cutoff is
promoted to an operating rule.
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

IDENTITY = "TURTLE_SOUP_XAUUSD_R14_UPSTREAM_JOURNEY_CAPACITY_GEOMETRY_FORENSICS_V1"
UPSTREAM_CAUSE = "UNKNOWN_UPSTREAM_JOURNEY_FAILED_BEFORE_ANY_ACTIVE_CIBO_DOL"


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _dt(value: Any) -> datetime | None:
    return None if value is None else datetime.fromisoformat(str(value))


def _find(root: Path, name: str) -> Path:
    direct = root / name
    if direct.exists():
        return direct
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _ahead(trade: Mapping[str, Any], candidate: Mapping[str, Any]) -> bool:
    entry = _d(trade["entry"])
    price = _d(candidate["candidate_price"])
    return price > entry if str(trade["side"]) == "long" else price < entry


def _load_targets(root: Path) -> dict[str, list[dict[str, Any]]]:
    path = _find(root, "TARGET_DESTINATION_LEDGER_V2.jsonl")
    episodes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                episodes[str(row["episode_id"])].append(row)
    return dict(episodes)


def _active_at_entry(
    trade: Mapping[str, Any],
    rows: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    entry_at = _dt(trade["entry_at"])
    assert entry_at is not None
    result: list[dict[str, Any]] = []
    for row in rows:
        known = _dt(row["candidate_known_at"])
        touch = _dt(row.get("touch_m5_opened_at"))
        if known is None or known > entry_at:
            continue
        if touch is not None and touch < entry_at:
            continue
        if _ahead(trade, row):
            result.append(row)
    return result


def _geometry(
    trade: Mapping[str, Any],
    rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    active = _active_at_entry(trade, rows)
    if not active:
        raise ValueError(f"no active CIBO DOL for {trade['episode_id']}")

    entry = _d(trade["entry"])
    stop = _d(trade["stop"])
    target = _d(trade["target"])
    risk = abs(entry - stop)
    selected_distance = abs(target - entry)
    if risk <= 0 or entry <= 0:
        raise ValueError("invalid entry/stop geometry")

    distances = sorted(abs(_d(row["candidate_price"]) - entry) for row in active)
    unique_distances = sorted(set(distances))
    selected_rank = (
        unique_distances.index(selected_distance) + 1
        if selected_distance in unique_distances
        else None
    )
    if selected_rank is None:
        raise ValueError(
            f"selected target absent from active CIBO universe: {trade['episode_id']}"
        )

    return {
        "active_dol_count": len(active),
        "nearest_dol_r": str(distances[0] / risk),
        "selected_dol_rank": selected_rank,
        "selected_rr": str(selected_distance / risk),
        "protected_risk_entry_fraction": str(risk / entry),
        "selected_target_entry_fraction": str(selected_distance / entry),
    }


def _median(values: Sequence[Decimal]) -> str:
    return str(statistics.median(values))


def _summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "trades": len(rows),
        "active_dol_count_median": _median(
            [_d(row["active_dol_count"]) for row in rows]
        ),
        "nearest_dol_r_median": _median(
            [_d(row["nearest_dol_r"]) for row in rows]
        ),
        "selected_dol_rank_median": _median(
            [_d(row["selected_dol_rank"]) for row in rows]
        ),
        "selected_rr_median": _median(
            [_d(row["selected_rr"]) for row in rows]
        ),
        "protected_risk_entry_fraction_median": _median(
            [_d(row["protected_risk_entry_fraction"]) for row in rows]
        ),
        "selected_target_entry_fraction_median": _median(
            [_d(row["selected_target_entry_fraction"]) for row in rows]
        ),
    }


def _group_summary(rows: Sequence[dict[str, Any]], key: str) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[key])].append(row)
    return {name: _summary(items) for name, items in sorted(grouped.items())}


def run(
    r12_root: Path,
    r13_root: Path,
    target_root: Path,
    output: Path,
) -> dict[str, Any]:
    trades = json.loads(_find(r12_root, "r12-autonomous-2y-trades.json").read_text())
    losses = json.loads(_find(r13_root, "r13-loss-ledger.json").read_text())
    targets = _load_targets(target_root)

    upstream_losses = [
        row for row in losses if row["forensic_loss_cause"] == UPSTREAM_CAUSE
    ]
    unknown_wins = [
        row
        for row in trades
        if row["r11_state"] == "UNKNOWN" and _d(row["primary_net_r"]) > 0
    ]
    if len(upstream_losses) != 622:
        raise ValueError(f"upstream loss drift: {len(upstream_losses)}")
    if len(unknown_wins) != 342:
        raise ValueError(f"unknown winner drift: {len(unknown_wins)}")

    enriched_losses: list[dict[str, Any]] = []
    enriched_wins: list[dict[str, Any]] = []

    for row in upstream_losses:
        episode = targets.get(str(row["episode_id"]))
        if not episode:
            raise ValueError(f"missing target episode {row['episode_id']}")
        enriched_losses.append({**row, **_geometry(row, episode)})

    for row in unknown_wins:
        episode = targets.get(str(row["episode_id"]))
        if not episode:
            raise ValueError(f"missing target episode {row['episode_id']}")
        enriched_wins.append({**row, **_geometry(row, episode)})

    loss_summary = _summary(enriched_losses)
    win_summary = _summary(enriched_wins)

    payload = {
        "schema": "qore.turtle_soup_xauusd_r14.upstream_journey_capacity_geometry_forensics.v1",
        "identity": IDENTITY,
        "evidence_status": "CONSUMED_R12_R13_AND_CIBO_TARGET_V2_DIAGNOSTIC_ONLY",
        "cohorts": {
            "unknown_upstream_losses": loss_summary,
            "unknown_wins": win_summary,
        },
        "pre_entry_geometry_contrast": {
            "active_dol_count_median_delta_loss_minus_win": str(
                _d(loss_summary["active_dol_count_median"])
                - _d(win_summary["active_dol_count_median"])
            ),
            "nearest_dol_r_median_ratio_loss_to_win": str(
                _d(loss_summary["nearest_dol_r_median"])
                / _d(win_summary["nearest_dol_r_median"])
            ),
            "selected_rr_median_ratio_loss_to_win": str(
                _d(loss_summary["selected_rr_median"])
                / _d(win_summary["selected_rr_median"])
            ),
            "protected_risk_fraction_median_ratio_loss_to_win": str(
                _d(loss_summary["protected_risk_entry_fraction_median"])
                / _d(win_summary["protected_risk_entry_fraction_median"])
            ),
            "selected_target_fraction_median_ratio_loss_to_win": str(
                _d(loss_summary["selected_target_entry_fraction_median"])
                / _d(win_summary["selected_target_entry_fraction_median"])
            ),
        },
        "diagnostics_not_rules": {
            "losses_by_target_route": _group_summary(enriched_losses, "target_route"),
            "wins_by_target_route": _group_summary(enriched_wins, "target_route"),
            "losses_by_source_timeframe": _group_summary(
                enriched_losses, "source_timeframe"
            ),
            "wins_by_source_timeframe": _group_summary(
                enriched_wins, "source_timeframe"
            ),
            "losses_by_entry_mode": _group_summary(enriched_losses, "entry_mode"),
            "wins_by_entry_mode": _group_summary(enriched_wins, "entry_mode"),
            "losses_by_session": _group_summary(enriched_losses, "session_bucket"),
            "wins_by_session": _group_summary(enriched_wins, "session_bucket"),
            "losses_by_side": _group_summary(enriched_losses, "side"),
            "wins_by_side": _group_summary(enriched_wins, "side"),
        },
        "interpretation": [
            "Active CIBO DOL abundance is similar in winners and upstream failures; candidate availability alone does not explain failure.",
            "Upstream failures present materially farther nearest DOL geometry in R units than UNKNOWN winners.",
            "The selected destination is materially farther relative to Protected Swing risk in upstream failures.",
            "Protected Swing risk is smaller relative to entry price in upstream failures while selected target distance is larger.",
            "This is evidence of journey-capacity/geometry mismatch, not an operating threshold. Causal structural features must explain why before any rule change.",
        ],
        "governance": {
            "diagnostic_only": True,
            "no_threshold_promoted": True,
            "no_target_family_promoted": True,
            "no_timeframe_filter_promoted": True,
            "no_session_filter_promoted": True,
            "no_side_filter_promoted": True,
            "fresh_holdout_consumed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "r14-upstream-capacity-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "r14-upstream-losses-enriched.json").write_text(
        json.dumps(enriched_losses, indent=2, sort_keys=True) + "\n"
    )
    (output / "r14-unknown-wins-enriched.json").write_text(
        json.dumps(enriched_wins, indent=2, sort_keys=True) + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit("usage: module R12_ROOT R13_ROOT TARGET_ROOT OUTPUT_DIR")
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
