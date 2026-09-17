"""R13: intelligence alignment and loss forensics for R12 autonomous XAUUSD.

Consumed-evidence diagnostic only. No thresholds, routes, sessions, sides, or
timeframes are promoted to operating rules. The purpose is to distinguish:
- intelligence coverage / directive alignment;
- target-destination alignment with causal CIBO DOL evidence;
- upstream journey failure before any active DOL;
- friction sensitivity;
- execution architecture still owned by the legacy R3 router.
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

IDENTITY = "TURTLE_SOUP_XAUUSD_R13_INTELLIGENCE_ALIGNMENT_LOSS_FORENSICS_V1"
EXPECTED_R12_IDENTITY = "TURTLE_SOUP_XAUUSD_R12_AUTONOMOUS_2Y_BEHAVIOR_V2"


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


def _route_match(trade: Mapping[str, Any], candidate: Mapping[str, Any]) -> bool:
    route = str(trade["target_route"])
    if route == "SOURCE_OPPOSITE":
        return str(candidate["candidate_type"]) == "SOURCE_OPPOSITE_BOUNDARY"
    family, timeframe = route.split("_", 1)
    kind = (
        "PRIOR_CANDLE_DIRECTIONAL_BOUNDARY"
        if family == "PRIOR"
        else "ACTIVE_SWING_3_DIRECTIONAL_BOUNDARY"
    )
    return (
        str(candidate["candidate_type"]) == kind
        and str(candidate["source_timeframe"]) == timeframe
    )


def _ahead(trade: Mapping[str, Any], candidate: Mapping[str, Any]) -> bool:
    entry = _d(trade["entry"])
    price = _d(candidate["candidate_price"])
    return price > entry if str(trade["side"]) == "long" else price < entry


def _stats(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    values = [_d(row["primary_net_r"]) for row in rows]
    if not values:
        return {"trades": 0}
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    gp = sum(wins, Decimal(0))
    gl = -sum(losses, Decimal(0))
    return {
        "trades": len(rows),
        "wins": len(wins),
        "losses": len(losses),
        "total_r": str(sum(values, Decimal(0))),
        "mean_r": str(sum(values, Decimal(0)) / Decimal(len(values))),
        "profit_factor": None if gl == 0 else str(gp / gl),
        "win_rate": str(Decimal(len(wins)) / Decimal(len(values))),
    }


def _groups(rows: Sequence[dict[str, Any]], key: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row[key])].append(row)
    return {name: _stats(items) for name, items in sorted(groups.items())}


def _load_target_ledger(root: Path) -> dict[str, list[dict[str, Any]]]:
    path = _find(root, "TARGET_DESTINATION_LEDGER_V2.jsonl")
    episodes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            episodes[str(row["episode_id"])].append(row)
    return dict(episodes)


def _active_at_entry(
    trade: Mapping[str, Any],
    rows: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    entry_at = _dt(trade["entry_at"])
    assert entry_at is not None
    active: list[dict[str, Any]] = []
    for row in rows:
        known_at = _dt(row["candidate_known_at"])
        touch_at = _dt(row.get("touch_m5_opened_at"))
        if known_at is None or known_at > entry_at:
            continue
        if touch_at is not None and touch_at < entry_at:
            continue
        if not _ahead(trade, row):
            continue
        active.append(row)
    return active


def _loss_dol_diagnostic(
    trade: Mapping[str, Any],
    candidates: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    active = _active_at_entry(trade, candidates)
    exit_at = _dt(trade["exit_at"])
    assert exit_at is not None
    target = _d(trade["target"])

    selected = [
        row
        for row in active
        if _route_match(trade, row)
        and _d(row["candidate_price"]) == target
    ]
    if len(selected) != 1:
        raise ValueError(
            f"selected CIBO target join drift for {trade['episode_id']}: {len(selected)}"
        )
    selected_id = str(selected[0]["candidate_id"])
    selected_touch = _dt(selected[0].get("touch_m5_opened_at"))
    selected_touched_before_exit = (
        selected_touch is not None and selected_touch <= exit_at
    )

    alternatives = []
    entry = _d(trade["entry"])
    stop = _d(trade["stop"])
    risk = abs(entry - stop)
    for row in active:
        if str(row["candidate_id"]) == selected_id:
            continue
        touch_at = _dt(row.get("touch_m5_opened_at"))
        if touch_at is None or touch_at > exit_at:
            continue
        reward = abs(_d(row["candidate_price"]) - entry)
        alternatives.append(
            {
                "candidate_id": str(row["candidate_id"]),
                "candidate_type": str(row["candidate_type"]),
                "source_timeframe": str(row["source_timeframe"]),
                "touch_at": touch_at.isoformat(),
                "potential_r": None if risk == 0 else str(reward / risk),
            }
        )

    potential_rs = [
        _d(item["potential_r"])
        for item in alternatives
        if item["potential_r"] is not None
    ]
    return {
        "active_cibo_dol_count_at_entry": len(active),
        "selected_dol_touched_before_loss_exit": selected_touched_before_exit,
        "alternative_dol_touched_before_loss_exit": bool(alternatives),
        "alternative_touch_count": len(alternatives),
        "nearest_alternative_potential_r": (
            None if not potential_rs else str(min(potential_rs))
        ),
        "best_alternative_potential_r": (
            None if not potential_rs else str(max(potential_rs))
        ),
        "alternatives": alternatives,
    }


def run(r12_root: Path, target_root: Path, output: Path) -> dict[str, Any]:
    report = json.loads(_find(r12_root, "r12-autonomous-2y-report.json").read_text())
    trades = json.loads(_find(r12_root, "r12-autonomous-2y-trades.json").read_text())
    baseline = json.loads(_find(r12_root, "r12-canonical-r3-2y-trades.json").read_text())

    if report["identity"] != EXPECTED_R12_IDENTITY:
        raise ValueError("unexpected R12 identity")
    if len(trades) != 1132:
        raise ValueError(f"R12 trade count drift: {len(trades)}")
    if sum(_d(row["primary_net_r"]) < 0 for row in trades) != 782:
        raise ValueError("R12 loss count drift")
    if sum(_d(row["primary_net_r"]) > 0 for row in trades) != 350:
        raise ValueError("R12 win count drift")

    targets = _load_target_ledger(target_root)
    loss_rows = [row for row in trades if _d(row["primary_net_r"]) < 0]

    enriched_losses: list[dict[str, Any]] = []
    cause_counts: Counter[str] = Counter()
    alternative_potential_r: list[Decimal] = []

    for trade in loss_rows:
        episode_rows = targets.get(str(trade["episode_id"]))
        if not episode_rows:
            raise ValueError(f"missing CIBO target episode {trade['episode_id']}")
        dol = _loss_dol_diagnostic(trade, episode_rows)
        state = str(trade["r11_state"])

        if state == "CONFLICTED":
            cause = "ENGINE_ABSTAIN_CONFLICTED_OVERRIDDEN"
        elif state == "STRUCTURALLY_VALID_CANDIDATE":
            cause = "RESEARCH_NO_ENTRY_OVERRIDDEN"
        elif dol["alternative_dol_touched_before_loss_exit"]:
            cause = "UNKNOWN_SELECTED_DOL_MISALIGNED_WITH_REACHED_CIBO_DOL"
        elif dol["selected_dol_touched_before_loss_exit"]:
            cause = "UNKNOWN_INTRABAR_OR_STOP_PRECEDENCE_AROUND_SELECTED_DOL"
        else:
            cause = "UNKNOWN_UPSTREAM_JOURNEY_FAILED_BEFORE_ANY_ACTIVE_CIBO_DOL"

        cause_counts[cause] += 1
        if dol["nearest_alternative_potential_r"] is not None:
            alternative_potential_r.append(_d(dol["nearest_alternative_potential_r"]))
        enriched_losses.append({**trade, **dol, "forensic_loss_cause": cause})

    state_assessments = report["two_year_behavior"]["r11_state_assessments"]
    assessed = int(report["two_year_behavior"]["assessed_fill_opportunities"])
    unknown_assessed = int(state_assessments.get("UNKNOWN", 0))

    directives = Counter(str(row["r11_engine_directive"]) for row in trades)
    gross_total = sum((_d(row["gross_r"]) for row in trades), Decimal(0))
    primary_total = sum((_d(row["primary_net_r"]) for row in trades), Decimal(0))
    friction_paid = gross_total - primary_total

    conflicted = [row for row in trades if row["r11_state"] == "CONFLICTED"]
    unknown = [row for row in trades if row["r11_state"] == "UNKNOWN"]
    candidate = [
        row for row in trades
        if row["r11_state"] == "STRUCTURALLY_VALID_CANDIDATE"
    ]

    payload = {
        "schema": "qore.turtle_soup_xauusd_r13.intelligence_alignment_loss_forensics.v1",
        "identity": IDENTITY,
        "evidence_status": "CONSUMED_R12_2Y_AND_CIBO_TARGET_V2_DIAGNOSTIC_ONLY",
        "source": {
            "r12_identity": report["identity"],
            "r12_run_id": 35286658128,
            "r12_artifact_id": 10524382631,
            "target_destination_run_id": 35204892665,
            "target_destination_artifact_id": 10489343458,
        },
        "intelligence_coverage": {
            "assessed_fill_opportunities": assessed,
            "state_counts": state_assessments,
            "unknown_share": str(Decimal(unknown_assessed) / Decimal(assessed)),
            "decisive_known_invalid_share": str(
                Decimal(int(state_assessments.get("KNOWN_INVALID", 0)))
                / Decimal(assessed)
            ),
            "positive_operating_permission_exists": False,
            "interpretation": (
                "R11 is a partial situation-recognition layer; it does not yet "
                "provide positive operating permission for the broad market."
            ),
        },
        "directive_alignment": {
            "executed_trades": len(trades),
            "executed_by_engine_directive": dict(directives),
            "conflicted_executed_despite_abstain_directive": len(conflicted),
            "unknown_executed_despite_no_decision": len(unknown),
            "research_candidate_executed_despite_no_entry": len(candidate),
            "engine_directive_fully_obeyed_for_all_entries": False,
            "architecture_fact": (
                "R3 selects entry/route/target before R11 assessment in R12 V2; "
                "R11 can veto KNOWN_INVALID but does not choose entry, stop or DOL."
            ),
        },
        "economics": {
            "executed": _stats(trades),
            "gross_total_r": str(gross_total),
            "primary_total_r": str(primary_total),
            "friction_0p05r_total": str(friction_paid),
            "gross_mean_r_per_trade": str(gross_total / Decimal(len(trades))),
            "base_friction_r_per_trade": "0.05",
            "gross_edge_exceeds_base_friction": gross_total / Decimal(len(trades)) > Decimal("0.05"),
            "conflicted": _stats(conflicted),
            "unknown": _stats(unknown),
            "research_candidate": _stats(candidate),
            "canonical_r3_same_window": _stats(baseline),
        },
        "loss_forensics": {
            "losses": len(loss_rows),
            "causal_partition": dict(cause_counts),
            "losses_with_alternative_active_cibo_dol_reached_before_exit": sum(
                bool(row["alternative_dol_touched_before_loss_exit"])
                for row in enriched_losses
            ),
            "alternative_reached_share_of_losses": str(
                Decimal(
                    sum(
                        bool(row["alternative_dol_touched_before_loss_exit"])
                        for row in enriched_losses
                    )
                )
                / Decimal(len(loss_rows))
            ),
            "nearest_alternative_potential_r_median": (
                None
                if not alternative_potential_r
                else str(statistics.median(alternative_potential_r))
            ),
            "nearest_alternative_potential_r_ge_0p5_count": sum(
                value >= Decimal("0.5") for value in alternative_potential_r
            ),
            "nearest_alternative_potential_r_ge_1_count": sum(
                value >= Decimal("1") for value in alternative_potential_r
            ),
            "nearest_alternative_potential_r_ge_2_count": sum(
                value >= Decimal("2") for value in alternative_potential_r
            ),
        },
        "diagnostics_not_rules": {
            "by_target_route": _groups(trades, "target_route"),
            "by_source_timeframe": _groups(trades, "source_timeframe"),
            "by_side": _groups(trades, "side"),
            "by_session": _groups(trades, "session_bucket"),
            "by_entry_mode": _groups(trades, "entry_mode"),
            "by_r11_state": _groups(trades, "r11_state"),
        },
        "root_cause_conclusions": [
            "R11 coverage is incomplete: UNKNOWN dominates assessed opportunities.",
            "R12 freedom mode intentionally overrode R11 ABSTAIN_CONFLICTED and NO_DECISION semantics.",
            "R11 is downstream of R3 route selection, so the intelligence does not currently own entry/stop/target choice.",
            "A material subset of losing trades had another causal CIBO DOL reached before loss exit, indicating route/target misalignment.",
            "Most remaining UNKNOWN losses failed before any active CIBO DOL was reached, so upstream journey validity remains unresolved.",
            "Gross expectancy is positive but thinner than base friction; execution cost converts the aggregate result negative.",
        ],
        "governance": {
            "diagnostic_only": True,
            "no_rule_promoted": True,
            "no_threshold_mined": True,
            "no_session_filter_promoted": True,
            "no_side_filter_promoted": True,
            "no_timeframe_filter_promoted": True,
            "fresh_holdout_consumed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "r13-intelligence-alignment-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "r13-loss-ledger.json").write_text(
        json.dumps(enriched_losses, indent=2, sort_keys=True) + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: module R12_ROOT TARGET_ROOT OUTPUT_DIR")
    print(
        json.dumps(
            run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
