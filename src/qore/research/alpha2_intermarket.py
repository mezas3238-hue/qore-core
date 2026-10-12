"""QORE-Alpha 2: original intermarket transmission-delay signal research.

Research only. This module NEVER authorizes or sends an order, and never
computes a broker-net PnL. Features use fully completed M5/H4 observations.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import median, pstdev
from typing import Iterable, Mapping, Sequence

MARKETS = (
    "NAS100", "SP500", "US30", "XAUUSD", "XAGUSD",
    "AUDUSD", "EURUSD", "GBPUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY",
    "AUDJPY", "AUDCAD", "AUDCHF", "AUDNZD", "CADCHF", "CADJPY", "CHFJPY",
    "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD",
    "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD",
    "NZDCAD", "NZDCHF", "NZDJPY",
)
H4 = timedelta(hours=4)
M5 = timedelta(minutes=5)
LOOKBACK = 160
MIN_PAIR = 96
MIN_DONORS = 5
DONOR_LIMIT = 7
MIN_ABS_CORR = 0.55
CONSENSUS_STRENGTH_SIGMA = 0.90
MAX_RESPONSE_FRACTION = 0.25
ATR_BARS = 20
ENTRY_DELAY = timedelta(minutes=5)
MAX_HOLD = timedelta(hours=12)
RESEARCH_CUTOFF = datetime(2024, 9, 17, tzinfo=UTC)
ORIGINAL_SOURCE_MANIFEST_SHA256 = (
    "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
)


@dataclass(frozen=True)
class Bar:
    at: datetime  # UTC bar START, not bar CLOSE
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class Signal:
    symbol: str
    bar_start_utc: str
    decision_utc: str
    earliest_entry_utc: str
    latest_exit_utc: str
    direction: int
    baseline_direction: int
    own_return: float
    predicted_return: float
    own_past_sigma: float
    stop_distance_price: float
    donors: tuple[str, ...]
    source_status: str = "H4_FROM_COMPLETE_NATIVE_M5_REQUIRED"
    execution_status: str = "BLOCKED_NO_BID_ASK_NEWS_PIT_OR_FILL"
    classification: str = "RESEARCH_SIGNAL_NOT_TRADE"


def _check_bar(bar: Bar) -> None:
    if bar.at.tzinfo is None or bar.at.utcoffset() != timedelta(0):
        raise ValueError("timestamp must be timezone-aware UTC")
    if not all(math.isfinite(v) and v > 0 for v in
               (bar.open, bar.high, bar.low, bar.close)):
        raise ValueError("OHLC values must be finite positive")
    if bar.high < max(bar.open, bar.close, bar.low):
        raise ValueError("high inconsistent with OHLC")
    if bar.low > min(bar.open, bar.close, bar.high):
        raise ValueError("low inconsistent with OHLC")


def read_m5(path: Path) -> Iterable[Bar]:
    """Read ONE original provider M5 CSV; no resampling/imputation of missing rows."""
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            at = datetime.fromisoformat(row["timestamp_utc"].replace("Z", "+00:00"))
            yield Bar(at=at, open=float(row["open"]), high=float(row["high"]),
                      low=float(row["low"]), close=float(row["close"]))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def aggregate_complete_h4(rows: Iterable[Bar]) -> dict[datetime, Bar]:
    """Retain only 48 *contiguous* native M5 rows per UTC-aligned H4 interval."""
    grouped: dict[datetime, Bar] = {}
    bucket: list[Bar] = []
    bucket_start: datetime | None = None
    previous: datetime | None = None

    def flush() -> None:
        if bucket_start is None or len(bucket) != 48:
            return
        if any(b.at != bucket_start + M5 * k for k, b in enumerate(bucket)):
            return
        grouped[bucket_start] = Bar(
            bucket_start, bucket[0].open, max(b.high for b in bucket),
            min(b.low for b in bucket), bucket[-1].close,
        )

    for b in rows:
        _check_bar(b)
        if b.at.minute % 5 != 0 or b.at.second or b.at.microsecond:
            raise ValueError("not M5-grid aligned")
        if previous is not None and b.at <= previous:
            raise ValueError("duplicate or out-of-order M5 timestamps")
        previous = b.at
        start = b.at.replace(hour=(b.at.hour // 4) * 4, minute=0, second=0,
                             microsecond=0)
        if start != bucket_start:
            flush()
            bucket, bucket_start = [], start
        bucket.append(b)
    flush()
    return grouped


def _returns(bars: Mapping[datetime, Bar]) -> dict[datetime, float]:
    result: dict[datetime, float] = {}
    for at, bar in bars.items():
        prev = bars.get(at - H4)
        if prev is not None:
            result[at] = math.log(bar.close / prev.close)
    return result


def _correlation_beta(a: Sequence[float], b: Sequence[float]) -> tuple[float, float]:
    if len(a) != len(b) or len(a) < MIN_PAIR:
        return 0.0, 0.0
    mean_a, mean_b = sum(a) / len(a), sum(b) / len(b)
    va = sum((v - mean_a) ** 2 for v in a)
    vb = sum((v - mean_b) ** 2 for v in b)
    if va <= 1e-24 or vb <= 1e-24:
        return 0.0, 0.0
    cov = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b, strict=True))
    corr = cov / math.sqrt(va * vb)
    beta = max(-2.0, min(2.0, cov / vb))
    return corr, beta


def _stop_distance(bars: Mapping[datetime, Bar], at: datetime) -> float | None:
    trs: list[float] = []
    for offset in range(40):
        t = at - H4 * offset
        current = bars.get(t)
        previous = bars.get(t - H4)
        if current is not None and previous is not None:
            trs.append(max(current.high - current.low,
                           abs(current.high - previous.close),
                           abs(current.low - previous.close)))
        if len(trs) >= ATR_BARS:
            break
    if len(trs) < ATR_BARS:
        return None
    return (sum(trs) / len(trs)) * 1.25


def signal_at(
    bars_by_symbol: Mapping[str, Mapping[datetime, Bar]],
    at: datetime,
    cached_returns: Mapping[str, Mapping[datetime, float]] | None = None,
) -> list[Signal]:
    """Decide only after H4 bar at 'at' has CLOSED; regressors end at at-H4.

    This function is deterministic and cannot inspect any future OHLC.
    """
    if at.tzinfo is None or at.utcoffset() != timedelta(0):
        raise ValueError("decision grid must be UTC")
    if at >= RESEARCH_CUTOFF:
        raise ValueError("reserved/embargoed price outcomes prohibited in research")
    if at + H4 + ENTRY_DELAY + MAX_HOLD > RESEARCH_CUTOFF:
        return []  # never generate a trade horizon crossing the embargo
    if at.hour % 4 or at.minute or at.second or at.microsecond:
        raise ValueError("timestamp must be UTC H4-grid aligned")
    rs = cached_returns if cached_returns is not None else {
        symbol: _returns(series) for symbol, series in bars_by_symbol.items()
    }
    results: list[Signal] = []
    for symbol in sorted(bars_by_symbol):
        own = rs[symbol]
        if at not in own:
            continue
        own_past = [own[at - H4 * k] for k in range(1, LOOKBACK + 1)
                    if at - H4 * k in own]
        if len(own_past) < MIN_PAIR:
            continue
        sigma = pstdev(own_past)
        if sigma <= 1e-12:
            continue
        donor_predictions: list[tuple[float, str, float]] = []
        for other in sorted(bars_by_symbol):
            if other == symbol or at not in rs[other]:
                continue
            other_r = rs[other]
            paired = [(own[t], other_r[t]) for k in range(1, LOOKBACK + 1)
                      if (t := at - H4 * k) in own and t in other_r]
            if len(paired) < MIN_PAIR:
                continue
            corr, beta = _correlation_beta([v[0] for v in paired],
                                           [v[1] for v in paired])
            if abs(corr) >= MIN_ABS_CORR:
                donor_predictions.append((abs(corr), other, beta * other_r[at]))
        donors = sorted(donor_predictions, key=lambda x: (-x[0], x[1]))[:DONOR_LIMIT]
        if len(donors) < MIN_DONORS:
            continue
        projected = sorted(item[2] for item in donors)
        predicted = median(projected[1:-1])
        if abs(predicted) < CONSENSUS_STRENGTH_SIGMA * sigma:
            continue
        direction = 1 if predicted > 0 else -1
        support = sum(1 for x in projected if direction * x > 0)
        if support < math.ceil(len(projected) * 0.8):
            continue
        response = direction * own[at]
        if not (0 <= response <= MAX_RESPONSE_FRACTION * abs(predicted)):
            continue
        prior_ret = own.get(at - H4, 0.0)
        comparison = own[at] if own[at] != 0 else prior_ret
        if comparison == 0:
            continue
        stop = _stop_distance(bars_by_symbol[symbol], at)
        if stop is None or stop <= 0:
            continue
        decision = at + H4
        results.append(Signal(
            symbol=symbol,
            bar_start_utc=at.isoformat(),
            decision_utc=decision.isoformat(),
            earliest_entry_utc=(decision + ENTRY_DELAY).isoformat(),
            latest_exit_utc=(decision + ENTRY_DELAY + MAX_HOLD).isoformat(),
            direction=direction,
            baseline_direction=1 if comparison > 0 else -1,
            own_return=own[at], predicted_return=predicted,
            own_past_sigma=sigma, stop_distance_price=stop,
            donors=tuple(item[1] for item in donors),
        ))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Alpha2 research signal generator; no orders")
    parser.add_argument("--m5-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--input-attestation", type=Path, required=True)
    parser.add_argument("--from-utc", required=True)
    parser.add_argument("--until-utc", required=True)
    args = parser.parse_args()
    start = datetime.fromisoformat(args.from_utc.replace("Z", "+00:00"))
    end = datetime.fromisoformat(args.until_utc.replace("Z", "+00:00"))
    if (start.tzinfo is None or end.tzinfo is None or
            start.utcoffset() != timedelta(0) or end.utcoffset() != timedelta(0)):
        raise ValueError("explicit UTC dates required")
    if end > RESEARCH_CUTOFF or not start < end:
        raise ValueError("research end must be at or before 2024-09-17 UTC")
    attestation = json.loads(args.input_attestation.read_text(encoding="utf-8"))
    if attestation.get("original_source_manifest_sha256") != ORIGINAL_SOURCE_MANIFEST_SHA256:
        raise ValueError("original 33 source manifest fingerprint mismatch")
    checksums = attestation.get("derived_csv_sha256")
    if not isinstance(checksums, dict) or set(checksums) != set(MARKETS):
        raise ValueError("exactly 33 derived CSV hashes are required")
    index: dict[str, dict[datetime, Bar]] = {}
    for symbol in MARKETS:
        path = args.m5_dir / f"{symbol}.csv"
        if not path.is_file():
            raise FileNotFoundError(f"33/33 mandatory, missing {symbol}; no dropping markets")
        if sha256_file(path) != checksums[symbol]:
            raise ValueError(f"staged CSV SHA256 mismatch for {symbol}")
        index[symbol] = aggregate_complete_h4(read_m5(path))
    returns_cache = {symbol: _returns(series) for symbol, series in index.items()}
    times = sorted(set().union(*(set(s) for s in index.values())))
    signals = [asdict(s) for t in times if start <= t < end
               for s in signal_at(index, t, cached_returns=returns_cache)]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "trader": "QORE-Alpha 2", "mode": "RESEARCH_ONLY",
        "universe": list(MARKETS), "market_count": len(MARKETS),
        "gross_net_results": "NOT_COMPUTED", "costs": "UNVERIFIED",
        "macro_asof": "UNVERIFIED", "certification": "BLOCKED",
        "original_source_manifest_sha256": ORIGINAL_SOURCE_MANIFEST_SHA256,
        "staging_provenance": "CSV_HASH_VERIFIED_DERIVATION_AUDIT_STILL_REQUIRED",
        "signals": signals,
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
