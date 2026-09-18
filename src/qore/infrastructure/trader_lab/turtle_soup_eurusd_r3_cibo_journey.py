"""Turtle Soup EURUSD R3: CIBO journey router, not a context filter.

Turtle Soup defines the causal setup (prior-candle liquidity raid, exact C2 and
causal CISD). CIBO is used to route execution: entry mechanism, structural
invalidation and an active Draw-On-Liquidity family. Context never votes a
setup in/out through a positive-score threshold. The 10Y CIBO corpus is already
consumed evidence: 2016-09-17..2022-09-17 fits the route map and
2022-09-17..2026-09-17 is internal temporal validation only.
"""
from __future__ import annotations

import bisect
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import cibo_market_atlas_journey_extractor_v1 as journey
from qore.infrastructure.trader_lab import turtle_soup_eurusd_r1 as r1
from qore.infrastructure.trader_lab import turtle_soup_eurusd_r2_cibo_full as r2
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Side,
    SourceCandle,
    build_h1,
    build_h4,
    build_m15,
    causal_cisd,
)

IDENTITY = "TURTLE_SOUP_EURUSD_R3_CIBO_JOURNEY_ROUTER"
SYMBOL = "EURUSD"
EVAL_OPEN = datetime(2016, 9, 17, tzinfo=UTC)
TRAIN_CLOSE = datetime(2022, 9, 17, tzinfo=UTC)
EVAL_CLOSE = datetime(2026, 9, 17, tzinfo=UTC)
PRIMARY_FRICTION_R = Decimal("0.05")
STRESS_FRICTION_R = Decimal("0.10")
ROUTE_SHRINKAGE_N = Decimal(80)
SOURCE_RUN_ID = 35166210458
TARGET_RUN_ID = 35204892665
TARGET_IDENTITY = "CIBO_TARGET_DESTINATION_V2_SUPPORTED_REFERENCE_UNIVERSE"
TARGET_ARTIFACT_ID = 10489596583
TARGET_ARTIFACT_DIGEST = "sha256:74b7e73f2e38f6be8a02f3eff01b7fdfa0d4cbd5fd464b580380ac951a4c7a85"
ENTRY_MODES = ("NEXT_SOURCE_OPEN", "CISD_THRESHOLD_RETEST")
TARGET_ROUTES = (
    "SOURCE_OPPOSITE",
    "PRIOR_H1", "PRIOR_H4", "PRIOR_D1",
    "SWING_H1", "SWING_H4", "SWING_D1",
)
ACTIONS = tuple((entry, target) for entry in ENTRY_MODES for target in TARGET_ROUTES)


@dataclass(frozen=True, slots=True)
class TargetCandidate:
    episode_id: str
    kind: str
    timeframe: str
    level: Decimal
    known_at: datetime
    touch_at: datetime | None


@dataclass(frozen=True, slots=True)
class Setup:
    context: r2.ContextSignal
    source: SourceCandle
    cisd_threshold: Decimal


@dataclass(frozen=True, slots=True)
class RoutedTrade:
    source_timeframe: str
    side: str
    entry_mode: str
    target_route: str
    episode_id: str
    entry_at: datetime
    exit_at: datetime
    entry: Decimal
    stop: Decimal
    target: Decimal
    target_kind: str
    target_timeframe: str
    gross_r: Decimal
    primary_net_r: Decimal
    stress_net_r: Decimal
    exit_reason: str
    session_bucket: str
    prior_body_alignment: str


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _target_match(route: str, row: TargetCandidate) -> bool:
    if route == "SOURCE_OPPOSITE":
        return row.kind == "SOURCE_OPPOSITE_BOUNDARY"
    family, timeframe = route.split("_", 1)
    kind = (
        "PRIOR_CANDLE_DIRECTIONAL_BOUNDARY"
        if family == "PRIOR"
        else "ACTIVE_SWING_3_DIRECTIONAL_BOUNDARY"
    )
    return row.kind == kind and row.timeframe == timeframe


def _active_targets(
    rows: Sequence[TargetCandidate], *, at: datetime, side: Side, anchor: Decimal, route: str
) -> list[TargetCandidate]:
    result = []
    for row in rows:
        if not _target_match(route, row) or row.known_at > at:
            continue
        if row.touch_at is not None and row.touch_at < at:
            continue
        ahead = row.level > anchor if side is Side.LONG else row.level < anchor
        if ahead:
            result.append(row)
    result.sort(key=lambda item: (abs(item.level - anchor), item.known_at, item.level))
    return result


def _load_targets(root: Path) -> tuple[dict[str, list[TargetCandidate]], dict[tuple[datetime, str, str, Decimal], str]]:
    manifest_paths = list(root.rglob("target-destination-v2-manifest.json"))
    ledger_paths = list(root.rglob("TARGET_DESTINATION_LEDGER_V2.jsonl"))
    if len(manifest_paths) != 1 or len(ledger_paths) != 1:
        raise ValueError("expected one EURUSD Target Destination V2 artifact")
    manifest = json.loads(manifest_paths[0].read_text())
    if manifest.get("identity") != TARGET_IDENTITY or manifest.get("symbol") != SYMBOL:
        raise ValueError("unexpected Target Destination V2 identity")
    episodes: dict[str, list[TargetCandidate]] = defaultdict(list)
    source_index: dict[tuple[datetime, str, str, Decimal], str] = {}
    with ledger_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            candidate = TargetCandidate(
                episode_id=str(raw["episode_id"]),
                kind=str(raw["candidate_type"]),
                timeframe=str(raw["source_timeframe"]),
                level=Decimal(str(raw["candidate_price"])),
                known_at=_dt(str(raw["candidate_known_at"])),
                touch_at=(None if raw.get("touch_m5_opened_at") is None else _dt(str(raw["touch_m5_opened_at"]))),
            )
            episodes[candidate.episode_id].append(candidate)
            if candidate.kind == "SOURCE_OPPOSITE_BOUNDARY":
                key = (
                    _dt(str(raw["departure_at"])),
                    str(raw["side"]),
                    candidate.timeframe,
                    candidate.level,
                )
                previous = source_index.get(key)
                if previous is not None and previous != candidate.episode_id:
                    raise ValueError("ambiguous source-opposite episode key")
                source_index[key] = candidate.episode_id
    return dict(episodes), source_index


def _lower_sources(source: SourceCandle, timeframe: str) -> tuple[SourceCandle, ...]:
    if timeframe == "H1":
        return r1._m5_sources(source.m5)
    if timeframe == "H4":
        return build_m15(source.m5)
    raise ValueError(f"unsupported setup timeframe: {timeframe}")


def _build_setups(evidence: r1.Evidence) -> tuple[list[Setup], dict[str, int]]:
    contexts, funnel = r2._context_signals(evidence)
    frames = {"H1": build_h1(evidence.bars), "H4": build_h4(evidence.bars)}
    frame_index = {
        timeframe: {candle.opened_at: candle for candle in candles}
        for timeframe, candles in frames.items()
    }
    setups: list[Setup] = []
    for context in contexts:
        signal = context.signal
        source = frame_index[context.timeframe].get(signal.c2_opened_at)
        if source is None:
            raise ValueError("source candle missing for R3 setup")
        found = causal_cisd(
            _lower_sources(source, context.timeframe),
            side=signal.side,
            extreme=signal.protected_swing,
        )
        if found is None or found.confirmed_at != signal.cisd_at:
            raise ValueError("R3 CISD reproduction drift")
        setups.append(Setup(context=context, source=source, cisd_threshold=found.threshold))
    setups.sort(key=lambda item: (item.context.signal.entry_at, 0 if item.context.timeframe == "H4" else 1))
    return setups, funnel


def _route_state(setup: Setup) -> tuple[str, str, str, str, str]:
    c = setup.context
    return (
        c.timeframe,
        c.side,
        c.prior_body_alignment,
        c.cisd_progress_bucket,
        c.source_range_state_bucket,
    )


def _entry(
    setup: Setup, evidence: r1.Evidence, opens: Sequence[datetime], mode: str
) -> tuple[datetime, Decimal] | None:
    signal = setup.context.signal
    stop = signal.protected_swing
    side = signal.side
    if mode == "NEXT_SOURCE_OPEN":
        index = bisect.bisect_left(opens, signal.entry_at)
        if index >= len(evidence.bars):
            return None
        bar = evidence.bars[index]
        invalid = bar.open <= stop if side is Side.LONG else bar.open >= stop
        return None if invalid else (bar.opened_at, bar.open)
    if mode != "CISD_THRESHOLD_RETEST":
        raise ValueError(mode)
    threshold = setup.cisd_threshold
    close = setup.source.close
    valid = stop < threshold <= close if side is Side.LONG else stop > threshold >= close
    if not valid:
        return None
    duration = timedelta(hours=1 if setup.context.timeframe == "H1" else 4)
    left = bisect.bisect_left(opens, signal.entry_at)
    right = bisect.bisect_left(opens, signal.entry_at + duration)
    for bar in evidence.bars[left:right]:
        if side is Side.LONG:
            if bar.open <= stop:
                return None
            if bar.open <= threshold:
                return bar.opened_at, bar.open
            if bar.low <= threshold:
                return bar.opened_at, threshold
        else:
            if bar.open >= stop:
                return None
            if bar.open >= threshold:
                return bar.opened_at, bar.open
            if bar.high >= threshold:
                return bar.opened_at, threshold
    return None


def _simulate(
    setup: Setup,
    rows: Sequence[TargetCandidate],
    evidence: r1.Evidence,
    opens: Sequence[datetime],
    action: tuple[str, str],
) -> tuple[Decimal | None, RoutedTrade | None, str]:
    entry_mode, target_route = action
    signal = setup.context.signal
    visible = _active_targets(rows, at=signal.entry_at, side=signal.side, anchor=signal.entry, route=target_route)
    if not visible:
        return None, None, "ROUTE_UNAVAILABLE_AT_DECISION"
    fill = _entry(setup, evidence, opens, entry_mode)
    if fill is None:
        return Decimal(0), None, "NO_FILL_OR_INVALIDATED_BEFORE_FILL"
    entry_at, entry = fill
    active = _active_targets(rows, at=entry_at, side=signal.side, anchor=entry, route=target_route)
    if not active:
        return Decimal(0), None, "DOL_CONSUMED_BEFORE_FILL"
    target_row = active[0]
    stop = signal.protected_swing
    risk = entry - stop if signal.side is Side.LONG else stop - entry
    reward = target_row.level - entry if signal.side is Side.LONG else entry - target_row.level
    if risk <= 0 or reward <= 0:
        return None, None, "INVALID_GEOMETRY"
    left = bisect.bisect_left(opens, entry_at)
    right = bisect.bisect_left(opens, min(entry_at + timedelta(hours=24), EVAL_CLOSE))
    path = evidence.bars[left:right]
    if not path:
        return None, None, "EMPTY_PATH"
    exit_at = path[-1].closed_at
    exit_price = path[-1].close
    reason = "TIME_24H"
    gross = ((exit_price - entry) / risk if signal.side is Side.LONG else (entry - exit_price) / risk)
    for bar in path:
        if signal.side is Side.LONG:
            if bar.open <= stop:
                exit_at, exit_price, reason, gross = bar.opened_at, bar.open, "GAP_STOP", (bar.open - entry) / risk
                break
            if bar.open >= target_row.level:
                exit_at, exit_price, reason, gross = bar.opened_at, target_row.level, "GAP_TARGET_CAPPED", reward / risk
                break
            stop_touch, target_touch = bar.low <= stop, bar.high >= target_row.level
        else:
            if bar.open >= stop:
                exit_at, exit_price, reason, gross = bar.opened_at, bar.open, "GAP_STOP", (entry - bar.open) / risk
                break
            if bar.open <= target_row.level:
                exit_at, exit_price, reason, gross = bar.opened_at, target_row.level, "GAP_TARGET_CAPPED", reward / risk
                break
            stop_touch, target_touch = bar.high >= stop, bar.low <= target_row.level
        if stop_touch and target_touch:
            exit_at, exit_price, reason, gross = bar.closed_at, stop, "STOP_FIRST", Decimal(-1)
            break
        if stop_touch:
            exit_at, exit_price, reason, gross = bar.closed_at, stop, "STOP", Decimal(-1)
            break
        if target_touch:
            exit_at, exit_price, reason, gross = bar.closed_at, target_row.level, "TARGET", reward / risk
            break
    trade = RoutedTrade(
        source_timeframe=setup.context.timeframe,
        side=signal.side.value,
        entry_mode=entry_mode,
        target_route=target_route,
        episode_id=target_row.episode_id,
        entry_at=entry_at,
        exit_at=exit_at,
        entry=entry,
        stop=stop,
        target=target_row.level,
        target_kind=target_row.kind,
        target_timeframe=target_row.timeframe,
        gross_r=gross,
        primary_net_r=gross - PRIMARY_FRICTION_R,
        stress_net_r=gross - STRESS_FRICTION_R,
        exit_reason=reason,
        session_bucket=signal.session_bucket,
        prior_body_alignment=signal.prior_body_alignment,
    )
    return trade.primary_net_r, trade, "FILLED"


def _fit_router(
    rows: Sequence[tuple[Setup, dict[tuple[str, str], tuple[Decimal | None, RoutedTrade | None, str]]]]
) -> dict[str, Any]:
    action_values: dict[tuple[str, str], list[Decimal]] = defaultdict(list)
    state_values: dict[tuple[tuple[str, str, str, str, str], tuple[str, str]], list[Decimal]] = defaultdict(list)
    for setup, outcomes in rows:
        if setup.context.signal.entry_at >= TRAIN_CLOSE:
            continue
        state = _route_state(setup)
        for action, (value, _trade, _reason) in outcomes.items():
            if value is None:
                continue
            action_values[action].append(value)
            state_values[(state, action)].append(value)
    baselines: dict[str, Any] = {}
    states: dict[str, Any] = {}
    for action in ACTIONS:
        values = action_values.get(action, [])
        if not values:
            continue
        baseline = sum(values, Decimal(0)) / len(values)
        baselines["|".join(action)] = {"n": len(values), "mean_primary_r": str(baseline)}
        for (state, candidate_action), members in state_values.items():
            if candidate_action != action:
                continue
            n = Decimal(len(members))
            shrunk = (sum(members, Decimal(0)) + ROUTE_SHRINKAGE_N * baseline) / (n + ROUTE_SHRINKAGE_N)
            states["|".join((*state, *action))] = {"n": len(members), "shrunk_mean_primary_r": str(shrunk)}
    return {
        "schema": "qore.turtle_soup_eurusd_r3.cibo_journey_router.v1",
        "identity": IDENTITY,
        "training_open": EVAL_OPEN.isoformat(),
        "training_close": TRAIN_CLOSE.isoformat(),
        "validation_open": TRAIN_CLOSE.isoformat(),
        "validation_close": EVAL_CLOSE.isoformat(),
        "routing_state": ["source_timeframe", "side", "prior_body_alignment", "cisd_progress_bucket", "source_range_state_bucket"],
        "actions": [list(action) for action in ACTIONS],
        "selection_rule": "CHOOSE_HIGHEST_EXPECTED_ROUTE_AMONG_CAUSALLY_AVAILABLE_ACTIONS_NO_POSITIVE_SCORE_GATE",
        "learned_abstention": False,
        "structural_abstention_only": True,
        "shrinkage_n": str(ROUTE_SHRINKAGE_N),
        "action_baselines": baselines,
        "state_action_means": states,
        "forbidden_as_route_inputs": ["mfe", "mae", "target_hit", "target_touch_time", "exit_reason", "future_price"],
        "diagnostic_only_not_route_inputs": ["session", "weekday", "exact_equal_liquidity", "fvg_after_raid"],
    }


def _score(setup: Setup, action: tuple[str, str], router: dict[str, Any]) -> Decimal | None:
    name = "|".join(action)
    baseline = router["action_baselines"].get(name)
    if baseline is None:
        return None
    state_name = "|".join((*_route_state(setup), *action))
    row = router["state_action_means"].get(state_name)
    return Decimal(str(row["shrunk_mean_primary_r"])) if row is not None else Decimal(str(baseline["mean_primary_r"]))


def _choose(
    setup: Setup,
    outcomes: dict[tuple[str, str], tuple[Decimal | None, RoutedTrade | None, str]],
    router: dict[str, Any],
) -> tuple[tuple[str, str] | None, tuple[Decimal | None, RoutedTrade | None, str] | None]:
    scored = []
    for action, outcome in outcomes.items():
        if outcome[0] is None:
            continue
        score = _score(setup, action, router)
        if score is not None:
            scored.append((score, action))
    if not scored:
        return None, None
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    action = scored[0][1]
    return action, outcomes[action]


def _stat(trades: Sequence[RoutedTrade], attr: str = "primary_net_r") -> dict[str, Any]:
    return r1._stat([getattr(trade, attr) for trade in trades])


def _groups(trades: Sequence[RoutedTrade], key: str) -> dict[str, Any]:
    groups: dict[str, list[RoutedTrade]] = defaultdict(list)
    for trade in trades:
        groups[str(getattr(trade, key))].append(trade)
    return {name: _stat(items) for name, items in sorted(groups.items())}


def _json_trade(trade: RoutedTrade) -> dict[str, Any]:
    raw = asdict(trade)
    return {key: (value.isoformat() if isinstance(value, datetime) else str(value) if isinstance(value, Decimal) else value) for key, value in raw.items()}


def run(source_root: Path, target_root: Path, output: Path) -> dict[str, Any]:
    evidence, provenance = journey.load_raw_m5(source_root)
    if evidence.symbol != SYMBOL or int(provenance["retained_bars"]) != 707716:
        raise ValueError("unexpected EURUSD 10Y source corpus")
    episodes, source_index = _load_targets(target_root)
    original_open, original_close = r1.EVAL_OPEN, r1.EVAL_CLOSE
    try:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = EVAL_OPEN, EVAL_CLOSE
        setups, funnel = _build_setups(evidence)
    finally:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = original_open, original_close
    opens = tuple(bar.opened_at for bar in evidence.bars)
    rows = []
    abstentions = Counter()
    matched = 0
    for setup in setups:
        signal = setup.context.signal
        episode_id = source_index.get((signal.cisd_at, signal.side.value, setup.context.timeframe, signal.target))
        if episode_id is None:
            abstentions["NO_CAUSAL_CIBO_EPISODE_MATCH"] += 1
            continue
        matched += 1
        target_rows = episodes[episode_id]
        outcomes = {action: _simulate(setup, target_rows, evidence, opens, action) for action in ACTIONS}
        rows.append((setup, outcomes))
    router = _fit_router(rows)
    selected: list[RoutedTrade] = []
    no_fill = Counter()
    route_counts = Counter()
    busy_until = EVAL_OPEN
    for setup, outcomes in rows:
        action, outcome = _choose(setup, outcomes, router)
        if action is None or outcome is None:
            abstentions["NO_CAUSALLY_AVAILABLE_ROUTE"] += 1
            continue
        route_counts["|".join(action)] += 1
        _value, trade, reason = outcome
        if trade is None:
            no_fill[reason] += 1
            continue
        if trade.entry_at < busy_until:
            abstentions["SINGLE_POSITION_BUSY"] += 1
            continue
        selected.append(trade)
        busy_until = trade.exit_at
    training = [trade for trade in selected if EVAL_OPEN <= trade.entry_at < TRAIN_CLOSE]
    validation = [trade for trade in selected if TRAIN_CLOSE <= trade.entry_at < EVAL_CLOSE]
    payload = {
        "schema": "qore.turtle_soup_eurusd_r3.cibo_journey_replay.v1",
        "identity": IDENTITY,
        "symbol": SYMBOL,
        "evidence_status": "CONSUMED_CIBO_10Y_DEVELOPMENT_WITH_INTERNAL_TEMPORAL_VALIDATION_NOT_FRESH_HOLDOUT",
        "source_m5_run_id": SOURCE_RUN_ID,
        "source_target_run_id": TARGET_RUN_ID,
        "source_target_artifact_id": TARGET_ARTIFACT_ID,
        "source_target_artifact_digest": TARGET_ARTIFACT_DIGEST,
        "retained_m5_bars": provenance["retained_bars"],
        "router": router,
        "contract": {
            "setup": "PRIOR_CANDLE_LIQUIDITY_RAID_EXACT_C2_CAUSAL_CISD",
            "entry": "ROUTED_NEXT_SOURCE_OPEN_OR_POST_C2_CISD_THRESHOLD_RETEST",
            "stop": "CAUSAL_CISD_PROTECTED_SWING_EXACT_NO_OFFSET",
            "target": "ROUTED_ACTIVE_UNTOUCHED_CIBO_DOL_FAMILY_KNOWN_AT_DECISION",
            "target_universe": list(TARGET_ROUTES),
            "abstention": "STRUCTURAL_ONLY_NO_ROUTE_NO_FILL_INVALIDATION_DOL_CONSUMED_OR_BUSY",
            "same_m5_bar_tie": "STOP_FIRST",
            "max_lifetime": "24H_MATCHING_TARGET_DESTINATION_V2_HORIZON",
            "not_filters": ["session", "weekday", "fvg", "equal_liquidity"],
        },
        "setup_pool": len(setups),
        "cibo_episode_matched": matched,
        "routed_rows": len(rows),
        "executed_trades": len(selected),
        "training_trades": len(training),
        "validation_trades": len(validation),
        "abstentions": dict(abstentions),
        "natural_no_fill": dict(no_fill),
        "route_counts": dict(route_counts),
        "training_primary": _stat(training),
        "training_stress_010r": _stat(training, "stress_net_r"),
        "validation_primary": _stat(validation),
        "validation_stress_010r": _stat(validation, "stress_net_r"),
        "full_primary": _stat(selected),
        "full_stress_010r": _stat(selected, "stress_net_r"),
        "full_by_entry_mode": _groups(selected, "entry_mode"),
        "full_by_target_route": _groups(selected, "target_route"),
        "full_by_source_timeframe": _groups(selected, "source_timeframe"),
        "full_by_side": _groups(selected, "side"),
        "full_by_session_diagnostic": _groups(selected, "session_bucket"),
        "full_by_prior_body_diagnostic": _groups(selected, "prior_body_alignment"),
        "funnel": funnel,
        "governance": {
            "fresh_holdout": False,
            "validation_block_used_for_fit": False,
            "positive_score_trade_filter": False,
            "post_entry_leakage_allowed": False,
            "automatic_promotion_allowed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "router.json").write_text(json.dumps(router, indent=2, sort_keys=True) + "\n")
    (output / "report.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    (output / "trades-full.json").write_text(json.dumps([_json_trade(item) for item in selected], indent=2, sort_keys=True) + "\n")
    (output / "trades-validation.json").write_text(json.dumps([_json_trade(item) for item in validation], indent=2, sort_keys=True) + "\n")
    return payload


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: module SOURCE_ROOT TARGET_ROOT OUTPUT_DIR")
    print(json.dumps(run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])), sort_keys=True))


if __name__ == "__main__":
    main()
