"""Prequential causal-memory engine for the true-2R Capitalizer.

This laboratory is intentionally economic, not a test-oriented patch.  It
evaluates an online decision engine that can only learn from trades that were
already CLOSED before the current candidate arrived.

The engine combines:
- source/microstructure identity;
- session/side/provenance;
- session journey and slot state;
- portfolio factor state;
- prior realized day state;
- causal categorical microstructure observations;
- optional true-2R M3 position-protection outcomes.

No current/future outcome is used to decide the current trade.  Blocked trades
do not enter memory.  Therefore each policy is a genuine prequential path rather
than a retrospective filter over the final ledger.

The study exposes several fixed, hypothesis-driven policies.  It does not tune
thresholds on the current outcomes and does not promote a winner automatically.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_economic_rebase_2r_v1 as rebase,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_m3_stop_protection_true_2r_v2 as m3,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_ONLINE_CAUSAL_MEMORY_2R_V1"
SOURCE_REBASE_RUN_ID = 36078677895
SOURCE_REBASE_SHA = "cfc04849c8bbfd6565310d89456f5e367ea880f7"
SOURCE_M3_RUN_ID = 36177149363
SOURCE_M3_SHA = "2d3cb599a9a6eb5566a7374e17317a43d4d6a6b0"

EXPECTED_TRADES = 948
MIN_GLOBAL_HISTORY = 24
MIN_CELL_HISTORY = 10
PRIOR_STRENGTH = Decimal("12")
NEGATIVE_STOP_EDGE = Decimal("0.05")
STRONG_NEGATIVE_MEAN_R = Decimal("-0.10")
KNN_MIN_HISTORY = 8
KNN_TOP_K = 15
KNN_MIN_SIMILARITY = Decimal("0.40")
DD_CEILING = Decimal("6")

ALLOWED_OBSERVATION_PREFIXES = (
    "LIQUIDITY_SOURCE:",
    "LIQUIDITY_KIND:",
    "ENTRY_MODE:",
    "M1_OB_FVG_OVERLAP:",
    "RECOVERY_SOURCE:",
    "WAIT5_ARMED:",
    "ORIGINAL_TERMINAL_REASON:",
    "PROTECTED_AT_MSS_STOP_VALID:",
    "REARM_STOP_VALID:",
)

POLICIES = (
    "BASELINE",
    "CONSENSUS_2",
    "CONSENSUS_3",
    "CONSENSUS_4",
    "THIRD_SLOT_CONSENSUS_2",
    "ADVERSE_DAY_CONSENSUS_2",
    "KNN_NEGATIVE",
    "HYBRID_CONSENSUS3_KNN",
)

MODES = (
    m3.ProtectionMode.ORIGINAL.value,
    m3.ProtectionMode.M3_SWING_IMPROVE.value,
    m3.ProtectionMode.M3_PROFITABLE_SWING_LOCK.value,
)


@dataclass(frozen=True, slots=True)
class TradeOutcome:
    symbol: str
    session: str
    operating_date: str
    side: str
    entry_at: str
    exit_at: str
    realized_gross_r: str
    exit_reason: str
    mode: str


@dataclass(frozen=True, slots=True)
class DecisionAudit:
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    mode: str
    policy: str
    accepted: bool
    reason: str
    feature_count: int
    mature_feature_count: int
    negative_cell_count: int
    strong_negative_cell_count: int
    posterior_mean_median_r: str | None
    knn_neighbors: int
    knn_mean_r: str | None
    knn_stop_rate: str | None
    global_closed_history: int
    global_prior_mean_r: str | None
    global_prior_stop_rate: str | None
    current_outcome_visible_to_decision: bool = False


def _aware(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be timestamp string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed


def _join_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["symbol"]), str(row["entry_at"])


def _load_rebase(root: Path) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    reports = sorted(root.rglob("capitalizer-cognitive-economic-rebase-2r-v1.json"))
    rows_paths = sorted(
        root.rglob("capitalizer-cognitive-economic-rebase-2r-v1-rows.jsonl")
    )
    if len(reports) != 1 or len(rows_paths) != 1:
        raise ValueError("online causal memory requires one true-2R rebase")
    report = json.loads(reports[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != rebase.IDENTITY:
        raise ValueError("unexpected true-2R rebase identity")
    rows: list[dict[str, Any]] = []
    with rows_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("rebase row must be object")
                if raw.get("current_outcome_visible_to_cognitive_state") is not False:
                    raise ValueError("rebase row exposes current outcome to cognition")
                rows.append(raw)
    if len(rows) != EXPECTED_TRADES:
        raise ValueError("online causal memory population mismatch")
    return report, tuple(rows)


def _load_m3_mode(root: Path, *, mode: str) -> tuple[TradeOutcome, ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-cognitive-m3-stop-protection-true-2r-v2-"
            f"{mode.lower()}-trades.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"online causal memory requires 9 {mode} M3 ledgers")
    result: list[TradeOutcome] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                raw = json.loads(line)
                result.append(
                    TradeOutcome(
                        symbol=str(raw["symbol"]),
                        session=str(raw["session"]),
                        operating_date=str(raw["operating_date"]),
                        side=str(raw["side"]),
                        entry_at=str(raw["entry_at"]),
                        exit_at=str(raw["exit_at"]),
                        realized_gross_r=str(raw["realized_gross_r"]),
                        exit_reason=str(raw["exit_reason"]),
                        mode=str(raw["mode"]),
                    )
                )
    ordered = tuple(
        sorted(
            result,
            key=lambda item: (_aware(item.entry_at, field="entry_at"), item.symbol),
        )
    )
    if len(ordered) != EXPECTED_TRADES:
        raise ValueError(f"online causal memory {mode} ledger must contain 948 trades")
    return ordered


def _count_bucket(value: int) -> str:
    if value <= 0:
        return "0"
    if value == 1:
        return "1"
    if value == 2:
        return "2"
    return "3_PLUS"


def _sign(value: Decimal) -> str:
    if value > 0:
        return "POSITIVE"
    if value < 0:
        return "NEGATIVE"
    return "ZERO"


def _features(row: dict[str, Any]) -> frozenset[str]:
    features: set[str] = {
        f"SYMBOL={row['symbol']}",
        f"SESSION={row['session']}",
        f"SIDE={row['side']}",
        f"PROVENANCE={row['provenance']}",
        f"SOURCE_FAMILY={row.get('source_microstructure_family')}",
        f"SLOT={int(row['prior_same_session_selected'])}",
        f"ACTIVE_POS={_count_bucket(int(row['baseline_active_positions']))}",
        f"PRIOR_CLOSED={_count_bucket(int(row['prior_closed_trades_today']))}",
        f"PRIOR_REALIZED_SIGN={_sign(Decimal(str(row['prior_realized_r_today'])))}",
    }
    completed = tuple(str(item) for item in row.get("completed_prior_sessions", ()))
    features.add(f"COMPLETED_SESSIONS={'>'.join(completed) if completed else 'NONE'}")

    shared = tuple(str(item) for item in row.get("baseline_shared_factors", ()))
    same = tuple(str(item) for item in row.get("baseline_same_direction_factors", ()))
    opposing = tuple(str(item) for item in row.get("baseline_opposing_direction_factors", ()))
    features.add(f"SHARED_FACTOR_COUNT={_count_bucket(len(shared))}")
    features.add(f"SAME_FACTOR_COUNT={_count_bucket(len(same))}")
    features.add(f"OPPOSING_FACTOR_COUNT={_count_bucket(len(opposing))}")
    for token in shared:
        features.add(f"SHARED_FACTOR={token}")
    for token in same:
        features.add(f"SAME_FACTOR={token}")
    for token in opposing:
        features.add(f"OPPOSING_FACTOR={token}")

    for raw in row.get("microstructure_observations", ()):
        token = str(raw)
        if token.startswith(ALLOWED_OBSERVATION_PREFIXES):
            features.add(f"MICRO={token}")
    return frozenset(features)


def _metrics(rows: tuple[TradeOutcome, ...]) -> dict[str, Any]:
    ordered = tuple(
        sorted(rows, key=lambda row: (_aware(row.entry_at, field="entry_at"), row.symbol))
    )
    values = tuple(Decimal(row.realized_gross_r) for row in ordered)
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
        "trades": len(ordered),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "stops": sum(row.exit_reason == "STOP" for row in ordered),
        "targets": sum(row.exit_reason == "TARGET" for row in ordered),
        "total_r": str(sum(values, Decimal("0"))),
        "profit_factor": None if gl == 0 else str(gp / gl),
        "max_drawdown_r": str(dd),
        "max_losing_streak": max_streak,
    }


def _history_stats(
    history: tuple[TradeOutcome, ...],
) -> tuple[Decimal, Decimal]:
    values = tuple(Decimal(item.realized_gross_r) for item in history)
    mean_r = sum(values, Decimal("0")) / Decimal(len(values))
    stop_rate = Decimal(sum(item.exit_reason == "STOP" for item in history)) / Decimal(
        len(history)
    )
    return mean_r, stop_rate


def _cell_posteriors(
    *,
    features: frozenset[str],
    feature_by_key: dict[tuple[str, str], frozenset[str]],
    history: tuple[TradeOutcome, ...],
    global_mean: Decimal,
    global_stop: Decimal,
) -> tuple[tuple[Decimal, Decimal, int, str], ...]:
    result: list[tuple[Decimal, Decimal, int, str]] = []
    for feature in sorted(features):
        selected = tuple(
            item
            for item in history
            if feature in feature_by_key[(item.symbol, item.entry_at)]
        )
        if len(selected) < MIN_CELL_HISTORY:
            continue
        values = tuple(Decimal(item.realized_gross_r) for item in selected)
        stops = sum(item.exit_reason == "STOP" for item in selected)
        denom = PRIOR_STRENGTH + Decimal(len(selected))
        posterior_mean = (
            PRIOR_STRENGTH * global_mean + sum(values, Decimal("0"))
        ) / denom
        posterior_stop = (
            PRIOR_STRENGTH * global_stop + Decimal(stops)
        ) / denom
        result.append((posterior_mean, posterior_stop, len(selected), feature))
    return tuple(result)


def _knn(
    *,
    current_features: frozenset[str],
    feature_by_key: dict[tuple[str, str], frozenset[str]],
    history: tuple[TradeOutcome, ...],
) -> tuple[int, Decimal | None, Decimal | None]:
    neighbors: list[tuple[Decimal, TradeOutcome]] = []
    for item in history:
        prior_features = feature_by_key[(item.symbol, item.entry_at)]
        union = len(current_features | prior_features)
        if union == 0:
            continue
        similarity = Decimal(len(current_features & prior_features)) / Decimal(union)
        if similarity >= KNN_MIN_SIMILARITY:
            neighbors.append((similarity, item))
    neighbors.sort(
        key=lambda pair: (
            pair[0],
            _aware(pair[1].exit_at, field="exit_at"),
        ),
        reverse=True,
    )
    chosen = tuple(item for _, item in neighbors[:KNN_TOP_K])
    if len(chosen) < KNN_MIN_HISTORY:
        return len(chosen), None, None
    mean_r, stop_rate = _history_stats(chosen)
    return len(chosen), mean_r, stop_rate


def _decision(
    *,
    policy: str,
    row: dict[str, Any],
    features: frozenset[str],
    feature_by_key: dict[tuple[str, str], frozenset[str]],
    history: tuple[TradeOutcome, ...],
) -> DecisionAudit:
    if policy == "BASELINE":
        return DecisionAudit(
            symbol=str(row["symbol"]),
            session=str(row["session"]),
            operating_date=str(row["operating_date"]),
            entry_at=str(row["entry_at"]),
            mode="",
            policy=policy,
            accepted=True,
            reason="BASELINE_ACCEPT",
            feature_count=len(features),
            mature_feature_count=0,
            negative_cell_count=0,
            strong_negative_cell_count=0,
            posterior_mean_median_r=None,
            knn_neighbors=0,
            knn_mean_r=None,
            knn_stop_rate=None,
            global_closed_history=len(history),
            global_prior_mean_r=None,
            global_prior_stop_rate=None,
        )

    if len(history) < MIN_GLOBAL_HISTORY:
        return DecisionAudit(
            symbol=str(row["symbol"]),
            session=str(row["session"]),
            operating_date=str(row["operating_date"]),
            entry_at=str(row["entry_at"]),
            mode="",
            policy=policy,
            accepted=True,
            reason="INSUFFICIENT_GLOBAL_HISTORY",
            feature_count=len(features),
            mature_feature_count=0,
            negative_cell_count=0,
            strong_negative_cell_count=0,
            posterior_mean_median_r=None,
            knn_neighbors=0,
            knn_mean_r=None,
            knn_stop_rate=None,
            global_closed_history=len(history),
            global_prior_mean_r=None,
            global_prior_stop_rate=None,
        )

    global_mean, global_stop = _history_stats(history)
    cells = _cell_posteriors(
        features=features,
        feature_by_key=feature_by_key,
        history=history,
        global_mean=global_mean,
        global_stop=global_stop,
    )
    negative = tuple(
        cell
        for cell in cells
        if cell[0] < 0 and cell[1] >= global_stop + NEGATIVE_STOP_EDGE
    )
    strong = tuple(
        cell
        for cell in cells
        if cell[0] <= STRONG_NEGATIVE_MEAN_R
        and cell[1] >= global_stop + NEGATIVE_STOP_EDGE
    )
    posterior_median = None
    if cells:
        posterior_median = Decimal(str(median([float(cell[0]) for cell in cells])))

    knn_n, knn_mean, knn_stop = _knn(
        current_features=features,
        feature_by_key=feature_by_key,
        history=history,
    )
    knn_negative = (
        knn_n >= KNN_MIN_HISTORY
        and knn_mean is not None
        and knn_stop is not None
        and knn_mean < 0
        and knn_stop >= global_stop + NEGATIVE_STOP_EDGE
    )

    accepted = True
    reason = "NO_NEGATIVE_CAUSAL_CONSENSUS"
    if policy == "CONSENSUS_2":
        accepted = len(negative) < 2
        reason = "NEGATIVE_CELL_CONSENSUS_2" if not accepted else reason
    elif policy == "CONSENSUS_3":
        accepted = len(negative) < 3
        reason = "NEGATIVE_CELL_CONSENSUS_3" if not accepted else reason
    elif policy == "CONSENSUS_4":
        accepted = len(negative) < 4
        reason = "NEGATIVE_CELL_CONSENSUS_4" if not accepted else reason
    elif policy == "THIRD_SLOT_CONSENSUS_2":
        active = int(row["prior_same_session_selected"]) >= 2
        accepted = not (active and len(negative) >= 2)
        reason = "THIRD_SLOT_NEGATIVE_CONSENSUS" if not accepted else reason
    elif policy == "ADVERSE_DAY_CONSENSUS_2":
        adverse = Decimal(str(row["prior_realized_r_today"])) < 0
        accepted = not (adverse and len(negative) >= 2)
        reason = "ADVERSE_DAY_NEGATIVE_CONSENSUS" if not accepted else reason
    elif policy == "KNN_NEGATIVE":
        accepted = not knn_negative
        reason = "KNN_NEGATIVE_EXPECTANCY" if not accepted else reason
    elif policy == "HYBRID_CONSENSUS3_KNN":
        accepted = not (len(negative) >= 3 and knn_negative)
        reason = "CONSENSUS3_AND_KNN_NEGATIVE" if not accepted else reason
    else:
        raise ValueError(f"unknown online causal memory policy: {policy}")

    return DecisionAudit(
        symbol=str(row["symbol"]),
        session=str(row["session"]),
        operating_date=str(row["operating_date"]),
        entry_at=str(row["entry_at"]),
        mode="",
        policy=policy,
        accepted=accepted,
        reason=reason,
        feature_count=len(features),
        mature_feature_count=len(cells),
        negative_cell_count=len(negative),
        strong_negative_cell_count=len(strong),
        posterior_mean_median_r=None if posterior_median is None else str(posterior_median),
        knn_neighbors=knn_n,
        knn_mean_r=None if knn_mean is None else str(knn_mean),
        knn_stop_rate=None if knn_stop is None else str(knn_stop),
        global_closed_history=len(history),
        global_prior_mean_r=str(global_mean),
        global_prior_stop_rate=str(global_stop),
    )


def _simulate_policy(
    *,
    policy: str,
    mode: str,
    rebase_rows: tuple[dict[str, Any], ...],
    outcomes: tuple[TradeOutcome, ...],
) -> tuple[dict[str, Any], tuple[DecisionAudit, ...], tuple[TradeOutcome, ...]]:
    row_by_key = {_join_key(row): row for row in rebase_rows}
    outcome_by_key = {(row.symbol, row.entry_at): row for row in outcomes}
    if set(row_by_key) != set(outcome_by_key):
        raise ValueError("online causal memory rebase/outcome identities differ")
    feature_by_key = {key: _features(row) for key, row in row_by_key.items()}

    ordered_keys = sorted(
        row_by_key,
        key=lambda key: (_aware(key[1], field="entry_at"), key[0]),
    )
    accepted: list[TradeOutcome] = []
    blocked: list[TradeOutcome] = []
    audits: list[DecisionAudit] = []

    for key in ordered_keys:
        row = row_by_key[key]
        outcome = outcome_by_key[key]
        entry_at = _aware(outcome.entry_at, field="entry_at")
        closed_history = tuple(
            item
            for item in accepted
            if _aware(item.exit_at, field="exit_at") <= entry_at
        )
        decision = _decision(
            policy=policy,
            row=row,
            features=feature_by_key[key],
            feature_by_key=feature_by_key,
            history=closed_history,
        )
        decision = DecisionAudit(
            **{
                **asdict(decision),
                "mode": mode,
            }
        )
        audits.append(decision)
        if decision.accepted:
            accepted.append(outcome)
        else:
            blocked.append(outcome)

    kept = tuple(accepted)
    rejected = tuple(blocked)
    control_metrics = _metrics(outcomes)
    kept_metrics = _metrics(kept)
    blocked_metrics = _metrics(rejected)
    total_stops = int(control_metrics["stops"])
    total_wins = int(control_metrics["wins"])
    blocked_stops = int(blocked_metrics["stops"])
    blocked_wins = int(blocked_metrics["wins"])

    report = {
        "policy": policy,
        "mode": mode,
        "control_trades": len(outcomes),
        "kept_trades": len(kept),
        "blocked_trades": len(rejected),
        "density_retention": str(Decimal(len(kept)) / Decimal(len(outcomes))),
        "control_metrics": control_metrics,
        "kept_metrics": kept_metrics,
        "blocked_metrics": blocked_metrics,
        "blocked_stops": blocked_stops,
        "blocked_wins": blocked_wins,
        "stop_capture_rate": (
            "0" if total_stops == 0 else str(Decimal(blocked_stops) / Decimal(total_stops))
        ),
        "winner_sacrifice_rate": (
            "0" if total_wins == 0 else str(Decimal(blocked_wins) / Decimal(total_wins))
        ),
        "dd_at_or_below_6r": Decimal(str(kept_metrics["max_drawdown_r"])) <= DD_CEILING,
        "pf_at_least_control": (
            kept_metrics["profit_factor"] is not None
            and control_metrics["profit_factor"] is not None
            and Decimal(str(kept_metrics["profit_factor"]))
            >= Decimal(str(control_metrics["profit_factor"]))
        ),
        "total_r_at_least_control": (
            Decimal(str(kept_metrics["total_r"]))
            >= Decimal(str(control_metrics["total_r"]))
        ),
        "decision_outcome_leakage": False,
    }
    return report, tuple(audits), kept


def build_report(
    rebase_root: Path,
    m3_root: Path,
) -> tuple[dict[str, Any], tuple[DecisionAudit, ...]]:
    rebase_report, rows = _load_rebase(rebase_root)
    modes = {mode: _load_m3_mode(m3_root, mode=mode) for mode in MODES}

    all_audits: list[DecisionAudit] = []
    results: list[dict[str, Any]] = []
    for mode in MODES:
        for policy in POLICIES:
            result, audits, _kept = _simulate_policy(
                policy=policy,
                mode=mode,
                rebase_rows=rows,
                outcomes=modes[mode],
            )
            results.append(result)
            all_audits.extend(audits)

    baseline_original = next(
        row
        for row in results
        if row["mode"] == m3.ProtectionMode.ORIGINAL.value
        and row["policy"] == "BASELINE"
    )
    successful = tuple(
        row
        for row in results
        if bool(row["dd_at_or_below_6r"])
        and bool(row["pf_at_least_control"])
    )
    high_density = tuple(
        row
        for row in successful
        if Decimal(str(row["density_retention"])) >= Decimal("0.90")
    )

    return {
        "identity": IDENTITY,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "source_m3_run_id": SOURCE_M3_RUN_ID,
        "source_m3_sha": SOURCE_M3_SHA,
        "development_window_role": "PREQUENTIAL_CONSUMED_LABORATORY",
        "target_r": "2.00",
        "control_trades": len(rows),
        "baseline_original_metrics": baseline_original["control_metrics"],
        "policy_count": len(POLICIES),
        "position_mode_count": len(MODES),
        "result_count": len(results),
        "results": results,
        "policies_at_or_below_6r_and_pf_at_least_control": len(successful),
        "high_density_90pct_policies_at_or_below_6r_and_pf_at_least_control": len(
            high_density
        ),
        "prequential_only_prior_closed_outcomes": True,
        "blocked_trades_do_not_enter_memory": True,
        "current_trade_outcome_visible_to_decision": False,
        "feature_thresholds_outcome_tuned": False,
        "automatic_policy_selection": False,
        "runtime_rule_selected": False,
        "fresh_holdout_required_after_candidate_selection": True,
        "rebase_control_reproduced": (
            int(rebase_report["control_trades"]) == len(rows)
        ),
        "strategy_rules_changed": False,
        "entry_geometry_changed": False,
        "original_stop_geometry_changed": False,
        "target_changed": False,
        "max3_changed": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "CROSS_VALIDATE_ANY_PARETO_CANDIDATE_ON_FRESH_HOLDOUT"
            if successful
            else "ENGINEER_NEXT_CAUSAL_STATE_REPRESENTATION_NOT_MORE_STATIC_FILTERS"
        ),
    }, tuple(all_audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[DecisionAudit, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-cognitive-online-causal-memory-2r-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-cognitive-online-causal-memory-2r-v1-decisions.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in audits:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rebase_root", type=Path)
    parser.add_argument("m3_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, audits = build_report(args.rebase_root, args.m3_root)
    write_report(report, audits, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
