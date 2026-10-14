"""Read-only VT08 comparison of a secondary-source inside-bar context.

QORE R2-C replay is the unchanged engineering control. SpeculatorFL and
TraderFlameseN explicitly propose inside bars as CRT selection context; this
experiment only annotates that one observable without modifying entry, stop,
target, lotage, trade volume, or execution. The two secondary accounts are
not independent methodological proofs. No source-certification or production
promotion can be inferred from these exploratory statistics.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    END_EXCLUSIVE,
    FOLD_1_END,
    START,
    ReplayBar,
    load_two_year_m5,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
    Model1LabTrade,
    _fold,
    _summary,
    aggregate_complete_m15,
    build_parent_crts,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    run_r2c,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_3SOURCE_INSIDE_BAR_REPLAY_EXPLORATORY_001"
SCHEMA = "qore.vt08.crt_pure.3source_inside_bar_context_replay.v1"
M15 = timedelta(minutes=15)


@dataclass(frozen=True, slots=True)
class C1InsideBarObservation:
    parent_c3_opened_at: str
    observed_at: str
    inside_bar_count: int
    eligible_m15_count: int
    complete_c1_m15: bool
    inside_bar_context: bool
    source_status: str = "LEVEL_B_ENGINEERING_OPERATIONALIZATION"


def count_inside_m15_bars(
    bars: tuple[M15Bar, ...],
    *,
    c1_opened_at: datetime,
    c1_closed_at: datetime,
) -> C1InsideBarObservation:
    """Count strict consecutive M15 inside bars wholly known by C1 close.

    This is ONE predeclared engineering interpretation of a Level-B protocol,
    NOT RomeoTPT's rule. Gaps prevent classification instead of manufacturing
    an 'absence of inside bars'. At least one strict containment is the binary
    context contrast; do not optimize a threshold based on results.
    """
    if c1_closed_at <= c1_opened_at:
        raise ValueError("C1 window must have positive duration")
    selected = tuple(
        bar for bar in bars if c1_opened_at <= bar.opened_at < c1_closed_at
    )
    expected_count = (c1_closed_at - c1_opened_at) / M15
    complete = (
        expected_count == len(selected)
        and all(
            bar.opened_at == c1_opened_at + index * M15
            for index, bar in enumerate(selected)
        )
    )
    inside_count = sum(
        right.high_price < left.high_price
        and right.low_price > left.low_price
        for left, right in zip(selected[:-1], selected[1:], strict=True)
    ) if complete else 0
    return C1InsideBarObservation(
        parent_c3_opened_at="",
        observed_at=c1_closed_at.isoformat(),
        inside_bar_count=inside_count,
        eligible_m15_count=len(selected),
        complete_c1_m15=complete,
        inside_bar_context=complete and inside_count >= 1,
    )


def _trade_groups(
    trades: tuple[Model1LabTrade, ...],
    observed: dict[str, C1InsideBarObservation],
) -> dict[str, tuple[Model1LabTrade, ...]]:
    if any(trade.c3_opened_at not in observed for trade in trades):
        raise RuntimeError("Replay parent not found; cannot attribute inside-bar context")
    unknown = tuple(
        trade for trade in trades
        if not observed[trade.c3_opened_at].complete_c1_m15
    )
    has = tuple(
        trade for trade in trades
        if observed[trade.c3_opened_at].complete_c1_m15
        and observed[trade.c3_opened_at].inside_bar_context
    )
    no = tuple(
        trade for trade in trades
        if observed[trade.c3_opened_at].complete_c1_m15
        and not observed[trade.c3_opened_at].inside_bar_context
    )
    if len(unknown) + len(has) + len(no) != len(trades):
        raise RuntimeError("Partition is not exhaustive")
    if len({id(item) for item in (*unknown, *has, *no)}) != len(trades):
        raise RuntimeError("Overlapping trade partition")
    return {
        "R2C_UNCHANGED_CONTROL": trades,
        "LEVEL_B_INSIDE_BAR_PRESENT": has,
        "LEVEL_B_INSIDE_BAR_ABSENT": no,
        "UNKNOWN_C1_DATA": unknown,
    }


def _folded(groups: dict[str, tuple[Model1LabTrade, ...]]) -> dict[str, Any]:
    return {
        group: {
            "full": _summary(trades),
            "period_1": _summary(_fold(trades, START, FOLD_1_END)),
            "period_2": _summary(_fold(trades, FOLD_1_END, END_EXCLUSIVE)),
        }
        for group, trades in groups.items()
    }


def compare_three_sources_inside_bar_context(
    market: CrtPureMarket, bars: tuple[ReplayBar, ...]
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    """Run the predeclared control once, then annotate past-known C1 context.

    A group is a subset of unchanged trade outcomes, not a newly executed order.
    Does not infer source hierarchy, causally verify old CRTH, or use CSD/PD arrays.
    """
    if market is CrtPureMarket.BTCUSD:
        raise ValueError("BTCUSD freeze: this replay is limited to AUDUSD/USDJPY")
    trades, counters, parent_count = run_r2c(market, bars)
    parents = build_parent_crts(market, bars)
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    c1_observations: dict[str, C1InsideBarObservation] = {}

    for parent in parents:
        expected_bars = int((parent.c1.closed_at - parent.c1.opened_at) / M15)
        c1_m15 = tuple(
            m15_by_time[parent.c1.opened_at + index * M15]
            for index in range(expected_bars)
            if parent.c1.opened_at + index * M15 in m15_by_time
        )
        observation = count_inside_m15_bars(
            c1_m15,
            c1_opened_at=parent.c1.opened_at,
            c1_closed_at=parent.c1.closed_at,
        )
        key = parent.c3_opened_at.isoformat()
        if key in c1_observations:
            raise RuntimeError("duplicate parent C3 identity; cannot group causal source")
        c1_observations[key] = C1InsideBarObservation(
            parent_c3_opened_at=key,
            observed_at=observation.observed_at,
            inside_bar_count=observation.inside_bar_count,
            eligible_m15_count=observation.eligible_m15_count,
            complete_c1_m15=observation.complete_c1_m15,
            inside_bar_context=observation.inside_bar_context,
        )

    groups = _trade_groups(trades, c1_observations)
    diagnostics = tuple(
        {
            "market": trade.market,
            "c3_opened_at": trade.c3_opened_at,
            "source_opened_at": trade.source_opened_at,
            "entry_opened_at": trade.entry_opened_at,
            "reference_ids": list(trade.reference_ids),
            "inside_bar_context": c1_observations[trade.c3_opened_at].inside_bar_context,
            "inside_bar_count": c1_observations[trade.c3_opened_at].inside_bar_count,
            "complete_c1_m15": c1_observations[trade.c3_opened_at].complete_c1_m15,
            "r_multiple_original": trade.r_multiple,
            "original_exit_reason": trade.exit_reason,
        }
        for trade in trades
    )
    return (
        {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "market": market.value,
            "period_start_utc": START.isoformat(),
            "period_end_exclusive_utc": END_EXCLUSIVE.isoformat(),
            "period_split_utc": FOLD_1_END.isoformat(),
            "parent_crt_count": parent_count,
            "source_comparison": {
                "romeotpt": "PRIMARY_CRT_MODEL1_FAMILY_SOURCE_ONLY",
                "speculatorfl": "LEVEL_B_INSIDE_BAR_CONTEXT_HYPOTHESIS",
                "traderflamesn": "LEVEL_B_CORROBORATES_SPECULATORFL_NOT_INDEPENDENT",
            },
            "control_identity": "VT08_CRT_PURE_R2C_CLOSE_UNMITIGATED_MODEL1_001",
            "control_policy_authority": "QORE_ENGINEERING_NOT_ROMEO_CERTIFIED",
            "context_definition": (
                "One or more strictly inside consecutive M15 candles "
                "within fully closed C1 H4, available before C2 and C3"
            ),
            "context_known_at": "C1_H4_CLOSE",
            "inside_bar_threshold_tuned": False,
            "changed_trade_geometry": False,
            "source_priority_promoted": False,
            "read_only": True,
            "notional_sizing_used": False,
            "venue_orders_used": False,
            "costs_validated": False,
            "broker_bid_ask_executability_validated": False,
            "multiple_hypotheses_exploratory": True,
            "no_certification_from_filter_performance": True,
            "event_counters_control": counters,
            "summaries": _folded(groups),
        },
        diagnostics,
    )



# MIT-licensed free *samples*, independent of the unavailable IC Markets feed.
# The raw URL is fixed per approved symbol; no credential or order API is used.
_PUBLIC_SAMPLES = {
    CrtPureMarket.AUDUSD: (
        "https://raw.githubusercontent.com/getdata-finance/"
        "audusd-5m-ohlcv-forex-historical-data/main/AUDUSD_5m.csv"
    ),
    CrtPureMarket.USDJPY: (
        "https://raw.githubusercontent.com/getdata-finance/"
        "usdjpy-5m-ohlcv-forex-historical-data/main/USDJPY_5m.csv"
    ),
}
_SCALE = Decimal("1000000")


def parse_public_sample_m5(
    market: CrtPureMarket, payload: bytes
) -> tuple[tuple[ReplayBar, ...], dict[str, Any]]:
    """Validate public sample OHLC, timestamps, scale, and source fingerprint.

    Provides *OHLC only*. Spread, execution costs and IC Markets equivalence
    are intentionally NOT asserted. Historical preview only, not full two years.
    """
    if market not in _PUBLIC_SAMPLES:
        raise ValueError("BTCUSD is frozen; no public sample study")
    digest = hashlib.sha256(payload).hexdigest()
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
    required = {"datetime", "open", "high", "low", "close"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError("public sample must contain datetime/open/high/low/close")
    by_time: dict[datetime, ReplayBar] = {}
    observed_times: list[datetime] = []
    for row in reader:
        opened_at = datetime.fromisoformat(row["datetime"])
        if opened_at.tzinfo is None or opened_at.utcoffset() is None:
            raise ValueError("public sample timestamp must have UTC offset")
        if opened_at.utcoffset() != timedelta(0):
            raise ValueError("public sample timestamps must be UTC")
        if opened_at.second or opened_at.microsecond or opened_at.minute % 5:
            raise ValueError("public M5 sample timestamp is not aligned")
        vals: dict[str, int] = {}
        for field in ("open", "high", "low", "close"):
            dec = Decimal(row[field])
            scaled = dec * _SCALE
            if not dec.is_finite() or scaled != int(scaled):
                raise ValueError("public sample price precision or finiteness invalid")
            vals[field] = int(scaled)
        if (
            vals["low"] > min(vals["open"], vals["close"])
            or vals["high"] < max(vals["open"], vals["close"])
            or vals["low"] > vals["high"]
            or vals["low"] <= 0
        ):
            raise ValueError("public sample candle violates OHLC geometry")
        observed_times.append(opened_at)
        if START - timedelta(days=1) <= opened_at < END_EXCLUSIVE + timedelta(days=1):
            bar = ReplayBar(
                opened_at=opened_at,
                open_price=vals["open"],
                high_price=vals["high"],
                low_price=vals["low"],
                close_price=vals["close"],
            )
            previous = by_time.setdefault(opened_at, bar)
            if previous != bar:
                raise ValueError("public sample has contradictory duplicate candle")
    if not observed_times or not by_time:
        raise ValueError("public sample lacks bars in research window")
    if any(right <= left for left, right in zip(
        observed_times[:-1], observed_times[1:], strict=True
    )):
        raise ValueError("public sample timestamps are not strictly ascending")
    bars = tuple(by_time[t] for t in sorted(by_time))
    return bars, {
        "source": "GETDATA_FINANCE_GITHUB_MIT_FREE_M5_SAMPLE",
        "url": _PUBLIC_SAMPLES[market],
        "raw_sha256": digest,
        "raw_bytes": len(payload),
        "source_first_bar_utc": observed_times[0].isoformat(),
        "source_last_bar_utc": observed_times[-1].isoformat(),
        "window_first_bar_utc": bars[0].opened_at.isoformat(),
        "window_last_bar_utc": bars[-1].opened_at.isoformat(),
        "window_m5_bars": len(bars),
        "bid_ask_available": False,
        "broker_equivalence_validated": False,
        "history_complete_two_years": False,
        "free_sample_not_full_history": True,
    }


def load_public_sample_m5(
    market: CrtPureMarket,
) -> tuple[tuple[ReplayBar, ...], dict[str, Any]]:
    if market not in _PUBLIC_SAMPLES:
        raise ValueError("BTCUSD frozen")
    with urlopen(_PUBLIC_SAMPLES[market], timeout=30) as response:
        payload = response.read(12_000_001)
    if len(payload) > 12_000_000:
        raise ValueError("public sample unexpectedly exceeds size cap")
    return parse_public_sample_m5(market, payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=["AUDUSD", "USDJPY"])
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--data-source",
        choices=("ctrader", "public-sample"),
        default="public-sample",
    )
    args = parser.parse_args()
    market = CrtPureMarket(args.market)
    provenance: dict[str, Any]
    if args.data_source == "public-sample":
        bars, provenance = load_public_sample_m5(market)
    else:
        bars = load_two_year_m5(market)
        provenance = {
            "source": "CTRADER_HISTORICAL_M5",
            "broker_equivalence_validated": False,
        }
    report, ledger = compare_three_sources_inside_bar_context(market, bars)
    report["data_provenance"] = provenance
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    with (args.output / "diagnostics.jsonl").open("w", encoding="utf-8") as writer:
        for item in ledger:
            writer.write(json.dumps(item, sort_keys=True) + "\n")
    print("VT08_THREE_SOURCE_INSIDE_BAR=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
