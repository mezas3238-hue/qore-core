"""Path-aware Stability Intelligence for the true-2R Capitalizer.

Unlike static feature filters, this engine reacts to the realized path that was
actually knowable before each new candidate.  It reconstructs a causal stability
state from already-closed accepted trades and changes both position protection
and opportunity pressure accordingly.

States:
- STABLE: normal execution, original 2R lifecycle.
- WATCH: deterioration is visible but not terminal; profitable M3 protection.
- DEFENSIVE: clustered loss pressure; stronger M3 structural protection and
  optional exposure/admission controls.

The variants below are fixed risk architectures expressed in R units.  They are
not fitted to the current outcomes.  Current-trade outcomes are read only after
an admission/mode decision has already been made.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_economic_rebase_2r_v1 as rebase,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_m3_stop_protection_true_2r_v2 as m3,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_STABILITY_INTELLIGENCE_2R_V1"
SOURCE_REBASE_RUN_ID = 36078677895
SOURCE_REBASE_SHA = "cfc04849c8bbfd6565310d89456f5e367ea880f7"
SOURCE_M3_RUN_ID = 36177149363
SOURCE_M3_SHA = "2d3cb599a9a6eb5566a7374e17317a43d4d6a6b0"
EXPECTED_TRADES = 948
DD_CEILING = Decimal("6")

POLICIES = (
    "MODE_SWITCH_ONLY",
    "DAY_STOP_2R",
    "SESSION_STOP_2R",
    "DAY_AND_SESSION_STOP_2R",
    "DEFENSIVE_SINGLE_ACTIVE",
    "WATCH2_DEFENSIVE1_ACTIVE",
    "DEFENSIVE_MAX1_SESSION",
    "COMPOSITE_STABILITY",
)


class StabilityState(StrEnum):
    STABLE = "STABLE"
    WATCH = "WATCH"
    DEFENSIVE = "DEFENSIVE"


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
class StabilityDecision:
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    policy: str
    state: str
    selected_mode: str
    accepted: bool
    reason: str
    closed_history: int
    path_drawdown_r: str
    recent5_r: str
    loss_streak: int
    stop_streak: int
    day_closed_r: str
    session_closed_r: str
    active_positions: int
    accepted_in_session_before: int
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
        raise ValueError("stability engine requires one true-2R rebase")
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
                rows.append(raw)
    if len(rows) != EXPECTED_TRADES:
        raise ValueError("stability engine population mismatch")
    return report, tuple(rows)


def _load_mode(root: Path, *, mode: str) -> tuple[TradeOutcome, ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-cognitive-m3-stop-protection-true-2r-v2-"
            f"{mode.lower()}-trades.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"stability engine requires 9 {mode} ledgers")
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
        sorted(result, key=lambda item: (_aware(item.entry_at, field="entry_at"), item.symbol))
    )
    if len(ordered) != EXPECTED_TRADES:
        raise ValueError(f"stability {mode} ledger must contain 948 trades")
    return ordered


def _metrics(rows: tuple[TradeOutcome, ...]) -> dict[str, Any]:
    ordered = tuple(
        sorted(rows, key=lambda item: (_aware(item.entry_at, field="entry_at"), item.symbol))
    )
    values = tuple(Decimal(item.realized_gross_r) for item in ordered)
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
        "stops": sum(item.exit_reason == "STOP" for item in ordered),
        "targets": sum(item.exit_reason == "TARGET" for item in ordered),
        "total_r": str(sum(values, Decimal("0"))),
        "profit_factor": None if gl == 0 else str(gp / gl),
        "max_drawdown_r": str(dd),
        "max_losing_streak": max_streak,
    }


def _closed_before(
    accepted: tuple[TradeOutcome, ...],
    *,
    entry_at: datetime,
) -> tuple[TradeOutcome, ...]:
    return tuple(
        sorted(
            (
                item
                for item in accepted
                if _aware(item.exit_at, field="exit_at") <= entry_at
            ),
            key=lambda item: (_aware(item.exit_at, field="exit_at"), item.symbol),
        )
    )


def _path_stats(
    history: tuple[TradeOutcome, ...],
) -> tuple[Decimal, Decimal, int, int]:
    equity = Decimal("0")
    peak = Decimal("0")
    dd = Decimal("0")
    for item in history:
        equity += Decimal(item.realized_gross_r)
        peak = max(peak, equity)
        dd = max(dd, peak - equity)

    recent = history[-5:]
    recent5 = sum((Decimal(item.realized_gross_r) for item in recent), Decimal("0"))

    loss_streak = 0
    stop_streak = 0
    for item in reversed(history):
        if Decimal(item.realized_gross_r) < 0:
            loss_streak += 1
        else:
            break
    for item in reversed(history):
        if item.exit_reason == "STOP":
            stop_streak += 1
        else:
            break
    return dd, recent5, loss_streak, stop_streak


def _state(
    history: tuple[TradeOutcome, ...],
) -> tuple[StabilityState, Decimal, Decimal, int, int]:
    dd, recent5, loss_streak, stop_streak = _path_stats(history)
    if dd >= Decimal("4") or loss_streak >= 3 or stop_streak >= 3 or recent5 <= Decimal("-3"):
        state = StabilityState.DEFENSIVE
    elif dd >= Decimal("2") or loss_streak >= 2 or stop_streak >= 2 or recent5 <= Decimal("-1.5"):
        state = StabilityState.WATCH
    else:
        state = StabilityState.STABLE
    return state, dd, recent5, loss_streak, stop_streak


def _selected_mode(state: StabilityState) -> str:
    if state is StabilityState.STABLE:
        return m3.ProtectionMode.ORIGINAL.value
    if state is StabilityState.WATCH:
        return m3.ProtectionMode.M3_PROFITABLE_SWING_LOCK.value
    return m3.ProtectionMode.M3_SWING_IMPROVE.value


def _realized_for(
    history: tuple[TradeOutcome, ...],
    *,
    operating_date: str,
    session: str | None,
) -> Decimal:
    return sum(
        (
            Decimal(item.realized_gross_r)
            for item in history
            if item.operating_date == operating_date
            and (session is None or item.session == session)
        ),
        Decimal("0"),
    )


def _active_positions(
    accepted: tuple[TradeOutcome, ...],
    *,
    entry_at: datetime,
) -> int:
    return sum(
        _aware(item.entry_at, field="entry_at") < entry_at
        and _aware(item.exit_at, field="exit_at") > entry_at
        for item in accepted
    )


def _accepted_session_before(
    accepted: tuple[TradeOutcome, ...],
    *,
    operating_date: str,
    session: str,
    entry_at: datetime,
) -> int:
    return sum(
        item.operating_date == operating_date
        and item.session == session
        and _aware(item.entry_at, field="entry_at") < entry_at
        for item in accepted
    )


def _admit(
    *,
    policy: str,
    state: StabilityState,
    day_r: Decimal,
    session_r: Decimal,
    active: int,
    accepted_session: int,
) -> tuple[bool, str]:
    if policy == "MODE_SWITCH_ONLY":
        return True, "MODE_SWITCH_ONLY"

    if policy == "DAY_STOP_2R":
        return (day_r > Decimal("-2"), "DAY_STOP_2R" if day_r <= Decimal("-2") else "ALLOW")

    if policy == "SESSION_STOP_2R":
        return (
            session_r > Decimal("-2"),
            "SESSION_STOP_2R" if session_r <= Decimal("-2") else "ALLOW",
        )

    if policy == "DAY_AND_SESSION_STOP_2R":
        blocked = day_r <= Decimal("-2") or session_r <= Decimal("-2")
        return (not blocked, "DAY_OR_SESSION_STOP_2R" if blocked else "ALLOW")

    if policy == "DEFENSIVE_SINGLE_ACTIVE":
        blocked = state is StabilityState.DEFENSIVE and active >= 1
        return (not blocked, "DEFENSIVE_SINGLE_ACTIVE" if blocked else "ALLOW")

    if policy == "WATCH2_DEFENSIVE1_ACTIVE":
        blocked = (
            (state is StabilityState.WATCH and active >= 2)
            or (state is StabilityState.DEFENSIVE and active >= 1)
        )
        return (not blocked, "STABILITY_ACTIVE_CAP" if blocked else "ALLOW")

    if policy == "DEFENSIVE_MAX1_SESSION":
        blocked = state is StabilityState.DEFENSIVE and accepted_session >= 1
        return (not blocked, "DEFENSIVE_MAX1_SESSION" if blocked else "ALLOW")

    if policy == "COMPOSITE_STABILITY":
        if day_r <= Decimal("-2"):
            return False, "COMPOSITE_DAY_STOP"
        if session_r <= Decimal("-1"):
            return False, "COMPOSITE_SESSION_STOP"
        if state is StabilityState.DEFENSIVE and active >= 1:
            return False, "COMPOSITE_DEFENSIVE_SINGLE_ACTIVE"
        if state is StabilityState.DEFENSIVE and accepted_session >= 1:
            return False, "COMPOSITE_DEFENSIVE_MAX1_SESSION"
        if state is StabilityState.WATCH and active >= 2:
            return False, "COMPOSITE_WATCH_MAX2_ACTIVE"
        return True, "ALLOW"

    raise ValueError(f"unknown stability policy: {policy}")


def _simulate(
    *,
    policy: str,
    rows: tuple[dict[str, Any], ...],
    mode_ledgers: dict[str, tuple[TradeOutcome, ...]],
) -> tuple[dict[str, Any], tuple[StabilityDecision, ...]]:
    by_mode = {
        mode: {(item.symbol, item.entry_at): item for item in ledger}
        for mode, ledger in mode_ledgers.items()
    }
    keys = {_join_key(row) for row in rows}
    if any(set(index) != keys for index in by_mode.values()):
        raise ValueError("stability rebase/mode identities differ")

    ordered_rows = tuple(
        sorted(
            rows,
            key=lambda row: (
                _aware(row["entry_at"], field="entry_at"),
                str(row["symbol"]),
            ),
        )
    )

    accepted: list[TradeOutcome] = []
    blocked_original: list[TradeOutcome] = []
    decisions: list[StabilityDecision] = []
    state_counts: dict[str, int] = {state.value: 0 for state in StabilityState}
    mode_counts: dict[str, int] = {mode: 0 for mode in mode_ledgers}

    for row in ordered_rows:
        key = _join_key(row)
        entry_at = _aware(row["entry_at"], field="entry_at")
        accepted_tuple = tuple(accepted)
        history = _closed_before(accepted_tuple, entry_at=entry_at)
        state, dd, recent5, loss_streak, stop_streak = _state(history)
        selected_mode = _selected_mode(state)
        day_r = _realized_for(
            history,
            operating_date=str(row["operating_date"]),
            session=None,
        )
        session_r = _realized_for(
            history,
            operating_date=str(row["operating_date"]),
            session=str(row["session"]),
        )
        active = _active_positions(accepted_tuple, entry_at=entry_at)
        session_count = _accepted_session_before(
            accepted_tuple,
            operating_date=str(row["operating_date"]),
            session=str(row["session"]),
            entry_at=entry_at,
        )
        allow, reason = _admit(
            policy=policy,
            state=state,
            day_r=day_r,
            session_r=session_r,
            active=active,
            accepted_session=session_count,
        )

        state_counts[state.value] += 1
        if allow:
            outcome = by_mode[selected_mode][key]
            accepted.append(outcome)
            mode_counts[selected_mode] += 1
        else:
            blocked_original.append(by_mode[m3.ProtectionMode.ORIGINAL.value][key])

        decisions.append(
            StabilityDecision(
                symbol=str(row["symbol"]),
                session=str(row["session"]),
                operating_date=str(row["operating_date"]),
                entry_at=str(row["entry_at"]),
                policy=policy,
                state=state.value,
                selected_mode=selected_mode,
                accepted=allow,
                reason=reason,
                closed_history=len(history),
                path_drawdown_r=str(dd),
                recent5_r=str(recent5),
                loss_streak=loss_streak,
                stop_streak=stop_streak,
                day_closed_r=str(day_r),
                session_closed_r=str(session_r),
                active_positions=active,
                accepted_in_session_before=session_count,
            )
        )

    kept = tuple(accepted)
    blocked = tuple(blocked_original)
    original = mode_ledgers[m3.ProtectionMode.ORIGINAL.value]
    original_metrics = _metrics(original)
    kept_metrics = _metrics(kept)
    blocked_metrics = _metrics(blocked)
    total_stops = int(original_metrics["stops"])
    total_wins = int(original_metrics["wins"])

    return {
        "policy": policy,
        "control_trades": len(original),
        "kept_trades": len(kept),
        "blocked_trades": len(blocked),
        "density_retention": str(Decimal(len(kept)) / Decimal(len(original))),
        "original_control_metrics": original_metrics,
        "kept_metrics": kept_metrics,
        "blocked_original_metrics": blocked_metrics,
        "blocked_stops": int(blocked_metrics["stops"]),
        "blocked_wins": int(blocked_metrics["wins"]),
        "stop_capture_rate": (
            "0"
            if total_stops == 0
            else str(Decimal(int(blocked_metrics["stops"])) / Decimal(total_stops))
        ),
        "winner_sacrifice_rate": (
            "0"
            if total_wins == 0
            else str(Decimal(int(blocked_metrics["wins"])) / Decimal(total_wins))
        ),
        "state_decision_counts": state_counts,
        "selected_mode_counts": mode_counts,
        "dd_at_or_below_6r": Decimal(str(kept_metrics["max_drawdown_r"])) <= DD_CEILING,
        "pf_at_least_original": (
            kept_metrics["profit_factor"] is not None
            and original_metrics["profit_factor"] is not None
            and Decimal(str(kept_metrics["profit_factor"]))
            >= Decimal(str(original_metrics["profit_factor"]))
        ),
        "total_r_at_least_original": (
            Decimal(str(kept_metrics["total_r"]))
            >= Decimal(str(original_metrics["total_r"]))
        ),
        "current_outcome_visible_to_decision": False,
    }, tuple(decisions)


def build_report(
    rebase_root: Path,
    m3_root: Path,
) -> tuple[dict[str, Any], tuple[StabilityDecision, ...]]:
    rebase_report, rows = _load_rebase(rebase_root)
    mode_ledgers = {
        mode.value: _load_mode(m3_root, mode=mode.value)
        for mode in m3.ProtectionMode
    }

    results: list[dict[str, Any]] = []
    decisions: list[StabilityDecision] = []
    for policy in POLICIES:
        result, audit = _simulate(
            policy=policy,
            rows=rows,
            mode_ledgers=mode_ledgers,
        )
        results.append(result)
        decisions.extend(audit)

    passes = tuple(
        row
        for row in results
        if row["dd_at_or_below_6r"]
        and Decimal(str(row["density_retention"])) >= Decimal("0.90")
    )
    full_passes = tuple(
        row
        for row in passes
        if row["pf_at_least_original"] and row["total_r_at_least_original"]
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
        "policy_count": len(POLICIES),
        "results": results,
        "policies_dd_at_or_below_6r_with_90pct_density": len(passes),
        "policies_full_economic_pass": len(full_passes),
        "stability_thresholds_outcome_tuned": False,
        "states_use_prior_closed_results_only": True,
        "dynamic_position_mode_selected_before_current_outcome": True,
        "current_trade_outcome_visible_to_decision": False,
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
            "FRESH_HOLDOUT_STABILITY_CANDIDATE"
            if passes
            else "ADD_CAUSAL_CROSS_MARKET_PRESSURE_TO_STABILITY_STATE"
        ),
    }, tuple(decisions)


def write_report(
    report: dict[str, Any],
    decisions: tuple[StabilityDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-cognitive-stability-intelligence-2r-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-cognitive-stability-intelligence-2r-v1-decisions.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in decisions:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rebase_root", type=Path)
    parser.add_argument("m3_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, decisions = build_report(args.rebase_root, args.m3_root)
    write_report(report, decisions, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
