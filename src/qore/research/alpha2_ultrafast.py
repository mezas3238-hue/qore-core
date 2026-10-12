"""QORE-Alpha 2 Trader Lab ultra-fast research signal runner.

Incremental 160-bar PAIRWISE co-moment updates are O(T*N^2), rather than
reference O(T*N^2*LOOKBACK). It consumes SHA-audited compact H4 outputs,
preserves exact causal entry times, and NEVER computes PnL or sends orders.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from qore.research.alpha2_intermarket import (
    ATR_BARS, CONSENSUS_STRENGTH_SIGMA, DONOR_LIMIT, ENTRY_DELAY, H4,
    LOOKBACK, MARKETS, MAX_HOLD, MAX_RESPONSE_FRACTION, MIN_ABS_CORR,
    MIN_DONORS, MIN_PAIR, RESEARCH_CUTOFF, Bar, Signal, _check_bar, sha256_file,
)
from qore.research.alpha2_lab_h4_extract import SOURCE33_SHA


def load_33_attested(root: Path) -> dict[str, dict[datetime, Bar]]:
    files = sorted(root.rglob("alpha2-h4-source-*.json"))
    if len(files) != 33:
        raise ValueError(f"expected exactly 33 SHAs, got {len(files)}")
    out: dict[str, dict[datetime, Bar]] = {}
    for source in files:
        metadata = json.loads(source.read_text(encoding="utf-8"))
        name = metadata.get("symbol")
        if not isinstance(name, str) or name not in MARKETS or name in out:
            raise ValueError("duplicate or outside-33 source identity")
        required = {
            "identity": "QORE_ALPHA2_SHA_GATED_CONSUMED_H4_FROM_NATIVE_M5_V1",
            "source33_sha256": SOURCE33_SHA,
            "source_input_full_11_year_raw_sha_verified_before_OHLC": True,
            "post_2024_09_17_price_not_read": True,
            "broker_H4_session_semantics_claimed": False,
            "pnl_or_outcomes_calculated": False,
            "paper_or_live_authorized": False,
        }
        if any(metadata.get(k) != v for k, v in required.items()):
            raise ValueError("H4 source independent proof/embargo flags missing")
        if not metadata.get("source", {}).get("native_original_source_sha_verified"):
            raise ValueError("unverified original M5 not admissible")
        filename = f"alpha2-complete-h4-{name}.csv"
        if metadata.get("csv_basename") != filename:
            raise ValueError("compact H4 basename drift")
        csv_path = source.parent / filename
        if sha256_file(csv_path) != metadata.get("h4_csv_sha256"):
            raise ValueError(f"source H4 CSV sha256 mismatch {name}")
        bars: dict[datetime, Bar] = {}
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != ["timestamp_utc", "open", "high", "low", "close"]:
                raise ValueError("native H4 compact column contract mismatch")
            previous: datetime | None = None
            for line in reader:
                t = datetime.fromisoformat(line["timestamp_utc"])
                if (t.tzinfo is None or t.utcoffset() != H4 - H4
                        or t >= RESEARCH_CUTOFF or t.hour % 4 or t.minute
                        or t.second or t.microsecond or previous is not None
                        and t <= previous):
                    raise ValueError("native completed H4 chronological embargo invalid")
                row = Bar(t, float(line["open"]), float(line["high"]),
                          float(line["low"]), float(line["close"]))
                _check_bar(row)
                bars[t] = row
                previous = t
        if not bars or len(bars) != metadata.get("complete_native_m5_H4_blocks"):
            raise ValueError("H4 compact count mismatch")
        out[name] = bars
    if set(out) != set(MARKETS):
        raise ValueError("33 original symbols not identical")
    return out


def optimized_signals(
    bars: dict[str, dict[datetime, Bar]],
    *,
    start: datetime,
    end: datetime,
) -> list[Signal]:
    """Single complete H4 pane, incrementally updated past-only covariance.

    The baseline/reference PATR logic is NEVER replaced by learned params.
    No symbol or emitted signal can use a price opened in any future H4.
    """
    if (start.tzinfo is None or end.tzinfo is None
            or start.utcoffset() != H4 - H4 or end.utcoffset() != H4 - H4
            or not start < end <= RESEARCH_CUTOFF
            or set(bars) - set(MARKETS)):
        raise ValueError("invalid research UTC window/symbol")
    symbols = tuple(sorted(bars))
    if len(symbols) < MIN_DONORS + 1:
        return []
    time_set = {at for series in bars.values() for at in series}
    if not time_set:
        return []
    beginning = min(time_set)
    ending = min(max(time_set), end)
    slots = int((ending - beginning) / H4) + 1
    if slots > 40000:
        raise ValueError("unreasonably large dense H4 input")
    dates = [beginning + k * H4 for k in range(slots)]
    n = len(symbols)
    close = np.full((slots, n), np.nan, dtype=np.float64)
    high = close.copy()
    low = close.copy()
    for j, symbol in enumerate(symbols):
        for at, bar in bars[symbol].items():
            if at >= end:
                continue
            idx = int((at - beginning) / H4)
            if not 0 <= idx < slots or dates[idx] != at:
                raise ValueError("source H4 not on shared UTC grid")
            _check_bar(bar)
            close[idx, j] = bar.close
            high[idx, j] = bar.high
            low[idx, j] = bar.low
    ret = np.full_like(close, np.nan)
    valid = np.isfinite(close[1:]) & np.isfinite(close[:-1])
    current = np.divide(close[1:], close[:-1],
                        out=np.ones_like(close[1:]), where=valid)
    ret[1:] = np.where(valid, np.log(current), np.nan)
    tr = np.full_like(close, np.nan)
    tr[1:] = np.where(valid, np.maximum.reduce((
        high[1:] - low[1:],
        np.abs(high[1:] - close[:-1]),
        np.abs(low[1:] - close[:-1]),
    )), np.nan)

    counts = np.zeros((n, n), dtype=np.int32)
    sum_x = np.zeros((n, n), dtype=np.float64)
    sum_xx = np.zeros((n, n), dtype=np.float64)
    sum_xy = np.zeros((n, n), dtype=np.float64)

    def accumulate(at: int, sign: int) -> None:
        row = ret[at]
        flag = np.isfinite(row).astype(np.float64)
        x = np.where(np.isfinite(row), row, 0.0)
        counts[:] += sign * np.outer(flag, flag).astype(np.int32)
        sum_x[:] += sign * np.outer(x, flag)
        sum_xx[:] += sign * np.outer(x * x, flag)
        sum_xy[:] += sign * np.outer(x, x)

    result: list[Signal] = []
    symbol_index = {s: j for j, s in enumerate(symbols)}
    for t in range(slots):
        if t > 0:
            accumulate(t - 1, 1)
        if t > LOOKBACK:
            accumulate(t - LOOKBACK - 1, -1)
        at = dates[t]
        if at < start or at >= end or at + H4 + ENTRY_DELAY + MAX_HOLD > RESEARCH_CUTOFF:
            continue
        # Near-flat variances, sparse history or missing contemporaneous
        # returns fail closed; unit t is the last closed H4, not the order time.
        d = np.diag(counts).astype(np.float64)
        diag_sum = np.diag(sum_x)
        diag_xx = np.diag(sum_xx)
        with np.errstate(divide="ignore", invalid="ignore"):
            own_var = (diag_xx - diag_sum * diag_sum / d) / d
        std = np.sqrt(np.maximum(own_var, 0.0))
        outer_counts = counts.astype(np.float64)
        with np.errstate(divide="ignore", invalid="ignore"):
            cov = sum_xy - sum_x * sum_x.T / outer_counts
            vx = sum_xx - sum_x * sum_x / outer_counts
            vy = vx.T
            correlation = cov / np.sqrt(vx * vy)
            beta = np.clip(cov / vy, -2.0, 2.0)
        for symbol in symbols:
            i = symbol_index[symbol]
            own = ret[t, i]
            if not np.isfinite(own) or d[i] < MIN_PAIR or std[i] <= 1e-12:
                continue
            donors: list[tuple[float, str, float]] = []
            for j, other in enumerate(symbols):
                if (i == j or not np.isfinite(ret[t, j])
                        or counts[i, j] < MIN_PAIR
                        or not np.isfinite(correlation[i, j])
                        or not np.isfinite(beta[i, j])
                        or abs(correlation[i, j]) < MIN_ABS_CORR):
                    continue
                donors.append((abs(float(correlation[i, j])), other,
                               float(beta[i, j] * ret[t, j])))
            top = sorted(donors, key=lambda v: (-v[0], v[1]))[:DONOR_LIMIT]
            if len(top) < MIN_DONORS:
                continue
            contributions = sorted(x[2] for x in top)
            selected = contributions[1:-1]
            # numpy median agrees with statistics.median even for an even count.
            pressure = float(np.median(selected))
            if abs(pressure) < CONSENSUS_STRENGTH_SIGMA * std[i]:
                continue
            direction = 1 if pressure > 0 else -1
            if sum(1 for v in contributions if v * direction > 0) < math.ceil(0.8 * len(top)):
                continue
            own_response = direction * own
            if not 0 <= own_response <= MAX_RESPONSE_FRACTION * abs(pressure):
                continue
            prev_own = ret[t - 1, i] if t else float("nan")
            ctrl = own if own != 0 else (
                prev_own if np.isfinite(prev_own) else 0.0
            )
            if ctrl == 0:
                continue
            # The reference code looks back 40 slots and accepts 20 known TRs.
            window = tr[max(0, t - 39):t + 1, i]
            valid_tr = window[np.isfinite(window)][-ATR_BARS:]
            if len(valid_tr) != ATR_BARS:
                continue
            stop = 1.25 * float(np.mean(valid_tr))
            if not np.isfinite(stop) or stop <= 0:
                continue
            decision = at + H4
            result.append(Signal(
                symbol=symbol, bar_start_utc=at.isoformat(),
                decision_utc=decision.isoformat(),
                earliest_entry_utc=(decision + ENTRY_DELAY).isoformat(),
                latest_exit_utc=(decision + ENTRY_DELAY + MAX_HOLD).isoformat(),
                direction=direction,
                baseline_direction=1 if ctrl > 0 else -1,
                own_return=float(own), predicted_return=pressure,
                own_past_sigma=float(std[i]), stop_distance_price=stop,
                donors=tuple(x[1] for x in top),
            ))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("compact_signed_33", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--from-utc", default="2016-09-17T00:00:00+00:00")
    parser.add_argument("--until-utc", default="2024-09-17T00:00:00+00:00")
    args = parser.parse_args()
    bars = load_33_attested(args.compact_signed_33)
    start = datetime.fromisoformat(args.from_utc.replace("Z", "+00:00"))
    until = datetime.fromisoformat(args.until_utc.replace("Z", "+00:00"))
    signals = optimized_signals(bars, start=start, end=until)
    from dataclasses import asdict  # output-only late import
    args.destination.mkdir(parents=True, exist_ok=True)
    output = args.destination / "alpha2-patr-33-signal-ledger-research-only.json"
    output.write_text(json.dumps({
        "identity": "QORE_ALPHA2_PATR_SHA33_ULTRAFAST_RESEARCH_LEDGER_V1",
        "model": "PATR_PRE_OUTCOME_V01", "universe": sorted(bars),
        "source33_sha256": SOURCE33_SHA,
        "from_utc": start.isoformat(), "until_utc": until.isoformat(),
        "number_of_signals": len(signals),
        "signals": [asdict(x) for x in signals],
        "original_source_shas_reaudited": True,
        "costs_verified": False, "macro_news_asof_verified": False,
        "gross_or_net_PnL_calculated": False,
        "broker_orders": 0, "utc001_certified": False,
        "production_untouched": True,
    }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "RESEARCH_SIGNALS_ONLY",
                      "signals": len(signals), "markets": len(bars),
                      "gross_or_net_PnL_calculated": False,
                      "output_sha256": sha256_file(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
