#!/usr/bin/env python3
"""One VT31 cleanroom: TRUE 3Y frozen NAS100 M1, native COG->OPS shadow.

All market observations are chronological and as-of. One persistent cognition
services London + New York AM/PM. Source-hour completeness is classified
retrospectively for evidence-quality gating; the decisions INSIDE complete
hours use only source bars that had ALREADY CLOSED. No MT5 quotes, execution,
FVG-touch broker fills, trade PF/DD, capital, CIBO/QDLE or old VT31 algorithms.
"""
from __future__ import annotations

import argparse
import hashlib
import json
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
    SessionId,
    window_bounds,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.trader import (
    VT31Trader,
)

SCHEMA = "qore.vt31.cleanroom.one_trader.3y_real_cognitive_source.v1"
FROZEN_SOURCE_SHA256 = (
    "0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa"
)
BASE = "VT31_NAS100_OWNER_3Y_BASE_001"
NY = ZoneInfo("America/New_York")
WINDOW_HOURS: dict[int, SessionId] = {
    3: SessionId.LONDON,
    10: SessionId.NY_AM,
    14: SessionId.NY_PM,
}


def _dt(value: object) -> datetime:
    t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("source M1 must contain timezone-aware ISO clock")
    return t.astimezone(UTC)


def _bar(row: dict[str, Any]) -> M1Bar:
    return M1Bar(
        opened_at=_dt(row["opened_at"]),
        closed_at=_dt(row["closed_at"]),
        open=Decimal(str(row["open"])),
        high=Decimal(str(row["high"])),
        low=Decimal(str(row["low"])),
        close=Decimal(str(row["close"])),
    )


def _completed_hour(buffer: list[M1Bar], session: SessionId) -> bool:
    if len(buffer) != 60:
        return False
    first, end = window_bounds(buffer[0].opened_at, session)
    if buffer[-1].closed_at != end:
        return False
    return all(
        b.opened_at == first + timedelta(minutes=index)
        for index, b in enumerate(buffer)
    )


def scan(rows: Iterable[dict[str, Any]]) -> dict[str, object]:
    trader = VT31Trader()
    full: Counter[str] = Counter()
    partial: Counter[str] = Counter()
    cognitive_calls: Counter[str] = Counter()
    state_counts: Counter[str] = Counter()
    fvg_selected: Counter[str] = Counter()
    draw_families: Counter[str] = Counter()
    missing_facts: Counter[str] = Counter()
    confirmations_by_session: Counter[str] = Counter()
    cross_window_source_samples: list[dict[str, object]] = []
    total = 0
    last_open: datetime | None = None
    pending_key: tuple[str, SessionId] | None = None
    pending: list[M1Bar] = []
    t0 = time.perf_counter()

    def flush() -> None:
        nonlocal pending_key, pending
        if pending_key is None:
            return
        session = pending_key[1]
        if _completed_hour(pending, session):
            full[session.value] += 1
            for bar in pending:
                result = trader.on_closed_m1(bar)
                assessment = result.cognition
                if assessment is None:
                    raise AssertionError("full source hour lacks clean cognition")
                cognitive_calls[session.value] += 1
                state_counts[
                    session.value + ":" + result.operational_phase.value
                ] += 1
                if assessment.decision is not None:
                    confirmations_by_session[session.value] += 1
                    draw_families[assessment.decision.draw_family] += 1
                else:
                    for reason in assessment.missing:
                        missing_facts[session.value + ":" + reason] += 1
            ops = trader._windows[pending_key]
            if ops.first_suitable is not None:
                candidate = ops.first_suitable
                fvg_selected[session.value] += 1
                if len(cross_window_source_samples) < 18:
                    cross_window_source_samples.append({
                        "trader_id": "VT31",
                        "session": session.value,
                        "fvg_formed_at": candidate.formed_at.isoformat(),
                        "side": candidate.side.value,
                        "draw_price": str(candidate.target_price),
                        "fvg_midpoint": str(
                            candidate.consequent_encroachment
                        ),
                        "broker_fill": False,
                    })
        else:
            partial[session.value] += 1
            for bar in pending:
                trader.research_observe_incomplete_source_m1(bar)
        pending_key = None
        pending = []

    for row in rows:
        bar = _bar(row)
        if last_open is not None and bar.opened_at <= last_open:
            raise ValueError("market M1 duplicate/out-of-order")
        last_open = bar.opened_at
        total += 1
        local = bar.opened_at.astimezone(NY)
        sess = WINDOW_HOURS.get(local.hour)
        key = (local.date().isoformat(), sess) if sess else None
        if key != pending_key:
            flush()
        if key is None:
            outside = trader.on_closed_m1(bar)
            if outside.session_model is not None:
                raise AssertionError("non-ICT M1 wrongly entered a source")
        else:
            pending_key = key
            pending.append(bar)
    flush()
    elapsed = time.perf_counter() - t0
    if total == 0 or total != trader.total_closed_m1:
        raise AssertionError("market M1 and single-trader input count drift")
    if sum(cognitive_calls.values()) != sum(full.values()) * 60:
        raise AssertionError("complete-hour cognition missing at source close")
    if sum(fvg_selected.values()) > sum(full.values()):
        raise AssertionError("more than first suitable FVG per ICT source hour")
    return {
        "schema": SCHEMA,
        "source_base": BASE,
        "trader_id": "VT31",
        "registered_trader_count": 1,
        "session_models": ["LONDON", "NEW_YORK"],
        "source_window_count": 3,
        "source_m1": total,
        "source_full_hour_days": {
            s.value: full[s.value] for s in SessionId
        },
        "source_partial_hour_days": {
            s.value: partial[s.value] for s in SessionId
        },
        "cognitive_calls_by_window": {
            s.value: cognitive_calls[s.value] for s in SessionId
        },
        "real_causal_cog_decisions_by_window": {
            s.value: confirmations_by_session[s.value] for s in SessionId
        },
        "native_source_fvg_candidates_by_window": {
            s.value: fvg_selected[s.value] for s in SessionId
        },
        "current_market_draw_family_observation_counts": dict(
            sorted(draw_families.items())
        ),
        "missing_real_context_event_counts": dict(
            sorted(missing_facts.items())
        ),
        "cleanroom_operational_phase_closed_m1_counts": dict(
            sorted(state_counts.items())
        ),
        "example_nonexecuted_FVG_source_candidates": (
            cross_window_source_samples
        ),
        "elapsed_replay_seconds": round(elapsed, 3),
        "last_m1_open_at": None if last_open is None else last_open.isoformat(),
        "governance": {
            "one_trader_not_two": True,
            "both_session_models_one_cognition": True,
            "fresh_holdout_opened": False,
            "legacy_VT31_imported": False,
            "source_only_full_M1_hour_gating": True,
            "coverage_gate_classified_after_hour_research_only": True,
            "candidate_cognition_uses_only_as_of_completed_M1": True,
            "bid_ask_quote_path_proven": False,
            "broker_or_paper_fill_proven": False,
            "trading_authorized": False,
            "cibo_or_qdle_risk_enabled": False,
            "positions_opened": 0,
            "economic_replay_run": False,
            "PF_computable": False,
            "DD_computable": False,
            "live_authorized": False,
            "certified": False,
        },
    }


def _stream(path: Path) -> Iterable[dict[str, Any]]:
    import ijson

    with path.open("rb") as source:
        for field, want in (
            ("base_id", BASE),
            ("market", "NAS100"),
            ("base_start_at", "2023-10-01T00:00:00+00:00"),
            ("base_end_exclusive", "2026-10-01T00:00:00+00:00"),
        ):
            source.seek(0)
            if next(ijson.items(source, field), None) != want:
                raise ValueError(f"not canonical consumed NAS100 market: {field}")
    with path.open("rb") as source:
        yield from ijson.items(source, "periods.M1.item")


def self_test() -> None:
    first = datetime(2025, 7, 7, 7, tzinfo=UTC)
    rows = [
        {
            "opened_at": (first + timedelta(minutes=i)).isoformat(),
            "closed_at": (first + timedelta(minutes=i + 1)).isoformat(),
            "open": "100", "high": "101",
            "low": "99", "close": "100",
        }
        for i in range(60)
    ]
    result = scan(rows)
    assert result["source_m1"] == 60
    assert result["source_full_hour_days"]["VT31_LONDON"] == 1
    assert result["cognitive_calls_by_window"]["VT31_LONDON"] == 60
    assert result["native_source_fvg_candidates_by_window"]["VT31_LONDON"] == 0
    assert result["governance"]["broker_or_paper_fill_proven"] is False
    incomplete = scan(rows[:-1])
    assert incomplete["source_partial_hour_days"]["VT31_LONDON"] == 1
    assert incomplete["cognitive_calls_by_window"]["VT31_LONDON"] == 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print("one-VT31 complete/partial hour closed-cognition self-test: PASS")
        return
    if args.evidence is None or args.output is None:
        parser.error("--evidence and --output required")
    import os
    if os.environ.get("VT31_INPUT_SOURCE_SHA256") != FROZEN_SOURCE_SHA256:
        raise ValueError("full 3Y scan requires verified exact consumed base digest")
    output = scan(_stream(args.evidence))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
