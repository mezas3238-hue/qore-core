#!/usr/bin/env python3
"""Causal 3Y research offer ledger for the ONE cleanroom VT31 trader.

The owner wants original ICT M1 logic, one trader for London+NY, and genuine
economic execution. This step constructs exact source offers and their causal
M1 terminal paths, but REFUSES to infer MT5 fills from source-only M1 OHLC.
No bid/ask tick artifact is supplied by this immutable 3Y source.
No old VT31 strategy or outcomes are used. Fresh holdout remains SEALED.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    MethodologyDecision,
    SessionId,
    window_bounds,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.order_lifecycle import (
    SourceLimitOrderAudit,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.trader import VT31Trader

NY = ZoneInfo("America/New_York")
SESSIONS = {3: SessionId.LONDON, 10: SessionId.NY_AM, 14: SessionId.NY_PM}
SOURCE_SHA = "0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa"
SOURCE_ID = "VT31_NAS100_OWNER_3Y_BASE_001"


def _dt(v: object) -> datetime:
    t = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("source timestamp requires UTC timezone")
    return t.astimezone(UTC)


def _m1(x: dict[str, Any]) -> M1Bar:
    return M1Bar(
        _dt(x["opened_at"]), _dt(x["closed_at"]),
        Decimal(str(x["open"])), Decimal(str(x["high"])),
        Decimal(str(x["low"])), Decimal(str(x["close"])),
    )


def _complete(bars: list[M1Bar], session: SessionId) -> bool:
    if len(bars) != 60:
        return False
    start, end = window_bounds(bars[0].opened_at, session)
    return (
        bars[-1].closed_at == end
        and all(
            bar.opened_at == start + timedelta(minutes=i)
            for i, bar in enumerate(bars)
        )
    )


def audit(rows: Iterable[dict[str, Any]]) -> dict[str, object]:
    trader = VT31Trader()
    m1_total = 0
    last_open: datetime | None = None
    pending_key: tuple[str, SessionId] | None = None
    pending_bars: list[M1Bar] = []
    coverage: Counter[str] = Counter()
    partial: Counter[str] = Counter()
    candidates: Counter[str] = Counter()
    phase_counts: Counter[str] = Counter()
    study_events: list[dict[str, object]] = []
    bidask_columns: Counter[str] = Counter()
    total_real_broker_quote_rows = 0
    started = time.perf_counter()

    def flush() -> None:
        nonlocal pending_key, pending_bars
        if pending_key is None:
            return
        day, window = pending_key
        if not _complete(pending_bars, window):
            partial[window.value] += 1
            for m1 in pending_bars:
                trader.research_observe_incomplete_source_m1(m1)
            pending_key, pending_bars = None, []
            return

        coverage[window.value] += 1
        offer: SourceLimitOrderAudit | None = None
        first_observed_touch: datetime | None = None
        first_ambiguous: datetime | None = None
        first_cognitive_revocation: datetime | None = None
        first_revocation_bar_overlap: datetime | None = None

        for m1 in pending_bars:
            observation = trader.on_closed_m1(m1)
            ops = trader._windows[(day, window)]
            phase = observation.operational_phase
            if phase is None:
                raise AssertionError("complete source M1 must have OPS phase")
            if offer is None and ops.first_suitable is not None:
                source = ops.first_suitable
                offer = SourceLimitOrderAudit(
                    client_order_id=(
                        f"VT31-NAS100-{day}-{window.name}-"
                        f"{source.formed_at.isoformat()}"
                    ),
                    source=source,
                    offered_at=source.formed_at,
                    source_provenance=ops.cognitive_source or "UNKNOWN_COG",
                )
                candidates[window.value] += 1
            if offer is None:
                continue
            gross_ce_overlap = (
                m1.closed_at > offer.offered_at
                and m1.low <= offer.source.consequent_encroachment <= m1.high
            )
            if (
                gross_ce_overlap
                and first_observed_touch is None
                and phase in (
                    MethodologyDecision.RESEARCH_PENDING_CE,
                    MethodologyDecision.RESEARCH_TOUCH_NOT_FILL,
                )
            ):
                # Research-only OHLC price overlap BEFORE a terminal
                # cancellation. Never count later prices from a canceled
                # order as a potential quote crossing or a real fill.
                first_observed_touch = m1.closed_at
            if (
                gross_ce_overlap
                and phase is MethodologyDecision.SOURCE_INVALIDATED
                and first_revocation_bar_overlap is None
            ):
                # No intrabar tick ordering exists: a CE-touch and COG
                # cancellation both appear in this CLOSED M1. The outcome
                # is UNKNOWN, not an eligible quote fill.
                first_revocation_bar_overlap = m1.closed_at
            if phase is MethodologyDecision.AMBIGUOUS_PRICE_PATH:
                first_ambiguous = first_ambiguous or m1.closed_at
            if phase is MethodologyDecision.SOURCE_INVALIDATED:
                first_cognitive_revocation = first_cognitive_revocation or m1.closed_at
                if offer.execution is not None:
                    raise AssertionError("research cannot invent broker ACK")
                if offer.state.value not in (
                    "INVALIDATED_BEFORE_PROVEN_FILL",
                    "EXPIRED_BEFORE_PROVEN_FILL",
                ):
                    offer.invalidate_source(m1.closed_at)

        if offer is not None:
            if offer.state.value != "INVALIDATED_BEFORE_PROVEN_FILL":
                offer.expire(window_bounds(pending_bars[0].opened_at, window)[1])
            ops = trader._windows[(day, window)]
            source = offer.source
            phase_counts[window.value + ":" + ops.decision.value] += 1
            snap = offer.snapshot()
            if snap["ack_id"] is not None or snap["source_order_routed"]:
                raise AssertionError("source OHLC is not authenticated broker execution")
            study_events.append({
                "client_order_id": offer.client_order_id,
                "ny_day": day,
                "trader_id": "VT31",
                "session_window": window.value,
                "session_model": (
                    "LONDON" if window is SessionId.LONDON else "NEW_YORK"
                ),
                "side": source.side.value,
                "formed_at": source.formed_at.isoformat(),
                "source_first_m1_open": source.first_candle_open.isoformat(),
                "m1_ce_research_limit": str(source.consequent_encroachment),
                "draw_target": str(source.target_price),
                "m1_projected_index_points": str(source.projected_index_points),
                "m1_touch_observed_at_not_fill": (
                    None if first_observed_touch is None
                    else first_observed_touch.isoformat()
                ),
                "m1_ambiguous_price_path_at": (
                    None if first_ambiguous is None
                    else first_ambiguous.isoformat()
                ),
                "m1_ce_overlap_same_m1_as_source_revocation": (
                    None if first_revocation_bar_overlap is None
                    else first_revocation_bar_overlap.isoformat()
                ),
                "cognition_lost_or_source_invalidated_at": (
                    None if first_cognitive_revocation is None
                    else first_cognitive_revocation.isoformat()
                ),
                "final_source_phase": ops.decision.value,
                "source_invalidation_reason": (
                    ops.source_invalidation_reason
                    or (
                        "M1_SOURCE_ZONE_INVALIDATED"
                        if ops.decision is MethodologyDecision.SOURCE_INVALIDATED
                        else None
                    )
                ),
                "research_order_terminal": offer.state.value,
                "bid_ask_quote_crossing_proven": False,
                "actual_broker_order_submitted": False,
                "broker_execution_ack": None,
                "paper_fill_count": 0,
                "live_fill_count": 0,
            })
        pending_key, pending_bars = None, []

    for row in rows:
        m1 = _m1(row)
        if last_open is not None and m1.opened_at <= last_open:
            raise ValueError("frozen 3Y M1 not strictly chronological")
        last_open = m1.opened_at
        m1_total += 1
        # Source bars are OHLC. Even if a minute-level bid/ask field were
        # present, WITHOUT tick timestamps and broker matching it would
        # still be insufficient to prove fills.
        if m1_total == 1:
            for key in sorted(row):
                bidask_columns["M1_FIELD:" + key] += 1

        local = m1.opened_at.astimezone(NY)
        window = SESSIONS.get(local.hour)
        key = (
            (local.date().isoformat(), window)
            if window is not None else None
        )
        if key != pending_key:
            flush()
        if key is None:
            outside = trader.on_closed_m1(m1)
            if outside.session_window is not None:
                raise AssertionError("outside ICT clock opened source session")
        else:
            pending_key = key
            pending_bars.append(m1)
    flush()

    if m1_total != trader.total_closed_m1:
        raise AssertionError("one trader M1 ingestion incomplete")
    if sum(candidates.values()) != len(study_events):
        raise AssertionError("offer source identity mismatch")
    counts = Counter(x["final_source_phase"] for x in study_events)
    gross_m1_price_touch = sum(
        x["m1_touch_observed_at_not_fill"] is not None for x in study_events
    )
    same_revocation_overlap = sum(
        x["m1_ce_overlap_same_m1_as_source_revocation"] is not None
        for x in study_events
    )
    revocation_reasons = Counter(
        str(x["source_invalidation_reason"])
        for x in study_events
        if x["source_invalidation_reason"] is not None
    )
    return {
        "schema": "qore.vt31.ict_cleanroom.one_trader.3y_m1_offer_audit.v1",
        "source_base": SOURCE_ID,
        "market_m1_count": m1_total,
        "trader_id": "VT31",
        "registered_traders": 1,
        "session_models": ["LONDON", "NEW_YORK"],
        "three_window_coverage": {x.value: coverage[x.value] for x in SessionId},
        "three_window_partial": {x.value: partial[x.value] for x in SessionId},
        "source_fvg_hypothesis_count": len(study_events),
        "candidate_count_by_window": {
            x.value: candidates[x.value] for x in SessionId
        },
        "post_source_final_phases": dict(sorted(counts.items())),
        "post_source_final_phases_by_window": dict(sorted(phase_counts.items())),
        "m1_price_touch_seen_while_source_valid_not_broker_fill": (
            gross_m1_price_touch
        ),
        "m1_ce_overlap_same_close_as_revocation_order_unknown": (
            same_revocation_overlap
        ),
        "terminal_source_invalidation_reason_counts": dict(
            sorted(revocation_reasons.items())
        ),
        "post_revocation_m1_price_touches_excluded": True,
        "historical_bid_ask_tick_stream_supplied": False,
        "M1_columns_on_first_market_row": sorted(bidask_columns),
        "real_historical_broker_quote_ticks": total_real_broker_quote_rows,
        "broker_execution_ack_count": 0,
        "paper_fills_proven": 0,
        "live_fills_proven": 0,
        "profit_factor": None,
        "max_drawdown": None,
        "trader_lab_economic_certification": "BLOCKED_WITHOUT_TIMED_QUOTES_AND_COSTS",
        "unfilled_research_only": True,
        "legacy_old_VT31_imports": False,
        "fresh_holdout_opened": False,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "events": study_events,
    }


def _source(path: Path) -> Iterable[dict[str, Any]]:
    import ijson

    for field, expected in (
        ("base_id", SOURCE_ID),
        ("market", "NAS100"),
        ("base_start_at", "2023-10-01T00:00:00+00:00"),
        ("base_end_exclusive", "2026-10-01T00:00:00+00:00"),
    ):
        with path.open("rb") as handle:
            actual = next(ijson.items(handle, field), None)
            if actual != expected:
                raise ValueError(f"3Y market truth field mismatch: {field}")
    with path.open("rb") as handle:
        yield from ijson.items(handle, "periods.M1.item")


def self_test() -> None:
    start = datetime(2025, 7, 7, 7, tzinfo=UTC)
    rows = [{
        "opened_at": (start + timedelta(minutes=i)).isoformat(),
        "closed_at": (start + timedelta(minutes=i+1)).isoformat(),
        "open": "100", "high": "101",
        "low": "99", "close": "100",
    } for i in range(60)]
    result = audit(rows)
    assert result["market_m1_count"] == 60
    assert result["three_window_coverage"]["VT31_LONDON"] == 1
    assert result["source_fvg_hypothesis_count"] == 0
    assert result["paper_fills_proven"] == 0
    assert result["registered_traders"] == 1
    try:
        audit(rows + rows[:1])
    except ValueError:
        pass
    else:
        raise AssertionError("lookahead/duplicate M1 accepted")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print("VT31 one-trader 3Y causal M1 order offer audit self-test: PASS")
        return
    if args.evidence is None or args.output is None:
        parser.error("--evidence and --output required")
    if os.environ.get("VT31_INPUT_SOURCE_SHA256") != SOURCE_SHA:
        raise ValueError("unverified 3Y NAS100 M1 source digest")
    report = audit(_source(args.evidence))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    synopsis = {k: v for k, v in report.items() if k != "events"}
    print(json.dumps(synopsis, sort_keys=True))


if __name__ == "__main__":
    main()
