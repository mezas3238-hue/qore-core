"""Source-complete nine-market M1 event-time observation witness from raw provider bars.

For every original source decision time, captures the last *closed* native
M1 bar in each one of the frozen nine markets. A missing same-minute candle
is a missing observation, never forward-filled quote, synthetic bar or market
regime. These records are necessary but NOT sufficient to construct Master
Frame regime, perception or market-state evidence.

Research only. No strategy gate, no fills, no live permissions.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEV_WINDOW_END,
    DEV_WINDOW_START,
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    NINE_MARKET_UNIVERSE,
)

IDENTITY = "QORE_SCALPER_A1_REAL_NATIVE_M1_NINE_MARKET_ASOF_WITNESS_V1"


def _aware(value: str) -> datetime:
    at = datetime.fromisoformat(value)
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("source decision must have a timezone")
    return at


def gather_original_decision_times(original_root: Path) -> tuple[datetime, ...]:
    """Exact global source decision barriers, not only MAX3-selected trades."""
    books = sorted(original_root.rglob(
        "capitalizer-*-v49-hf-capacity-opportunities.jsonl"
    ))
    if len(books) != 9:
        raise ValueError("need precisely nine source books")
    all_times: set[datetime] = set()
    symbols: set[str] = set()
    source_count = 0
    for path in books:
        rows = tuple(
            V49Opportunity(**json.loads(line))
            for line in path.read_text().splitlines() if line.strip()
        )
        if not rows or len({row.symbol for row in rows}) != 1:
            raise ValueError("source book empty or mixed market")
        symbols.add(rows[0].symbol)
        for row in rows:
            at = _aware(row.m1_trigger_confirmed_at)
            if not DEV_WINDOW_START <= at < DEV_WINDOW_END:
                raise ValueError("original source outside pinned development window")
            all_times.add(at)
            source_count += 1
    if symbols != set(NINE_MARKET_UNIVERSE) or source_count != 2876:
        raise ValueError("nine-market source census differs from frozen control")
    return tuple(sorted(all_times))


@dataclass(frozen=True, slots=True)
class A1NativeMarketObservation:
    symbol: str
    decision_at: str
    last_native_m1_closed_at: str | None
    last_native_m1_opened_at: str | None
    last_completed_close: str | None
    has_exact_predecision_m1: bool
    provider_native_m1: bool = True
    synthetic_data_used: bool = False
    bid_ask_quote_available: bool = False
    regime_attested: bool = False
    full_master_frame_attested: bool = False

    def __post_init__(self) -> None:
        at = _aware(self.decision_at)
        if self.symbol not in NINE_MARKET_UNIVERSE:
            raise ValueError("market outside nine-market cognitive universe")
        if self.last_native_m1_closed_at is not None and (
            _aware(self.last_native_m1_closed_at) > at
        ):
            raise ValueError("native snapshot must never use future M1")
        if self.has_exact_predecision_m1 != (
            self.last_native_m1_closed_at == self.decision_at
        ):
            raise ValueError("exact M1 completeness cannot be fabricated")
        if (
            not self.provider_native_m1 or self.synthetic_data_used
            or self.bid_ask_quote_available or self.regime_attested
            or self.full_master_frame_attested
        ):
            raise ValueError("bar witness must never attest broker quotes/regime/brain")


def observe_market_asof(
    *, symbol: str, decision_times: tuple[datetime, ...],
    bars: tuple[CapitalizerM1Bar, ...],
) -> tuple[A1NativeMarketObservation, ...]:
    """Streaming two-pointer join: CLOSED native bars only, O(m1+events)."""
    if not decision_times or len(set(decision_times)) != len(decision_times):
        raise ValueError("nonempty unique event-time census required")
    if tuple(sorted(decision_times)) != decision_times:
        raise ValueError("decision times must be globally chronological")
    if any(bar.symbol != symbol for bar in bars):
        raise ValueError("native market symbol mismatch")
    previous: CapitalizerM1Bar | None = None
    index = 0
    observations: list[A1NativeMarketObservation] = []
    for at in decision_times:
        while index < len(bars) and bars[index].closed_at <= at:
            if previous is not None and bars[index].opened_at <= previous.opened_at:
                raise ValueError("native M1 bars out of order or duplicated")
            previous = bars[index]
            index += 1
        observations.append(A1NativeMarketObservation(
            symbol=symbol,
            decision_at=at.isoformat(),
            last_native_m1_closed_at=(
                previous.closed_at.isoformat() if previous is not None else None
            ),
            last_native_m1_opened_at=(
                previous.opened_at.isoformat() if previous is not None else None
            ),
            last_completed_close=str(previous.close) if previous is not None else None,
            has_exact_predecision_m1=(
                previous is not None and previous.closed_at == at
            ),
        ))
    return tuple(observations)


def verify_native_m1_manifest(root: Path, symbol: str) -> None:
    if symbol not in NINE_MARKET_UNIVERSE:
        raise ValueError("unknown frozen market")
    m = json.loads((root / "m1-clone-manifest.json").read_text())
    if (
        m["canonical_symbol"] != symbol
        or m["provider_native_m1"] is not True
        or m["synthetic_m1"] is not False
        or m["interpolated_m1"] is not False
        or m["contradictory_m1"] != 0
        or m["read_only"] is not True
    ):
        raise ValueError("not a verified provider-native M1 source")


def write_market_witness(
    *, native_root: Path, decision_times: tuple[datetime, ...],
    symbol: str, output_root: Path,
) -> dict[str, object]:
    verify_native_m1_manifest(native_root, symbol)
    # Keep the historical year and one context day; no provider future prices.
    m1 = tuple(
        b for b in iter_cibo_m1(native_root)
        if DEV_WINDOW_START - timedelta(days=1) <= b.opened_at < DEV_WINDOW_END
    )
    witnesses = observe_market_asof(
        symbol=symbol, decision_times=decision_times, bars=m1
    )
    output_root.mkdir(parents=True, exist_ok=True)
    with (output_root / "scalper-a1-native-market-witness.jsonl").open("w") as f:
        for row in witnesses:
            f.write(json.dumps(asdict(row), sort_keys=True) + "\n")
    report: dict[str, object] = {
        "identity": IDENTITY, "market": symbol, "barriers": len(witnesses),
        "exact_predecision_native_m1": sum(x.has_exact_predecision_m1 for x in witnesses),
        "missing_exact_m1": sum(not x.has_exact_predecision_m1 for x in witnesses),
        "broker_quote_attested": False, "regime_attested": False,
        "full_master_frame_attested": False,
    }
    (output_root / "scalper-a1-market-witness-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    timestamps = sub.add_parser("times")
    timestamps.add_argument("source_root", type=Path)
    timestamps.add_argument("output", type=Path)
    witness = sub.add_parser("market")
    witness.add_argument("native_root", type=Path)
    witness.add_argument("timestamps", type=Path)
    witness.add_argument("symbol")
    witness.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.mode == "times":
        at = gather_original_decision_times(args.source_root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps([x.isoformat() for x in at]) + "\n")
        print(json.dumps({"unique_barriers": len(at), "source_rows": 2876}))
    else:
        at = tuple(_aware(x) for x in json.loads(args.timestamps.read_text()))
        report = write_market_witness(
            native_root=args.native_root, decision_times=at,
            symbol=args.symbol, output_root=args.output,
        )
        print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
