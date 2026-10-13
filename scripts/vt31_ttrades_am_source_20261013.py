#!/usr/bin/env python3
"""NEW TTrades NY-AM FVG-only causal source study (not prior VT31 G3, not PnL).

Exact frozen original NAS100 CFD M1; TTrades' 9AM raid/10AM reversal framework
with an explicitly QORE research-only ATR/body displacement definition.
No broker quotes, orders, CE fills, capital, PF or live authorization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
MARKET_SHA = "0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa"
ARTIFACT_ID = 11459859004
M1_TOTAL = 1059784
ATR_LEN = 20
ATR_MULT = 1.5
MIN_BODY_RATIO = 0.70
FORWARD_MIN = 15
BOOT = 2000
SEED = 13102026


@dataclass(frozen=True)
class Bar:
    time: datetime
    open: float
    high: float
    low: float
    close: float

    def __post_init__(self) -> None:
        if not self.time.tzinfo or self.time.utcoffset() is None:
            raise ValueError("M1 must have UTC-aware time")
        if not (1000 < self.low <= min(self.open, self.close)
                <= max(self.open, self.close) <= self.high < 1_000_000):
            raise ValueError("invalid NAS100 market M1 bounds")


def stamp(raw: str) -> datetime:
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("M1 naive timestamp")
    return parsed.astimezone(UTC)


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as inp:
        while chunk := inp.read(2**20):
            h.update(chunk)
    return h.hexdigest()


def market_source(path: Path) -> Iterable[dict[str, object]]:
    import ijson
    with path.open("rb") as inp:
        for field, expected in (
            ("base_id", "VT31_NAS100_OWNER_3Y_BASE_001"),
            ("market", "NAS100"),
            ("base_start_at", "2023-10-01T00:00:00+00:00"),
            ("base_end_exclusive", "2026-10-01T00:00:00+00:00"),
        ):
            inp.seek(0)
            if next(ijson.items(inp, field), None) != expected:
                raise ValueError("original frozen market header/provenance changed")
        inp.seek(0)
        yield from ijson.items(inp, "periods.M1.item")


def collect_days(
    rows: Iterable[dict[str, object]], *, expected_m1: int = M1_TOTAL,
) -> dict[str, dict[int, list[Bar]]]:
    days: dict[str, dict[int, list[Bar]]] = defaultdict(
        lambda: {9: [], 10: [], 11: []}
    )
    last = None
    count = 0
    for row in rows:
        opened = stamp(str(row["opened_at"]))
        closed = stamp(str(row["closed_at"]))
        if closed - opened != timedelta(minutes=1):
            raise ValueError("non M1 duration in source")
        if last is not None and opened <= last:
            raise ValueError("duplicate/out-of-order source M1")
        last = opened
        count += 1
        local = opened.astimezone(NY)
        if local.hour not in (9, 10, 11) or (
            local.hour == 11 and local.minute > 15
        ):
            continue
        b = Bar(
            opened, float(row["open"]), float(row["high"]),
            float(row["low"]), float(row["close"]),
        )
        days[local.date().isoformat()][local.hour].append(b)
    if count != expected_m1:
        raise ValueError("original 3Y M1 count mismatch")
    return days


def full_hour(bars: list[Bar], hour: int) -> bool:
    if len(bars) != 60:
        return False
    first = bars[0].time.astimezone(NY)
    return (
        first.hour == hour and first.minute == 0
        and all(
            b.time == bars[0].time + timedelta(minutes=i)
            for i, b in enumerate(bars)
        )
    )


def displacement(
    prior: list[Bar], current: Bar, side: str,
    high9: float, low9: float,
) -> bool:
    """All ATR references PRECEDE current close; threshold NOT from TTrades."""
    if len(prior) < ATR_LEN + 1:
        return False
    hist = prior[-ATR_LEN:]
    earlier = prior[-(ATR_LEN + 1):-1]
    tr = [
        max(
            b.high - b.low,
            abs(b.high - prev.close),
            abs(b.low - prev.close),
        )
        for b, prev in zip(hist, earlier)
    ]
    atr = sum(tr) / ATR_LEN
    body = abs(current.close - current.open)
    span = current.high - current.low
    if atr <= 0 or span <= 0:
        return False
    good_body = body > ATR_MULT * atr and body / span >= MIN_BODY_RATIO
    if side == "LONG":
        return good_body and current.close > current.open and current.close > low9
    return good_body and current.close < current.open and current.close < high9


def fvg(c1: Bar, c2: Bar, c3: Bar, side: str) -> tuple[float, float] | None:
    if c1.time + timedelta(minutes=1) != c2.time or (
        c2.time + timedelta(minutes=1) != c3.time
    ):
        return None
    if side == "LONG" and c3.low > c1.high:
        return c1.high, c3.low
    if side == "SHORT" and c3.high < c1.low:
        return c3.high, c1.low
    return None


def single_day(
    day: str, bars: dict[int, list[Bar]],
) -> tuple[str, dict[str, object] | None]:
    nine = bars[9]
    ten = bars[10]
    if not full_hour(nine, 9):
        return "MISSING_REFERENCE_H1", None
    if not full_hour(ten, 10):
        return "MISSING_SB_HOUR", None
    hi = max(b.high for b in nine)
    lo = min(b.low for b in nine)
    if hi <= lo:
        return "DEGENERATE_9AM_RANGE", None

    kind: str | None = None
    sweep_i: int | None = None
    sweep_extreme: float | None = None
    displacement_i: int | None = None
    all_prior = nine + ten
    for i, b in enumerate(ten):
        sweep_high = b.high > hi
        sweep_low = b.low < lo
        if kind is None:
            if sweep_high and sweep_low:
                return "DOUBLE_SWEEP_AMBIGUOUS", None
            if sweep_high:
                kind, sweep_i, sweep_extreme = "SHORT", i, b.high
            elif sweep_low:
                kind, sweep_i, sweep_extreme = "LONG", i, b.low
            continue
        assert sweep_i is not None and sweep_extreme is not None
        if (kind == "SHORT" and sweep_low) or (
            kind == "LONG" and sweep_high
        ):
            return "DOUBLE_SWEEP_AMBIGUOUS", None
        if kind == "SHORT":
            sweep_extreme = max(sweep_extreme, b.high)
        else:
            sweep_extreme = min(sweep_extreme, b.low)
        if displacement_i is None and i > sweep_i and displacement(
            all_prior[:60 + i], b, kind, hi, lo,
        ):
            displacement_i = i
        if displacement_i is None or i < 2 or i - 2 < sweep_i:
            continue
        zone = fvg(ten[i-2], ten[i-1], b, kind)
        if zone is None:
            continue
        ce = (zone[0] + zone[1]) / 2
        target = hi if kind == "LONG" else lo
        stop_ref = sweep_extreme
        if not (
            stop_ref < ce < target if kind == "LONG" else target < ce < stop_ref
        ):
            return "NONEXECUTABLE_GEOMETRY", None
        formed = b.time + timedelta(minutes=1)
        return "SOURCE_ONLY_CANDIDATE", {
            "id": f"TTRADES_AM_FVG_SOURCE_V0|{day}|{formed.isoformat()}",
            "day_ny": day,
            "side": kind,
            "h1_9am_high": hi,
            "h1_9am_low": lo,
            "sweep_start_m1": ten[sweep_i].time.isoformat(),
            "sweep_extreme_reference_NOT_BROKER_SL": stop_ref,
            "displacement_confirmed": (
                ten[displacement_i].time + timedelta(minutes=1)
            ).isoformat(),
            "fvg_c3_close": formed.isoformat(),
            "fvg_zone_low": zone[0],
            "fvg_zone_high": zone[1],
            "CE_reference_NOT_LIMIT_FILL": ce,
            "DOL_exact_opposite_9am_H1": target,
            "gross_15m_next_m1_open_NOT_TRADE": None,
            "source_only": True,
        }
    if kind is None:
        return "NO_SWEEP", None
    if displacement_i is None:
        return "NO_DISPLACEMENT", None
    return "NO_VALID_FVG", None


def forward_15(
    event: dict[str, object], bars: dict[int, list[Bar]],
) -> float | None:
    at = stamp(str(event["fvg_c3_close"]))
    src = {bar.time: bar for hour in (10, 11) for bar in bars[hour]}
    needed = [at + timedelta(minutes=i) for i in range(FORWARD_MIN + 1)]
    if any(t not in src for t in needed):
        return None
    multiplier = 1 if event["side"] == "LONG" else -1
    return multiplier * (src[needed[-1]].open - src[needed[0]].open)


def quantile(values: list[float], fraction: float) -> float:
    sorted_v = sorted(values)
    j = (len(sorted_v) - 1) * fraction
    i = int(j)
    return sorted_v[i] + (sorted_v[min(len(sorted_v)-1, i+1)] - sorted_v[i]) * (j-i)


def diagnostic(returns: list[tuple[str, float]]) -> dict[str, object]:
    if not returns:
        return {
            "n": 0, "mean_gross_pts": None,
            "weekly_cluster_boot_ci95": None, "testable_samples": False,
        }
    totals: dict[str, list[float]] = defaultdict(list)
    for day, gross in returns:
        nydate = datetime.fromisoformat(day).date()
        iso = nydate.isocalendar()
        totals[f"{iso.year}-W{iso.week:02d}"].append(gross)
    weeks = [(sum(x), len(x)) for x in totals.values()]
    rng = random.Random(SEED)
    boots = []
    for _ in range(BOOT):
        drawn = [weeks[rng.randrange(len(weeks))] for _ in weeks]
        boots.append(sum(v for v, _ in drawn) / sum(n for _, n in drawn))
    m = sum(v for _, v in returns) / len(returns)
    return {
        "n": len(returns),
        "mean_gross_pts": round(m, 6),
        "positive_fraction_NOT_win_rate": round(
            sum(x > 0 for _, x in returns) / len(returns), 6
        ),
        "week_blocks": len(weeks),
        "weekly_cluster_boot_ci95": [
            round(quantile(boots, .025), 6), round(quantile(boots, .975), 6)
        ],
        "development_only_NOT_OOS": True,
        "NOT_CE_ENTRY_OR_BROKER_PNL": True,
        "testable_samples": len(returns) >= 30 and len(weeks) >= 20,
    }


def analyze(days: dict[str, dict[int, list[Bar]]]) -> dict[str, object]:
    counts: Counter[str] = Counter()
    years: dict[str, Counter[str]] = defaultdict(Counter)
    events = []
    returns = []
    for date, bars in sorted(days.items()):
        status, event = single_day(date, bars)
        counts[status] += 1
        years[date[:4]][status] += 1
        if event is not None:
            value = forward_15(event, bars)
            if value is None:
                counts["NO_M1_FORWARD_COVERAGE"] += 1
            else:
                event["gross_15m_next_m1_open_NOT_TRADE"] = round(value, 6)
                returns.append((date, value))
            events.append(event)
    # Do not declare success without a source-coverage denominator.
    if not days or sum(v for k, v in counts.items() if k != "NO_M1_FORWARD_COVERAGE") != len(days):
        raise ValueError("missing research-day adjudications")
    score = diagnostic(returns)
    return {
        "schema": "qore.vt31.ttrades_am_fvg_source_only.v0",
        "preregistered_document_commit": (
            "fd9fde9a57b04a822d6296e7a858761eeb68fc83"
        ),
        "model": "VT31_TTRADES_AM_FVG_SOURCE_ONLY_V0",
        "instrument": "NAS100_CFD_NOT_VERIFIED_AS_NQ_FUTURES",
        "market_sha256": MARKET_SHA,
        "market_m1_count": M1_TOTAL,
        "market_artifact": ARTIFACT_ID,
        "source_days_ny_total": len(days),
        "status_counts": dict(sorted(counts.items())),
        "by_year": {yr: dict(sorted(c.items())) for yr, c in sorted(years.items())},
        "source_candidates": len(events),
        "signal_15m_from_next_M1_OPEN_not_CE": score,
        "events": events,
        "atr_displacement_is_QORE_HEURISTIC_not_TTrades_prescription": True,
        "FVG_only_does_not_cover_TTrades_OB_breaker_entries": True,
        "stop_price_and_tick_grid_NOT_VERIFIED": True,
        "quotes_bid_ask_and_order_ACK_count": 0,
        "economic_PF_drawdown_sharpe": None,
        "g3_v1_unmodified_and_unsigned": True,
        "historical_development_not_independent_holdout": True,
        "no_LIVE_or_order_authority": True,
        "decision": (
            "NO_GO_ECONOMIC_CERTIFICATION"
            if not score["testable_samples"] or score["mean_gross_pts"] <= 0
            else "EXPLORATORY_POSITIVE_DIRECTIONAL_ONLY_NOT_EDGE"
        ),
    }


def self_test() -> None:
    t = datetime(2025, 7, 1, 13, tzinfo=UTC)
    hour = [Bar(t+timedelta(minutes=i), 30000, 30002, 29998, 30000)
            for i in range(60)]
    assert full_hour(hour, 9)
    assert not full_hour(hour[:-1], 9)
    longfvg = fvg(
        Bar(t, 30000, 30002, 29998, 30000),
        Bar(t+timedelta(minutes=1), 30003, 30007, 30001, 30006),
        Bar(t+timedelta(minutes=2), 30008, 30010, 30004, 30009),
        "LONG",
    )
    assert longfvg == (30002, 30004)
    assert diagnostic([])["mean_gross_pts"] is None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--market", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if args.self_test:
        self_test()
        print("TTrades new source-only 9AM 10AM strict pre-market COG tests PASS")
        return
    if not args.market or not args.out:
        p.error("frozen market and report path required")
    if file_hash(args.market) != MARKET_SHA:
        raise ValueError("frozen source SHA256 mismatch, refuse test")
    days = collect_days(market_source(args.market))
    result = analyze(days)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status_counts": result["status_counts"],
        "source_candidates": result["source_candidates"],
        "signal_15m": result["signal_15m_from_next_M1_OPEN_not_CE"],
        "decision": result["decision"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
