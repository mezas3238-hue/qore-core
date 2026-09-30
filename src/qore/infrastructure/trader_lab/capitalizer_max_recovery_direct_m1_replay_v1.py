"""Direct native-M1 replay of the frozen Capitalizer MAX_RECOVERY + milestone stack.

Purpose
-------
Rebuild the CURRENT Capitalizer trade universe from provider-native M1 without
reusing consumed development ledgers, then evaluate a frozen milestone-protection
map on a non-overlapping window.

The direct scanner reconstructs exactly the three MAX_RECOVERY_FINAL families:
1. causal closeback arbitration;
2. protected-swing geometry rescue;
3. rejected-WAIT parallel complete-cycle rearm.

It then applies the exact final H1 arbitration and portfolio MAX3 semantics.
Every final trade is replayed at fixed true 2R and through the already-validated
causal R-milestone protection engine.

This module supports arbitrary frozen windows.  A workflow must first prove that
the 2024-09-17 -> 2026-09-17 DEVELOPMENT replay exactly reproduces the canonical
963 raw / 948 MAX3 control before any 2022-09-17 -> 2024-09-17 result may be
called a fresh holdout.

No outcome is used for entry admission or recovery-family selection.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_milestone_walkforward_router_2r_v1 as router,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_v2 as recovery,
)
from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v3_frozen_replay_2y_v1 as frozen_v3,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_no_rearm_closeback_arbitration_2y_v1 as arbitration,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_2y_v1 as wait5,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_stop_invalid_geometry_atlas_2y_v1 as stop_geometry,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait_rearm_atlas_2y_v1 as rearm,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerSession,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    _aggregate_h1,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    _aggregate_tf,
    _index_day_inputs,
    _pivots,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_cisd_v1 import (
    find_source_first_m3_mss,
)

IDENTITY = "QORE_CAPITALIZER_MAX_RECOVERY_DIRECT_M1_REPLAY_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_MAX_RECOVERY_DIRECT_M1_REPLAY_V1"
FREEZE_IDENTITY = "QORE_CAPITALIZER_MILESTONE_DD_UTILITY_MODE_MAP_V1"

DEVELOPMENT_START = datetime(2024, 9, 17, tzinfo=UTC)
DEVELOPMENT_END = datetime(2026, 9, 17, tzinfo=UTC)
HOLDOUT_START = datetime(2022, 9, 17, tzinfo=UTC)
HOLDOUT_END = datetime(2024, 9, 17, tzinfo=UTC)
LOOKBACK_DAYS = 21
TARGET_R = Decimal("2.00")
WAIT_MINUTES = 5

EXPECTED_DEV_RAW = 963
EXPECTED_DEV_MAX3 = 948
EXPECTED_DEV_PF = Decimal("1.466020472120789368123727041")
EXPECTED_DEV_TOTAL_R = Decimal("153.9927998412621697329314877")
EXPECTED_DEV_DD = Decimal("12.93584837435268644582248142")
EXPECTED_DEV_LS = 7


@dataclass(frozen=True, slots=True)
class DirectTrade:
    symbol: str
    session: str
    operating_date: str
    side: str
    h1_open: str
    h1_deadline: str
    entry_at: str
    exit_at: str
    entry_price: str
    stop_price: str
    target_price: str
    realized_gross_r: str
    exit_reason: str
    same_minute_stop_target_ambiguity: bool
    provenance: str
    target_r: str = "2.00"
    outcome_used_for_admission: bool = False


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("direct replay requires timezone-aware timestamp")
    return parsed


@contextmanager
def _window(
    *,
    start: datetime,
    end: datetime,
) -> Iterator[None]:
    if start.tzinfo is None or end.tzinfo is None or not start < end:
        raise ValueError("direct replay window must be aware and increasing")
    lookback = start - timedelta(days=LOOKBACK_DAYS)

    old_frozen = (
        frozen_v3.WINDOW_START,
        frozen_v3.WINDOW_END,
        frozen_v3.LOOKBACK_START,
    )
    mutable_wait5: Any = wait5
    mutable_v3: Any = v3
    old_wait = (
        mutable_wait5.WINDOW_START,
        mutable_wait5.WINDOW_END,
        mutable_wait5.LOOKBACK_START,
    )
    old_v3 = (
        mutable_v3.WINDOW_START,
        mutable_v3.WINDOW_END,
        mutable_v3.LOOKBACK_START,
    )
    try:
        frozen_v3.WINDOW_START = start
        frozen_v3.WINDOW_END = end
        frozen_v3.LOOKBACK_START = lookback
        mutable_wait5.WINDOW_START = start
        mutable_wait5.WINDOW_END = end
        mutable_wait5.LOOKBACK_START = lookback
        mutable_v3.WINDOW_START = start
        mutable_v3.WINDOW_END = end
        mutable_v3.LOOKBACK_START = lookback
        yield
    finally:
        (
            frozen_v3.WINDOW_START,
            frozen_v3.WINDOW_END,
            frozen_v3.LOOKBACK_START,
        ) = old_frozen
        (
            mutable_wait5.WINDOW_START,
            mutable_wait5.WINDOW_END,
            mutable_wait5.LOOKBACK_START,
        ) = old_wait
        (
            mutable_v3.WINDOW_START,
            mutable_v3.WINDOW_END,
            mutable_v3.LOOKBACK_START,
        ) = old_v3


def _direct_from_v3(
    trade: v3.V3Trade,
    *,
    provenance: str,
) -> DirectTrade:
    return DirectTrade(
        symbol=trade.symbol,
        session=trade.session,
        operating_date=trade.operating_date,
        side=trade.side,
        h1_open=trade.h1_open,
        h1_deadline=trade.h1_deadline,
        entry_at=trade.entry_at,
        exit_at=trade.exit_at,
        entry_price=trade.entry_price,
        stop_price=trade.stop_price,
        target_price=trade.target_price,
        realized_gross_r=trade.realized_gross_r,
        exit_reason=trade.exit_reason,
        same_minute_stop_target_ambiguity=trade.same_minute_stop_target_ambiguity,
        provenance=provenance,
    )


def _recovery_proxy(trade: DirectTrade) -> recovery.RecoveryTrade:
    return recovery.RecoveryTrade(
        symbol=trade.symbol,
        session=trade.session,
        operating_date=trade.operating_date,
        side=trade.side,
        h1_open=trade.h1_open,
        h1_deadline=trade.h1_deadline,
        entry_at=trade.entry_at,
        exit_at=trade.exit_at,
        realized_gross_r=trade.realized_gross_r,
        exit_reason=trade.exit_reason,
        same_minute_stop_target_ambiguity=trade.same_minute_stop_target_ambiguity,
        provenance=trade.provenance,
    )


def _identity(trade: DirectTrade) -> tuple[str, str, str, str, str, str, str]:
    return (
        trade.symbol,
        trade.session,
        trade.operating_date,
        trade.side,
        trade.h1_open,
        trade.entry_at,
        trade.provenance,
    )


def _finish_trade(
    *,
    symbol: str,
    session: CapitalizerSession,
    operating_day: date,
    side: CapitalizerSide,
    h1_open: datetime,
    h1_deadline: datetime,
    entry_at: datetime,
    entry_price: Decimal,
    stop_price: Decimal,
    execution: tuple[CapitalizerM1Bar, ...],
    entry_index: int,
    provenance: str,
) -> DirectTrade:
    risk = abs(entry_price - stop_price)
    if risk <= 0:
        raise ValueError("direct recovery trade requires positive risk")
    target_price = (
        entry_price + TARGET_R * risk
        if side is CapitalizerSide.LONG
        else entry_price - TARGET_R * risk
    )
    realized, reason, _held, ambiguous, exit_at = v3._lifecycle(
        execution,
        entry_index=entry_index,
        side=side,
        entry_price=entry_price,
        stop_price=stop_price,
        target_price=target_price,
        deadline=h1_deadline,
    )
    return DirectTrade(
        symbol=symbol,
        session=session.value,
        operating_date=operating_day.isoformat(),
        side=side.value,
        h1_open=h1_open.isoformat(),
        h1_deadline=h1_deadline.isoformat(),
        entry_at=entry_at.isoformat(),
        exit_at=exit_at.isoformat(),
        entry_price=str(entry_price),
        stop_price=str(stop_price),
        target_price=str(target_price),
        realized_gross_r=str(realized),
        exit_reason=reason,
        same_minute_stop_target_ambiguity=ambiguous,
        provenance=provenance,
    )


def _parallel_rearm(
    *,
    symbol: str,
    session: CapitalizerSession,
    operating_day: date,
    closeback: v3.SweepCloseback,
    original_mss: v3.M3MssEvent,
    execution: tuple[CapitalizerM1Bar, ...],
    m5: tuple[Any, ...],
    m5_closes: tuple[datetime, ...],
    m3: tuple[Any, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: tuple[Any, ...],
    buffer_price: Decimal,
) -> DirectTrade | None:
    eligible_at = original_mss.confirmed_at + timedelta(minutes=WAIT_MINUTES)
    raid = rearm._new_raid(
        execution,
        after=eligible_at,
        before=closeback.h1_deadline,
        liquidity_kind=closeback.reference.kind,
        original_extreme=closeback.sweep_extreme,
    )
    if raid is None:
        return None

    new_closeback_at = rearm._new_closeback(
        m5,
        m5_closes,
        raid_at=raid.opened_at,
        deadline=closeback.h1_deadline,
        liquidity_kind=closeback.reference.kind,
        liquidity_price=closeback.reference.price,
    )
    if new_closeback_at is None:
        return None

    new_mss = find_source_first_m3_mss(
        m3,
        m3_closes,
        m3_pivots,
        sweep_at=raid.opened_at,
        after=new_closeback_at,
        before=closeback.h1_deadline,
        side=closeback.side,
    )
    if new_mss is None:
        return None

    zone = v3._m1_causal_zone(execution, event=new_mss)
    if zone is None:
        return None
    fill = v3._find_m1_fill(
        execution,
        event=new_mss,
        zone=zone,
        deadline=closeback.h1_deadline,
    )
    if fill is None:
        return None
    entry_index, entry_price, _mode = fill
    entry_at = execution[entry_index].opened_at
    stop_price = (
        new_mss.broken_swing_price - buffer_price
        if closeback.side is CapitalizerSide.LONG
        else new_mss.broken_swing_price + buffer_price
    )
    valid = (
        stop_price < entry_price
        if closeback.side is CapitalizerSide.LONG
        else stop_price > entry_price
    )
    if not valid:
        return None

    return _finish_trade(
        symbol=symbol,
        session=session,
        operating_day=operating_day,
        side=closeback.side,
        h1_open=closeback.h1_open,
        h1_deadline=closeback.h1_deadline,
        entry_at=entry_at,
        entry_price=entry_price,
        stop_price=stop_price,
        execution=execution,
        entry_index=entry_index,
        provenance="WAIT_REJECTED_PARALLEL_REARM",
    )


def _current_first_recoveries(
    *,
    all_bars: tuple[CapitalizerM1Bar, ...],
    session: CapitalizerSession,
    start: datetime,
    end: datetime,
) -> tuple[tuple[DirectTrade, ...], tuple[DirectTrade, ...], Counter[str]]:
    symbol = all_bars[0].symbol
    h1 = _aggregate_h1(all_bars)
    h1_swings = v3._build_h1_swings(h1)
    m5 = _aggregate_tf(all_bars, minutes=5)
    m5_closes = tuple(item.closed_at for item in m5)
    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_closes = tuple(item.closed_at for item in m3)
    m3_pivots = _pivots(m3)
    buffer_price = v3._stop_buffer(all_bars)
    execution_by_day, reference_by_day = _index_day_inputs(
        all_bars,
        session=session,
    )

    protected: list[DirectTrade] = []
    rearms: list[DirectTrade] = []
    counts: Counter[str] = Counter()

    dates = sorted(
        key
        for key in execution_by_day
        if start.date().isoformat() <= key < end.date().isoformat()
    )
    for value in dates:
        operating_day = date.fromisoformat(value)
        execution = execution_by_day.get(value, ())
        if len(execution) < 15:
            continue
        prior_session = reference_by_day.get(value)
        previous_day = v3._previous_day_range(
            all_bars,
            operating_day=operating_day,
        )

        for h1_open, h1_deadline, hour_bars in v3._h1_windows(execution):
            levels = v3._liquidity_levels(
                prior_session=prior_session,
                previous_day=previous_day,
                h1_swings=h1_swings,
                hour_open=h1_open,
            )
            if not levels:
                continue
            _sweep_seen, closeback = v3._find_sweep_closeback(
                hour_bars,
                levels=levels,
                m5=m5,
                m5_closes=m5_closes,
                h1_open=h1_open,
                h1_deadline=h1_deadline,
            )
            if closeback is None:
                continue

            event = find_source_first_m3_mss(
                m3,
                m3_closes,
                m3_pivots,
                sweep_at=closeback.sweep_at,
                after=closeback.closeback_at,
                before=h1_deadline,
                side=closeback.side,
            )
            if event is None:
                continue
            zone = v3._m1_causal_zone(execution, event=event)
            if zone is None:
                continue
            normal_fill = v3._find_m1_fill(
                execution,
                event=event,
                zone=zone,
                deadline=h1_deadline,
            )
            if normal_fill is None:
                continue

            original_stop = (
                event.broken_swing_price - buffer_price
                if closeback.side is CapitalizerSide.LONG
                else event.broken_swing_price + buffer_price
            )
            normal_index, normal_price, _normal_mode = normal_fill
            overlap = zone.overlap_low is not None and zone.overlap_high is not None
            eligible_at = event.confirmed_at + timedelta(minutes=WAIT_MINUTES)
            wait_required = (
                not overlap and execution[normal_index].opened_at < eligible_at
            )

            final_index = normal_index
            final_price = normal_price
            if wait_required:
                wait_fill, wait_status = wait5._find_wait5_fill(
                    execution,
                    event=event,
                    zone=zone,
                    stop_price=original_stop,
                    deadline=h1_deadline,
                )
                if wait_fill is None:
                    counts[f"WAIT_REJECTED:{wait_status}"] += 1
                    recovered = _parallel_rearm(
                        symbol=symbol,
                        session=session,
                        operating_day=operating_day,
                        closeback=closeback,
                        original_mss=event,
                        execution=execution,
                        m5=m5,
                        m5_closes=m5_closes,
                        m3=m3,
                        m3_closes=m3_closes,
                        m3_pivots=m3_pivots,
                        buffer_price=buffer_price,
                    )
                    if recovered is not None:
                        rearms.append(recovered)
                        counts["WAIT_REARM_EXECUTABLE"] += 1
                    continue
                final_index, final_price, _wait_mode = wait_fill

            original_valid = (
                original_stop < final_price
                if closeback.side is CapitalizerSide.LONG
                else original_stop > final_price
            )
            if original_valid:
                continue

            counts["STOP_INVALID_GEOMETRY"] += 1
            pivot = stop_geometry._protected_pivot(
                m3_pivots,
                before=event.displacement_opened_at,
                side=closeback.side,
            )
            if pivot is None:
                continue
            protected_stop = stop_geometry._buffered_stop(
                side=closeback.side,
                pivot_price=pivot.price,
                buffer_price=buffer_price,
            )
            if not stop_geometry._valid_stop(
                side=closeback.side,
                entry_price=final_price,
                stop_price=protected_stop,
            ):
                continue

            fill_at = execution[final_index].opened_at
            prefill = tuple(
                bar
                for bar in execution
                if event.confirmed_at <= bar.opened_at < fill_at
            )
            if any(
                wait5._stop_hit(
                    bar,
                    side=closeback.side.value,
                    stop_price=protected_stop,
                )
                for bar in prefill
            ):
                continue

            protected.append(
                _finish_trade(
                    symbol=symbol,
                    session=session,
                    operating_day=operating_day,
                    side=closeback.side,
                    h1_open=h1_open,
                    h1_deadline=h1_deadline,
                    entry_at=fill_at,
                    entry_price=final_price,
                    stop_price=protected_stop,
                    execution=execution,
                    entry_index=final_index,
                    provenance="PROTECTED_SWING_GEOMETRY_RESCUE",
                )
            )
            counts["PROTECTED_SWING_RESCUE"] += 1

    return (
        tuple(sorted(protected, key=lambda item: (_aware(item.entry_at), item.symbol))),
        tuple(sorted(rearms, key=lambda item: (_aware(item.entry_at), item.symbol))),
        counts,
    )


def _final_h1_union(
    trades: tuple[DirectTrade, ...],
) -> tuple[DirectTrade, ...]:
    direct_by_key = {_identity(item): item for item in trades}
    if len(direct_by_key) != len(trades):
        raise ValueError("direct recovery identity collision")

    selected_proxy, _duplicates, _ties = recovery._arbitrate_h1(
        tuple(_recovery_proxy(item) for item in trades)
    )
    selected: list[DirectTrade] = []
    for item in selected_proxy:
        key = (
            item.symbol,
            item.session,
            item.operating_date,
            item.side,
            item.h1_open,
            item.entry_at,
            item.provenance,
        )
        direct = direct_by_key.get(key)
        if direct is None:
            raise ValueError("direct recovery arbitration mapping failed")
        selected.append(direct)
    return tuple(
        sorted(selected, key=lambda item: (_aware(item.entry_at), item.symbol))
    )


def _portfolio_max3(
    trades: tuple[DirectTrade, ...],
) -> tuple[DirectTrade, ...]:
    grouped: dict[str, list[DirectTrade]] = defaultdict(list)
    for trade in trades:
        grouped[f"{trade.session}:{trade.operating_date}"].append(trade)
    selected: list[DirectTrade] = []
    for key in sorted(grouped):
        ordered = sorted(
            grouped[key],
            key=lambda item: (_aware(item.entry_at), item.symbol),
        )
        selected.extend(ordered[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(
        sorted(selected, key=lambda item: (_aware(item.entry_at), item.symbol))
    )


def _target_outcome(trade: DirectTrade) -> Any:
    from qore.infrastructure.trader_lab import (
        capitalizer_max_recovery_target_sensitivity_2y_v1 as target_v1,
    )

    return target_v1.TargetOutcome(
        symbol=trade.symbol,
        session=trade.session,
        operating_date=trade.operating_date,
        side=trade.side,
        h1_open=trade.h1_open,
        h1_deadline=trade.h1_deadline,
        entry_at=trade.entry_at,
        entry_price=trade.entry_price,
        stop_price=trade.stop_price,
        target_r="2.00",
        target_price=trade.target_price,
        exit_at=trade.exit_at,
        realized_gross_r=trade.realized_gross_r,
        exit_reason=trade.exit_reason,
        same_minute_stop_target_ambiguity=trade.same_minute_stop_target_ambiguity,
        provenance=trade.provenance,
    )


def _milestone_ledgers(
    final_raw: tuple[DirectTrade, ...],
    *,
    all_bars: tuple[CapitalizerM1Bar, ...],
    session: CapitalizerSession,
) -> dict[str, tuple[milestone.SimulatedTrade, ...]]:
    execution_by_day, _ = _index_day_inputs(all_bars, session=session)
    result: dict[str, list[milestone.SimulatedTrade]] = {
        mode.value: [] for mode in milestone.ProtectionMode
    }

    for trade in final_raw:
        execution = execution_by_day.get(trade.operating_date, ())
        if not execution:
            raise ValueError("milestone direct replay missing execution day")
        by_open = {bar.opened_at: index for index, bar in enumerate(execution)}
        outcome = _target_outcome(trade)
        for mode in milestone.ProtectionMode:
            simulated = milestone._simulate(
                outcome,
                bars=execution,
                by_open=by_open,
                mode=mode,
            )
            result[mode.value].append(simulated)

    return {
        mode: tuple(
            sorted(rows, key=lambda item: (_aware(item.entry_at), item.symbol))
        )
        for mode, rows in result.items()
    }


def build_market_report(
    m1_root: Path,
    *,
    session: CapitalizerSession,
    start: datetime,
    end: datetime,
) -> tuple[
    dict[str, Any],
    tuple[DirectTrade, ...],
    dict[str, tuple[milestone.SimulatedTrade, ...]],
]:
    lookback = start - timedelta(days=LOOKBACK_DAYS)
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if lookback <= bar.opened_at < end + timedelta(days=1)
    )
    if not all_bars:
        raise ValueError("direct MAX_RECOVERY replay found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("direct MAX_RECOVERY replay requires one symbol")

    with _window(start=start, end=end):
        _arb_report, arbitration_rows = arbitration.build_market_report(
            m1_root,
            session=session,
        )

    arbitration_direct = tuple(
        _direct_from_v3(item, provenance="CAUSAL_ARBITRATION_BASE")
        for item in arbitration_rows
    )
    protected, rearms, recovery_counts = _current_first_recoveries(
        all_bars=all_bars,
        session=session,
        start=start,
        end=end,
    )
    final_raw = _final_h1_union(
        tuple((*arbitration_direct, *protected, *rearms))
    )

    ledgers = _milestone_ledgers(
        final_raw,
        all_bars=all_bars,
        session=session,
    )
    original = ledgers[milestone.ProtectionMode.ORIGINAL.value]
    baseline_by_key = {
        (item.symbol, item.entry_at): item for item in final_raw
    }
    mismatches = 0
    for row in original:
        source = baseline_by_key[(row.symbol, row.entry_at)]
        if (
            Decimal(row.realized_gross_r) != Decimal(source.realized_gross_r)
            or row.exit_reason != source.exit_reason
            or row.exit_at != source.exit_at
            or row.same_minute_stop_target_ambiguity
            != source.same_minute_stop_target_ambiguity
        ):
            mismatches += 1

    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "window_start": start.isoformat(),
        "window_end_exclusive": end.isoformat(),
        "lookback_start": lookback.isoformat(),
        "arbitration_raw": len(arbitration_direct),
        "protected_rescue_raw": len(protected),
        "wait_rearm_raw": len(rearms),
        "final_h1_raw": len(final_raw),
        "recovery_counts": dict(sorted(recovery_counts.items())),
        "original_milestone_reproduction_mismatches": mismatches,
        "provider_native_m1": True,
        "three_recovery_families_rebuilt_from_m1": True,
        "one_trade_per_market_h1": True,
        "earliest_causal_entry_wins": True,
        "portfolio_max3_applied_only_in_matrix": True,
        "fixed_2r": True,
        "outcome_used_for_admission": False,
        "milestone_modes_selected": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }, final_raw, ledgers


def write_market(
    report: dict[str, Any],
    final_raw: tuple[DirectTrade, ...],
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-max-recovery-direct-m1-replay-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-final-raw.jsonl").open("w", encoding="utf-8") as handle:
        for row in final_raw:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")
    for mode, rows in ledgers.items():
        with (output / f"{stem}-{mode.lower()}-trades.jsonl").open(
            "w",
            encoding="utf-8",
        ) as handle:
            for simulated in rows:
                handle.write(json.dumps(asdict(simulated), sort_keys=True) + "\n")


def _load_mode(
    root: Path,
    *,
    mode: milestone.ProtectionMode,
) -> tuple[milestone.SimulatedTrade, ...]:
    pattern = (
        "capitalizer-*-max-recovery-direct-m1-replay-v1-"
        f"{mode.value.lower()}-trades.jsonl"
    )
    paths = sorted(root.rglob(pattern))
    if len(paths) != 9:
        raise ValueError(f"direct matrix requires 9 {mode.value} ledgers")
    rows: list[milestone.SimulatedTrade] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(milestone.SimulatedTrade(**json.loads(line)))
    return tuple(
        sorted(rows, key=lambda item: (_aware(item.entry_at), item.symbol))
    )


def _max3_milestone(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> tuple[milestone.SimulatedTrade, ...]:
    grouped: dict[str, list[milestone.SimulatedTrade]] = defaultdict(list)
    for row in rows:
        grouped[f"{row.session}:{row.operating_date}"].append(row)
    selected: list[milestone.SimulatedTrade] = []
    for key in sorted(grouped):
        selected.extend(
            sorted(
                grouped[key],
                key=lambda item: (_aware(item.entry_at), item.symbol),
            )[:MAX_EXECUTIONS_PER_SESSION]
        )
    return tuple(
        sorted(selected, key=lambda item: (_aware(item.entry_at), item.symbol))
    )


def _dd_utility(rows: tuple[milestone.SimulatedTrade, ...]) -> Decimal:
    metrics = milestone._metrics(rows)
    mean_r = Decimal(str(metrics["total_r"])) / Decimal(len(rows))
    dd = Decimal(str(metrics["max_drawdown_r"]))
    return router._score(
        policy="DD_UTILITY",
        mean_r=mean_r,
        negative_rate=Decimal("0"),
        downside=Decimal("0"),
        dd=dd,
    )


def _development_mode_map(
    selected: dict[str, tuple[milestone.SimulatedTrade, ...]],
) -> dict[str, str]:
    symbols = sorted(
        {row.symbol for row in selected[milestone.ProtectionMode.ORIGINAL.value]}
    )
    result: dict[str, str] = {}
    for symbol in symbols:
        candidates: list[tuple[Decimal, Decimal, Decimal, str]] = []
        for mode in milestone.ProtectionMode:
            rows = tuple(
                row for row in selected[mode.value] if row.symbol == symbol
            )
            if not rows:
                raise ValueError("mode-map market lost all MAX3 trades")
            metrics = milestone._metrics(rows)
            score = _dd_utility(rows)
            mean_r = Decimal(str(metrics["total_r"])) / Decimal(len(rows))
            dd = Decimal(str(metrics["max_drawdown_r"]))
            candidates.append((score, mean_r, -dd, mode.value))
        result[symbol] = max(candidates)[3]
    return result


def _mapped_ledger(
    selected: dict[str, tuple[milestone.SimulatedTrade, ...]],
    mode_map: dict[str, str],
) -> tuple[milestone.SimulatedTrade, ...]:
    indexes = {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in selected.items()
    }
    baseline = selected[milestone.ProtectionMode.ORIGINAL.value]
    result: list[milestone.SimulatedTrade] = []
    for row in baseline:
        mode = mode_map.get(row.symbol)
        if mode is None or mode not in indexes:
            raise ValueError(f"frozen mode map missing valid mode for {row.symbol}")
        result.append(indexes[mode][(row.symbol, row.entry_at)])
    return tuple(
        sorted(result, key=lambda item: (_aware(item.entry_at), item.symbol))
    )


def build_matrix(
    root: Path,
    *,
    role: str,
    frozen_map_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    reports = sorted(root.rglob("capitalizer-*-max-recovery-direct-m1-replay-v1.json"))
    if len(reports) != 9:
        raise ValueError(f"direct matrix requires 9 market reports, got {len(reports)}")
    market_reports = [
        dict(json.loads(path.read_text(encoding="utf-8"))) for path in reports
    ]
    if sum(int(item["original_milestone_reproduction_mismatches"]) for item in market_reports):
        raise ValueError("direct replay milestone ORIGINAL did not reproduce baseline")

    raw_by_mode = {
        mode.value: _load_mode(root, mode=mode)
        for mode in milestone.ProtectionMode
    }
    selected = {
        mode: _max3_milestone(rows) for mode, rows in raw_by_mode.items()
    }
    original = selected[milestone.ProtectionMode.ORIGINAL.value]
    original_metrics = milestone._metrics(original)

    variants = {
        mode: milestone._metrics(rows) for mode, rows in selected.items()
    }

    freeze: dict[str, Any] | None = None
    frozen_metrics: dict[str, Any] | None = None
    mode_map: dict[str, str] | None = None

    if role == "DEVELOPMENT":
        raw_original = raw_by_mode[milestone.ProtectionMode.ORIGINAL.value]
        if len(raw_original) != EXPECTED_DEV_RAW:
            raise ValueError(
                f"direct development raw control mismatch: {len(raw_original)}"
            )
        if len(original) != EXPECTED_DEV_MAX3:
            raise ValueError(
                f"direct development MAX3 control mismatch: {len(original)}"
            )
        if Decimal(str(original_metrics["profit_factor"])) != EXPECTED_DEV_PF:
            raise ValueError("direct development PF control mismatch")
        if Decimal(str(original_metrics["total_r"])) != EXPECTED_DEV_TOTAL_R:
            raise ValueError("direct development Total-R control mismatch")
        if Decimal(str(original_metrics["max_drawdown_r"])) != EXPECTED_DEV_DD:
            raise ValueError("direct development DD control mismatch")
        if int(original_metrics["max_losing_streak"]) != EXPECTED_DEV_LS:
            raise ValueError("direct development losing-streak control mismatch")

        mode_map = _development_mode_map(selected)
        frozen_ledger = _mapped_ledger(selected, mode_map)
        frozen_metrics = milestone._metrics(frozen_ledger)
        freeze = {
            "identity": FREEZE_IDENTITY,
            "source_role": "DEVELOPMENT",
            "source_window_start": DEVELOPMENT_START.isoformat(),
            "source_window_end_exclusive": DEVELOPMENT_END.isoformat(),
            "selection_policy": "PER_MARKET_DD_UTILITY",
            "dd_utility_penalty_per_r": "0.03",
            "mode_map": mode_map,
            "holdout_outcomes_visible_to_selection": False,
            "map_frozen_before_holdout_aggregation": True,
            "automatic_promotion_allowed": False,
        }
    elif role == "FRESH_HOLDOUT":
        if frozen_map_path is None:
            raise ValueError("fresh holdout requires frozen development mode map")
        freeze = dict(json.loads(frozen_map_path.read_text(encoding="utf-8")))
        if freeze.get("identity") != FREEZE_IDENTITY:
            raise ValueError("unexpected frozen mode-map identity")
        raw_map = freeze.get("mode_map")
        if not isinstance(raw_map, dict):
            raise ValueError("frozen mode map missing map")
        mode_map = {str(key): str(value) for key, value in raw_map.items()}
        frozen_ledger = _mapped_ledger(selected, mode_map)
        frozen_metrics = milestone._metrics(frozen_ledger)
    else:
        raise ValueError("role must be DEVELOPMENT or FRESH_HOLDOUT")

    global_lock = variants[milestone.ProtectionMode.LOCK025_AFTER_075.value]

    report = {
        "identity": MATRIX_IDENTITY,
        "evaluation_role": role,
        "market_count": 9,
        "raw_trades": len(raw_by_mode[milestone.ProtectionMode.ORIGINAL.value]),
        "max3_trades": len(original),
        "density_retention": "1",
        "original_metrics": original_metrics,
        "mode_metrics": variants,
        "global_lock025_after_075_metrics": global_lock,
        "frozen_dd_utility_mode_map": mode_map,
        "frozen_dd_utility_metrics": frozen_metrics,
        "three_recovery_families_rebuilt_from_native_m1": True,
        "development_control_reproduction_required": True,
        "holdout_outcomes_visible_to_mode_map_selection": False,
        "same_fixed_2r": True,
        "same_max3": True,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }
    return report, freeze


def write_matrix(
    report: dict[str, Any],
    freeze: dict[str, Any] | None,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-nine-market-max-recovery-direct-m1-replay-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if freeze is not None and report["evaluation_role"] == "DEVELOPMENT":
        (output / "capitalizer-milestone-dd-utility-mode-map-v1.json").write_text(
            json.dumps(freeze, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("timestamp must include UTC offset")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    market.add_argument("--session", required=True, choices=[x.value for x in CapitalizerSession])
    market.add_argument("--start", required=True, type=_parse_dt)
    market.add_argument("--end-exclusive", required=True, type=_parse_dt)

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    matrix.add_argument("--role", required=True, choices=["DEVELOPMENT", "FRESH_HOLDOUT"])
    matrix.add_argument("--frozen-map", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report, final_raw, ledgers = build_market_report(
            args.m1_root,
            session=CapitalizerSession(args.session),
            start=args.start,
            end=args.end_exclusive,
        )
        write_market(report, final_raw, ledgers, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report, freeze = build_matrix(
        args.input_root,
        role=args.role,
        frozen_map_path=args.frozen_map,
    )
    write_matrix(report, freeze, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
