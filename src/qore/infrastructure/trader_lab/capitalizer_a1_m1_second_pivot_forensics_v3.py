"""Find subsequent source-native M1 CISD pivots after a broken first pivot.

All observations strictly precede or coincide with the ORIGINAL confirmed M1
source decision. No trade admission, outcomes, fake quotes, author certification.
A second pivot counts as intact only if no M1 since its SWING has touched it.
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

from qore.infrastructure.trader_lab.capitalizer_a1_m1_protected_route_forensics_v2 import (
    A1M1ProtectedRouteReview,
    M1ProtectionClass,
    SourceRouteClass,
)
from qore.infrastructure.trader_lab.capitalizer_a1_source_sensor_independent_attestation_v1 import (
    ProofStatus,
    __source_bar,
    _dt,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEV_WINDOW_END,
    DEV_WINDOW_START,
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_structural_cisd_v48 import (
    V48TimedSourceBar,
    observe_first_structural_cisd,
)
from qore.infrastructure.trader_lab.capitalizer_v50_g_causal_decision_trace import (
    source_opportunity_id,
)

IDENTITY = "QORE_SCALPER_A1_SECOND_NATIVE_M1_PROTECTED_PIVOT_V3"


class SecondaryPivotClass(StrEnum):
    PREVIOUS_V2_PROOF = "PREVIOUS_V2_PROOF"
    LATER_CONFIRMED_INTACT = "LATER_CONFIRMED_INTACT"
    NO_LATER_INTACT_WITH_BREACHES = "NO_LATER_INTACT_WITH_BREACHES"
    NO_LATER_CONFIRMED_PIVOT = "NO_LATER_CONFIRMED_PIVOT"


@dataclass(frozen=True, slots=True)
class A1SecondPivotReview:
    source_opportunity_id: str
    symbol: str
    source_family: str
    decision_at: str
    previous_class: M1ProtectionClass
    finding: SecondaryPivotClass
    distinct_pivots: int
    later_intact: bool
    protected_price: str | None
    swing_at: str | None
    confirmed_at: str | None
    source_signals_changed: bool = False
    entry_veto_added: bool = False
    outcome_used: bool = False
    author_certified: bool = False
    live_authorized: bool = False

    def __post_init__(self) -> None:
        decision = _dt(self.decision_at)
        if not self.source_opportunity_id or self.distinct_pivots < 0:
            raise ValueError("invalid second-pivot source identity")
        if self.later_intact != (
            self.finding is SecondaryPivotClass.LATER_CONFIRMED_INTACT
        ):
            raise ValueError("intact-pivot status mismatch")
        payload = (self.protected_price, self.swing_at, self.confirmed_at)
        if all(x is not None for x in payload) != self.later_intact:
            raise ValueError("intact second pivot must have a complete witness")
        if self.confirmed_at is not None and (
            _dt(self.confirmed_at) > decision
            or self.swing_at is None
            or _dt(self.swing_at) >= _dt(self.confirmed_at)
            or Decimal(self.protected_price or "0") <= 0
        ):
            raise ValueError("future or invalid second-pivot witness")
        if any((
            self.source_signals_changed, self.entry_veto_added,
            self.outcome_used, self.author_certified, self.live_authorized,
        )):
            raise ValueError("pivot forensics grants no economic/execution authority")


def _intact_after_swing(
    *,
    m1: tuple[CapitalizerM1Bar, ...],
    swing_at: datetime,
    swing: Decimal,
    side: CapitalizerSourceDirection,
) -> bool:
    if not m1:
        return False
    forward = (
        swing < m1[-1].close if side is CapitalizerSourceDirection.BULLISH
        else swing > m1[-1].close
    )
    # No future price, and do not overlook invalidation BEFORE confirmation.
    return forward and all(
        (
            bar.low > swing if side is CapitalizerSourceDirection.BULLISH
            else bar.high < swing
        )
        for bar in m1 if bar.opened_at > swing_at
    )


def review_second_pivot(
    *, source: V49Opportunity, first: A1M1ProtectedRouteReview,
    m1: tuple[CapitalizerM1Bar, ...],
) -> A1SecondPivotReview:
    at = _dt(source.m1_trigger_confirmed_at)
    thesis = _dt(source.m15_setup_confirmed_at)
    sid = source_opportunity_id(source)
    if (
        first.source_opportunity_id != sid
        or first.symbol != source.symbol
        or first.source_family != source.m1_trigger_family
        or _dt(first.decision_at) != at
    ):
        raise ValueError("V2 proof differs from frozen original source ID/time/family")
    if not thesis < at or not m1 or m1[-1].closed_at != at or any(
        bar.symbol != source.symbol or bar.closed_at > at for bar in m1
    ):
        raise ValueError("M1 pivot analysis requires source native closed candles")
    if m1[-1].close != Decimal(source.decision_reference_price):
        raise ValueError("source entry differs from native M1 close")
    if first.structurally_protected_at_entry:
        return A1SecondPivotReview(
            source_opportunity_id=sid, symbol=source.symbol,
            source_family=source.m1_trigger_family, decision_at=at.isoformat(),
            previous_class=first.protection_class,
            finding=SecondaryPivotClass.PREVIOUS_V2_PROOF,
            distinct_pivots=0, later_intact=False,
            protected_price=None, swing_at=None, confirmed_at=None,
        )
    local = tuple(bar for bar in m1 if bar.opened_at >= thesis)
    bars = tuple(
        V48TimedSourceBar(
            opened_at=bar.opened_at, closed_at=bar.closed_at,
            source=__source_bar(bar),
        )
        for bar in local
    )
    side = CapitalizerSourceDirection(source.h1_state_direction)
    cursor = thesis
    count = 0
    breaches = 0
    best: tuple[datetime, datetime, Decimal] | None = None
    # Advance by pivot occurrence, NOT by confirmation, so overlapping
    # causal series with later confirmations are not silently skipped.
    for _ in range(len(bars)):
        if cursor >= at:
            break
        observed = observe_first_structural_cisd(
            bars, direction=side, after=cursor, before=at,
            higher_timeframe_closure_confirmed=True,
        )
        if (
            not observed.source_valid
            or observed.swing_occurred_at is None
            or observed.swing_price is None
            or observed.confirmed_at is None
        ):
            break
        physical = next(
            (bar for bar in local
             if bar.opened_at == observed.swing_occurred_at), None
        )
        if physical is None or physical.closed_at <= cursor:
            raise ValueError("non-increasing physical CISD swing frontier")
        count += 1
        if _intact_after_swing(
            m1=local, swing_at=observed.swing_occurred_at,
            swing=observed.swing_price, side=side,
        ):
            candidate = (
                observed.confirmed_at,
                observed.swing_occurred_at,
                observed.swing_price,
            )
            if best is None or candidate[:2] > best[:2]:
                best = candidate
        else:
            breaches += 1
        cursor = physical.closed_at
    label = (
        SecondaryPivotClass.LATER_CONFIRMED_INTACT if best is not None
        else SecondaryPivotClass.NO_LATER_INTACT_WITH_BREACHES if breaches
        else SecondaryPivotClass.NO_LATER_CONFIRMED_PIVOT
    )
    return A1SecondPivotReview(
        source_opportunity_id=sid, symbol=source.symbol,
        source_family=source.m1_trigger_family, decision_at=at.isoformat(),
        previous_class=first.protection_class, finding=label,
        distinct_pivots=count, later_intact=best is not None,
        protected_price=str(best[2]) if best else None,
        swing_at=best[1].isoformat() if best else None,
        confirmed_at=best[0].isoformat() if best else None,
    )


def attest_market(
    *, native_root: Path, source_root: Path, v2_root: Path, output: Path,
) -> dict[str, object]:
    sources = sorted(source_root.rglob(
        "capitalizer-*-v49-hf-capacity-opportunities.jsonl"
    ))
    first_books = sorted(v2_root.rglob(
        "scalper-a1-m1-protection-family-review.jsonl"
    ))
    if len(sources) != 1 or len(first_books) != 1:
        raise ValueError("one original source and one pinned V2 market ledger required")
    original = tuple(
        V49Opportunity(**json.loads(line))
        for line in sources[0].read_text().splitlines() if line.strip()
    )
    first_rows = tuple(
        json.loads(line)
        for line in first_books[0].read_text().splitlines() if line.strip()
    )
    first = {
        r["source_opportunity_id"]: A1M1ProtectedRouteReview(
            **{
                **r,
                "strict_previous_attestation": ProofStatus(
                    r["strict_previous_attestation"]
                ),
                "protection_class": M1ProtectionClass(r["protection_class"]),
                "route_class": SourceRouteClass(r["route_class"]),
            }
        )
        for r in first_rows
    }
    if not original or len(first) != len(original) or len(first_rows) != len(first):
        raise ValueError("V2 source ledger missing or duplicated original source IDs")
    symbol = original[0].symbol
    manifest = json.loads((native_root / "m1-clone-manifest.json").read_text())
    if (
        manifest["canonical_symbol"] != symbol
        or manifest["provider_native_m1"] is not True
        or manifest["synthetic_m1"] is not False
        or manifest["interpolated_m1"] is not False
        or manifest["contradictory_m1"] != 0
        or manifest["read_only"] is not True
    ):
        raise ValueError("second-pivot study requires verified provider-native M1")
    candles = tuple(
        bar for bar in iter_cibo_m1(native_root)
        if DEV_WINDOW_START - timedelta(days=14) <= bar.opened_at < DEV_WINDOW_END
    )
    opened = tuple(bar.opened_at for bar in candles)
    counts: Counter[str] = Counter()
    ids: set[str] = set()
    output.mkdir(parents=True, exist_ok=True)
    with (output / "scalper-a1-second-pivot-evidence.jsonl").open("w") as f:
        for src in original:
            sid = source_opportunity_id(src)
            if sid in ids or sid not in first:
                raise ValueError("original opportunity missing or duplicated")
            ids.add(sid)
            left = bisect.bisect_left(opened, _dt(src.m15_setup_confirmed_at))
            right = bisect.bisect_left(opened, _dt(src.m1_trigger_confirmed_at))
            row = review_second_pivot(
                source=src, first=first[sid], m1=candles[left:right]
            )
            counts["CLASS:" + row.finding.value] += 1
            counts["FAMILY:" + row.source_family] += 1
            counts["JOINT:" + row.source_family + ":" + row.finding.value] += 1
            f.write(json.dumps(asdict(row), sort_keys=True)+"\n")
    result: dict[str, object] = {
        "identity": IDENTITY, "symbol": symbol,
        "source_count": len(original), "reconciled_source_ids": len(ids),
        "class_counts": dict(sorted(counts.items())),
        "source_entries_changed": 0, "added_trade_vetoes": 0,
        "full_master_frame_replayed": False, "certified": False,
    }
    (output / "scalper-a1-second-pivot-market-summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True)+"\n"
    )
    return result


def aggregate_nine_market(root: Path) -> dict[str, object]:
    paths = sorted(root.rglob("scalper-a1-second-pivot-market-summary.json"))
    if len(paths) != 9:
        raise ValueError("second pivot requires all nine markets")
    reports = [json.loads(p.read_text()) for p in paths]
    if len({p["symbol"] for p in reports}) != 9:
        raise ValueError("duplicate native-M1 markets")
    counts: Counter[str] = Counter()
    for r in reports:
        if (
            r["source_entries_changed"] != 0
            or r["added_trade_vetoes"] != 0
            or r["full_master_frame_replayed"]
            or r["certified"]
        ):
            raise ValueError("M1 revalidation must not authorize trading")
        counts.update(r["class_counts"])
    n = sum(int(r["source_count"]) for r in reports)
    if n != 2876 or sum(int(r["reconciled_source_ids"]) for r in reports) != n:
        raise ValueError("source census no longer matches original 2876")
    total = sum(counts["CLASS:" + c.value] for c in SecondaryPivotClass)
    if total != n or counts["CLASS:PREVIOUS_V2_PROOF"] != 1885:
        raise ValueError("secondary classifications lost V2 protected baseline")
    recovered = counts["CLASS:LATER_CONFIRMED_INTACT"]
    return {
        "identity": IDENTITY, "markets": 9,
        "original_opportunities": n,
        "V2_protected_witnesses": 1885,
        "additional_later_protected_witnesses": recovered,
        "contextually_protected_witnesses": 1885 + recovered,
        "still_unconfirmed": 991 - recovered,
        "class_counts": dict(sorted(counts.items())),
        "source_entries_changed": 0, "new_trade_vetoes": 0,
        "full_master_frame_replayed": False,
        "cognitive_profit_factor": None, "cognitive_drawdown_r": None,
        "author_certified": False, "live_authorized": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="mode", required=True)
    m = sub.add_parser("market")
    for key in ("native_m1", "original_v49", "first_v2", "output"):
        m.add_argument(key, type=Path)
    a = sub.add_parser("matrix")
    a.add_argument("markets", type=Path)
    a.add_argument("output", type=Path)
    opts = p.parse_args()
    if opts.mode == "market":
        report = attest_market(
            native_root=opts.native_m1, source_root=opts.original_v49,
            v2_root=opts.first_v2, output=opts.output,
        )
    else:
        report = aggregate_nine_market(opts.markets)
        opts.output.mkdir(parents=True, exist_ok=True)
        (opts.output / "scalper-a1-second-pivot-nine-market.json").write_text(
            json.dumps(report, indent=2, sort_keys=True)+"\n"
        )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
