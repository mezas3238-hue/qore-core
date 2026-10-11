"""V50-R pre-economic causal M1 re-arm capacity census.

The V49 high-frequency engine takes only the earliest M1 trigger for each M15 setup. V50-G
showed that most first triggers have execution invalidation inside local M1 noise.

V50-R keeps the same H1 state, same M15 setup and same source trigger families. When the first
trigger yields Geometry WAIT_STOP_BREATHING, it does not consume a MAX3 slot. Instead, while
the parent H1/M15 setup remains causally alive, the engine asks the SAME V49 trigger observers
for the next genuinely later M1 event and rebuilds decision-time geometry.

This census is PRE-ECONOMIC:
- no trade outcome, P&L, MFE/MAE or future terminal label;
- no holdout/Fresh Holdout;
- no stop relaxation;
- no target chosen from future;
- no runtime policy promotion.

It measures only whether re-arm can recover executable high-frequency capacity.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerSession,
    allowed_markets,
)
from qore.infrastructure.trader_lab.capitalizer_experience_memory import (
    CapitalizerExperienceMemory,
)
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import (
    _aggregate,
    _build_h1_bias_events,
    _operating_date,
    _timed_m15,
)
from qore.infrastructure.trader_lab.capitalizer_h1_context_state_v49 import (
    V49H1BiasSignal,
    build_h1_context_states,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEFAULT_LOOKBACK,
    DEV_WINDOW_END,
    DEV_WINDOW_START,
    V49Opportunity,
    _all_m15_setups,
    _earliest_m1_trigger,
    _slice,
    _untouched_h1_target_fast,
)
from qore.infrastructure.trader_lab.capitalizer_metacognition_v2 import (
    CapitalizerEpistemicReadiness,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_specialist import (
    V50GeometryDecision,
    propose_v50_geometry,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_hf_bridge import (
    V50CognitiveDisposition,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_opportunity import (
    build_v50_cognitive_snapshot,
)

IDENTITY = "QORE_CAPITALIZER_V50_R_M1_REARM_CAPACITY"
MATRIX_IDENTITY = "QORE_CAPITALIZER_V50_R_NINE_MARKET_REARM_CAPACITY"
REARMABLE = {V50GeometryDecision.WAIT_STOP_BREATHING}
COGNITIVE_ALLOWED = {
    V50CognitiveDisposition.PASS_TO_COMPETITION,
    V50CognitiveDisposition.REFINE_STOP_GEOMETRY,
    V50CognitiveDisposition.REFINE_TARGET_LADDER,
}


@dataclass(frozen=True, slots=True)
class V50RearmAttempt:
    symbol: str
    session: str
    operating_date: str
    h1_state_from: str
    h1_state_until: str
    h1_state_basis: str
    m15_setup_confirmed_at: str
    m15_protected_swing_price: str
    trigger_confirmed_at: str
    trigger_family: str
    decision_reference_price: str
    structural_target_witness_price: str
    attempt_index: int
    geometry_decision: str
    cognitive_disposition: str
    geometry_ready: bool
    cognitive_geometry_ready: bool
    slot_consumed_during_wait: bool = False
    stop_relaxed: bool = False
    outcome_used: bool = False
    economics_used: bool = False
    fresh_holdout_used: bool = False

    def __post_init__(self) -> None:
        if self.attempt_index < 1:
            raise ValueError("V50-R attempt index must be >=1")
        if self.slot_consumed_during_wait or self.stop_relaxed:
            raise ValueError("V50-R waiting cannot consume slot or relax stop")
        if self.outcome_used or self.economics_used or self.fresh_holdout_used:
            raise ValueError("V50-R capacity must remain pre-economic")


@dataclass(frozen=True, slots=True)
class V50RearmMarketReport:
    identity: str
    symbol: str
    session: str
    source_m15_setups: int
    trigger_attempts: int
    first_trigger_attempts: int
    rearm_trigger_attempts: int
    first_attempt_geometry_ready: int
    recovered_geometry_ready_after_rearm: int
    total_geometry_ready_setups: int
    recovered_cognitive_geometry_ready_after_rearm: int
    total_cognitive_geometry_ready_setups: int
    geometry_ready_but_cognition_blocked: int
    cognitive_rearm_attempts: int
    cognitive_rearm_recovered_ready: int
    exhausted_rearmable_setups: int
    thesis_invalidated_before_trigger: int
    by_geometry_decision: tuple[tuple[str, int], ...]
    by_geometry_reason: tuple[tuple[str, int], ...]
    by_attempt_index: tuple[tuple[int, int], ...]
    maximum_attempt_index: int
    outcome_used: bool = False
    economics_used: bool = False
    reserved_holdout_reopened: bool = False
    fresh_holdout_used: bool = False
    development_only: bool = True
    runtime_policy_candidate: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("unexpected V50-R report identity")
        if (
            self.outcome_used
            or self.economics_used
            or self.reserved_holdout_reopened
            or self.fresh_holdout_used
            or self.runtime_policy_candidate
        ):
            raise ValueError("V50-R capacity crossed research boundary")


def _session_groups(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    session: CapitalizerSession,
) -> tuple[tuple[str, tuple[CapitalizerM1Bar, ...]], ...]:
    grouped: dict[str, list[CapitalizerM1Bar]] = defaultdict(list)
    for bar in bars:
        if not (DEV_WINDOW_START <= bar.opened_at < DEV_WINDOW_END):
            continue
        if capitalizer_session_at(bar.opened_at) is not session:
            continue
        grouped[_operating_date(bar.opened_at, session)].append(bar)
    return tuple(
        (day, tuple(sorted(rows, key=lambda item: item.opened_at)))
        for day, rows in sorted(grouped.items())
        if rows
    )


def _thesis_intact_until(
    bars: tuple[CapitalizerM1Bar, ...],
    opened: tuple[datetime, ...],
    *,
    setup_confirmed_at: datetime,
    trigger_confirmed_at: datetime,
    protected_swing_price: Decimal,
    direction: CapitalizerSourceDirection,
) -> bool:
    """Return whether the M15 protected swing remains intact through trigger confirmation."""

    window = _slice(
        bars,
        opened,
        start=setup_confirmed_at,
        end=trigger_confirmed_at,
        context=0,
    )
    if direction is CapitalizerSourceDirection.BULLISH:
        return not any(bar.low <= protected_swing_price for bar in window)
    return not any(bar.high >= protected_swing_price for bar in window)


def _opportunity(
    *,
    symbol: str,
    session: CapitalizerSession,
    operating_day: str,
    state: Any,
    setup: Any,
    trigger_at: datetime,
    family: str,
    decision_price: Decimal,
    target: Decimal,
) -> V49Opportunity:
    if setup.confirmed_at is None or setup.swing_price is None:
        raise ValueError("V50-R requires complete M15 setup")
    return V49Opportunity(
        symbol=symbol,
        session=session.value,
        operating_date=operating_day,
        h1_state_direction=state.direction.value,
        h1_state_from=state.active_from.isoformat(),
        h1_state_until=state.active_until.isoformat(),
        h1_state_basis=state.established_by,
        m15_setup_confirmed_at=setup.confirmed_at.isoformat(),
        m15_protected_swing_price=str(setup.swing_price),
        m1_trigger_confirmed_at=trigger_at.isoformat(),
        m1_trigger_family=family,
        decision_reference_price=str(decision_price),
        structural_target_witness_price=str(target),
    )


def build_rearm_capacity(
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[V50RearmMarketReport, tuple[V50RearmAttempt, ...]]:
    lookback_start = DEV_WINDOW_START - DEFAULT_LOOKBACK
    bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if lookback_start <= bar.opened_at < DEV_WINDOW_END
    )
    if not bars:
        raise ValueError("V50-R found no retained M1")
    symbol = bars[0].symbol
    if any(bar.symbol != symbol for bar in bars):
        raise ValueError("V50-R market root must contain one symbol")
    if symbol not in allowed_markets(session):
        raise ValueError("V50-R symbol/session outside Capitalizer identity")

    h1 = _aggregate(bars, minutes=60)
    m15 = _timed_m15(_aggregate(bars, minutes=15))
    m15_opened = tuple(item.opened_at for item in m15)
    m1_opened = tuple(item.opened_at for item in bars)
    bias_events = tuple(
        item
        for item in _build_h1_bias_events(h1)
        if lookback_start <= item.confirmed_at < DEV_WINDOW_END
    )
    signals = tuple(
        V49H1BiasSignal(
            confirmed_at=item.confirmed_at,
            direction=item.direction,
            basis_id=f"{item.closure_kind}:{item.poi_kind}",
        )
        for item in bias_events
    )

    attempts: list[V50RearmAttempt] = []
    counters: Counter[str] = Counter()
    geometry_counts: Counter[str] = Counter()
    geometry_reason_counts: Counter[str] = Counter()
    attempt_counts: Counter[int] = Counter()

    for operating_day, session_bars in _session_groups(bars, session=session):
        session_start = session_bars[0].opened_at
        session_end = session_bars[-1].closed_at
        states = build_h1_context_states(
            signals,
            session=session,
            session_start=session_start,
            session_end=session_end,
        )
        for state in states:
            m15_window = _slice(
                m15,
                m15_opened,
                start=state.active_from,
                end=state.active_until,
            )
            setups = _all_m15_setups(m15_window, state=state)
            counters["M15_SETUPS"] += len(setups)

            for index, setup in enumerate(setups):
                if setup.confirmed_at is None or setup.swing_price is None:
                    raise ValueError("V50-R source-valid setup missing payload")
                deadline = (
                    setups[index + 1].confirmed_at
                    if index + 1 < len(setups)
                    else state.active_until
                )
                if deadline is None or deadline <= setup.confirmed_at:
                    continue

                cursor = setup.confirmed_at
                attempt_index = 0
                seen_trigger_times: set[datetime] = set()
                recovered = False
                cognitive_rearm_active = False

                while cursor < deadline:
                    m1_window = _slice(
                        bars,
                        m1_opened,
                        start=cursor,
                        end=deadline,
                        context=0,
                    )
                    if len(m1_window) < 4:
                        break
                    trigger = _earliest_m1_trigger(
                        m1_window,
                        direction=state.direction,
                        thesis_at=cursor,
                        deadline_at=deadline,
                    )
                    if trigger is None:
                        break
                    trigger_at, family, decision_price = trigger
                    if trigger_at in seen_trigger_times:
                        break
                    seen_trigger_times.add(trigger_at)
                    if trigger_at <= cursor:
                        raise ValueError("V50-R trigger chronology must advance")
                    if capitalizer_session_at(trigger_at) is not session:
                        break

                    stop_valid = (
                        setup.swing_price < decision_price
                        if state.direction is CapitalizerSourceDirection.BULLISH
                        else setup.swing_price > decision_price
                    )
                    if not stop_valid:
                        cursor = trigger_at
                        continue

                    if not _thesis_intact_until(
                        bars,
                        m1_opened,
                        setup_confirmed_at=setup.confirmed_at,
                        trigger_confirmed_at=trigger_at,
                        protected_swing_price=setup.swing_price,
                        direction=state.direction,
                    ):
                        counters["THESIS_INVALIDATED_BEFORE_TRIGGER"] += 1
                        break

                    target = _untouched_h1_target_fast(
                        h1,
                        bars,
                        m1_opened,
                        decision_at=trigger_at,
                        decision_price=decision_price,
                        direction=state.direction,
                    )
                    if target is None:
                        cursor = trigger_at
                        continue

                    attempt_index += 1
                    counters["TRIGGER_ATTEMPTS"] += 1
                    attempt_counts[attempt_index] += 1
                    if attempt_index == 1:
                        counters["FIRST_TRIGGER_ATTEMPTS"] += 1
                    else:
                        counters["REARM_TRIGGER_ATTEMPTS"] += 1

                    opportunity = _opportunity(
                        symbol=symbol,
                        session=session,
                        operating_day=operating_day,
                        state=state,
                        setup=setup,
                        trigger_at=trigger_at,
                        family=family,
                        decision_price=decision_price,
                        target=target,
                    )
                    snapshot = build_v50_cognitive_snapshot(
                        opportunity,
                        m1_bars=bars,
                        h1_bars=h1,
                        experience_memory=CapitalizerExperienceMemory(),
                        metacognitive_readiness=CapitalizerEpistemicReadiness.WELL_SUPPORTED,
                    )
                    geometry = propose_v50_geometry(snapshot)
                    geometry_counts[geometry.decision.value] += 1
                    geometry_reason_counts.update(geometry.reasons)
                    ready = geometry.decision is V50GeometryDecision.READY
                    cognitive_ready = (
                        ready
                        and snapshot.cognitive.disposition in COGNITIVE_ALLOWED
                    )
                    attempts.append(
                        V50RearmAttempt(
                            symbol=symbol,
                            session=session.value,
                            operating_date=operating_day,
                            h1_state_from=state.active_from.isoformat(),
                            h1_state_until=state.active_until.isoformat(),
                            h1_state_basis=state.established_by,
                            m15_setup_confirmed_at=setup.confirmed_at.isoformat(),
                            m15_protected_swing_price=str(setup.swing_price),
                            trigger_confirmed_at=trigger_at.isoformat(),
                            trigger_family=family,
                            decision_reference_price=str(decision_price),
                            structural_target_witness_price=str(target),
                            attempt_index=attempt_index,
                            geometry_decision=geometry.decision.value,
                            cognitive_disposition=snapshot.cognitive.disposition.value,
                            geometry_ready=ready,
                            cognitive_geometry_ready=cognitive_ready,
                        )
                    )

                    if ready:
                        if attempt_index == 1:
                            counters["FIRST_READY"] += 1
                        else:
                            counters["RECOVERED_READY"] += 1
                            if cognitive_ready:
                                counters["RECOVERED_COG_READY"] += 1
                        counters["TOTAL_READY"] += 1
                        if cognitive_ready:
                            counters["TOTAL_COG_READY"] += 1
                            if cognitive_rearm_active:
                                counters["COGNITIVE_REARM_RECOVERED"] += 1
                            recovered = True
                            break

                        # Geometry READY is not sufficient for the cognitive population.
                        # A cognition-blocked first execution does not consume MAX3 and does
                        # not invalidate the parent H1/M15 thesis. Continue only on a strictly
                        # later source-valid M1 event while the protected swing remains intact.
                        counters["GEOMETRY_READY_COGNITION_BLOCKED"] += 1
                        cognitive_rearm_active = True
                        counters["COGNITIVE_REARM_ATTEMPTS"] += 1
                        cursor = trigger_at
                        continue

                    if geometry.decision not in REARMABLE:
                        break

                    cursor = trigger_at

                if (
                    attempt_index > 0
                    and not recovered
                    and attempts
                    and attempts[-1].geometry_decision
                    == V50GeometryDecision.WAIT_STOP_BREATHING.value
                ):
                    counters["EXHAUSTED_REARMABLE"] += 1

    ordered = tuple(
        sorted(
            attempts,
            key=lambda item: (
                item.trigger_confirmed_at,
                item.symbol,
                item.attempt_index,
            ),
        )
    )
    return (
        V50RearmMarketReport(
            identity=IDENTITY,
            symbol=symbol,
            session=session.value,
            source_m15_setups=counters["M15_SETUPS"],
            trigger_attempts=counters["TRIGGER_ATTEMPTS"],
            first_trigger_attempts=counters["FIRST_TRIGGER_ATTEMPTS"],
            rearm_trigger_attempts=counters["REARM_TRIGGER_ATTEMPTS"],
            first_attempt_geometry_ready=counters["FIRST_READY"],
            recovered_geometry_ready_after_rearm=counters["RECOVERED_READY"],
            total_geometry_ready_setups=counters["TOTAL_READY"],
            recovered_cognitive_geometry_ready_after_rearm=counters[
                "RECOVERED_COG_READY"
            ],
            total_cognitive_geometry_ready_setups=counters["TOTAL_COG_READY"],
            geometry_ready_but_cognition_blocked=counters[
                "GEOMETRY_READY_COGNITION_BLOCKED"
            ],
            cognitive_rearm_attempts=counters["COGNITIVE_REARM_ATTEMPTS"],
            cognitive_rearm_recovered_ready=counters["COGNITIVE_REARM_RECOVERED"],
            exhausted_rearmable_setups=counters["EXHAUSTED_REARMABLE"],
            thesis_invalidated_before_trigger=counters[
                "THESIS_INVALIDATED_BEFORE_TRIGGER"
            ],
            by_geometry_decision=tuple(sorted(geometry_counts.items())),
            by_geometry_reason=tuple(sorted(geometry_reason_counts.items())),
            by_attempt_index=tuple(sorted(attempt_counts.items())),
            maximum_attempt_index=max(attempt_counts, default=0),
        ),
        ordered,
    )


def write_market(
    report: V50RearmMarketReport,
    attempts: tuple[V50RearmAttempt, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = f"capitalizer-{report.symbol.lower()}-v50-r-rearm-capacity"
    (output / f"{stem}.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-attempts.jsonl").open("w", encoding="utf-8") as handle:
        for item in attempts:
            handle.write(json.dumps(asdict(item), sort_keys=True) + "\n")


def _read_matrix_attempts(root: Path) -> tuple[V50RearmAttempt, ...]:
    paths = sorted(root.rglob("capitalizer-*-v50-r-rearm-capacity-attempts.jsonl"))
    if len(paths) != 9:
        raise ValueError(f"V50-R matrix requires 9 attempt ledgers, got {len(paths)}")
    rows: list[V50RearmAttempt] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(V50RearmAttempt(**json.loads(line)))
    return tuple(
        sorted(
            rows,
            key=lambda item: (
                item.trigger_confirmed_at,
                item.symbol,
                item.attempt_index,
            ),
        )
    )


def _setup_key(
    item: V50RearmAttempt,
) -> tuple[str, str, str, str, str]:
    return (
        item.symbol,
        item.session,
        item.operating_date,
        item.h1_state_from,
        item.m15_setup_confirmed_at,
    )


def _portfolio_ready(
    rows: tuple[V50RearmAttempt, ...],
    *,
    cognitive: bool,
) -> tuple[V50RearmAttempt, ...]:
    # The attempt ledger may contain several later M1 re-arms for one M15 setup.
    # A portfolio population may execute that parent setup at most once.
    first_ready_by_setup: dict[
        tuple[str, str, str, str, str], V50RearmAttempt
    ] = {}
    for item in rows:
        ready = item.cognitive_geometry_ready if cognitive else item.geometry_ready
        if not ready:
            continue
        key = _setup_key(item)
        current = first_ready_by_setup.get(key)
        if current is None or (
            datetime.fromisoformat(item.trigger_confirmed_at),
            item.attempt_index,
        ) < (
            datetime.fromisoformat(current.trigger_confirmed_at),
            current.attempt_index,
        ):
            first_ready_by_setup[key] = item

    grouped: dict[tuple[str, str], list[V50RearmAttempt]] = defaultdict(list)
    for item in first_ready_by_setup.values():
        grouped[(item.session, item.operating_date)].append(item)

    selected: list[V50RearmAttempt] = []
    for session_key in sorted(grouped):
        candidates = sorted(
            grouped[session_key],
            key=lambda item: (
                datetime.fromisoformat(item.trigger_confirmed_at),
                item.symbol,
                item.attempt_index,
            ),
        )
        selected.extend(candidates[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(
        sorted(
            selected,
            key=lambda item: (
                datetime.fromisoformat(item.trigger_confirmed_at),
                item.symbol,
            ),
        )
    )


def _capacity_breakdown(rows: tuple[V50RearmAttempt, ...]) -> dict[str, Any]:
    return {
        "trades_after_max3": len(rows),
        "recovered_after_rearm": sum(item.attempt_index > 1 for item in rows),
        "first_attempt_ready": sum(item.attempt_index == 1 for item in rows),
        "by_session": {
            session: sum(item.session == session for item in rows)
            for session in ("ASIA", "LONDON", "NEW_YORK")
        },
        "by_market": {
            symbol: sum(item.symbol == symbol for item in rows)
            for symbol in sorted({item.symbol for item in rows})
        },
        "active_session_days": len(
            {(item.session, item.operating_date) for item in rows}
        ),
        "active_operating_dates": len({item.operating_date for item in rows}),
    }


def build_matrix(root: Path) -> dict[str, Any]:
    paths = sorted(root.rglob("capitalizer-*-v50-r-rearm-capacity.json"))
    if len(paths) != 9:
        raise ValueError(f"V50-R matrix requires 9 reports, got {len(paths)}")
    reports = tuple(json.loads(path.read_text(encoding="utf-8")) for path in paths)
    attempts = _read_matrix_attempts(root)
    geometry_portfolio = _portfolio_ready(attempts, cognitive=False)
    cognitive_geometry_portfolio = _portfolio_ready(attempts, cognitive=True)
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "first_attempt_geometry_ready": sum(
            int(row["first_attempt_geometry_ready"]) for row in reports
        ),
        "recovered_geometry_ready_after_rearm": sum(
            int(row["recovered_geometry_ready_after_rearm"]) for row in reports
        ),
        "total_geometry_ready_setups": sum(
            int(row["total_geometry_ready_setups"]) for row in reports
        ),
        "recovered_cognitive_geometry_ready_after_rearm": sum(
            int(row["recovered_cognitive_geometry_ready_after_rearm"])
            for row in reports
        ),
        "total_cognitive_geometry_ready_setups": sum(
            int(row["total_cognitive_geometry_ready_setups"]) for row in reports
        ),
        "rearm_trigger_attempts": sum(
            int(row["rearm_trigger_attempts"]) for row in reports
        ),
        "geometry_ready_but_cognition_blocked": sum(
            int(row["geometry_ready_but_cognition_blocked"]) for row in reports
        ),
        "cognitive_rearm_attempts": sum(
            int(row["cognitive_rearm_attempts"]) for row in reports
        ),
        "cognitive_rearm_recovered_ready": sum(
            int(row["cognitive_rearm_recovered_ready"]) for row in reports
        ),
        "thesis_invalidated_before_trigger": sum(
            int(row["thesis_invalidated_before_trigger"]) for row in reports
        ),
        "portfolio_geometry_ready": _capacity_breakdown(geometry_portfolio),
        "portfolio_cognitive_geometry_ready": _capacity_breakdown(
            cognitive_geometry_portfolio
        ),
        "max_executions_per_session": MAX_EXECUTIONS_PER_SESSION,
        "portfolio_selection_outcome_aware": False,
        "outcome_used": False,
        "economics_used": False,
        "reserved_holdout_reopened": False,
        "fresh_holdout_used": False,
        "development_only": True,
        "runtime_policy_candidate": False,
        "market_reports": sorted(reports, key=lambda row: str(row["symbol"])),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    market.add_argument(
        "--session",
        required=True,
        choices=[item.value for item in CapitalizerSession],
    )

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        market_report, attempts = build_rearm_capacity(
            args.m1_root,
            session=CapitalizerSession(args.session),
        )
        write_market(market_report, attempts, args.output)
        print(json.dumps(asdict(market_report), sort_keys=True))
        return

    matrix_report = build_matrix(args.input_root)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "capitalizer-v50-r-nine-market-rearm-capacity.json").write_text(
        json.dumps(matrix_report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(matrix_report, sort_keys=True))


if __name__ == "__main__":
    main()
