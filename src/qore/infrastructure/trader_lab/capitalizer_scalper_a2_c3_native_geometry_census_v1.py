"""Native 9-market H1 Candle-3 paired GEOMETRY census (not an entry replay).

Two preregistered TTrades primary-source interpretations on EXACT same
contiguous 60/60 provider-native M1 H1 triples. Missing H1 means UNKNOWN,
not strategy rejection. No POI/CISD certification or future returns are read.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from itertools import groupby
from pathlib import Path
from typing import Any, Iterable

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEV_WINDOW_END,
    DEV_WINDOW_START,
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_c3_source_variants_v1 import (
    C3AsOfInput,
    compare_c3_primary_readings,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    detect_candle2_reversal_closure,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    _jsonl,
    source_id,
)

IDENTITY = "QORE_SCALPER_A2_C3_NATIVE_GEOMETRY_9MARKET_V1"
ONE_HOUR = timedelta(hours=1)


@dataclass(frozen=True, slots=True)
class NativeH1:
    closed_at: datetime
    bar: CapitalizerSourceBar


def _h1_key(bar: CapitalizerM1Bar) -> datetime:
    return bar.opened_at.astimezone(UTC).replace(
        minute=0, second=0, microsecond=0
    )


def exact_native_h1(
    bars: Iterable[CapitalizerM1Bar],
) -> tuple[NativeH1, ...]:
    """Never aggregate a partial H1 or fill an absent M1 minute."""

    h1: list[NativeH1] = []
    for hour, iterator in groupby(bars, key=_h1_key):
        minutes = tuple(iterator)
        if len(minutes) != 60 or any(
            b.opened_at != hour + timedelta(minutes=i)
            or b.closed_at != hour + timedelta(minutes=i + 1)
            for i, b in enumerate(minutes)
        ):
            continue
        h1.append(NativeH1(
            closed_at=hour + ONE_HOUR,
            bar=CapitalizerSourceBar(
                open=minutes[0].open,
                high=max(b.high for b in minutes),
                low=min(b.low for b in minutes),
                close=minutes[-1].close,
            ),
        ))
    return tuple(h1)


def _category(december: bool, january: bool) -> str:
    if december and january:
        return "BOTH"
    if december:
        return "DECEMBER_ONLY"
    if january:
        return "JANUARY_ONLY"
    return "NEITHER"


def build_geometry_rows(
    h1: tuple[NativeH1, ...],
) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for i in range(2, len(h1)):
        c1, c2, c3 = h1[i-2:i+1]
        if (
            c2.closed_at - c1.closed_at != ONE_HOUR
            or c3.closed_at - c2.closed_at != ONE_HOUR
            or not (DEV_WINDOW_START <= c3.closed_at < DEV_WINDOW_END)
        ):
            continue
        c2_reversal_geometry = detect_candle2_reversal_closure(
            previous=c1.bar,
            candle2=c2.bar,
            point_of_interest_present=False,
        ) is not None
        # Run both geometries even when C2 geometry exists: actual C2
        # author-confirmation requires source POI, which is unavailable here.
        probes = compare_c3_primary_readings(C3AsOfInput(
            candle2=c2.bar,
            candle3=c3.bar,
            candle2_closed_at=c2.closed_at,
            candle3_closed_at=c3.closed_at,
            candle2_reversal_already_confirmed=False,
        ))
        dec, jan = probes
        rows.append({
            "h1_c3_closed_at": c3.closed_at.isoformat(),
            "c2_reversal_geometry_without_poi": c2_reversal_geometry,
            "category": _category(dec.geometric_match, jan.geometric_match),
            "december_direction": dec.geometric_direction,
            "january_direction": jan.geometric_direction,
            "poi_attested": False,
            "ltf_cisd_attested": False,
            "changes_v49_admission": False,
        })
    return tuple(rows)


def market(
    original_root: Path,
    native_root: Path,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    source_files = sorted(original_root.rglob(
        "capitalizer-*-v49-hf-capacity-opportunities.jsonl"
    ))
    if len(source_files) != 1:
        raise ValueError("one locked V49 source ledger per market is required")
    sources = tuple(V49Opportunity(**item) for item in _jsonl(source_files[0]))
    if not sources:
        raise ValueError("missing original source opportunities")
    symbol = sources[0].symbol
    if any(row.symbol != symbol for row in sources):
        raise ValueError("source symbol mismatch")
    # The reader is provider-native; enclosing workflow verifies native manifest.
    native = tuple(
        b for b in iter_cibo_m1(native_root)
        if DEV_WINDOW_START - timedelta(days=15) <= b.opened_at < DEV_WINDOW_END
    )
    if not native or any(b.symbol != symbol for b in native):
        raise ValueError("missing or mixed native M1 symbol")
    if any(native[i].opened_at >= native[i+1].opened_at
           for i in range(len(native)-1)):
        raise ValueError("native M1 duplicates or unsorted timestamps")
    h1 = exact_native_h1(native)
    geometry = build_geometry_rows(h1)
    indexed = {r["h1_c3_closed_at"]: r for r in geometry}
    if len(indexed) != len(geometry):
        raise ValueError("duplicate H1 C3 observation identity")

    source_rows: list[dict[str, Any]] = []
    unique: set[str] = set()
    for source in sources:
        sid = source_id(source)
        if sid in unique:
            raise ValueError("duplicate V49 source opportunity ID")
        unique.add(sid)
        basis_is_c3 = "CANDLE3" in source.h1_state_basis.upper()
        h1_from = datetime.fromisoformat(source.h1_state_from)
        if h1_from.utcoffset() is None:
            raise ValueError("original source H1 state timestamp is naive")
        witness = indexed.get(h1_from.astimezone(UTC).isoformat())
        source_rows.append({
            "source_opportunity_id": sid,
            "symbol": symbol,
            "original_h1_basis": source.h1_state_basis,
            "original_h1_direction": source.h1_state_direction,
            "h1_state_from": source.h1_state_from,
            "basis_is_c3": basis_is_c3,
            "exact_native_c3_witness_available": witness is not None,
            "geometry_category": witness["category"] if witness else "UNKNOWN",
            "december_direction": witness["december_direction"] if witness else None,
            "january_direction": witness["january_direction"] if witness else None,
            "admission_changed": False,
            "author_source_validated": False,
        })
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "sources": len(sources),
        "native_h1_complete": len(h1),
        "consecutive_h1_triples": len(geometry),
        "geometry_counts": dict(sorted(Counter(r["category"] for r in geometry).items())),
        "c2_geometric_reversal_without_poi": sum(
            bool(r["c2_reversal_geometry_without_poi"]) for r in geometry
        ),
        "sources_c3_basis": sum(bool(r["basis_is_c3"]) for r in source_rows),
        "sources_exact_h1_c3_witness": sum(
            bool(r["exact_native_c3_witness_available"]) for r in source_rows
        ),
        "poi_and_ltf_cisd_not_independently_attested": True,
        "trades_reexecuted": 0,
        "admissions_changed": 0,
        "authorizes_trading": False,
        "certification": "BLOCKED_SOURCE_PROVENANCE",
    }, geometry, tuple(source_rows)


def aggregate(root: Path) -> dict[str, Any]:
    reports = [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(root.rglob("scalper-c3-native-market.json"))
    ]
    if len(reports) != 9 or len({r["symbol"] for r in reports}) != 9:
        raise ValueError("requires nine distinct native markets")
    sources = sum(int(r["sources"]) for r in reports)
    if sources != 2876:
        raise ValueError("not all immutable V49 source IDs were reconciled")
    kinds: Counter[str] = Counter()
    for report in reports:
        kinds.update(report["geometry_counts"])
        if report["trades_reexecuted"] or report["admissions_changed"]:
            raise ValueError("C3 geometry has no trading authority")
    return {
        "identity": IDENTITY,
        "sources": sources,
        "markets": len(reports),
        "native_h1_complete": sum(r["native_h1_complete"] for r in reports),
        "consecutive_h1_triples": sum(r["consecutive_h1_triples"] for r in reports),
        "geometry_counts": dict(sorted(kinds.items())),
        "c2_geometric_reversal_without_poi": sum(
            r["c2_geometric_reversal_without_poi"] for r in reports
        ),
        "sources_c3_basis": sum(r["sources_c3_basis"] for r in reports),
        "sources_exact_h1_c3_witness": sum(
            r["sources_exact_h1_c3_witness"] for r in reports
        ),
        "reports_by_market": {r["symbol"]: r for r in reports},
        "source_geometry_not_full_methodology": True,
        "master_frame_evaluated": False,
        "paper_pf": None, "paper_max_dd_r": None,
        "certification": "BLOCKED_SOURCE_PROVENANCE",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    m = sub.add_parser("market")
    m.add_argument("original", type=Path)
    m.add_argument("native", type=Path)
    m.add_argument("output", type=Path)
    a = sub.add_parser("matrix")
    a.add_argument("inputs", type=Path)
    a.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.mode == "market":
        report, geometry, sources = market(args.original, args.native)
        (args.output / "scalper-c3-native-market.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        for name, rows in (
            ("scalper-c3-native-geometry.jsonl", geometry),
            ("scalper-c3-source-id-witness.jsonl", sources),
        ):
            with (args.output / name).open("w", encoding="utf-8") as handle:
                for row in rows:
                    handle.write(json.dumps(row, sort_keys=True) + "\n")
        print(json.dumps(report, sort_keys=True))
    else:
        report = aggregate(args.inputs)
        (args.output / "scalper-c3-native-nine-market.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
