"""Independent as-of forensic explanation for missing M1 protected-swing evidence.

Runs over the SAME 2876 immutable V49 source identities and real provider
native M1 as earlier A1 attestation. A protected pivot verified BEFORE a
source entry may remain structurally protected if the actual M1 path NEVER
revisits it. This is NOT source-route authorization. CISD family/timestamp
discrepancies are separately counted and NEVER treated as a veto.

No hindsight, no counterfactual outcomes, no synthetic candles, no live orders.
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

from qore.infrastructure.trader_lab.capitalizer_a1_source_sensor_independent_attestation_v1 import (
    ProofStatus,
    __source_bar,
    _dt,
    _m1_protected,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
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
from qore.infrastructure.trader_lab.capitalizer_ttrades_m1_fvg_cisd_continuation_v48 import (
    observe_first_m1_fvg_cisd_continuation,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_structural_cisd_v48 import (
    V48TimedSourceBar,
    observe_first_structural_cisd,
)
from qore.infrastructure.trader_lab.capitalizer_v50_g_causal_decision_trace import (
    source_opportunity_id,
)

IDENTITY = "QORE_SCALPER_A1_M1_PROTECTED_EARLIER_V2_CAUSAL_REVIEW"
FAMILIES = frozenset(("LIQUIDITY_SWEEP_CISD", "FVG_RETRACE_CISD"))


class M1ProtectionClass(StrEnum):
    AT_SOURCE_CLOSE = "AT_SOURCE_CLOSE"
    PRIOR_CONFIRMED_INTACT = "PRIOR_CONFIRMED_INTACT"
    PRIOR_CONFIRMED_BREACHED = "PRIOR_CONFIRMED_BREACHED"
    NO_CONFIRMED_STRUCTURAL_PIVOT = "NO_CONFIRMED_STRUCTURAL_PIVOT"


class SourceRouteClass(StrEnum):
    SOURCE_ROUTE_CONFIRMED_AT_ENTRY = "SOURCE_ROUTE_CONFIRMED_AT_ENTRY"
    SOURCE_ROUTE_CONFIRMED_EARLIER = "SOURCE_ROUTE_CONFIRMED_EARLIER"
    ONLY_OTHER_ROUTE_CONFIRMED = "ONLY_OTHER_ROUTE_CONFIRMED"
    NO_ROUTE_CONFIRMED_BY_SOURCE = "NO_ROUTE_CONFIRMED_BY_SOURCE"


@dataclass(frozen=True, slots=True)
class A1M1ProtectedRouteReview:
    source_opportunity_id: str
    symbol: str
    source_family: str
    decision_at: str
    strict_previous_attestation: ProofStatus
    protection_class: M1ProtectionClass
    structurally_protected_at_entry: bool
    protected_price: str | None
    protection_confirmed_at: str | None
    route_class: SourceRouteClass
    own_route_first_confirmed_at: str | None
    other_route_first_confirmed_at: str | None
    source_signal_preserved: bool = True
    eligibility_changed: bool = False
    author_methodology_certified: bool = False
    future_outcome_used: bool = False
    live_authorized: bool = False

    def __post_init__(self) -> None:
        if self.source_family not in FAMILIES or not self.source_opportunity_id:
            raise ValueError("invalid source family or opportunity identity")
        decision = _dt(self.decision_at)
        if self.structurally_protected_at_entry != (
            self.protection_class in (
                M1ProtectionClass.AT_SOURCE_CLOSE,
                M1ProtectionClass.PRIOR_CONFIRMED_INTACT,
            )
        ):
            raise ValueError("protected verdict and causal evidence contradict")
        if (self.strict_previous_attestation is ProofStatus.OBSERVED) != (
            self.protection_class is M1ProtectionClass.AT_SOURCE_CLOSE
        ):
            raise ValueError("A1 v2 cannot erase or fabricate the existing strict proof")
        if self.protection_confirmed_at is not None and (
            _dt(self.protection_confirmed_at) > decision
        ):
            raise ValueError("future M1 protected pivot")
        for at in (
            self.own_route_first_confirmed_at,
            self.other_route_first_confirmed_at,
        ):
            if at is not None and _dt(at) > decision:
                raise ValueError("future source route evidence")
        if any((
            not self.source_signal_preserved, self.eligibility_changed,
            self.author_methodology_certified, self.future_outcome_used,
            self.live_authorized,
        )):
            raise ValueError("M1 analysis is descriptive, not a trading gate")


def _first_routes(
    m1: tuple[CapitalizerM1Bar, ...], *,
    thesis_at: datetime, decision_at: datetime,
    direction: CapitalizerSourceDirection,
) -> dict[str, datetime | None]:
    side = (
        CapitalizerSide.LONG
        if direction is CapitalizerSourceDirection.BULLISH
        else CapitalizerSide.SHORT
    )
    sweep = observe_first_m1_cisd(
        m1, thesis_at=thesis_at, deadline_at=decision_at, side=side
    )
    fvg = observe_first_m1_fvg_cisd_continuation(
        m1, thesis_at=thesis_at, deadline_at=decision_at, direction=direction
    )
    return {
        "LIQUIDITY_SWEEP_CISD": sweep.confirmed_at if sweep.confirmed else None,
        "FVG_RETRACE_CISD": fvg.cisd_confirmed_at if fvg.confirmed else None,
    }


def review_source_m1(
    *, source: V49Opportunity,
    m1: tuple[CapitalizerM1Bar, ...],
) -> A1M1ProtectedRouteReview:
    """Review ONLY bars with closed_at <= original decision, never subsequent M1."""
    at, thesis = _dt(source.m1_trigger_confirmed_at), _dt(
        source.m15_setup_confirmed_at
    )
    if not thesis < at or source.m1_trigger_family not in FAMILIES:
        raise ValueError("unsupported or reversed original M15/M1 causal frontier")
    if not m1 or m1[-1].closed_at != at or any(
        b.symbol != source.symbol or b.closed_at > at for b in m1
    ):
        raise ValueError("incomplete/foreign/future native M1 at source close")
    if m1[-1].close != Decimal(source.decision_reference_price):
        raise ValueError("native source M1 close differs from frozen V49")
    local = tuple(
        b for b in m1 if b.opened_at >= thesis and b.closed_at <= at
    )
    direction = CapitalizerSourceDirection(source.h1_state_direction)
    strict = _m1_protected(source, m1=local, at=at, direction=direction)
    evidence = None
    if len(local) >= 4:
        timed = tuple(
            V48TimedSourceBar(
                opened_at=b.opened_at, closed_at=b.closed_at,
                source=__source_bar(b),
            )
            for b in local
        )
        evidence = observe_first_structural_cisd(
            timed, direction=direction, after=thesis, before=at,
            higher_timeframe_closure_confirmed=True,
        )
    witness_at = evidence.confirmed_at if evidence and evidence.source_valid else None
    pivot = evidence.swing_price if witness_at is not None and evidence else None
    if strict.status is ProofStatus.OBSERVED:
        cls = M1ProtectionClass.AT_SOURCE_CLOSE
    elif witness_at is None or pivot is None:
        cls = M1ProtectionClass.NO_CONFIRMED_STRUCTURAL_PIVOT
    else:
        intact = all(
            (
                b.low > pivot
                if direction is CapitalizerSourceDirection.BULLISH
                else b.high < pivot
            )
            for b in local if witness_at < b.closed_at <= at
        )
        # Also reject a pivot on the wrong side of actual source M1 close.
        forward = (
            pivot < m1[-1].close
            if direction is CapitalizerSourceDirection.BULLISH
            else pivot > m1[-1].close
        )
        cls = (
            M1ProtectionClass.PRIOR_CONFIRMED_INTACT
            if intact and forward
            else M1ProtectionClass.PRIOR_CONFIRMED_BREACHED
        )

    routes = _first_routes(
        local, thesis_at=thesis, decision_at=at, direction=direction,
    ) if len(local) >= 4 else {name: None for name in FAMILIES}
    own = routes[source.m1_trigger_family]
    other_name = next(name for name in FAMILIES if name != source.m1_trigger_family)
    other = routes[other_name]
    if own == at:
        route_class = SourceRouteClass.SOURCE_ROUTE_CONFIRMED_AT_ENTRY
    elif own is not None and own < at:
        route_class = SourceRouteClass.SOURCE_ROUTE_CONFIRMED_EARLIER
    elif other is not None:
        route_class = SourceRouteClass.ONLY_OTHER_ROUTE_CONFIRMED
    else:
        route_class = SourceRouteClass.NO_ROUTE_CONFIRMED_BY_SOURCE
    return A1M1ProtectedRouteReview(
        source_opportunity_id=source_opportunity_id(source),
        symbol=source.symbol,
        source_family=source.m1_trigger_family,
        decision_at=at.isoformat(),
        strict_previous_attestation=strict.status,
        protection_class=cls,
        structurally_protected_at_entry=cls in (
            M1ProtectionClass.AT_SOURCE_CLOSE,
            M1ProtectionClass.PRIOR_CONFIRMED_INTACT,
        ),
        protected_price=str(pivot) if pivot is not None else None,
        protection_confirmed_at=witness_at.isoformat() if witness_at else None,
        route_class=route_class,
        own_route_first_confirmed_at=own.isoformat() if own else None,
        other_route_first_confirmed_at=other.isoformat() if other else None,
    )


def run_m1_market_forensics(
    *, source_root: Path, native_root: Path, output: Path,
) -> dict[str, object]:
    sources = sorted(source_root.rglob(
        "capitalizer-*-v49-hf-capacity-opportunities.jsonl"
    ))
    if len(sources) != 1:
        raise ValueError("expected one exact frozen V49 market source book")
    original = tuple(V49Opportunity(**json.loads(line)) for line
                     in sources[0].read_text().splitlines() if line.strip())
    if not original or len({r.symbol for r in original}) != 1:
        raise ValueError("malformed original source book")
    symbol = original[0].symbol
    manifest = json.loads((native_root / "m1-clone-manifest.json").read_text())
    if not (
        manifest["canonical_symbol"] == symbol
        and manifest["provider_native_m1"] is True
        and manifest["synthetic_m1"] is False
        and manifest["interpolated_m1"] is False
        and manifest["read_only"] is True
        and manifest["contradictory_m1"] == 0
    ):
        raise ValueError("raw M1 provider manifest not trusted")
    bars = tuple(b for b in iter_cibo_m1(native_root) if
                 DEV_WINDOW_START - timedelta(days=14) <= b.opened_at < DEV_WINDOW_END)
    opened = tuple(b.opened_at for b in bars)
    seen: set[str] = set()
    counts: Counter[str] = Counter()
    output.mkdir(parents=True, exist_ok=True)
    with (output / "scalper-a1-m1-protection-family-review.jsonl").open("w") as handle:
        for source in original:
            left = bisect.bisect_left(opened, _dt(source.m15_setup_confirmed_at))
            right = bisect.bisect_left(opened, _dt(source.m1_trigger_confirmed_at))
            # Only causal post-M15 M1 bars, through the source decision close.
            record = review_source_m1(source=source, m1=bars[left:right])
            if record.source_opportunity_id in seen:
                raise ValueError("reused historical source ID")
            seen.add(record.source_opportunity_id)
            counts[f"PROTECTION:{record.protection_class.value}"] += 1
            counts[f"ROUTE:{record.route_class.value}"] += 1
            counts[f"FAMILY:{record.source_family}"] += 1
            counts[f"JOINT:{record.source_family}:{record.protection_class.value}"] += 1
            handle.write(json.dumps(asdict(record), sort_keys=True)+"\n")
    result: dict[str, object] = {
        "identity": IDENTITY,
        "symbol": symbol,
        "original_opportunities": len(original),
        "verified_source_ids": len(seen),
        "strict_original_m1_proof_count": counts[
            "PROTECTION:AT_SOURCE_CLOSE"
        ],
        "extended_causal_m1_proof_count": (
            counts["PROTECTION:AT_SOURCE_CLOSE"]
            + counts["PROTECTION:PRIOR_CONFIRMED_INTACT"]
        ),
        "class_counts": dict(sorted(counts.items())),
        "new_entry_vetoes": 0,
        "source_entries_modified": 0,
        "full_nine_market_master_frame_claimed": False,
        "live_authorized": False,
    }
    (output / "scalper-a1-m1-protection-market-summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True)+"\n"
    )
    return result


def aggregate_m1_nine_market_forensics(root: Path) -> dict[str, object]:
    paths = sorted(root.rglob("scalper-a1-m1-protection-market-summary.json"))
    if len(paths) != 9:
        raise ValueError("nine original M1 market reviews must be present")
    reports = [json.loads(p.read_text()) for p in paths]
    if len({r["symbol"] for r in reports}) != 9:
        raise ValueError("duplicated market report")
    counts: Counter[str] = Counter()
    for report in reports:
        if (
            report["source_entries_modified"] != 0
            or report["new_entry_vetoes"] != 0
            or report["full_nine_market_master_frame_claimed"]
        ):
            raise ValueError("M1 forensic review cannot become strategy authorization")
        counts.update(report["class_counts"])
    n = sum(int(r["original_opportunities"]) for r in reports)
    if n != 2876 or sum(int(r["verified_source_ids"]) for r in reports) != n:
        raise ValueError("M1 market/source provenance did not preserve V49 census")
    total = sum(counts[f"PROTECTION:{c.value}"] for c in M1ProtectionClass)
    if total != n or sum(counts[f"ROUTE:{c.value}"] for c in SourceRouteClass) != n:
        raise ValueError("one complete forensic category required for every source")
    if counts["PROTECTION:AT_SOURCE_CLOSE"] != 1244:
        raise ValueError("new forensic pass must match 1244 strict A1 reference cases")
    return {
        "identity": IDENTITY,
        "markets": 9,
        "original_opportunities": n,
        "source_ids_preserved": True,
        "strict_previous_proofs": counts["PROTECTION:AT_SOURCE_CLOSE"],
        "new_prior_intact_proofs": counts["PROTECTION:PRIOR_CONFIRMED_INTACT"],
        "extended_causal_proofs": (
            counts["PROTECTION:AT_SOURCE_CLOSE"]
            + counts["PROTECTION:PRIOR_CONFIRMED_INTACT"]
        ),
        "not_independently_proven": (
            counts["PROTECTION:PRIOR_CONFIRMED_BREACHED"]
            + counts["PROTECTION:NO_CONFIRMED_STRUCTURAL_PIVOT"]
        ),
        "classification": dict(sorted(counts.items())),
        "new_entry_vetoes": 0,
        "certified_author_methodology": False,
        "full_master_frame_historical_replay": False,
        "cognitive_pf": None,
        "cognitive_drawdown_r": None,
        "live_authorized": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="mode", required=True)
    market = sub.add_parser("market")
    market.add_argument("native_m1", type=Path)
    market.add_argument("source_book", type=Path)
    market.add_argument("output", type=Path)
    overall = sub.add_parser("matrix")
    overall.add_argument("market_reports", type=Path)
    overall.add_argument("output", type=Path)
    opts = p.parse_args()
    if opts.mode == "market":
        report = run_m1_market_forensics(
            source_root=opts.source_book, native_root=opts.native_m1,
            output=opts.output,
        )
    else:
        report = aggregate_m1_nine_market_forensics(opts.market_reports)
        opts.output.mkdir(parents=True, exist_ok=True)
        (opts.output / "scalper-a1-m1-protection-nine-market-summary.json").write_text(
            json.dumps(report, indent=2, sort_keys=True)+"\n"
        )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
