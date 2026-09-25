"""True-2R simultaneous factor-collision falsification for Capitalizer.

Consumes the true-2R cognitive economic rebase and the frozen 2R third-slot
Cross-Feature report.

The lab addresses a known cognitive blind spot: two candidates with the exact
same decision timestamp do not see one another as prior active exposure. If they
share an underlying factor in the same economic direction, cognition should at
least recognize that they compete before both tickets become exposure.

This lab does NOT choose or promote a runtime rule. It evaluates deterministic,
outcome-blind tie controls and reports the residual max-drawdown episode after
each control, standalone and combined with one frozen consumed-window third-slot
development hypothesis.

No current-trade outcome is visible to collision detection or tie-breaking.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
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
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_preentry_stop_risk_atlas_2y_v1 as stoprisk_v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_simultaneous_factor_collision_atlas_2y_v1 as collision_v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_third_slot_journey_atlas_2r_v1 as journey_2r,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_SIMULTANEOUS_FACTOR_COLLISION_ATLAS_2R_V1"
SOURCE_REBASE_RUN_ID = 36078677895
SOURCE_REBASE_SHA = "cfc04849c8bbfd6565310d89456f5e367ea880f7"
SOURCE_CROSS_RUN_ID = 36083458303
SOURCE_CROSS_SHA = "dbbef8abd9a75ab08da577dcf2e390e755b2f1fe"

THIRD_SLOT_JOURNEY_FEATURE = "PRIOR_SESSION_REALIZED_SIGN"
THIRD_SLOT_JOURNEY_VALUE = "NEGATIVE"
THIRD_SLOT_PREENTRY_FEATURE = "ENTRY_MODE"
THIRD_SLOT_PREENTRY_VALUE = "OB_FVG_RETEST"


@dataclass(frozen=True, slots=True)
class DrawdownEpisode:
    max_drawdown_r: str
    peak_equity_r: str
    trough_equity_r: str
    peak_after_entry_at: str | None
    trough_after_entry_at: str | None
    trough_symbol: str | None
    drawdown_trade_count: int
    drawdown_stops: int
    drawdown_losses: int


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
        raise ValueError("2R collision atlas requires one rebase artifact")
    report = json.loads(report_paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != rebase.IDENTITY:
        raise ValueError("unexpected 2R rebase identity")
    if str(report.get("target_r")) != "2.00":
        raise ValueError("2R collision atlas requires true 2R rebase")

    rows: list[dict[str, Any]] = []
    with row_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("2R rebase row must be object")
                rows.append(raw)
    if len(rows) != rebase.EXPECTED_TRADES:
        raise ValueError("2R collision atlas population mismatch")
    return report, tuple(rows)


def _load_cross_reference(root: Path) -> dict[str, Any]:
    paths = sorted(
        root.rglob("capitalizer-cognitive-third-slot-cross-feature-atlas-2r-v1.json")
    )
    if len(paths) != 1:
        raise ValueError("2R collision atlas requires one cross-feature artifact")
    report = json.loads(paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise ValueError("2R cross-feature report must be object")

    matches = [
        row
        for row in report.get("cells", ())
        if row.get("journey_feature") == THIRD_SLOT_JOURNEY_FEATURE
        and row.get("journey_value") == THIRD_SLOT_JOURNEY_VALUE
        and row.get("preentry_feature") == THIRD_SLOT_PREENTRY_FEATURE
        and row.get("preentry_value") == THIRD_SLOT_PREENTRY_VALUE
    ]
    if len(matches) != 1:
        raise ValueError("2R third-slot development cell must be unique")
    return dict(matches[0])


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


def _cell_map(cells: tuple[tuple[str, str], ...]) -> dict[str, str]:
    result = dict(cells)
    if len(result) != len(cells):
        raise ValueError("duplicate causal cell name")
    return result


def _third_slot_drop_keys(
    rows: tuple[dict[str, Any], ...],
    control: tuple[dict[str, Any], ...],
) -> frozenset[tuple[str, str]]:
    by_key = {_join_key(row): row for row in rows}
    selected: set[tuple[str, str]] = set()
    for trade in control:
        row = by_key[_join_key(trade)]
        if int(row["prior_same_session_selected"]) != 2:
            continue
        journey_cells = _cell_map(
            journey_2r._causal_cells(
                candidate=trade,
                rebase_row=row,
                control=control,
            )
        )
        preentry_cells = _cell_map(stoprisk_v1._causal_cells(row))
        if (
            journey_cells[THIRD_SLOT_JOURNEY_FEATURE]
            == THIRD_SLOT_JOURNEY_VALUE
            and preentry_cells[THIRD_SLOT_PREENTRY_FEATURE]
            == THIRD_SLOT_PREENTRY_VALUE
        ):
            selected.add(_join_key(trade))
    return frozenset(selected)


def _build_clusters(
    rows: tuple[dict[str, Any], ...],
) -> tuple[collision_v1.CollisionCluster, ...]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["session"]), str(row["entry_at"]))].append(row)

    clusters: list[collision_v1.CollisionCluster] = []
    for (session, entry_at), raw_rows in sorted(grouped.items()):
        if len(raw_rows) < 2:
            continue
        ordered = tuple(sorted(raw_rows, key=lambda item: str(item["symbol"])))
        factors = collision_v1._shared_same_direction_factors(ordered)
        if not factors:
            continue
        candidates: list[collision_v1.CollisionCandidate] = []
        for row in ordered:
            mss, fvg = collision_v1._mss_fvg(row)
            candidates.append(
                collision_v1.CollisionCandidate(
                    symbol=str(row["symbol"]),
                    session=session,
                    side=str(row["side"]),
                    entry_at=entry_at,
                    mss_at=mss.isoformat(),
                    fvg_at=fvg.isoformat(),
                )
            )
        clusters.append(
            collision_v1.CollisionCluster(
                entry_at=entry_at,
                session=session,
                shared_same_direction_factors=factors,
                candidates=tuple(candidates),
            )
        )
    return tuple(clusters)


def _collision_drop_keys(
    clusters: tuple[collision_v1.CollisionCluster, ...],
    *,
    policy: str,
) -> frozenset[tuple[str, str]]:
    dropped: set[tuple[str, str]] = set()
    for cluster in clusters:
        keep = collision_v1._winner(cluster, policy)
        for candidate in cluster.candidates:
            if candidate != keep:
                dropped.add((candidate.symbol, candidate.entry_at))
    return frozenset(dropped)


def _apply_drop(
    control: tuple[dict[str, Any], ...],
    drop: frozenset[tuple[str, str]],
) -> tuple[dict[str, Any], ...]:
    return tuple(row for row in control if _join_key(row) not in drop)


def _drawdown_episode(
    rows: tuple[dict[str, Any], ...],
) -> DrawdownEpisode:
    ordered = tuple(
        sorted(rows, key=lambda row: (_aware(row["entry_at"]), str(row["symbol"])))
    )
    equity = Decimal("0")
    peak = Decimal("0")
    max_dd = Decimal("0")
    peak_index = -1
    max_peak_index = -1
    trough_index = -1
    trough_equity = Decimal("0")

    for index, row in enumerate(ordered):
        equity += Decimal(str(row["realized_gross_r"]))
        if equity > peak:
            peak = equity
            peak_index = index
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
            max_peak_index = peak_index
            trough_index = index
            trough_equity = equity

    start = max_peak_index + 1
    episode_rows = (
        ordered[start : trough_index + 1]
        if trough_index >= 0 and start <= trough_index
        else ()
    )
    peak_at = None
    if max_peak_index >= 0:
        peak_at = str(ordered[max_peak_index]["entry_at"])
    trough_at = None
    trough_symbol = None
    if trough_index >= 0:
        trough_at = str(ordered[trough_index]["entry_at"])
        trough_symbol = str(ordered[trough_index]["symbol"])

    return DrawdownEpisode(
        max_drawdown_r=str(max_dd),
        peak_equity_r=str(
            Decimal("0")
            if max_peak_index < 0
            else sum(
                (
                    Decimal(str(row["realized_gross_r"]))
                    for row in ordered[: max_peak_index + 1]
                ),
                Decimal("0"),
            )
        ),
        trough_equity_r=str(trough_equity),
        peak_after_entry_at=peak_at,
        trough_after_entry_at=trough_at,
        trough_symbol=trough_symbol,
        drawdown_trade_count=len(episode_rows),
        drawdown_stops=sum(
            str(row["exit_reason"]) == "STOP" for row in episode_rows
        ),
        drawdown_losses=sum(
            Decimal(str(row["realized_gross_r"])) < 0 for row in episode_rows
        ),
    )


def build_report(
    rebase_root: Path,
    cross_root: Path,
) -> dict[str, Any]:
    rebase_report, rows = _load_rebase(rebase_root)
    cross_reference = _load_cross_reference(cross_root)
    control = tuple(_trade(row) for row in rows)
    third_slot_drop = _third_slot_drop_keys(rows, control)
    if len(third_slot_drop) != int(cross_reference["third_slot_trades"]):
        raise ValueError("2R third-slot hypothesis does not reproduce cross cell")

    clusters = _build_clusters(rows)
    factor_counts = Counter(
        factor
        for cluster in clusters
        for factor in cluster.shared_same_direction_factors
    )

    policies: list[dict[str, Any]] = []
    for policy in collision_v1.POLICIES:
        collision_drop = _collision_drop_keys(clusters, policy=policy)
        combined_drop = frozenset((*third_slot_drop, *collision_drop))
        standalone = _apply_drop(control, collision_drop)
        combined = _apply_drop(control, combined_drop)
        policies.append(
            {
                "policy": policy,
                "collision_dropped_trades": len(collision_drop),
                "standalone_metrics": stoprisk_2r._metrics(standalone),
                "standalone_drawdown_episode": _drawdown_episode(standalone).__dict__,
                "combined_dropped_trades": len(combined_drop),
                "combined_metrics": stoprisk_2r._metrics(combined),
                "combined_drawdown_episode": _drawdown_episode(combined).__dict__,
                "combined_density_retention": str(
                    Decimal(len(combined)) / Decimal(len(control))
                ),
            }
        )

    clusters_report = []
    for cluster in clusters:
        outcomes = []
        for candidate in cluster.candidates:
            trade = next(
                item
                for item in control
                if str(item["symbol"]) == candidate.symbol
                and str(item["entry_at"]) == candidate.entry_at
            )
            outcomes.append(
                {
                    "symbol": candidate.symbol,
                    "post_audit_realized_gross_r": trade["realized_gross_r"],
                    "post_audit_exit_reason": trade["exit_reason"],
                }
            )
        clusters_report.append(
            {
                "entry_at": cluster.entry_at,
                "session": cluster.session,
                "shared_same_direction_factors": (
                    cluster.shared_same_direction_factors
                ),
                "candidates": tuple(
                    {
                        "symbol": item.symbol,
                        "side": item.side,
                        "mss_at": item.mss_at,
                        "fvg_at": item.fvg_at,
                    }
                    for item in cluster.candidates
                ),
                "post_audit_outcomes": tuple(outcomes),
            }
        )

    return {
        "identity": IDENTITY,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "source_cross_run_id": SOURCE_CROSS_RUN_ID,
        "source_cross_sha": SOURCE_CROSS_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": "2.00",
        "control_trades": len(control),
        "control_metrics": stoprisk_2r._metrics(control),
        "control_drawdown_episode": _drawdown_episode(control).__dict__,
        "third_slot_reference": {
            "journey_feature": THIRD_SLOT_JOURNEY_FEATURE,
            "journey_value": THIRD_SLOT_JOURNEY_VALUE,
            "preentry_feature": THIRD_SLOT_PREENTRY_FEATURE,
            "preentry_value": THIRD_SLOT_PREENTRY_VALUE,
            "trades": len(third_slot_drop),
            "cross_feature_counterfactual_metrics": cross_reference[
                "full_portfolio_if_abstained_metrics"
            ],
            "development_hypothesis_only": True,
            "runtime_rule_selected": False,
        },
        "collision_cluster_count": len(clusters),
        "collision_candidate_count": sum(
            len(cluster.candidates) for cluster in clusters
        ),
        "collision_factor_counts": dict(sorted(factor_counts.items())),
        "collision_clusters": clusters_report,
        "same_timestamp_candidates_compete_before_active_exposure_exists": True,
        "all_collision_evidence_known_by_entry": True,
        "policy_count": len(policies),
        "policies": policies,
        "all_policies_outcome_blind": True,
        "outcomes_used_only_for_post_audit_metrics": True,
        "collision_policy_selected": False,
        "combined_rule_selected": False,
        "automatic_promotion_allowed": False,
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
        "next_phase": "FALSIFY_2R_COLLISION_INFORMATION_VALUE_AND_RESIDUAL_DD",
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output
        / "capitalizer-cognitive-simultaneous-factor-collision-atlas-2r-v1.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rebase_root", type=Path)
    parser.add_argument("cross_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_report(args.rebase_root, args.cross_root)
    write_report(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
