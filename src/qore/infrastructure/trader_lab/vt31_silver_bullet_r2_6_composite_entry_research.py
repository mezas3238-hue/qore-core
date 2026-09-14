"""VT-31 R2.6 causal multi-family entry-selection research.

TTrades demonstrates Breaker, Fair Value Gap and Order Block entries but does
not prescribe one universal family priority.  This research resolves only that
ambiguity: after structural confirmation it selects the nearest still-valid
retracement level across every demonstrated family.  The policy is identical
for all Owner-authorized markets and both sides.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import cast

from qore.infrastructure.market_data import Instrument, OhlcSnapshot
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    MARKETS,
    SOURCE_MARKET,
    Vt31R25ResearchError,
    Vt31R25Variant,
    _day,
    _entry,
    _metrics,
    _quartiles,
    _Setup,
    _simulate,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    SOURCE_SHA256,
    SOURCE_VIDEO,
    Vt31R22EntryEvidence,
    _detect_raid,
    _entry_evidence,
    _session_bars,
    _structure,
    _validate_evidence,
    build_reference_range,
)

SCHEMA = "qore.trader_lab.vt31_r2_6_composite_entry_research.v1"
HYPOTHESIS_COUNT = 3
_LOCATIONS = ("near-stop", "midpoint", "near-target")


@dataclass(frozen=True, slots=True)
class Vt31R26Variant:
    location: str

    @property
    def variant_id(self) -> str:
        return f"all-families-nearest-retracement:{self.location}"

    def fingerprint(self) -> str:
        payload = {
            "schema": "qore.trader.vt31.r2.6.variant.v1",
            "source": SOURCE_VIDEO,
            "source_sha256": SOURCE_SHA256,
            "source_market": SOURCE_MARKET,
            "owner_transfer_markets": sorted(MARKETS),
            "reference": "09:00-10:00-America/New_York",
            "window": "10:00-11:00-America/New_York",
            "raid": "strict-first-side;both-sides-abstain",
            "confirmation": "structural-close-v1",
            "entry_families": ["breaker", "fair-value-gap", "order-block"],
            "selector": "nearest-still-valid-retracement-to-confirmation-close",
            "zone_location": self.location,
            "stop": "raid-extreme-no-buffer",
            "target": "opposite-reference-boundary",
            "management": "3R-arms-breakeven",
            "pending_expiry": "11:00-America/New_York",
            "gap_policy": "censor",
            "same_bar_policy": "censor-unknown-path",
        }
        return sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


VARIANTS = tuple(Vt31R26Variant(location) for location in _LOCATIONS)


def _d(value: float) -> Decimal:
    return Decimal(str(value))


def _select_nearest_retracement(
    candidates: tuple[Vt31R22EntryEvidence, ...],
    *,
    side: DemoTradingSetupSide,
    confirmation_close: Decimal,
    extreme: Decimal,
    target: Decimal,
    location: str,
) -> tuple[Decimal | None, str]:
    priced: list[tuple[Decimal, Decimal]] = []
    for candidate in candidates:
        entry = _entry(candidate, side, location)
        geometry_valid = (
            target < entry < extreme
            if side is DemoTradingSetupSide.SHORT
            else extreme < entry < target
        )
        is_retracement = (
            entry > confirmation_close
            if side is DemoTradingSetupSide.SHORT
            else entry < confirmation_close
        )
        if geometry_valid and is_retracement:
            priced.append((abs(entry - confirmation_close), entry))
    if not priced:
        return None, "no-still-valid-retracement"
    nearest_distance = min(distance for distance, _ in priced)
    nearest_prices = {
        entry for distance, entry in priced if distance == nearest_distance
    }
    if len(nearest_prices) != 1:
        return None, "ambiguous-equal-distance-retracements"
    return next(iter(nearest_prices)), "selected"


def _evaluate(
    *,
    instrument: Instrument,
    as_of: datetime,
    bars: tuple[OhlcSnapshot, ...],
    variant: Vt31R26Variant,
) -> tuple[_Setup | None, str]:
    _validate_evidence(instrument, as_of, bars)
    reference = build_reference_range(instrument=instrument, as_of=as_of, bars=bars)
    if reference is None:
        return None, "reference-incomplete"
    session = _session_bars(as_of, bars)
    raid = _detect_raid(session, reference)
    if raid is None:
        return None, "no-raid"
    if raid.high_taken and raid.low_taken:
        return None, "both-sides-swept"
    structure = _structure(session, raid)
    if structure is None:
        return None, "no-structure-confirmation"
    confirmation_index, extreme_index, extreme, _ = structure
    candidates = _entry_evidence(
        session, raid, confirmation_index, extreme_index
    )
    if not candidates:
        return None, "no-demonstrated-entry-family"
    confirmation_close = _d(session[confirmation_index].close)
    target = (
        reference.low
        if raid.side is DemoTradingSetupSide.SHORT
        else reference.high
    )
    entry, reason = _select_nearest_retracement(
        candidates,
        side=raid.side,
        confirmation_close=confirmation_close,
        extreme=extreme,
        target=target,
        location=variant.location,
    )
    if entry is None:
        return None, reason
    return (
        _Setup(
            raid.side,
            as_of.astimezone(UTC),
            entry,
            extreme,
            target,
            cast(Vt31R25Variant, variant),
        ),
        "setup",
    )


def run_research(path: Path) -> dict[str, object]:
    series, account, evidence, checked, evidence_software_sha, provider = (
        load_market_evidence(path)
    )
    research_software_sha = os.environ.get("QORE_SOFTWARE_SHA", "")
    if re.fullmatch(r"[0-9a-f]{40}", research_software_sha) is None:
        raise Vt31R25ResearchError(
            "QORE_SOFTWARE_SHA must identify the exact R2.6 research commit"
        )
    instrument = series[0].instrument
    indexed_by_day: dict[date, list[tuple[int, OhlcSnapshot]]] = defaultdict(list)
    for index, bar in enumerate(series):
        indexed_by_day[_day(bar.opened_at)].append((index, bar))
    reports: dict[str, object] = {}
    for variant in VARIANTS:
        trades: list[dict[str, object]] = []
        abstains: Counter[str] = Counter()
        setups = 0
        for local_day in sorted(indexed_by_day):
            indexed = indexed_by_day[local_day]
            reference = tuple(
                bar
                for _, bar in indexed
                if (9, 0, 0) <= _wall(bar.opened_at) < (10, 0, 0)
            )
            session = tuple(
                (index, bar)
                for index, bar in indexed
                if (10, 0, 0) <= _wall(bar.opened_at) < (11, 0, 0)
            )
            if len(reference) != 60 or len(session) != 60:
                abstains["required-session-evidence-incomplete"] += 1
                continue
            prefix: list[OhlcSnapshot] = list(reference)
            selected: _Setup | None = None
            signal_index: int | None = None
            reason = "no-setup"
            for global_index, bar in session:
                prefix.append(bar)
                selected, reason = _evaluate(
                    instrument=instrument,
                    as_of=bar.closed_at,
                    bars=tuple(prefix),
                    variant=variant,
                )
                if selected is not None:
                    signal_index = global_index
                    break
                if reason == "both-sides-swept":
                    break
            if selected is None or signal_index is None:
                abstains[reason] += 1
                continue
            setups += 1
            trade, status = _simulate(series, signal_index, selected)
            if trade is None:
                abstains[status] += 1
            else:
                trades.append(trade)
        by_side = {
            side: _metrics([item for item in trades if item["side"] == side])
            for side in ("long", "short")
        }
        by_year = {
            year: _metrics(
                [
                    item
                    for item in trades
                    if cast(str, item["local_date"]).startswith(year)
                ]
            )
            for year in sorted(
                {cast(str, item["local_date"])[:4] for item in trades}
            )
        }
        reports[variant.variant_id] = {
            "fingerprint": variant.fingerprint(),
            "source_rule": False,
            "qore_ambiguity_containment": True,
            "setup_count": setups,
            "fill_count": len(trades),
            "metrics": _metrics(trades),
            "stress_0_05r": _metrics(trades, friction=Decimal("0.05")),
            "stress_0_10r": _metrics(trades, friction=Decimal("0.10")),
            "by_side": by_side,
            "by_year": by_year,
            "quartiles": _quartiles(trades),
            "abstain_counts": dict(sorted(abstains.items())),
            "trades": trades,
        }
    return {
        "schema": SCHEMA,
        "research_only": True,
        "source": SOURCE_VIDEO,
        "source_sha256": SOURCE_SHA256,
        "source_market": SOURCE_MARKET,
        "owner_authorized_transfer_markets": sorted(MARKETS),
        "identical_configuration_across_markets": True,
        "hypothesis_count": HYPOTHESIS_COUNT,
        "market": instrument.symbol,
        "provider_symbol_name": provider,
        "environment": "demo",
        "read_only": True,
        "account_fingerprint": account,
        "evidence_fingerprint": evidence,
        "evidence_checked_at": checked.astimezone(UTC).isoformat(
            timespec="microseconds"
        ),
        "evidence_software_sha": evidence_software_sha,
        "software_sha": research_software_sha,
        "candidate_frozen": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "variants": reports,
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: vt31-r2-6-composite-entry-research PATH")
        return 2
    try:
        report = run_research(Path(args[0]))
    except Vt31R25ResearchError as error:
        print(f"VT-31 R2.6 research failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
