"""Provenance atlas for the 44 M5-ALIGNED substitute confirmations in Step 4.

This diagnostic reconstructs the literal Step-4 first-match selector on every frozen
2Y bottleneck closeback and attributes each actual M5 substitute to:
- the original V3 bottleneck first-blocker;
- whether V3 had no valid MSS in N+1 (true MSS-density recovery), or
  whether the substitute preempted a later valid V3 MSS (timing reorder);
- whether the substitute survived downstream V3 logic into a raw Step-4 trade.

No admission rule is changed.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import iter_cibo_m1
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_m3_mss_bottleneck_forensics_2y_v1 import (
    IDENTITY as BOTTLENECK_IDENTITY,
)
from qore.infrastructure.trader_lab.capitalizer_m3_mss_bottleneck_forensics_2y_v1 import (
    LOOKBACK_START,
    WINDOW_END,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    _aggregate_tf,
    _pivots,
)
from qore.infrastructure.trader_lab.capitalizer_v3_m5_directional_state_v1 import (
    CapitalizerM5DirectionalState,
    classify_m5_directional_state,
)

IDENTITY = "QORE_CAPITALIZER_V3_M5_SUBSTITUTE_PROVENANCE_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_M5_SUBSTITUTE_PROVENANCE_2Y_V1"
)
EXPECTED_STEP4_SUBSTITUTE_CONFIRMATIONS = 44
EXPECTED_CISD_FIRST_BLOCKER_SUBSTITUTES = 28


@dataclass(frozen=True, slots=True)
class SubstituteProvenanceRow:
    symbol: str
    session: str
    operating_date: str
    closeback_at: str
    h1_deadline: str
    side: str
    liquidity_source: str
    original_first_blocker: str
    original_valid_m3_within_h1: bool
    substitute_m3_at: str
    original_v3_mss_at: str | None
    provenance: str
    lead_minutes_vs_original_v3_mss: str | None
    produced_step4_raw_trade: bool
    outcome_used_for_admission: bool = False


def _load_bottleneck_rows(root: Path) -> tuple[dict[str, Any], ...]:
    summaries = sorted(
        root.rglob("capitalizer-*-m3-mss-bottleneck-forensics-2y-v1.json")
    )
    ledgers = sorted(
        root.rglob(
            "capitalizer-*-m3-mss-bottleneck-forensics-2y-v1-closebacks.jsonl"
        )
    )
    if len(summaries) != 1 or len(ledgers) != 1:
        raise ValueError("provenance atlas requires one bottleneck market artifact")
    summary = json.loads(summaries[0].read_text(encoding="utf-8"))
    if summary.get("identity") != BOTTLENECK_IDENTITY:
        raise ValueError("unexpected bottleneck identity")
    rows: list[dict[str, Any]] = []
    with ledgers[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("bottleneck row must be object")
                rows.append(raw)
    return tuple(rows)


def _load_m5_states(
    root: Path,
) -> dict[tuple[str, str], CapitalizerM5DirectionalState]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-m3-microstructure-context-2y-v1-rows.jsonl")
    )
    if len(paths) != 1:
        raise ValueError("provenance atlas requires one microstructure ledger")
    result: dict[tuple[str, str], CapitalizerM5DirectionalState] = {}
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("microstructure row must be object")
            key = (str(raw["closeback_at"]), str(raw["side"]))
            result[key] = classify_m5_directional_state(
                side=CapitalizerSide(str(raw["side"])),
                microstructure_signature=str(raw["microstructure_signature"]),
            )
    return result


def _load_step4_substitute_trade_keys(root: Path) -> set[tuple[str, str, str]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-cisd-or-m5-aligned-2y-v1-trades.jsonl")
    )
    if len(paths) != 1:
        raise ValueError("provenance atlas requires one Step-4 market trade ledger")
    result: set[tuple[str, str, str]] = set()
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("Step-4 trade row must be object")
            if raw.get("m3_confirmation_route") != "M5_ALIGNED_SUBSTITUTE":
                continue
            result.add(
                (
                    str(raw["m5_closeback_at"]),
                    str(raw["side"]),
                    str(raw["m3_mss_at"]),
                )
            )
    return result


def _first_step4_event(
    bars: Any,
    closes: tuple[datetime, ...],
    pivots: Any,
    *,
    after: datetime,
    before: datetime,
    side: CapitalizerSide,
    state: CapitalizerM5DirectionalState,
) -> tuple[str, v3.M3MssEvent] | None:
    start = bisect.bisect_right(closes, after)
    end = bisect.bisect_right(closes, before)
    break_kind = "HIGH" if side is CapitalizerSide.LONG else "LOW"
    for index in range(start, end):
        bar = bars[index]
        source = bar.source
        full_range = source.high - source.low
        if full_range <= 0:
            continue
        directional = (
            source.close > source.open
            if side is CapitalizerSide.LONG
            else source.close < source.open
        )
        if not directional:
            continue
        body_ratio = abs(source.close - source.open) / full_range
        if body_ratio < v3.BODY_RATIO_MIN:
            continue
        atr = v3._atr14(bars, index)
        if atr is None or full_range <= v3.ATR_MULTIPLIER * atr:
            continue
        broken = v3._latest_pivot(
            pivots,
            before=bar.opened_at,
            kind=break_kind,
        )
        if broken is None:
            continue
        structure_break = (
            source.close > broken.price
            if side is CapitalizerSide.LONG
            else source.close < broken.price
        )
        if not structure_break:
            continue
        boundary = v3._opposing_series_boundary(
            bars,
            index=index,
            side=side,
        )
        if boundary is None:
            continue
        cisd_break = (
            source.close > boundary
            if side is CapitalizerSide.LONG
            else source.close < boundary
        )
        if cisd_break:
            route = "CISD"
        elif state is CapitalizerM5DirectionalState.ALIGNED:
            route = "M5_ALIGNED_SUBSTITUTE"
        else:
            continue
        return (
            route,
            v3.M3MssEvent(
                side=side,
                confirmed_at=bar.closed_at,
                displacement_opened_at=bar.opened_at,
                displacement_closed_at=bar.closed_at,
                broken_swing_price=broken.price,
                cisd_boundary=boundary,
                body_ratio=body_ratio,
                atr14=atr,
                displacement_range=full_range,
            ),
        )
    return None


def build_market_report(
    bottleneck_root: Path,
    micro_root: Path,
    step4_root: Path,
    m1_root: Path,
) -> tuple[dict[str, Any], tuple[SubstituteProvenanceRow, ...]]:
    diagnostics = _load_bottleneck_rows(bottleneck_root)
    states = _load_m5_states(micro_root)
    raw_trade_keys = _load_step4_substitute_trade_keys(step4_root)

    native = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not native:
        raise ValueError("provenance atlas found no native M1")
    symbol = native[0].symbol
    if any(bar.symbol != symbol for bar in native):
        raise ValueError("provenance atlas requires one symbol")
    m3 = _aggregate_tf(native, minutes=3)
    closes = tuple(item.closed_at for item in m3)
    pivots = _pivots(m3)

    rows: list[SubstituteProvenanceRow] = []
    for raw in diagnostics:
        after = datetime.fromisoformat(str(raw["closeback_at"]))
        before = datetime.fromisoformat(str(raw["h1_deadline"]))
        side = CapitalizerSide(str(raw["side"]))
        state = states.get((after.isoformat(), side.value))
        if state is None:
            raise ValueError("missing M5 state in provenance atlas")

        selected = _first_step4_event(
            m3,
            closes,
            pivots,
            after=after,
            before=before,
            side=side,
            state=state,
        )
        if selected is None or selected[0] != "M5_ALIGNED_SUBSTITUTE":
            continue
        event = selected[1]

        original = v3._find_m3_mss(
            m3,
            closes,
            pivots,
            after=after,
            before=before,
            side=side,
        )
        if original is None:
            provenance = "RECOVERS_NO_V3_MSS"
            lead = None
        else:
            if not event.confirmed_at < original.confirmed_at:
                raise AssertionError("M5 substitute must precede original V3 MSS")
            provenance = "PREEMPTS_LATER_V3_MSS"
            lead = str(
                (original.confirmed_at - event.confirmed_at).total_seconds()
                / 60.0
            )

        trade_key = (
            after.isoformat(),
            side.value,
            event.confirmed_at.isoformat(),
        )
        rows.append(
            SubstituteProvenanceRow(
                symbol=symbol,
                session=str(raw["session"]),
                operating_date=str(raw["operating_date"]),
                closeback_at=after.isoformat(),
                h1_deadline=before.isoformat(),
                side=side.value,
                liquidity_source=str(raw["liquidity_source"]),
                original_first_blocker=str(raw["first_blocker"]),
                original_valid_m3_within_h1=bool(
                    raw["valid_m3_within_h1"]
                ),
                substitute_m3_at=event.confirmed_at.isoformat(),
                original_v3_mss_at=(
                    None
                    if original is None
                    else original.confirmed_at.isoformat()
                ),
                provenance=provenance,
                lead_minutes_vs_original_v3_mss=lead,
                produced_step4_raw_trade=trade_key in raw_trade_keys,
            )
        )

    ordered = tuple(sorted(rows, key=lambda item: item.closeback_at))
    blockers = Counter(item.original_first_blocker for item in ordered)
    provenance_counts = Counter(item.provenance for item in ordered)
    trade_blockers = Counter(
        item.original_first_blocker
        for item in ordered
        if item.produced_step4_raw_trade
    )
    trade_provenance = Counter(
        item.provenance
        for item in ordered
        if item.produced_step4_raw_trade
    )
    report = {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": ordered[0].session if ordered else None,
        "substitute_confirmations": len(ordered),
        "by_original_first_blocker": dict(sorted(blockers.items())),
        "by_provenance": dict(sorted(provenance_counts.items())),
        "step4_raw_substitute_trades": sum(
            item.produced_step4_raw_trade for item in ordered
        ),
        "raw_trade_by_original_first_blocker": dict(
            sorted(trade_blockers.items())
        ),
        "raw_trade_by_provenance": dict(sorted(trade_provenance.items())),
        "cisd_first_blocker_substitutes": blockers["CISD"],
        "strategy_mutated": False,
        "outcome_used_for_admission": False,
        "diagnostic_only": True,
        "economic_candidate": False,
    }
    return report, ordered


def write_market(
    report: dict[str, Any],
    rows: tuple[SubstituteProvenanceRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-m5-substitute-provenance-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-m5-substitute-provenance-2y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(
            f"substitute provenance matrix requires 9 reports, got {len(paths)}"
        )
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    blockers: Counter[str] = Counter()
    provenance: Counter[str] = Counter()
    trade_blockers: Counter[str] = Counter()
    trade_provenance: Counter[str] = Counter()
    per_session: dict[str, Counter[str]] = {}
    for report in reports:
        for key, value in dict(report["by_original_first_blocker"]).items():
            blockers[str(key)] += int(value)
        for key, value in dict(report["by_provenance"]).items():
            provenance[str(key)] += int(value)
        for key, value in dict(report["raw_trade_by_original_first_blocker"]).items():
            trade_blockers[str(key)] += int(value)
        for key, value in dict(report["raw_trade_by_provenance"]).items():
            trade_provenance[str(key)] += int(value)
        session = str(report["session"])
        counter = per_session.setdefault(session, Counter())
        counter["substitute_confirmations"] += int(
            report["substitute_confirmations"]
        )
        counter["step4_raw_substitute_trades"] += int(
            report["step4_raw_substitute_trades"]
        )
        counter["cisd_first_blocker_substitutes"] += int(
            report["cisd_first_blocker_substitutes"]
        )

    confirmations = sum(
        int(item["substitute_confirmations"]) for item in reports
    )
    cisd_subset = blockers["CISD"]
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "substitute_confirmations": confirmations,
        "step4_confirmation_control_reproduced": (
            confirmations == EXPECTED_STEP4_SUBSTITUTE_CONFIRMATIONS
        ),
        "by_original_first_blocker": dict(sorted(blockers.items())),
        "by_provenance": dict(sorted(provenance.items())),
        "cisd_first_blocker_substitutes": cisd_subset,
        "cisd_v2_subset_control_reproduced": (
            cisd_subset == EXPECTED_CISD_FIRST_BLOCKER_SUBSTITUTES
        ),
        "substitutes_outside_cisd_first_blocker": (
            confirmations - cisd_subset
        ),
        "step4_raw_substitute_trades": sum(
            int(item["step4_raw_substitute_trades"]) for item in reports
        ),
        "raw_trade_by_original_first_blocker": dict(
            sorted(trade_blockers.items())
        ),
        "raw_trade_by_provenance": dict(sorted(trade_provenance.items())),
        "per_session": {
            key: dict(value) for key, value in sorted(per_session.items())
        },
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "strategy_mutated": False,
        "outcome_used_for_admission": False,
        "diagnostic_only": True,
        "economic_candidate": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = (
        output
        / "capitalizer-nine-market-v3-m5-substitute-provenance-2y-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("bottleneck_root", type=Path)
    market.add_argument("micro_root", type=Path)
    market.add_argument("step4_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "market":
        report, rows = build_market_report(
            args.bottleneck_root,
            args.micro_root,
            args.step4_root,
            args.m1_root,
        )
        write_market(report, rows, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
