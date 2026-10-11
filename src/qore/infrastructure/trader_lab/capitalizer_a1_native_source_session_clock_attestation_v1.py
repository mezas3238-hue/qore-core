"""Audit original V49 M1 decision clock vs QORE sessions and source killzones.

Provider/source original chronology, DST conversion and two DIFFERENT session
definitions stay separate. This is clock provenance, NOT an author's permission
to trade, not a Market Brain regime, and not a broker quote attestation.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_a1_entry_timing_clock_v1 import (
    session_end_at,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    allowed_markets,
)
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import (
    _operating_date,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import (
    capitalizer_session_at,
)
from qore.infrastructure.trader_lab.capitalizer_source_session_context_v2 import (
    CapitalizerSourceSessionResolution,
    assess_source_session_context,
)
from qore.infrastructure.trader_lab.capitalizer_v50_g_causal_decision_trace import (
    source_opportunity_id,
)

IDENTITY = "QORE_SCALPER_A1_NATIVE_V49_SOURCE_SESSION_CLOCK_DST_V1"
NY = ZoneInfo("America/New_York")


class ClockAttestationStatus(StrEnum):
    QORE_BUCKET_RECONFIRMED = "QORE_BUCKET_RECONFIRMED"
    QORE_BUCKET_CONTRADICTED = "QORE_BUCKET_CONTRADICTED"


@dataclass(frozen=True, slots=True)
class A1V49SourceClockEvidence:
    source_opportunity_id: str
    symbol: str
    source_session: CapitalizerSession
    source_operating_date: str
    observed_at: str
    m1_opened_at: str
    new_york_local_time: str
    new_york_utc_offset_minutes: int
    qore_bucket_reconfirmed: ClockAttestationStatus
    local_operating_day_reconfirmed: bool
    within_qore_research_session: bool
    remaining_session_seconds: int | None
    methodology_window_resolution: CapitalizerSourceSessionResolution
    methodology_window_id: str
    source_author_fidelity_proven: bool = False
    new_entry_veto: bool = False
    did_execute_master_frame: bool = False
    broker_quote_attested: bool = False
    live_authorized: bool = False

    def __post_init__(self) -> None:
        at = datetime.fromisoformat(self.observed_at)
        start = datetime.fromisoformat(self.m1_opened_at)
        if (
            at.utcoffset() is None
            or start.utcoffset() is None
            or at - start != timedelta(minutes=1)
            or not self.source_opportunity_id
        ):
            raise ValueError("M1 source clock requires exact timezone-aware closed bar")
        if self.local_operating_day_reconfirmed and not self.within_qore_research_session:
            raise ValueError("cannot confirm V49 operational date outside research bucket")
        if self.within_qore_research_session != (
            self.qore_bucket_reconfirmed is ClockAttestationStatus.QORE_BUCKET_RECONFIRMED
        ):
            raise ValueError("session observation flag disagrees with causal comparison")
        if any((
            self.source_author_fidelity_proven, self.new_entry_veto,
            self.did_execute_master_frame, self.broker_quote_attested,
            self.live_authorized,
        )):
            raise ValueError("clock revalidation cannot authorize a strategy or execution")


def assess_v49_source_clock(source: V49Opportunity) -> A1V49SourceClockEvidence:
    """Recompute original decision source group independently of stored label."""
    at = datetime.fromisoformat(source.m1_trigger_confirmed_at)
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("original V49 source time must have a timezone")
    before = at - timedelta(minutes=1)
    local = at.astimezone(NY)
    offset = local.utcoffset()
    if offset is None:
        raise ValueError("New York source clock lacks civil timezone offset")
    # DST correctness is judged by zoneinfo at the UTC INSTANT; never
    # add a static "-4" or "-5" shift to provider data.
    if (offset.total_seconds() / 60) not in (-240, -300):
        raise ValueError("historical New York timezone offset unsupported")
    session = CapitalizerSession(source.session)
    permitted = source.symbol in allowed_markets(session)
    recorded_at = capitalizer_session_at(at)
    recorded_at_open = capitalizer_session_at(before)
    consistent = permitted and recorded_at is session and recorded_at_open is session
    operational_day_matches = consistent and (
        _operating_date(before, session) == source.operating_date
    )
    secs: int | None = None
    if consistent:
        end_at = session_end_at(at, session.value)
        secs = int((end_at - at).total_seconds())
        if secs <= 0:
            raise ValueError("source clock has nonpositive session runway")
    # ICT/source-specific window is a DIFFERENT construct. Asian Open
    # reference absent from original source row: categorically unproven.
    methodology = assess_source_session_context(
        session=session, observed_at=at, asian_open_reference_at=None,
    )
    return A1V49SourceClockEvidence(
        source_opportunity_id=source_opportunity_id(source),
        symbol=source.symbol,
        source_session=session,
        source_operating_date=source.operating_date,
        observed_at=at.isoformat(),
        m1_opened_at=before.isoformat(),
        new_york_local_time=local.isoformat(),
        new_york_utc_offset_minutes=int(offset.total_seconds() / 60),
        qore_bucket_reconfirmed=(
            ClockAttestationStatus.QORE_BUCKET_RECONFIRMED
            if consistent else ClockAttestationStatus.QORE_BUCKET_CONTRADICTED
        ),
        local_operating_day_reconfirmed=operational_day_matches,
        within_qore_research_session=consistent,
        remaining_session_seconds=secs,
        methodology_window_resolution=methodology.resolution,
        methodology_window_id=methodology.source_window_id,
    )


def audit_nine_market_source_clock(root: Path, target: Path) -> dict[str, object]:
    """Preserve every source, including conflicts; never automatically veto."""
    paths = sorted(root.rglob("capitalizer-*-v49-hf-capacity-opportunities.jsonl"))
    if len(paths) != 9:
        raise ValueError("session clock audit requires all nine frozen V49 books")
    seen: set[str] = set()
    symbols: set[str] = set()
    counts: Counter[str] = Counter()
    target.mkdir(parents=True, exist_ok=True)
    with (target / "scalper-a1-native-v49-source-clock-evidence.jsonl").open("w") as out:
        for path in paths:
            rows = tuple(
                V49Opportunity(**json.loads(line))
                for line in path.read_text().splitlines() if line.strip()
            )
            if not rows or len({x.symbol for x in rows}) != 1:
                raise ValueError("empty or mixed original source book")
            symbol = rows[0].symbol
            if symbol in symbols:
                raise ValueError("duplicate V49 source market")
            symbols.add(symbol)
            for row in rows:
                evidence = assess_v49_source_clock(row)
                if evidence.source_opportunity_id in seen:
                    raise ValueError("duplicate V49 source identity")
                seen.add(evidence.source_opportunity_id)
                counts["QORE:" + evidence.qore_bucket_reconfirmed.value] += 1
                counts["OPERATING_DATE:" + str(
                    evidence.local_operating_day_reconfirmed
                )] += 1
                counts["DST_OFFSET_MINUTES:" + str(
                    evidence.new_york_utc_offset_minutes
                )] += 1
                counts["SOURCE_WINDOW:" + (
                    evidence.source_session.value + ":" +
                    evidence.methodology_window_resolution.value
                )] += 1
                out.write(json.dumps(asdict(evidence), sort_keys=True) + "\n")
    if len(seen) != 2876 or len(symbols) != 9:
        raise ValueError("native source clock lost V49 original 2876/9 coverage")
    summary: dict[str, object] = {
        "identity": IDENTITY,
        "original_source_ids": len(seen),
        "markets": len(symbols),
        "counts": dict(sorted(counts.items())),
        "source_entries_removed": 0,
        "new_vetoes": 0,
        "session_bucket_equals_author_killzone": False,
        "asian_open_author_clock_attested": False,
        "broker_bid_ask_attested": False,
        "full_nine_market_master_frame_replayed": False,
        "cognitive_pf": None,
        "cognitive_drawdown_r": None,
        "author_certified": False,
        "live_authorized": False,
    }
    (target / "scalper-a1-native-nine-market-clock-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)+"\n"
    )
    return summary


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("original_v49", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    print(json.dumps(audit_nine_market_source_clock(args.original_v49,args.output),
                     sort_keys=True))


if __name__ == "__main__":
    main()
