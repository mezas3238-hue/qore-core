"""VT08 Index R76 — strict untouched POI memory forensics.

R72 proved that a large number of bias-ready slots are lost because the exact
current generator finds no POI. R74/R75 then falsified local and cross-index
daily-bias fallback as generalizable density fixes.

R76 moves to POI memory without creating any new signal. It reconstructs every
mechanically source-valid FVG, relevant swing and last-H4 CISD observed in the
provider-backed history. A historical POI qualifies for the strict memory
ledger only while no observed M15 bar after its observation timestamp has
retouched its price geometry before the decision anchor.

For each exact executable anchor with a frozen V7 daily bias, R76 compares:
- the exact current source POIs used by the frozen source-complete generator;
- older, distinct source POIs of the same side that remain strictly untouched
  in observed provider bars.

The key diagnostic is the number of exact no-POI slots for which such an older
strictly untouched source POI already existed. This is forensics only: no old
POI is admitted to trading, no signal is generated, and no economic outcome is
used.
"""

from __future__ import annotations

import argparse
import json
from bisect import bisect_left
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_density_round4 as r4,
)
from qore.infrastructure.trader_lab import (
    vt08_index_concurrent_market_contract as contract,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r6_five_year_validation as r6,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r59_candidate_freeze as freeze,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r66_fresh_historical_holdout as r66,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r67_r66_failure_forensics as r67,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r72_upstream_density_loss as r72,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r75_cross_index_ambiguous_bias_consensus as r75,
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

SCHEMA = "qore.trader_lab.vt08_index_r76_strict_untouched_poi_memory.v1"
IDENTITY = "VT08_INDEX_R76_STRICT_UNTOUCHED_POI_MEMORY_FORENSICS_001"

SOURCE_R72_RUN_ID = 35506163421
SOURCE_R72_ARTIFACT_ID = 10604260215
SOURCE_R72_ARTIFACT_DIGEST = (
    "sha256:58713e79d2c2120b0519dc27bf93220f1bcd3e7365747fead22dacb6021eee41"
)
SOURCE_R75_RUN_ID = 35513157662
SOURCE_R75_ARTIFACT_ID = 10605704489
SOURCE_R75_ARTIFACT_DIGEST = (
    "sha256:ca27c6a773db2fba966af8d11443e93cedd381854d68a341d9a665ef256bfd10"
)

EXPECTED_NO_POI = {"5Y": 2337, "2Y": 936, "R66": 934}


@dataclass(frozen=True, slots=True)
class PoiRecord:
    side: DemoTradingSetupSide
    poi: v6.SourcePoi
    formed_h4_open: datetime
    first_retouched_at: datetime | None

    def identity(self) -> tuple[object, ...]:
        return (
            self.side.value,
            self.poi.kind.value,
            self.poi.low,
            self.poi.high,
            self.poi.observed_at.astimezone(UTC),
        )


def _poi_identity(poi: v6.SourcePoi, side: DemoTradingSetupSide) -> tuple[object, ...]:
    return (
        side.value,
        poi.kind.value,
        poi.low,
        poi.high,
        poi.observed_at.astimezone(UTC),
    )


def _raw_source_records(
    *,
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    h4: dict[datetime, Vt08IndexC2R1Bar],
) -> tuple[tuple[DemoTradingSetupSide, v6.SourcePoi, datetime], ...]:
    keys = tuple(sorted(h4))
    records: dict[
        tuple[object, ...],
        tuple[DemoTradingSetupSide, v6.SourcePoi, datetime],
    ] = {}

    for index in range(2, len(keys)):
        a_key, b_key, c_key = keys[index - 2 : index + 1]
        a, b, c = h4[a_key], h4[b_key], h4[c_key]

        if a.high < c.low:
            poi = v6.SourcePoi(v6.PoiKind.FVG, a.high, c.low, c.closed_at)
            records[_poi_identity(poi, DemoTradingSetupSide.LONG)] = (
                DemoTradingSetupSide.LONG,
                poi,
                c_key,
            )
        if a.low > c.high:
            poi = v6.SourcePoi(v6.PoiKind.FVG, c.high, a.low, c.closed_at)
            records[_poi_identity(poi, DemoTradingSetupSide.SHORT)] = (
                DemoTradingSetupSide.SHORT,
                poi,
                c_key,
            )

        if b.low < a.low and b.low < c.low:
            poi = v6.SourcePoi(
                v6.PoiKind.RELEVANT_SWING,
                b.low,
                b.low,
                c.closed_at,
            )
            records[_poi_identity(poi, DemoTradingSetupSide.LONG)] = (
                DemoTradingSetupSide.LONG,
                poi,
                c_key,
            )
        if b.high > a.high and b.high > c.high:
            poi = v6.SourcePoi(
                v6.PoiKind.RELEVANT_SWING,
                b.high,
                b.high,
                c.closed_at,
            )
            records[_poi_identity(poi, DemoTradingSetupSide.SHORT)] = (
                DemoTradingSetupSide.SHORT,
                poi,
                c_key,
            )

    for key in keys:
        bars = r6._bars_between_fast(
            indexed,
            start=key,
            end=h4[key].closed_at,
        )
        for side in (
            DemoTradingSetupSide.LONG,
            DemoTradingSetupSide.SHORT,
        ):
            poi = v6._last_cisd_poi(bars, side=side)
            if poi is None:
                continue
            records[_poi_identity(poi, side)] = (side, poi, key)

    return tuple(
        sorted(
            records.values(),
            key=lambda row: (
                row[1].observed_at.astimezone(UTC),
                row[0].value,
                row[1].kind.value,
                row[1].low,
                row[1].high,
            ),
        )
    )


def _first_retouched_at(
    poi: v6.SourcePoi,
    *,
    bars: Sequence[Vt08IndexC2R1Bar],
    opened: Sequence[datetime],
) -> datetime | None:
    start = bisect_left(
        opened,
        poi.observed_at.astimezone(UTC),
    )
    for index in range(start, len(bars)):
        bar = bars[index]
        if poi.touched_by(bar):
            return bar.opened_at.astimezone(UTC)
    return None


def _records(
    *,
    bars: Sequence[Vt08IndexC2R1Bar],
) -> tuple[
    tuple[PoiRecord, ...],
    dict[datetime, int],
    dict[datetime, Vt08IndexC2R1Bar],
    tuple[datetime, ...],
]:
    indexed = {
        bar.opened_at.astimezone(UTC): bar
        for bar in bars
    }
    h4 = v6._build_h4(indexed)
    keys = tuple(sorted(h4))
    key_index = {key: index for index, key in enumerate(keys)}
    opened = tuple(bar.opened_at.astimezone(UTC) for bar in bars)

    result = tuple(
        PoiRecord(
            side=side,
            poi=poi,
            formed_h4_open=formed,
            first_retouched_at=_first_retouched_at(
                poi,
                bars=bars,
                opened=opened,
            ),
        )
        for side, poi, formed in _raw_source_records(
            indexed=indexed,
            h4=h4,
        )
    )
    return result, key_index, h4, keys


def _age_bucket(age_h4: int) -> str:
    if age_h4 <= 2:
        return "AGE_2_H4"
    if age_h4 <= 4:
        return "AGE_3_4_H4"
    if age_h4 <= 8:
        return "AGE_5_8_H4"
    return "AGE_9PLUS_H4"


def _market(
    *,
    symbol: str,
    bars: Sequence[Vt08IndexC2R1Bar],
    start_date: Any,
    end_date: Any,
) -> dict[str, Any]:
    records, key_index, h4, keys = _records(bars=bars)
    indexed = {
        bar.opened_at.astimezone(UTC): bar
        for bar in bars
    }

    by_side = {
        side: tuple(row for row in records if row.side is side)
        for side in (
            DemoTradingSetupSide.LONG,
            DemoTradingSetupSide.SHORT,
        )
    }
    cursors = {
        side: 0
        for side in by_side
    }
    active = {
        side: {}
        for side in by_side
    }

    exact_no_poi_slots = 0
    recoverable_slots = 0
    exact_poi_slots = 0
    older_memory_poi_total = 0
    older_family: Counter[str] = Counter()
    recoverable_family: Counter[str] = Counter()
    recoverable_anchor: Counter[str] = Counter()
    recoverable_age: Counter[str] = Counter()
    memory_slots = 0

    side_cache: dict[Any, DemoTradingSetupSide | None] = {}

    for opened in keys:
        local = opened.astimezone(v7._NY)
        local_date = local.date()
        if not (start_date <= local_date < end_date):
            continue
        if local.hour not in r4.V7_ANCHORS:
            continue
        if local_date not in side_cache:
            side_cache[local_date] = v7._daily_bias(
                indexed,
                before=opened,
            )
        side = side_cache[local_date]
        if side is None:
            continue

        side_records = by_side[side]
        cursor = cursors[side]
        while (
            cursor < len(side_records)
            and side_records[cursor].poi.observed_at.astimezone(UTC)
            <= opened.astimezone(UTC)
        ):
            row = side_records[cursor]
            active[side][row.identity()] = row
            cursor += 1
        cursors[side] = cursor

        expired = [
            identity
            for identity, row in active[side].items()
            if row.first_retouched_at is not None
            and row.first_retouched_at < opened.astimezone(UTC)
        ]
        for identity in expired:
            active[side].pop(identity, None)

        exact = r6._source_pois_fast(
            indexed,
            h4,
            keys,
            h4_opened_at=opened,
            side=side,
        )
        exact_ids = {
            _poi_identity(poi, side)
            for poi in exact
        }
        older = [
            row
            for identity, row in active[side].items()
            if identity not in exact_ids
            and row.formed_h4_open < opened.astimezone(UTC)
        ]

        if exact:
            exact_poi_slots += 1
        else:
            exact_no_poi_slots += 1

        if older:
            memory_slots += 1
            older_memory_poi_total += len(older)
            for row in older:
                older_family[row.poi.kind.value] += 1

        if not exact and older:
            recoverable_slots += 1
            recoverable_anchor[str(local.hour)] += 1
            families_in_slot = {
                row.poi.kind.value
                for row in older
            }
            for family in families_in_slot:
                recoverable_family[family] += 1
            current_index = key_index[opened]
            youngest_age = min(
                current_index - key_index[row.formed_h4_open]
                for row in older
            )
            recoverable_age[_age_bucket(youngest_age)] += 1

    return {
        "symbol": symbol,
        "source_record_count": len(records),
        "exact_poi_slots": exact_poi_slots,
        "exact_no_poi_slots": exact_no_poi_slots,
        "slots_with_distinct_strict_untouched_older_poi": memory_slots,
        "strict_untouched_older_poi_observations_across_slots": (
            older_memory_poi_total
        ),
        "no_poi_slots_with_strict_untouched_older_poi": recoverable_slots,
        "recoverable_fraction_of_exact_no_poi": (
            str(
                Decimal(recoverable_slots)
                / Decimal(exact_no_poi_slots)
            )
            if exact_no_poi_slots
            else "0"
        ),
        "older_poi_family_observations": dict(sorted(older_family.items())),
        "recoverable_slots_by_family_presence": dict(
            sorted(recoverable_family.items())
        ),
        "recoverable_slots_by_anchor": dict(
            sorted(recoverable_anchor.items())
        ),
        "recoverable_slots_by_youngest_poi_age": dict(
            sorted(recoverable_age.items())
        ),
    }


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    bars_by_symbol, provenance = r72._load_window(
        roots=roots,
        window_id=window_id,
    )
    start_date, end_date, canonical_sample = r72._window_contract(window_id)

    markets = {
        symbol: _market(
            symbol=symbol,
            bars=bars_by_symbol[symbol],
            start_date=start_date,
            end_date=end_date,
        )
        for symbol in contract.MARKETS
    }
    exact_no_poi = sum(
        int(row["exact_no_poi_slots"])
        for row in markets.values()
    )
    if exact_no_poi != EXPECTED_NO_POI[window_id]:
        raise ValueError(
            f"R76 {window_id} exact no-POI reconstruction drift: "
            f"{exact_no_poi} != {EXPECTED_NO_POI[window_id]}"
        )

    recoverable = sum(
        int(row["no_poi_slots_with_strict_untouched_older_poi"])
        for row in markets.values()
    )
    return {
        "window_id": window_id,
        "canonical_sample": canonical_sample,
        "exact_no_poi_slots": exact_no_poi,
        "no_poi_slots_with_strict_untouched_older_poi": recoverable,
        "recoverable_fraction": (
            str(Decimal(recoverable) / Decimal(exact_no_poi))
            if exact_no_poi
            else "0"
        ),
        "by_market": markets,
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R76 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R76 source failure decision drift")
    if r72.IDENTITY != "VT08_INDEX_R72_UPSTREAM_DENSITY_LOSS_FORENSICS_001":
        raise ValueError("R76 R72 identity drift")
    if r75.IDENTITY != (
        "VT08_INDEX_R75_STRICT_CROSS_INDEX_AMBIGUOUS_BIAS_CONSENSUS_001"
    ):
        raise ValueError("R76 R75 identity drift")

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
        "source_evidence": {
            "r72": {
                "run_id": SOURCE_R72_RUN_ID,
                "artifact_id": SOURCE_R72_ARTIFACT_ID,
                "artifact_digest": SOURCE_R72_ARTIFACT_DIGEST,
            },
            "r75": {
                "run_id": SOURCE_R75_RUN_ID,
                "artifact_id": SOURCE_R75_ARTIFACT_ID,
                "artifact_digest": SOURCE_R75_ARTIFACT_DIGEST,
                "bias_fallback_path_survived": False,
            },
        },
        "memory_definition": {
            "families": [
                v6.PoiKind.FVG.value,
                v6.PoiKind.RELEVANT_SWING.value,
                v6.PoiKind.CISD.value,
            ],
            "historical_fvg_and_relevant_swing": (
                "every completed consecutive H4 triple using exact V6 geometry"
            ),
            "historical_cisd": (
                "last completed M15 CISD POI inside each completed H4, per side"
            ),
            "strict_memory_condition": (
                "no observed provider M15 bar retouched POI geometry after "
                "observation and before decision anchor"
            ),
            "claim_of_methodology_persistence": False,
            "signal_admission_changed": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": "R76_STRICT_POI_MEMORY_FORENSICS_COMPLETE_NO_SIGNAL_CHANGE",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "provider_observations_only": True,
            "synthetic_or_interpolated_prices_created": False,
            "future_information_used": False,
            "old_poi_admitted_to_trading": False,
            "signals_created": False,
            "signals_suppressed": False,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "risk_changed": False,
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
                    "no_poi": report["five_year"]["exact_no_poi_slots"],
                    "strict_memory_recoverable": report["five_year"][
                        "no_poi_slots_with_strict_untouched_older_poi"
                    ],
                    "fraction": report["five_year"]["recoverable_fraction"],
                },
                "recent_two_year": {
                    "no_poi": report["recent_two_year"]["exact_no_poi_slots"],
                    "strict_memory_recoverable": report["recent_two_year"][
                        "no_poi_slots_with_strict_untouched_older_poi"
                    ],
                    "fraction": report["recent_two_year"][
                        "recoverable_fraction"
                    ],
                },
                "r66": {
                    "no_poi": report["r66_failed_holdout"][
                        "exact_no_poi_slots"
                    ],
                    "strict_memory_recoverable": report[
                        "r66_failed_holdout"
                    ]["no_poi_slots_with_strict_untouched_older_poi"],
                    "fraction": report["r66_failed_holdout"][
                        "recoverable_fraction"
                    ],
                    "by_market": report["r66_failed_holdout"]["by_market"],
                },
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
