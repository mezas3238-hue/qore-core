"""Outcome-free current-MAX_RECOVERY geometry collector for Capitalizer V38.

The authoritative direct replay remains the source of trade identity. This
collector independently reconstructs only information available before entry
for each current recovery family, then joins that geometry to the authoritative
raw replay by causal identity (never by outcome).

A mismatch in selected identities fails closed. No strategy decision changes.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)
from qore.infrastructure.trader_lab import (
    capitalizer_preentry_native_m1_geometry_v38 as geometry,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerSide,
)

IDENTITY = "QORE_CAPITALIZER_PREENTRY_NATIVE_M1_GEOMETRY_COLLECTOR_V38"

IdentityKey = tuple[str, str, str, str, str, str, str]


@dataclass(frozen=True, slots=True)
class SelectedGeometry:
    symbol: str
    session: str
    operating_date: str
    side: str
    h1_open: str
    entry_at: str
    provenance: str
    geometry: geometry.PreentryNativeM1Geometry
    authoritative_identity_joined: bool = True
    outcome_used_for_geometry: bool = False
    exit_used_for_geometry: bool = False

    def __post_init__(self) -> None:
        if not self.authoritative_identity_joined:
            raise ValueError("V38 geometry must join authoritative identity")
        if self.outcome_used_for_geometry or self.exit_used_for_geometry:
            raise ValueError("V38 geometry cannot use outcome/exit")
        if self.geometry.symbol != self.symbol:
            raise ValueError("V38 joined symbol mismatch")
        if self.geometry.side != self.side:
            raise ValueError("V38 joined side mismatch")
        if self.geometry.entry_at != self.entry_at:
            raise ValueError("V38 joined entry timestamp mismatch")


def _identity_from_parts(
    *,
    symbol: str,
    session: str,
    operating_date: str,
    side: str,
    h1_open: datetime,
    entry_at: datetime,
    provenance: str,
) -> IdentityKey:
    return (
        symbol,
        session,
        operating_date,
        side,
        h1_open.isoformat(),
        entry_at.isoformat(),
        provenance,
    )


def _record(
    sink: dict[IdentityKey, geometry.PreentryNativeM1Geometry],
    *,
    key: IdentityKey,
    value: geometry.PreentryNativeM1Geometry,
) -> None:
    prior = sink.get(key)
    if prior is not None and prior != value:
        raise ValueError("V38 geometry identity collision with drift")
    sink[key] = value


def _parallel_rearm_geometry(
    *,
    symbol: str,
    session: CapitalizerSession,
    operating_day: date,
    closeback: Any,
    original_mss: Any,
    execution: tuple[CapitalizerM1Bar, ...],
    m5: tuple[Any, ...],
    m5_closes: tuple[datetime, ...],
    m3: tuple[Any, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: tuple[Any, ...],
    buffer_price: Decimal,
) -> tuple[IdentityKey, geometry.PreentryNativeM1Geometry] | None:
    eligible_at = original_mss.confirmed_at + timedelta(
        minutes=direct.WAIT_MINUTES
    )
    raid = direct.rearm._new_raid(
        execution,
        after=eligible_at,
        before=closeback.h1_deadline,
        liquidity_kind=closeback.reference.kind,
        original_extreme=closeback.sweep_extreme,
    )
    if raid is None:
        return None

    new_closeback_at = direct.rearm._new_closeback(
        m5,
        m5_closes,
        raid_at=raid.opened_at,
        deadline=closeback.h1_deadline,
        liquidity_kind=closeback.reference.kind,
        liquidity_price=closeback.reference.price,
    )
    if new_closeback_at is None:
        return None

    new_mss = direct.find_source_first_m3_mss(
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

    zone = direct.v3._m1_causal_zone(execution, event=new_mss)
    if zone is None:
        return None
    fill = direct.v3._find_m1_fill(
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

    provenance = "WAIT_REJECTED_PARALLEL_REARM"
    key = _identity_from_parts(
        symbol=symbol,
        session=session.value,
        operating_date=operating_day.isoformat(),
        side=closeback.side.value,
        h1_open=closeback.h1_open,
        entry_at=entry_at,
        provenance=provenance,
    )
    value = geometry.build_geometry(
        symbol=symbol,
        side=closeback.side.value,
        entry_at=entry_at,
        entry_price=entry_price,
        stop_price=stop_price,
        stop_buffer_price=buffer_price,
        m5_closeback_at=new_closeback_at,
        mss=new_mss,
        zone=zone,
    )
    return key, value


def _recovery_geometry(
    *,
    all_bars: tuple[CapitalizerM1Bar, ...],
    session: CapitalizerSession,
    start: datetime,
    end: datetime,
) -> dict[IdentityKey, geometry.PreentryNativeM1Geometry]:
    symbol = all_bars[0].symbol
    h1 = direct._aggregate_h1(all_bars)
    h1_swings = direct.v3._build_h1_swings(h1)
    m5 = direct._aggregate_tf(all_bars, minutes=5)
    m5_closes = tuple(item.closed_at for item in m5)
    m3 = direct._aggregate_tf(all_bars, minutes=3)
    m3_closes = tuple(item.closed_at for item in m3)
    m3_pivots = direct._pivots(m3)
    buffer_price = direct.v3._stop_buffer(all_bars)
    execution_by_day, reference_by_day = direct._index_day_inputs(
        all_bars,
        session=session,
    )

    sink: dict[IdentityKey, geometry.PreentryNativeM1Geometry] = {}
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
        previous_day = direct.v3._previous_day_range(
            all_bars,
            operating_day=operating_day,
        )

        for h1_open, h1_deadline, hour_bars in direct.v3._h1_windows(
            execution
        ):
            levels = direct.v3._liquidity_levels(
                prior_session=prior_session,
                previous_day=previous_day,
                h1_swings=h1_swings,
                hour_open=h1_open,
            )
            if not levels:
                continue
            _sweep_seen, closeback = direct.v3._find_sweep_closeback(
                hour_bars,
                levels=levels,
                m5=m5,
                m5_closes=m5_closes,
                h1_open=h1_open,
                h1_deadline=h1_deadline,
            )
            if closeback is None:
                continue

            event = direct.find_source_first_m3_mss(
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
            zone = direct.v3._m1_causal_zone(execution, event=event)
            if zone is None:
                continue
            normal_fill = direct.v3._find_m1_fill(
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
            overlap = (
                zone.overlap_low is not None
                and zone.overlap_high is not None
            )
            eligible_at = event.confirmed_at + timedelta(
                minutes=direct.WAIT_MINUTES
            )
            wait_required = (
                not overlap
                and execution[normal_index].opened_at < eligible_at
            )

            final_index = normal_index
            final_price = normal_price
            if wait_required:
                wait_fill, _wait_status = direct.wait5._find_wait5_fill(
                    execution,
                    event=event,
                    zone=zone,
                    stop_price=original_stop,
                    deadline=h1_deadline,
                )
                if wait_fill is None:
                    recovered = _parallel_rearm_geometry(
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
                        _record(
                            sink,
                            key=recovered[0],
                            value=recovered[1],
                        )
                    continue
                final_index, final_price, _wait_mode = wait_fill

            original_valid = (
                original_stop < final_price
                if closeback.side is CapitalizerSide.LONG
                else original_stop > final_price
            )
            if original_valid:
                continue

            pivot = direct.stop_geometry._protected_pivot(
                m3_pivots,
                before=event.displacement_opened_at,
                side=closeback.side,
            )
            if pivot is None:
                continue
            protected_stop = direct.stop_geometry._buffered_stop(
                side=closeback.side,
                pivot_price=pivot.price,
                buffer_price=buffer_price,
            )
            if not direct.stop_geometry._valid_stop(
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
                direct.wait5._stop_hit(
                    bar,
                    side=closeback.side.value,
                    stop_price=protected_stop,
                )
                for bar in prefill
            ):
                continue

            provenance = "PROTECTED_SWING_GEOMETRY_RESCUE"
            key = _identity_from_parts(
                symbol=symbol,
                session=session.value,
                operating_date=operating_day.isoformat(),
                side=closeback.side.value,
                h1_open=h1_open,
                entry_at=fill_at,
                provenance=provenance,
            )
            value = geometry.build_geometry(
                symbol=symbol,
                side=closeback.side.value,
                entry_at=fill_at,
                entry_price=final_price,
                stop_price=protected_stop,
                stop_buffer_price=buffer_price,
                m5_closeback_at=closeback.closeback_at,
                mss=event,
                zone=zone,
            )
            _record(sink, key=key, value=value)

    return sink


def build_market_geometry(
    m1_root: Path,
    *,
    session: CapitalizerSession,
    start: datetime,
    end: datetime,
) -> tuple[dict[str, Any], tuple[SelectedGeometry, ...]]:
    report, final_raw, _ledgers = direct.build_market_report(
        m1_root,
        session=session,
        start=start,
        end=end,
    )
    lookback = start - timedelta(days=direct.LOOKBACK_DAYS)
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if lookback <= bar.opened_at < end + timedelta(days=1)
    )
    if not all_bars:
        raise ValueError("V38 collector found no provider-native M1")

    with direct._window(start=start, end=end):
        _arb_report, arbitration_rows = direct.arbitration.build_market_report(
            m1_root,
            session=session,
        )

    candidates: dict[
        IdentityKey,
        geometry.PreentryNativeM1Geometry,
    ] = {}
    for row in arbitration_rows:
        direct_trade = direct._direct_from_v3(
            row,
            provenance="CAUSAL_ARBITRATION_BASE",
        )
        _record(
            candidates,
            key=direct._identity(direct_trade),
            value=geometry.from_v3_trade(row),
        )

    recovery_candidates = _recovery_geometry(
        all_bars=all_bars,
        session=session,
        start=start,
        end=end,
    )
    for key, value in recovery_candidates.items():
        _record(candidates, key=key, value=value)

    final_keys = tuple(direct._identity(row) for row in final_raw)
    missing = tuple(key for key in final_keys if key not in candidates)
    if missing:
        raise ValueError(
            "V38 geometry coverage missing authoritative identities: "
            f"{len(missing)}"
        )

    selected = tuple(
        SelectedGeometry(
            symbol=row.symbol,
            session=row.session,
            operating_date=row.operating_date,
            side=row.side,
            h1_open=row.h1_open,
            entry_at=row.entry_at,
            provenance=row.provenance,
            geometry=candidates[direct._identity(row)],
        )
        for row in final_raw
    )
    provenance_counts = Counter(row.provenance for row in final_raw)
    return {
        "identity": IDENTITY,
        "source_replay_identity": report["identity"],
        "symbol": report["symbol"],
        "session": report["session"],
        "window_start": report["window_start"],
        "window_end_exclusive": report["window_end_exclusive"],
        "authoritative_raw_trades": len(final_raw),
        "geometry_rows": len(selected),
        "geometry_coverage": "1",
        "provenance_counts": dict(sorted(provenance_counts.items())),
        "provider_native_m1": True,
        "feature_timestamp_le_entry": True,
        "outcome_used_for_geometry": False,
        "exit_used_for_geometry": False,
        "strategy_rules_changed": False,
        "entry_changed": False,
        "stop_changed": False,
        "target_changed": False,
        "max3_changed": False,
        "fresh_holdout_opened": False,
        "candidate_count": 0,
        "runtime_policy_candidate": False,
        "trader_certified": False,
    }, selected


def load_geometry_rows(
    root: Path,
) -> tuple[SelectedGeometry, ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-preentry-native-m1-geometry-v38-rows.jsonl"
        )
    )
    if not paths:
        raise ValueError("V38 selected geometry files not found")
    rows: list[SelectedGeometry] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for raw in handle:
                if not raw.strip():
                    continue
                item = json.loads(raw)
                if not isinstance(item, dict):
                    raise ValueError("V38 geometry row must be object")
                nested = item.get("geometry")
                if not isinstance(nested, dict):
                    raise ValueError("V38 geometry row missing nested geometry")
                item["geometry"] = geometry.PreentryNativeM1Geometry(**nested)
                rows.append(SelectedGeometry(**item))
    keys = tuple((row.symbol, row.entry_at) for row in rows)
    if len(keys) != len(set(keys)):
        raise ValueError("V38 geometry population has duplicate entrant keys")
    return tuple(
        sorted(
            rows,
            key=lambda row: (datetime.fromisoformat(row.entry_at), row.symbol),
        )
    )


def select_portfolio_geometry(
    geometry_rows: tuple[SelectedGeometry, ...],
    selected_ledger: tuple[milestone.SimulatedTrade, ...],
) -> tuple[SelectedGeometry, ...]:
    """Select exact current entrants without inspecting their realized outcomes."""

    by_key = {
        (row.symbol, row.entry_at): row
        for row in geometry_rows
    }
    if len(by_key) != len(geometry_rows):
        raise ValueError("V38 geometry key collision")
    selected_keys = tuple(
        (row.symbol, row.entry_at)
        for row in selected_ledger
    )
    if len(selected_keys) != len(set(selected_keys)):
        raise ValueError("V38 selected ledger has duplicate entrant keys")
    missing = tuple(key for key in selected_keys if key not in by_key)
    if missing:
        raise ValueError(
            "V38 selected portfolio missing causal geometry: "
            f"{len(missing)}"
        )
    return tuple(by_key[key] for key in selected_keys)


def portfolio_coverage_report(
    *,
    period: str,
    geometry_rows: tuple[SelectedGeometry, ...],
    selected_ledger: tuple[milestone.SimulatedTrade, ...],
) -> dict[str, Any]:
    selected = select_portfolio_geometry(geometry_rows, selected_ledger)
    counts = Counter(row.provenance for row in selected)
    return {
        "identity": (
            "QORE_CAPITALIZER_PREENTRY_NATIVE_M1_GEOMETRY_"
            "PORTFOLIO_COVERAGE_V38"
        ),
        "period": period,
        "selected_entrants": len(selected_ledger),
        "geometry_rows": len(selected),
        "coverage": "1",
        "provenance_counts": dict(sorted(counts.items())),
        "join_key": ["symbol", "entry_at"],
        "selected_realized_outcomes_read_for_join": False,
        "feature_timestamp_le_entry": True,
        "future_bar_used": False,
        "outcome_used_for_geometry": False,
        "fresh_holdout_opened": False,
        "candidate_count": 0,
        "trader_certified": False,
    }


def write_market(
    report: dict[str, Any],
    rows: tuple[SelectedGeometry, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-preentry-native-m1-geometry-v38"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("m1_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--session", required=True, choices=[x.value for x in CapitalizerSession])
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    args = parser.parse_args()

    start = datetime.fromisoformat(args.start)
    end = datetime.fromisoformat(args.end)
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("V38 collector requires aware start/end")

    report, rows = build_market_geometry(
        args.m1_root,
        session=CapitalizerSession(args.session),
        start=start,
        end=end,
    )
    write_market(report, rows, args.output)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
