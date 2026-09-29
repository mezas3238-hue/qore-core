"""Provider-native time/causal coverage census for Capitalizer V46 Phase B.

Phase B is data/time coverage only. It exhaustively scans every completed
provider-native M1 decision clock inside the canonical source-session windows
for the three consumed periods. It does not read outcomes or calculate
strategy economics.

Frozen in PR #623 comment 5887937886.
"""

from __future__ import annotations

import argparse
import bisect
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import (
    capitalizer_canonical_historical_replay_adapter_v46 as adapter,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
)
from qore.infrastructure.trader_lab.capitalizer_source_session_context_v2 import (
    CapitalizerSourceSessionResolution,
    assess_source_session_context,
)

IDENTITY = "QORE_CAPITALIZER_NATIVE_SOURCE_PROVIDER_TIME_COVERAGE_V46_PHASE_B"
PREDECLARATION_COMMENT_ID = 5887937886
SOURCE_RUN_ID = 35548099334
SOURCE_SHA = "18c338aedd5013ce65a6cb6408ffbc2e904a6217"
LOOKBACK_DAYS = 21
NEW_YORK = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class PeriodSpec:
    slug: str
    identity: str
    start: datetime
    end: datetime

    @property
    def lookback_start(self) -> datetime:
        return self.start - timedelta(days=LOOKBACK_DAYS)


PERIODS = (
    PeriodSpec(
        "reserved",
        "CONSUMED_RESERVED_2020_2022",
        datetime.fromisoformat("2020-09-17T00:00:00+00:00"),
        datetime.fromisoformat("2022-09-17T00:00:00+00:00"),
    ),
    PeriodSpec(
        "validation",
        "CONSUMED_VALIDATION_2022_2024",
        datetime.fromisoformat("2022-09-17T00:00:00+00:00"),
        datetime.fromisoformat("2024-09-17T00:00:00+00:00"),
    ),
    PeriodSpec(
        "development",
        "DEVELOPMENT_2024_2026",
        datetime.fromisoformat("2024-09-17T00:00:00+00:00"),
        datetime.fromisoformat("2026-09-17T00:00:00+00:00"),
    ),
)


@dataclass(slots=True)
class _BucketState:
    minutes: int
    key: tuple[int, int, int, int, int, int] | None = None
    count: int = 0
    last_closed_at: datetime | None = None

    def _key_for(self, bar: CapitalizerM1Bar) -> tuple[int, int, int, int, int, int]:
        local = bar.opened_at.astimezone(NEW_YORK)
        offset = local.utcoffset()
        if offset is None:
            raise ValueError("Phase B NY-local bar requires UTC offset")
        floored = (local.minute // self.minutes) * self.minutes
        return (
            local.year,
            local.month,
            local.day,
            local.hour,
            floored,
            int(offset.total_seconds()),
        )

    def feed(self, bar: CapitalizerM1Bar) -> datetime | None:
        key = self._key_for(bar)
        completed: datetime | None = None
        if self.key is not None and key != self.key:
            minimum = max(1, self.minutes * 3 // 4)
            if self.count >= minimum:
                completed = self.last_closed_at
            self.count = 0
            self.last_closed_at = None
        self.key = key
        self.count += 1
        self.last_closed_at = bar.closed_at
        return completed

    def finish(self) -> datetime | None:
        minimum = max(1, self.minutes * 3 // 4)
        if self.key is not None and self.count >= minimum:
            return self.last_closed_at
        return None


@dataclass(slots=True)
class _PeriodState:
    spec: PeriodSpec
    source_rows: int = 0
    lookback_rows: int = 0
    first_source_at: datetime | None = None
    last_source_at: datetime | None = None
    earliest_artifact_at: datetime | None = None
    prelookback_source_seen: bool = False
    eligible_clocks: list[datetime] | None = None
    unresolved_source_clocks: int = 0
    asian_reference_resolution_count: int = 0
    synthetic_source_fact_count: int = 0
    future_bar_count: int = 0
    m15: _BucketState | None = None
    h1: _BucketState | None = None
    m15_completed: list[datetime] | None = None
    h1_completed: list[datetime] | None = None

    def __post_init__(self) -> None:
        self.eligible_clocks = []
        self.m15 = _BucketState(15)
        self.h1 = _BucketState(60)
        self.m15_completed = []
        self.h1_completed = []


def _session_assessment(
    *,
    session: CapitalizerSession,
    decision_at: datetime,
):
    reference = None
    if session is CapitalizerSession.ASIA:
        reference = adapter.resolve_historical_asian_open_reference(decision_at)
    assessment = assess_source_session_context(
        session=session,
        observed_at=decision_at,
        asian_open_reference_at=None if reference is None else reference.reference_at,
    )
    return assessment, reference


def _feed_state(
    state: _PeriodState,
    *,
    bar: CapitalizerM1Bar,
    session: CapitalizerSession,
) -> None:
    spec = state.spec
    if state.earliest_artifact_at is None:
        state.earliest_artifact_at = bar.opened_at
    if bar.opened_at <= spec.lookback_start:
        state.prelookback_source_seen = True
    if bar.opened_at < spec.lookback_start or bar.opened_at >= spec.end:
        return
    if bar.opened_at < spec.start:
        state.lookback_rows += 1
    else:
        state.source_rows += 1
        if state.first_source_at is None:
            state.first_source_at = bar.opened_at
        state.last_source_at = bar.closed_at

        assessment, reference = _session_assessment(
            session=session,
            decision_at=bar.closed_at,
        )
        if assessment.resolution is CapitalizerSourceSessionResolution.REVIEW_REQUIRED:
            state.unresolved_source_clocks += 1
        elif assessment.resolution is CapitalizerSourceSessionResolution.ELIGIBLE:
            assert state.eligible_clocks is not None
            state.eligible_clocks.append(bar.closed_at)
            if reference is not None:
                state.asian_reference_resolution_count += 1
                if reference.synthetic:
                    state.synthetic_source_fact_count += 1

    assert state.m15 is not None
    assert state.h1 is not None
    assert state.m15_completed is not None
    assert state.h1_completed is not None
    m15_done = state.m15.feed(bar)
    if m15_done is not None:
        state.m15_completed.append(m15_done)
    h1_done = state.h1.feed(bar)
    if h1_done is not None:
        state.h1_completed.append(h1_done)


def _finish_state(state: _PeriodState) -> None:
    assert state.m15 is not None
    assert state.h1 is not None
    assert state.m15_completed is not None
    assert state.h1_completed is not None
    m15_done = state.m15.finish()
    if m15_done is not None:
        state.m15_completed.append(m15_done)
    h1_done = state.h1.finish()
    if h1_done is not None:
        state.h1_completed.append(h1_done)


def _coverage_row(
    state: _PeriodState,
    *,
    symbol: str,
    session: CapitalizerSession,
) -> dict[str, Any]:
    spec = state.spec
    assert state.eligible_clocks is not None
    assert state.m15_completed is not None
    assert state.h1_completed is not None

    eligible = tuple(state.eligible_clocks)
    h1_ready = 0
    m15_ready = 0
    both_ready = 0
    max_source_minus_decision_seconds = 0.0

    for decision in eligible:
        h1_index = bisect.bisect_right(state.h1_completed, decision)
        m15_index = bisect.bisect_right(state.m15_completed, decision)
        h1_ok = h1_index > 0
        m15_ok = m15_index > 0
        h1_ready += int(h1_ok)
        m15_ready += int(m15_ok)
        both_ready += int(h1_ok and m15_ok)
        for values, index in (
            (state.h1_completed, h1_index),
            (state.m15_completed, m15_index),
        ):
            if index:
                delta = (values[index - 1] - decision).total_seconds()
                if delta > 0:
                    state.future_bar_count += 1
                max_source_minus_decision_seconds = max(
                    max_source_minus_decision_seconds,
                    delta,
                )

    lookback_present = state.prelookback_source_seen
    coverage = "1" if eligible and both_ready == len(eligible) else (
        "0" if not eligible else str(both_ready / len(eligible))
    )
    hard_pass = bool(
        lookback_present
        and eligible
        and both_ready == len(eligible)
        and state.unresolved_source_clocks == 0
        and state.future_bar_count == 0
        and state.synthetic_source_fact_count == 0
    )

    return {
        "identity": IDENTITY,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "source_run_id": SOURCE_RUN_ID,
        "source_sha": SOURCE_SHA,
        "period": spec.identity,
        "symbol": symbol,
        "session": session.value,
        "period_start": spec.start.isoformat(),
        "period_end_exclusive": spec.end.isoformat(),
        "lookback_start": spec.lookback_start.isoformat(),
        "lookback_days": LOOKBACK_DAYS,
        "provider_native_m1": True,
        "provider_timeframe_seconds": 60,
        "source_m1_rows": state.source_rows,
        "lookback_m1_rows": state.lookback_rows,
        "first_source_at": (
            None if state.first_source_at is None else state.first_source_at.isoformat()
        ),
        "last_source_at": (
            None if state.last_source_at is None else state.last_source_at.isoformat()
        ),
        "artifact_has_21d_lookback": lookback_present,
        "eligible_source_session_decision_clocks": len(eligible),
        "h1_causal_history_ready_clocks": h1_ready,
        "m15_causal_history_ready_clocks": m15_ready,
        "h1_m15_causal_history_ready_clocks": both_ready,
        "missing_history_clocks": len(eligible) - both_ready,
        "h1_m15_causal_history_coverage": coverage,
        "duplicate_timestamps": 0,
        "backward_time_events": 0,
        "unresolved_source_session_clocks": state.unresolved_source_clocks,
        "future_bar_count": state.future_bar_count,
        "synthetic_source_fact_count": state.synthetic_source_fact_count,
        "asian_reference_resolution_count": state.asian_reference_resolution_count,
        "max_source_timestamp_minus_decision_seconds": (
            max_source_minus_decision_seconds
        ),
        "h1_reconstructed_from_provider_m1": True,
        "m15_reconstructed_from_provider_m1": True,
        "m1_execution_provider_native": True,
        "outcomes_read": False,
        "realized_r_read": False,
        "exit_read": False,
        "mae_mfe_read": False,
        "fixed_2r_used": False,
        "fresh_holdout_opened": False,
        "candidate_count": 0,
        "trader_certified": False,
        "hard_gate_passed": hard_pass,
    }


def build_market_report(
    root: Path,
    *,
    session: CapitalizerSession,
) -> dict[str, Any]:
    states = [_PeriodState(spec) for spec in PERIODS]
    symbol: str | None = None

    try:
        for bar in iter_cibo_m1(root):
            if symbol is None:
                symbol = bar.symbol
            elif bar.symbol != symbol:
                raise ValueError("Phase B one market artifact changed symbol")
            for state in states:
                _feed_state(state, bar=bar, session=session)
    except ValueError as exc:
        if "chronology must be strictly increasing" in str(exc):
            raise ValueError(
                "Phase B provider M1 duplicate/backward chronology detected"
            ) from exc
        raise

    if symbol is None:
        raise ValueError("Phase B provider M1 artifact is empty")
    for state in states:
        _finish_state(state)

    rows = tuple(
        _coverage_row(state, symbol=symbol, session=session)
        for state in states
    )
    return {
        "identity": IDENTITY,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "symbol": symbol,
        "session": session.value,
        "period_rows": rows,
        "all_periods_passed": all(row["hard_gate_passed"] for row in rows),
        "strategy_economics_calculated": False,
        "fresh_holdout_opened": False,
        "candidate_count": 0,
        "trader_certified": False,
    }


def aggregate_reports(root: Path) -> dict[str, Any]:
    paths = sorted(root.rglob("capitalizer-v46-phase-b-*-coverage.json"))
    if len(paths) != 9:
        raise ValueError(f"V46 Phase B aggregate requires 9 markets, got {len(paths)}")

    reports = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    rows = [
        row
        for report in reports
        for row in report["period_rows"]
    ]
    if len(rows) != 27:
        raise ValueError("V46 Phase B aggregate requires exactly 27 rows")

    identities = {
        (str(row["symbol"]), str(row["period"]))
        for row in rows
    }
    if len(identities) != 27:
        raise ValueError("V46 Phase B duplicate market/period row")

    passed = all(bool(row["hard_gate_passed"]) for row in rows)
    return {
        "identity": IDENTITY,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "market_count": len(reports),
        "market_period_rows": len(rows),
        "all_27_rows_passed": passed,
        "failed_rows": [
            {
                "symbol": row["symbol"],
                "period": row["period"],
                "coverage": row["h1_m15_causal_history_coverage"],
                "missing_history_clocks": row["missing_history_clocks"],
            }
            for row in rows
            if not row["hard_gate_passed"]
        ],
        "phase_b_executed": True,
        "strategy_economics_calculated": False,
        "outcomes_read": False,
        "fresh_holdout_opened": False,
        "candidate_count": 0,
        "trader_certified": False,
        "next_phase": (
            "CANONICAL_FACT_COVERAGE_READY_FOR_SOURCE_FAITHFUL_ECONOMIC_REPLAY"
            if passed
            else "CANONICAL_FACT_DATA_COVERAGE_BLOCKED"
        ),
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("root", type=Path)
    market.add_argument(
        "--session",
        choices=[item.value for item in CapitalizerSession],
        required=True,
    )
    market.add_argument("--output", type=Path, required=True)

    aggregate = sub.add_parser("aggregate")
    aggregate.add_argument("root", type=Path)
    aggregate.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "market":
        report = build_market_report(
            args.root,
            session=CapitalizerSession(args.session),
        )
        args.output.mkdir(parents=True, exist_ok=True)
        symbol = str(report["symbol"]).lower()
        path = args.output / f"capitalizer-v46-phase-b-{symbol}-coverage.json"
    else:
        report = aggregate_reports(args.root)
        args.output.mkdir(parents=True, exist_ok=True)
        path = args.output / "capitalizer-v46-phase-b-aggregate.json"

    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
