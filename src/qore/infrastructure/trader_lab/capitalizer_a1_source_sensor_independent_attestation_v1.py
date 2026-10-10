"""Independent M15 / M1 / H1 source witness checks on pinned provider-native M1.

The 2,876 A2 shadow fields marked NOT_AVAILABLE remain UNCHANGED.
This module separately attempts to attest three market STRUCTURE claims from
as-of CLOSED provider-native bars. The fourth field, FULL_COGNITIVE_MASTER_FRAME,
is an execution contract, NOT a market sensor: it remains NOT_AVAILABLE until an
actual nine-market frame has executed with independently evidenced context.

No outcomes, no future M1, no H1 future state expiry, no fresh restrictions.
SOURCE AGREEMENT is only research evidence, never trade permission.
"""
from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import (
    V48AggregatedBar,
    _aggregate,
    _timed_m15,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEV_WINDOW_END,
    DEV_WINDOW_START,
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_m1_cisd_observer_v48 import (
    observe_first_m1_cisd,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_structural_cisd_v48 import (
    V48TimedSourceBar,
    observe_first_structural_cisd,
)
from qore.infrastructure.trader_lab.capitalizer_v50_g_causal_decision_trace import (
    source_opportunity_id,
)

IDENTITY = "QORE_SCALPER_A1_INDEPENDENT_NATIVE_M1_SOURCE_SENSORS_V1"
NAMES = (
    "ACTUAL_M15_STRUCTURE_REVALIDATION",
    "M1_PROTECTED_SWING_ATTESTATION",
    "H1_TARGET_ROOM_R",
    "FULL_COGNITIVE_MASTER_FRAME",
)


class ProofStatus(StrEnum):
    OBSERVED = "OBSERVED"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    CONTRADICTORY = "CONTRADICTORY"


def _dt(value: str) -> datetime:
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("source chronology must be timezone-aware")
    return result


def _bar_time_closed(
    source: V48AggregatedBar, *, minutes: int, at: datetime
) -> bool:
    """Not merely last sampled bar: time bucket MUST have finished."""
    return (
        source.opened_at + timedelta(minutes=minutes) <= at
        and source.closed_at <= at
        and source.minute_count == minutes
    )


@dataclass(frozen=True, slots=True)
class A1SourceSensorEvidence:
    sensor: str
    status: ProofStatus
    reason: str
    observed_at: str
    source_witness: str | None
    independent_witness: str | None
    provenance: str
    author_fidelity_certified: bool = False
    trading_veto_created: bool = False
    outcome_used: bool = False

    def __post_init__(self) -> None:
        if self.sensor not in NAMES or not self.reason or not self.provenance:
            raise ValueError("sensor evidence missing source/provenance")
        _dt(self.observed_at)
        if self.author_fidelity_certified or self.trading_veto_created or self.outcome_used:
            raise ValueError("independent sensor research cannot certify or veto")


@dataclass(frozen=True, slots=True)
class A1SourceSensorAttestation:
    source_opportunity_id: str
    symbol: str
    decision_at: str
    evidence: tuple[A1SourceSensorEvidence, ...]
    source_identity_preserved: bool = True
    historical_outcome_visible: bool = False
    trader_selected: bool = False
    physical_broker_quotes_attested: bool = False

    def __post_init__(self) -> None:
        if (
            not self.source_identity_preserved
            or self.historical_outcome_visible
            or self.trader_selected
            or self.physical_broker_quotes_attested
        ):
            raise ValueError("sensor audit must not alter trade selection")
        if set(x.sensor for x in self.evidence) != set(NAMES):
            raise ValueError("all four independent sensor statuses required")
        if len(self.evidence) != len(NAMES):
            raise ValueError("duplicate sensor evidence")


def _m15_structural(
    source: V49Opportunity,
    *,
    m15: tuple[V48AggregatedBar, ...],
    at: datetime,
    direction: CapitalizerSourceDirection,
) -> A1SourceSensorEvidence:
    target_at = _dt(source.m15_setup_confirmed_at)
    target_price = Decimal(source.m15_protected_swing_price)
    state_at = _dt(source.h1_state_from)
    eligible = tuple(
        row for row in m15
        if row.closed_at <= at
        and _bar_time_closed(row, minutes=15, at=at)
    )
    # Three pre-state bars are required as causal swing context, matching V49.
    left = next(
        (i for i, item in enumerate(eligible) if item.opened_at >= state_at),
        len(eligible),
    )
    window = _timed_m15(eligible[max(0, left - 3):])
    cursor = state_at
    matched: bool = False
    observed_witness: str | None = None
    for _ in range(len(window) + 1):
        if cursor >= at:
            break
        found = observe_first_structural_cisd(
            window, direction=direction, after=cursor, before=at,
            higher_timeframe_closure_confirmed=True,
        )
        if not found.source_valid or found.confirmed_at is None:
            break
        if found.confirmed_at > target_at:
            break
        if found.confirmed_at == target_at:
            observed_witness = (
                f"confirmed={found.confirmed_at.isoformat()};"
                f"swing={found.swing_price};swing_at={found.swing_occurred_at}"
            )
            matched = found.swing_price == target_price
            break
        cursor = found.confirmed_at
    return A1SourceSensorEvidence(
        sensor="ACTUAL_M15_STRUCTURE_REVALIDATION",
        status=(ProofStatus.OBSERVED if matched else ProofStatus.NOT_AVAILABLE),
        reason=(
            "REOBSERVED_FULLY_CLOSED_M15_CISD_MATCHES_ORIGINAL_STOP"
            if matched else "INDEPENDENT_COMPLETE_M15_STRUCTURE_NOT_ATTESTED"
        ),
        observed_at=at.isoformat(),
        source_witness=f"confirmed={target_at.isoformat()};stop={target_price}",
        independent_witness=observed_witness,
        provenance="provider_native_m1_complete_15min_buckets+source_cisd_v48",
    )


def _m1_protected(
    source: V49Opportunity,
    *,
    m1: tuple[CapitalizerM1Bar, ...], at: datetime,
    direction: CapitalizerSourceDirection,
) -> A1SourceSensorEvidence:
    # Only independently CONFIRMED structural swing may be called protected.
    # Sweep CISD proves a causal swept boundary, not automatically a protected
    # TTrades structural pivot. Distinct source families stay distinguishable.
    thesis_at = _dt(source.m15_setup_confirmed_at)
    local = tuple(
        row for row in m1
        if row.opened_at >= thesis_at and row.closed_at <= at
    )
    found: str | None = None
    status = ProofStatus.NOT_AVAILABLE
    if len(local) >= 4 and at > thesis_at:
        timed = tuple(
            V48TimedSourceBar(
                opened_at=row.opened_at, closed_at=row.closed_at,
                source=__source_bar(row),
            )
            for row in local
        )
        witness = observe_first_structural_cisd(
            timed, direction=direction, after=thesis_at, before=at,
            higher_timeframe_closure_confirmed=True,
        )
        if witness.source_valid:
            found = (
                f"confirmed={witness.confirmed_at};swing={witness.swing_price};"
                f"swing_at={witness.swing_occurred_at}"
            )
            if witness.confirmed_at == at:
                status = ProofStatus.OBSERVED
    return A1SourceSensorEvidence(
        sensor="M1_PROTECTED_SWING_ATTESTATION",
        status=status,
        reason=(
            "M1_STRUCTURAL_CISD_AT_EXACT_SOURCE_CLOSE_WITH_PROTECTED_PIVOT"
            if status is ProofStatus.OBSERVED
            else "M1_PROTECTED_SWING_NOT_INDEPENDENTLY_REOBSERVED_AT_SOURCE_CLOSE"
        ),
        observed_at=at.isoformat(),
        source_witness=f"{source.m1_trigger_family};at={at.isoformat()}",
        independent_witness=found,
        provenance="native_m1_structural_cisd_v48_no_sweep_extreme_alias",
    )


def __source_bar(row: CapitalizerM1Bar):
    from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
        CapitalizerSourceBar,
    )
    return CapitalizerSourceBar(
        open=row.open, high=row.high, low=row.low, close=row.close
    )


def _h1_target(
    source: V49Opportunity,
    *,
    h1: tuple[V48AggregatedBar, ...],
    m1: tuple[CapitalizerM1Bar, ...],
    at: datetime,
    direction: CapitalizerSourceDirection,
) -> A1SourceSensorEvidence:
    original = Decimal(source.structural_target_witness_price)
    entry = Decimal(source.decision_reference_price)
    risk = abs(entry - Decimal(source.m15_protected_swing_price))
    if risk <= 0:
        raise ValueError("source M15 stop and entry cannot be identical")
    # Crucial: use only FULLY-CLOSED physical H1 buckets at <= as-of,
    # never V49's optional 45/60 partial aggregate as proof.
    candidates = tuple(
        bar for bar in h1 if _bar_time_closed(bar, minutes=60, at=at)
    )
    witnesses: list[tuple[Decimal, datetime]] = []
    for bar in reversed(candidates[-24:]):
        level = (
            bar.source.high
            if direction is CapitalizerSourceDirection.BULLISH
            else bar.source.low
        )
        ahead = (
            level > entry if direction is CapitalizerSourceDirection.BULLISH
            else level < entry
        )
        if not ahead:
            continue
        untouched = all(
            row.high < level if direction is CapitalizerSourceDirection.BULLISH
            else row.low > level
            for row in m1
            if bar.closed_at < row.opened_at and row.closed_at <= at
        )
        if untouched:
            witnesses.append((level, bar.closed_at))
    original_witness = next(
        ((value, confirmed) for value, confirmed in witnesses if value == original),
        None,
    )
    status = (
        ProofStatus.OBSERVED if original_witness is not None
        else ProofStatus.NOT_AVAILABLE
    )
    room = (
        (original-entry) / risk
        if direction is CapitalizerSourceDirection.BULLISH
        else (entry-original) / risk
    )
    return A1SourceSensorEvidence(
        sensor="H1_TARGET_ROOM_R",
        status=status,
        reason=(
            "ORIGINAL_TARGET_IS_UNTOUCHED_PRIOR_COMPLETE_H1_LIQUIDITY_WITNESS"
            if original_witness is not None
            else "NO_INDEPENDENT_FULLY_CLOSED_UNTOUCHED_H1_TARGET_WITNESS"
        ),
        observed_at=at.isoformat(),
        source_witness=f"target={original};room_r={room}",
        independent_witness=(
            f"target={original_witness[0]};confirmed={original_witness[1]}"
            if original_witness is not None else None
        ),
        provenance="provider_native_m1_completed_60min_h1+causal_untouched_scan",
    )


def attest_source_sensors(
    source: V49Opportunity,
    *,
    m1: tuple[CapitalizerM1Bar, ...],
    m15: tuple[V48AggregatedBar, ...],
    h1: tuple[V48AggregatedBar, ...],
) -> A1SourceSensorAttestation:
    """Independent source-attestation overlay, NEVER a replacement source gate."""
    at = _dt(source.m1_trigger_confirmed_at)
    if any(bar.closed_at > at for bar in m1):
        raise ValueError("sensor witness must not consume future M1")
    if not m1 or m1[-1].closed_at != at:
        raise ValueError("original source requires exact closed native M1 candle")
    if m1[-1].symbol != source.symbol:
        raise ValueError("source market versus native M1 mismatch")
    if Decimal(source.decision_reference_price) != m1[-1].close:
        raise ValueError("source entry differs from native decision candle close")
    direction = CapitalizerSourceDirection(source.h1_state_direction)
    evidence = (
        _m15_structural(source, m15=m15, at=at, direction=direction),
        _m1_protected(source, m1=m1, at=at, direction=direction),
        _h1_target(source, h1=h1, m1=m1, at=at, direction=direction),
        A1SourceSensorEvidence(
            sensor="FULL_COGNITIVE_MASTER_FRAME",
            status=ProofStatus.NOT_AVAILABLE,
            reason="REAL_NINE_MARKET_MASTER_FRAME_CANNOT_BE_PROVED_FROM_ONE_MARKET_OHLC",
            observed_at=at.isoformat(),
            source_witness=None, independent_witness=None,
            provenance="requires_asof_nine_market_world_perceptions_regime_crossmarket",
        ),
    )
    return A1SourceSensorAttestation(
        source_opportunity_id=source_opportunity_id(source),
        symbol=source.symbol,
        decision_at=at.isoformat(),
        evidence=evidence,
    )


def attest_market(native_root: Path, source_root: Path, target: Path) -> dict[str, Any]:
    paths = sorted(source_root.rglob(
        "capitalizer-*-v49-hf-capacity-opportunities.jsonl"
    ))
    if len(paths) != 1:
        raise ValueError("one frozen original V49 market source book needed")
    opportunities = tuple(
        V49Opportunity(**json.loads(line))
        for line in paths[0].read_text().splitlines() if line.strip()
    )
    if not opportunities or len({row.symbol for row in opportunities}) != 1:
        raise ValueError("invalid original source market book")
    symbol = opportunities[0].symbol
    manifest = json.loads((native_root / "m1-clone-manifest.json").read_text())
    if (
        manifest["canonical_symbol"] != symbol
        or manifest["provider_native_m1"] is not True
        or manifest["synthetic_m1"] is not False
        or manifest["interpolated_m1"] is not False
        or manifest["contradictory_m1"] != 0
        or manifest["read_only"] is not True
    ):
        raise ValueError("source M1 is not attested provider-native read-only")
    bars = tuple(
        row for row in iter_cibo_m1(native_root)
        if DEV_WINDOW_START - timedelta(days=14) <= row.opened_at < DEV_WINDOW_END
    )
    opened = tuple(row.opened_at for row in bars)
    m15 = _aggregate(bars, minutes=15)
    h1 = _aggregate(bars, minutes=60)
    target.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    status_counts: Counter[str] = Counter()
    with (target / "scalper-a1-independent-source-sensors.jsonl").open("w") as out:
        for source in opportunities:
            sid = source_opportunity_id(source)
            if sid in seen:
                raise ValueError("duplicate source opportunity")
            seen.add(sid)
            at = _dt(source.m1_trigger_confirmed_at)
            left = bisect.bisect_left(
                opened, _dt(source.m15_setup_confirmed_at) - timedelta(minutes=5)
            )
            # As-of includes enough earlier H1 native context for untouched check.
            right = bisect.bisect_left(opened, at)
            asof = bars[:right]
            if not asof or asof[-1].closed_at != at:
                raise ValueError("source M1 decision close not present natively")
            row = attest_source_sensors(
                source, m1=asof,
                m15=m15, h1=h1,
            )
            for item in row.evidence:
                status_counts[item.sensor+":"+item.status.value] += 1
            out.write(json.dumps(asdict(row), sort_keys=True) + "\n")
    report: dict[str, Any] = {
        "identity": IDENTITY,
        "symbol": symbol,
        "original_opportunities": len(opportunities),
        "independently_attested_rows": len(seen),
        "sensor_status_counts": dict(sorted(status_counts.items())),
        "source_entries_modified": 0,
        "new_entry_vetoes": 0,
        "full_master_frame_claimed": False,
        "trader_certified": False,
        "live_authorized": False,
    }
    (target / "scalper-a1-independent-source-sensors-market.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    return report


def aggregate_nine_markets(root: Path) -> dict[str, Any]:
    paths = sorted(root.rglob("scalper-a1-independent-source-sensors-market.json"))
    if len(paths) != 9:
        raise ValueError("independent witness requires 9 market reports")
    reports = [json.loads(p.read_text()) for p in paths]
    if len({r["symbol"] for r in reports}) != 9:
        raise ValueError("duplicated independent market")
    counts: Counter[str] = Counter()
    for report in reports:
        if (
            report["source_entries_modified"] != 0
            or report["new_entry_vetoes"] != 0
            or report["full_master_frame_claimed"]
        ):
            raise ValueError("revalidation is not strategy gating")
        counts.update(report["sensor_status_counts"])
    census = sum(int(r["original_opportunities"]) for r in reports)
    if census != 2876:
        raise ValueError("revalidation must preserve 2876 original source IDs")
    if sum(int(r["independently_attested_rows"]) for r in reports) != census:
        raise ValueError("revalidation lost source identities")
    for name in NAMES:
        total = sum(counts[name + ":" + s.value] for s in ProofStatus)
        if total != census:
            raise ValueError("one status per source/sensor required")
    return {
        "identity": IDENTITY,
        "markets": 9,
        "source_opportunities": census,
        "sensor_status_counts": dict(sorted(counts.items())),
        "full_historical_master_frame_completed": False,
        "cognitive_profit_factor": None,
        "cognitive_drawdown_r": None,
        "new_entry_vetoes": 0,
        "trader_certified": False,
        "live_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    market = sub.add_parser("market")
    market.add_argument("native_m1", type=Path)
    market.add_argument("source_v49", type=Path)
    market.add_argument("output", type=Path)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("market_reports", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.mode == "market":
        report = attest_market(args.native_m1, args.source_v49, args.output)
    else:
        report = aggregate_nine_markets(args.market_reports)
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "scalper-a1-independent-source-sensors-nine-market.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n"
        )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
