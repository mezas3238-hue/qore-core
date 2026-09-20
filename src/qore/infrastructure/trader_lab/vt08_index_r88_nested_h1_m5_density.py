"""VT08 Index R88 — nested H1 -> M5 source-faithful density census.

R85-R87 proved that repairing the H4->M15 path with additional M15 rearm
mechanics cannot approach the density contract. TTrades also documents a
source-authorized nested alignment in which higher-timeframe bias is preserved,
H1 supplies structure, and M5 supplies the entry trigger.

R88 is a no-PnL census of that *separate* nested execution path inside the
Owner-authorized H4 windows:

- frozen V7 daily bias remains mandatory;
- H4 executable windows remain 22/02/06/10 NY; 14:00 remains disabled;
- raw CIBO M5 provider rows are consumed read-only with no interpolation;
- H1 bars are admitted only when all twelve constituent M5 bars are present;
- source POIs for H1 use the frozen hierarchy FVG -> relevant swing -> CISD,
  using the prior three complete H1 candles;
- M5 Protected Swings use the source-exact R84 mechanics:
  short-term liquidity sweep or reaction at the original source FVG;
- after a source-exact M5 Protected Swing, require the exact V6 continuation
  rule and the wick/body transition relative to the current H1 open;
- repeated entries require a distinct later source PS and later continuation.

This does not mutate VT08, does not attach target/risk/PnL, and does not claim a
candidate. It asks only whether the source-authorized H1->M5 nested path has
enough structural opportunity density to merit economic validation.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_density_round4 as r4,
)
from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_tuning_round1 as r1,
)
from qore.infrastructure.trader_lab import (
    vt08_index_concurrent_market_contract as contract,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r59_candidate_freeze as freeze,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r67_r66_failure_forensics as r67,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r84_source_exact_ps_event_census as r84,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r86_dynamic_m15_fvg_rearm as r86,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r87_dynamic_liquidity_rearm as r87,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v6_ttrades_source_faithful as v6,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v7_ttrades_source_corrected as v7,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)

SCHEMA = "qore.trader_lab.vt08_index_r88_nested_h1_m5_density.v1"
IDENTITY = "VT08_INDEX_R88_NESTED_H1_M5_SOURCE_DENSITY_CENSUS_001"

SOURCE_R86_RUN_ID = 35526025751
SOURCE_R86_ARTIFACT_ID = 10610380553
SOURCE_R86_ARTIFACT_DIGEST = (
    "sha256:7993a038465b831c3eb60852c9077f0afd1345d61c6dece6c1ef7314bfddcf37"
)
SOURCE_R87_RUN_ID = 35526010382
SOURCE_R87_ARTIFACT_ID = 10609054819
SOURCE_R87_ARTIFACT_DIGEST = (
    "sha256:3ebd698e742b29e5254eb1b0ec5a0868828c96f81eab8d8cb8c36df7d3dfb155"
)


@dataclass(frozen=True, slots=True)
class NestedExecutable:
    symbol: str
    h4_opened_at: datetime
    h1_opened_at: datetime
    side: DemoTradingSetupSide
    source_poi_kind: str
    family: str
    ps_confirmed_at: datetime
    protected_swing: Decimal
    continuation_at: datetime
    entry: Decimal

    def identity(self) -> tuple[object, ...]:
        return (
            self.symbol,
            self.continuation_at.astimezone(UTC),
            self.side.value,
            self.entry,
            self.protected_swing,
        )


def _load_raw_m5(
    root: Path,
    *,
    symbol: str,
) -> tuple[tuple[Vt08IndexC2R1Bar, ...], dict[str, Any]]:
    manifest = r1._read_json(
        r1._single(root, "symbol-consumption-manifest.json")
    )
    if manifest.get("identity") != r1.SOURCE_IDENTITY:
        raise ValueError(f"R88 CIBO source identity drift for {symbol}")
    if manifest.get("canonical_symbol") != symbol:
        raise ValueError(f"R88 CIBO symbol drift for {symbol}")
    if not bool(manifest.get("read_only")):
        raise ValueError(f"R88 CIBO source not read-only for {symbol}")
    if bool(manifest.get("live_authorized")) or bool(
        manifest.get("real_capital_authorized")
    ):
        raise ValueError(f"R88 CIBO authority drift for {symbol}")

    ledger = root / "RAW_M5_LEDGER"
    paths = tuple(sorted(ledger.glob("*.jsonl")))
    if not paths:
        raise ValueError(f"R88 no raw M5 ledger partitions for {symbol}")

    rows: dict[datetime, Vt08IndexC2R1Bar] = {}
    partition_names: list[str] = []
    for path in paths:
        partition_names.append(path.name)
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                decoded = json.loads(line)
                if not isinstance(decoded, dict):
                    raise ValueError("R88 raw M5 row must be object")
                row = cast(dict[str, Any], decoded)
                if row.get("schema") != r1.RAW_SCHEMA:
                    raise ValueError(f"R88 raw schema drift for {symbol}")
                if row.get("identity") != r1.SOURCE_IDENTITY:
                    raise ValueError(f"R88 raw identity drift for {symbol}")
                if row.get("canonical_symbol") != symbol:
                    raise ValueError(f"R88 raw symbol drift for {symbol}")
                opened = r1._parse_time(row.get("opened_at")).astimezone(UTC)
                if opened.minute % 5 != 0 or opened.second != 0:
                    raise ValueError(f"R88 unaligned M5 timestamp for {symbol}")
                bar = Vt08IndexC2R1Bar(
                    opened_at=opened,
                    closed_at=opened + timedelta(minutes=5),
                    open=r1._price(row["open_relative"]),
                    high=r1._price(row["high_relative"]),
                    low=r1._price(row["low_relative"]),
                    close=r1._price(row["close_relative"]),
                )
                prior = rows.setdefault(opened, bar)
                if prior != bar:
                    raise ValueError(f"R88 duplicate M5 price drift for {symbol}")

    ordered = tuple(rows[key] for key in sorted(rows))
    return ordered, {
        "source_identity": r1.SOURCE_IDENTITY,
        "raw_m5_rows": len(ordered),
        "partitions": partition_names,
        "synthetic_prices": 0,
        "interpolated_prices": 0,
        "read_only": True,
    }


def _complete_h1(
    m5: Sequence[Vt08IndexC2R1Bar],
) -> tuple[
    dict[datetime, Vt08IndexC2R1Bar],
    dict[datetime, tuple[Vt08IndexC2R1Bar, ...]],
]:
    buckets: dict[datetime, list[Vt08IndexC2R1Bar]] = defaultdict(list)
    for bar in m5:
        opened = bar.opened_at.astimezone(UTC)
        key = opened.replace(minute=0, second=0, microsecond=0)
        buckets[key].append(bar)

    h1: dict[datetime, Vt08IndexC2R1Bar] = {}
    components: dict[datetime, tuple[Vt08IndexC2R1Bar, ...]] = {}
    for key, rows in sorted(buckets.items()):
        ordered = tuple(sorted(rows, key=lambda bar: bar.opened_at))
        expected = tuple(key + timedelta(minutes=5 * i) for i in range(12))
        observed = tuple(bar.opened_at.astimezone(UTC) for bar in ordered)
        if observed != expected:
            continue
        h1[key] = Vt08IndexC2R1Bar(
            opened_at=key,
            closed_at=key + timedelta(hours=1),
            open=ordered[0].open,
            high=max(bar.high for bar in ordered),
            low=min(bar.low for bar in ordered),
            close=ordered[-1].close,
        )
        components[key] = ordered
    return h1, components


def _prior_keys(
    mapping: dict[datetime, Any],
    *,
    before: datetime,
    count: int,
) -> tuple[datetime, ...]:
    keys = tuple(key for key in sorted(mapping) if key < before.astimezone(UTC))
    return keys[-count:]


def _h1_source_pois(
    *,
    h1: dict[datetime, Vt08IndexC2R1Bar],
    components: dict[datetime, tuple[Vt08IndexC2R1Bar, ...]],
    before: datetime,
    side: DemoTradingSetupSide,
) -> tuple[v6.SourcePoi, ...]:
    keys = _prior_keys(h1, before=before, count=3)
    if len(keys) < 3:
        return ()
    a, b, c = (h1[key] for key in keys)
    result: list[v6.SourcePoi] = []

    if side is DemoTradingSetupSide.LONG and a.high < c.low:
        result.append(v6.SourcePoi(v6.PoiKind.FVG, a.high, c.low, c.closed_at))
    if side is DemoTradingSetupSide.SHORT and a.low > c.high:
        result.append(v6.SourcePoi(v6.PoiKind.FVG, c.high, a.low, c.closed_at))

    if side is DemoTradingSetupSide.LONG and b.low < a.low and b.low < c.low:
        result.append(
            v6.SourcePoi(v6.PoiKind.RELEVANT_SWING, b.low, b.low, c.closed_at)
        )
    if side is DemoTradingSetupSide.SHORT and b.high > a.high and b.high > c.high:
        result.append(
            v6.SourcePoi(v6.PoiKind.RELEVANT_SWING, b.high, b.high, c.closed_at)
        )

    cisd = v6._last_cisd_poi(components[keys[-1]], side=side)
    if cisd is not None:
        result.append(cisd)

    priority = {
        v6.PoiKind.FVG: 0,
        v6.PoiKind.RELEVANT_SWING: 1,
        v6.PoiKind.CISD: 2,
    }
    unique: dict[tuple[object, ...], v6.SourcePoi] = {}
    for poi in sorted(
        result,
        key=lambda item: (
            priority[item.kind],
            item.observed_at.astimezone(UTC),
            item.low,
            item.high,
        ),
    ):
        unique.setdefault(
            (
                poi.kind.value,
                poi.low,
                poi.high,
                poi.observed_at.astimezone(UTC),
            ),
            poi,
        )
    return tuple(unique.values())


def _m5_source_ps(
    *,
    symbol: str,
    h4_opened_at: datetime,
    h1_opened_at: datetime,
    side: DemoTradingSetupSide,
    pois: Sequence[v6.SourcePoi],
    m5_inside_h1: Sequence[Vt08IndexC2R1Bar],
    h1_bar: Vt08IndexC2R1Bar,
) -> tuple[NestedExecutable, ...]:
    swings = r84._short_term_swings(m5_inside_h1, side=side)
    series_rows = r84._confirmed_opposing_series(m5_inside_h1, side=side)
    result: dict[tuple[object, ...], NestedExecutable] = {}

    for poi in pois:
        touches = r4._touch_indices(m5_inside_h1, poi, start_index=0)
        for touch_index in touches:
            for series in series_rows:
                if series.confirm_index <= touch_index:
                    continue
                liquidity = r84._swept_known_short_term_liquidity(
                    swings,
                    series=series,
                    side=side,
                    touch_index=touch_index,
                )
                fvg = r84._original_fvg_reaction(
                    m5_inside_h1,
                    poi=poi,
                    series=series,
                    touch_index=touch_index,
                )
                family = r84._event_family(liquidity=liquidity, fvg=fvg)
                if family is None:
                    continue

                continuation_index = v6._first_continuation(
                    m5_inside_h1,
                    side=side,
                    start_index=series.confirm_index + 1,
                    protected_swing=series.extreme,
                )
                if continuation_index is None:
                    continue
                continuation = m5_inside_h1[continuation_index]
                entry = continuation.close

                in_body = (
                    entry > h1_bar.open
                    if side is DemoTradingSetupSide.LONG
                    else entry < h1_bar.open
                )
                if not in_body:
                    continue

                risk = (
                    entry - series.extreme
                    if side is DemoTradingSetupSide.LONG
                    else series.extreme - entry
                )
                if risk <= 0:
                    continue

                row = NestedExecutable(
                    symbol=symbol,
                    h4_opened_at=h4_opened_at,
                    h1_opened_at=h1_opened_at,
                    side=side,
                    source_poi_kind=poi.kind.value,
                    family=family,
                    ps_confirmed_at=m5_inside_h1[
                        series.confirm_index
                    ].closed_at.astimezone(UTC),
                    protected_swing=series.extreme,
                    continuation_at=continuation.closed_at.astimezone(UTC),
                    entry=entry,
                )
                result.setdefault(row.identity(), row)

    return tuple(
        sorted(
            result.values(),
            key=lambda row: (
                row.continuation_at,
                row.h1_opened_at,
                row.protected_swing,
            ),
        )
    )


def _market(
    *,
    symbol: str,
    m15: Sequence[Vt08IndexC2R1Bar],
    m5: Sequence[Vt08IndexC2R1Bar],
    start_date: Any,
    end_date: Any,
) -> dict[str, Any]:
    m15_indexed = {
        bar.opened_at.astimezone(UTC): bar
        for bar in m15
    }
    h4 = v6._build_h4(m15_indexed)
    h1, h1_components = _complete_h1(m5)
    side_cache: dict[Any, DemoTradingSetupSide | None] = {}

    rows: dict[tuple[object, ...], NestedExecutable] = {}
    by_anchor: dict[str, Counter[str]] = {}
    by_family: Counter[str] = Counter()
    by_poi: Counter[str] = Counter()
    h1_examined = 0
    h1_with_source_poi = 0
    h1_with_executable = 0

    for h4_opened in sorted(h4):
        local = h4_opened.astimezone(v7._NY)
        local_date = local.date()
        if not (start_date <= local_date < end_date):
            continue
        if local.hour not in r4.V7_ANCHORS:
            continue
        if local_date not in side_cache:
            side_cache[local_date] = v7._daily_bias(
                m15_indexed,
                before=h4_opened,
            )
        side = side_cache[local_date]
        if side is None:
            continue

        anchor = str(local.hour)
        by_anchor.setdefault(anchor, Counter())
        for hour_offset in range(4):
            h1_opened = h4_opened.astimezone(UTC) + timedelta(hours=hour_offset)
            h1_bar = h1.get(h1_opened)
            m5_inside = h1_components.get(h1_opened)
            if h1_bar is None or m5_inside is None:
                by_anchor[anchor]["INCOMPLETE_H1"] += 1
                continue
            h1_examined += 1

            pois = _h1_source_pois(
                h1=h1,
                components=h1_components,
                before=h1_opened,
                side=side,
            )
            if not pois:
                by_anchor[anchor]["NO_H1_SOURCE_POI"] += 1
                continue
            h1_with_source_poi += 1

            executable = _m5_source_ps(
                symbol=symbol,
                h4_opened_at=h4_opened,
                h1_opened_at=h1_opened,
                side=side,
                pois=pois,
                m5_inside_h1=m5_inside,
                h1_bar=h1_bar,
            )
            if not executable:
                by_anchor[anchor]["NO_M5_EXECUTABLE"] += 1
                continue
            h1_with_executable += 1
            by_anchor[anchor]["H1_WITH_EXECUTABLE"] += 1
            for row in executable:
                rows.setdefault(row.identity(), row)

    ordered = tuple(
        sorted(
            rows.values(),
            key=lambda row: (
                row.continuation_at,
                row.symbol,
                row.protected_swing,
            ),
        )
    )
    for row in ordered:
        by_family[row.family] += 1
        by_poi[row.source_poi_kind] += 1

    rearm = 0
    first = 0
    grouped: dict[tuple[str, datetime], list[NestedExecutable]] = defaultdict(list)
    for row in ordered:
        grouped[(row.symbol, row.h4_opened_at)].append(row)
    for group in grouped.values():
        group.sort(key=lambda row: row.continuation_at)
        if group:
            first += 1
            rearm += max(0, len(group) - 1)

    return {
        "symbol": symbol,
        "complete_h1_bars_total": len(h1),
        "h1_examined_inside_authorized_h4": h1_examined,
        "h1_with_source_poi": h1_with_source_poi,
        "h1_with_m5_executable": h1_with_executable,
        "deduplicated_nested_executables": len(ordered),
        "first_nested_executables_per_h4": first,
        "additional_nested_executables_same_h4": rearm,
        "by_family": dict(sorted(by_family.items())),
        "by_source_poi": dict(sorted(by_poi.items())),
        "by_anchor": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_anchor.items())
        },
    }


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    _stream, m15_by_symbol, m15_provenance = r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    start_date, end_date, canonical_reference = r74._window_contract(window_id)

    raw_m5: dict[str, tuple[Vt08IndexC2R1Bar, ...]] = {}
    raw_provenance: dict[str, Any] = {}
    for symbol in contract.MARKETS:
        bars, provenance = _load_raw_m5(roots[symbol], symbol=symbol)
        raw_m5[symbol] = bars
        raw_provenance[symbol] = provenance

    markets = {
        symbol: _market(
            symbol=symbol,
            m15=m15_by_symbol[symbol],
            m5=raw_m5[symbol],
            start_date=start_date,
            end_date=end_date,
        )
        for symbol in contract.MARKETS
    }
    count = sum(
        int(row["deduplicated_nested_executables"])
        for row in markets.values()
    )
    first = sum(
        int(row["first_nested_executables_per_h4"])
        for row in markets.values()
    )
    rearm = sum(
        int(row["additional_nested_executables_same_h4"])
        for row in markets.values()
    )

    if window_id == "5Y":
        density_min = contract.FIVE_YEAR_TRADE_RANGE[0]
        density_max: int | None = contract.FIVE_YEAR_TRADE_RANGE[1]
        density_pass = (
            density_min <= count <= contract.FIVE_YEAR_TRADE_RANGE[1]
        )
    elif window_id == "2Y":
        density_min = contract.TWO_YEAR_MIN_TRADES
        density_max = None
        density_pass = count >= density_min
    else:
        density_min = 1000
        density_max = None
        density_pass = count >= density_min

    return {
        "window_id": window_id,
        "canonical_h4_m15_signal_reference": canonical_reference,
        "nested_h1_m5_executable_count": count,
        "first_nested_executables_per_h4": first,
        "additional_nested_executables_same_h4": rearm,
        "density_minimum": density_min,
        "density_maximum": density_max,
        "density_pass": density_pass,
        "by_market": markets,
        "raw_m5_provenance": raw_provenance,
        "m15_provenance": m15_provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R88 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R88 source failure decision drift")
    if r86.IDENTITY != "VT08_INDEX_R86_DYNAMIC_M15_FVG_REARM_CENSUS_001":
        raise ValueError("R88 R86 identity drift")
    if r87.IDENTITY != (
        "VT08_INDEX_R87_DYNAMIC_SHORT_TERM_LIQUIDITY_REARM_CENSUS_001"
    ):
        raise ValueError("R88 R87 identity drift")
    if 14 in r4.V7_ANCHORS:
        raise ValueError("R88 Owner-disabled 14:00 anchor unexpectedly enabled")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five = _window(roots=roots, window_id="5Y")
    two = _window(roots=roots, window_id="2Y")
    failed = _window(roots=roots, window_id="R66")

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_predecessors": {
            "r86": {
                "run_id": SOURCE_R86_RUN_ID,
                "artifact_id": SOURCE_R86_ARTIFACT_ID,
                "artifact_digest": SOURCE_R86_ARTIFACT_DIGEST,
                "m15_dynamic_fvg_density_sufficient": False,
            },
            "r87": {
                "run_id": SOURCE_R87_RUN_ID,
                "artifact_id": SOURCE_R87_ARTIFACT_ID,
                "artifact_digest": SOURCE_R87_ARTIFACT_DIGEST,
                "m15_dynamic_liquidity_density_sufficient": False,
            },
        },
        "source_contract": {
            "higher_bias": "V7_DAILY_BIAS",
            "authorized_h4_windows_ny": list(r4.V7_ANCHORS),
            "owner_disabled_14_preserved": True,
            "nested_structure_timeframe": "H1",
            "nested_entry_timeframe": "M5",
            "h1_requires_12_of_12_provider_m5": True,
            "h1_poi_hierarchy": ["fvg", "relevant-swing", "cisd"],
            "h1_relevant_swing_window": 3,
            "m5_ps_families": [
                r84.FAMILY_LIQUIDITY,
                r84.FAMILY_FVG,
                r84.FAMILY_BOTH,
            ],
            "m5_continuation": "EXACT_V6_FIRST_CONTINUATION",
            "h1_wick_body_transition_required": True,
            "pnl_evaluated": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": "R88_NESTED_H1_M5_SOURCE_DENSITY_CENSUS_COMPLETE_NO_TRADES",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "provider_m5_only": True,
            "synthetic_prices_created": False,
            "interpolated_prices_created": False,
            "future_information_used": False,
            "pnl_evaluated": False,
            "source_nested_path_is_separate_from_h4_m15_candidate": True,
            "h4_m15_candidate_mutated": False,
            "risk_changed": False,
            "target_changed": False,
            "anchors_changed": False,
            "owner_disabled_14_preserved": True,
            "candidate_created": False,
            "trader_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    report = build_report(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "five_year": {
                    key: report["five_year"][key]
                    for key in (
                        "nested_h1_m5_executable_count",
                        "first_nested_executables_per_h4",
                        "additional_nested_executables_same_h4",
                        "density_pass",
                    )
                },
                "recent_two_year": {
                    key: report["recent_two_year"][key]
                    for key in (
                        "nested_h1_m5_executable_count",
                        "first_nested_executables_per_h4",
                        "additional_nested_executables_same_h4",
                        "density_pass",
                    )
                },
                "r66": {
                    key: report["r66_failed_holdout"][key]
                    for key in (
                        "nested_h1_m5_executable_count",
                        "first_nested_executables_per_h4",
                        "additional_nested_executables_same_h4",
                        "density_pass",
                    )
                },
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
