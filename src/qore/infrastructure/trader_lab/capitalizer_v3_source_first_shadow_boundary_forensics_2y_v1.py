"""Causal shadow-state atlas at the exact SOURCE_FIRST M3 confirmation.

For each frozen SOURCE_FIRST raw trade, reconstruct the same M3 stream and inspect the
*frozen V3 immediate opposing-series boundary* at SOURCE_FIRST confirmation time.

This produces a runtime-observable shadow state:
- V3_BOUNDARY_MISSING
- V3_BOUNDARY_PRESENT_NOT_CROSSED
- V3_BOUNDARY_CROSSED

It also records the immediate previous-M3 relation and opposing-run length. The frozen
boundary-semantics census relation-vs-V3 is joined only for post-hoc explanation and is
explicitly prohibited as an admission rule.

Diagnostic only. No strategy rule is changed.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import iter_cibo_m1
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    TFBar,
    _aggregate_tf,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_SHADOW_BOUNDARY_FORENSICS_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_SHADOW_BOUNDARY_FORENSICS_2Y_V1"
)
EXPECTED_SOURCE_FIRST_RAW = 1142
EXPECTED_SOURCE_FIRST_MAX3 = 1118

MISSING = "V3_BOUNDARY_MISSING"
PRESENT_NOT_CROSSED = "V3_BOUNDARY_PRESENT_NOT_CROSSED"
CROSSED = "V3_BOUNDARY_CROSSED"


@dataclass(frozen=True, slots=True)
class ShadowBoundaryRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    m5_closeback_at: str
    source_first_mss_at: str
    source_first_boundary: str
    v3_shadow_state: str
    v3_shadow_boundary: str | None
    v3_shadow_distance_atr: str | None
    previous_m3_relation: str
    opposing_run_length: int
    relation_vs_future_v3: str
    realized_gross_r: str
    outcome_used_for_admission: bool = False
    future_relation_used_for_admission: bool = False


def _load_source_first(root: Path) -> tuple[v3.V3Trade, ...]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-source-first-cisd-2y-v1-trades.jsonl")
    )
    if len(paths) != 1:
        raise ValueError("shadow atlas requires one SOURCE_FIRST market ledger")
    rows: list[v3.V3Trade] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(v3.V3Trade(**json.loads(line)))
    return tuple(rows)


def _load_semantics(root: Path) -> dict[tuple[str, str, str], dict[str, Any]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-cisd-boundary-semantics-census-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("shadow atlas requires one boundary-semantics ledger")
    result: dict[tuple[str, str, str], dict[str, Any]] = {}
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("boundary-semantics row must be object")
            key = (
                str(raw["symbol"]),
                str(raw["side"]),
                str(raw["closeback_at"]),
            )
            result[key] = raw
    return result


def _previous_relation(
    bars: tuple[TFBar, ...],
    *,
    index: int,
    side: CapitalizerSide,
) -> str:
    if index <= 0:
        return "NO_PREVIOUS_BAR"
    source = bars[index - 1].source
    if source.close == source.open:
        return "DOJI"
    opposing = (
        source.close < source.open
        if side is CapitalizerSide.LONG
        else source.close > source.open
    )
    return "OPPOSING" if opposing else "SAME_DIRECTION"


def _opposing_run_length(
    bars: tuple[TFBar, ...],
    *,
    index: int,
    side: CapitalizerSide,
) -> int:
    length = 0
    current = index - 1
    while current >= 0:
        source = bars[current].source
        opposing = (
            source.close < source.open
            if side is CapitalizerSide.LONG
            else source.close > source.open
        )
        if not opposing:
            break
        length += 1
        current -= 1
    return length


def _shadow_state(
    bars: tuple[TFBar, ...],
    *,
    index: int,
    side: CapitalizerSide,
) -> tuple[str, Decimal | None, Decimal | None]:
    boundary = v3._opposing_series_boundary(
        bars,
        index=index,
        side=side,
    )
    if boundary is None:
        return MISSING, None, None

    source = bars[index].source
    crossed = (
        source.close > boundary
        if side is CapitalizerSide.LONG
        else source.close < boundary
    )
    atr = v3._atr14(bars, index)
    distance: Decimal | None = None
    if atr is not None and atr > 0:
        distance = abs(source.close - boundary) / atr
    return (
        CROSSED if crossed else PRESENT_NOT_CROSSED,
        boundary,
        distance,
    )


def build_market_report(
    replay_root: Path,
    semantics_root: Path,
    m1_root: Path,
) -> tuple[dict[str, Any], tuple[ShadowBoundaryRow, ...]]:
    trades = _load_source_first(replay_root)
    semantics = _load_semantics(semantics_root)
    if not trades:
        raise ValueError("shadow atlas requires SOURCE_FIRST trades")

    symbol = trades[0].symbol
    session = trades[0].session
    if any(trade.symbol != symbol or trade.session != session for trade in trades):
        raise ValueError("shadow atlas market input must be one symbol/session")

    first_mss = min(datetime.fromisoformat(item.m3_mss_at) for item in trades)
    last_mss = max(datetime.fromisoformat(item.m3_mss_at) for item in trades)
    native = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if first_mss - timedelta(days=2)
        <= bar.opened_at
        <= last_mss + timedelta(minutes=3)
    )
    if not native:
        raise ValueError("shadow atlas found no native M1")
    m3 = _aggregate_tf(native, minutes=3)
    by_close = {bar.closed_at: index for index, bar in enumerate(m3)}

    rows: list[ShadowBoundaryRow] = []
    for trade in trades:
        confirmed_at = datetime.fromisoformat(trade.m3_mss_at)
        index = by_close.get(confirmed_at)
        if index is None:
            raise ValueError(f"missing M3 confirmation bar {confirmed_at.isoformat()}")
        side = CapitalizerSide(trade.side)
        state, boundary, distance = _shadow_state(
            m3,
            index=index,
            side=side,
        )
        meta = semantics.get(
            (trade.symbol, trade.side, trade.m5_closeback_at)
        )
        if meta is None:
            raise ValueError("missing frozen boundary-semantics metadata")
        if str(meta["source_first_mss_at"]) != trade.m3_mss_at:
            raise ValueError("SOURCE_FIRST trade/semantics MSS mismatch")

        rows.append(
            ShadowBoundaryRow(
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                side=trade.side,
                m5_closeback_at=trade.m5_closeback_at,
                source_first_mss_at=trade.m3_mss_at,
                source_first_boundary=trade.m3_cisd_boundary,
                v3_shadow_state=state,
                v3_shadow_boundary=(
                    None if boundary is None else str(boundary)
                ),
                v3_shadow_distance_atr=(
                    None if distance is None else str(distance)
                ),
                previous_m3_relation=_previous_relation(
                    m3,
                    index=index,
                    side=side,
                ),
                opposing_run_length=_opposing_run_length(
                    m3,
                    index=index,
                    side=side,
                ),
                relation_vs_future_v3=str(
                    meta["source_first_relation_vs_v3"]
                ),
                realized_gross_r=trade.realized_gross_r,
            )
        )

    ordered = tuple(sorted(rows, key=lambda item: item.source_first_mss_at))
    states = Counter(item.v3_shadow_state for item in ordered)
    relation_by_state: dict[str, Counter[str]] = {}
    for item in ordered:
        relation_by_state.setdefault(item.v3_shadow_state, Counter())[
            item.relation_vs_future_v3
        ] += 1

    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session,
        "raw_trades": len(trades),
        "shadow_state_counts": dict(sorted(states.items())),
        "future_relation_by_shadow_state": {
            key: dict(sorted(value.items()))
            for key, value in sorted(relation_by_state.items())
        },
        "shadow_state_is_decision_time": True,
        "future_relation_is_diagnostic_only": True,
        "outcome_used_for_admission": False,
        "future_relation_used_for_admission": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
    }, ordered


def write_market(
    report: dict[str, Any],
    rows: tuple[ShadowBoundaryRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-source-first-shadow-boundary-forensics-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("replay_root", type=Path)
    parser.add_argument("semantics_root", type=Path)
    parser.add_argument("m1_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, rows = build_market_report(
        args.replay_root,
        args.semantics_root,
        args.m1_root,
    )
    write_market(report, rows, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
