"""VT08 Index R85 — source-exact Protected-Swing continuation/rearm census.

R84 established an upper-bound event layer of source-qualified Protected Swings
without attaching trades. R85 advances exactly one causal step: for every R84
source-exact Protected-Swing event, require the frozen V6/V7 continuation rule
and SAME_C2 body transition, then count executable continuation closures.

No PnL, target, risk allocator or trade suppression is evaluated. The purpose is
to determine whether the strict source-qualified event layer can mechanically
supply the Owner density contract before any economics are considered.

A rearm is counted only when a later distinct Protected-Swing event in the same
market/H4 confirms after an earlier executable continuation and itself produces
a later valid continuation. Multiple causal events resolving to the identical
continuation timestamp/entry/stop are deduplicated.

Owner-disabled 14:00 execution remains disabled. Executable anchors stay frozen
at 22/02/06/10 NY.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
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
    vt08_index_r67_r66_failure_forensics as r67,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r74_ambiguous_bias_resolvers as r74,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r84_source_exact_ps_event_census as r84,
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

SCHEMA = "qore.trader_lab.vt08_index_r85_source_exact_ps_continuation_rearm.v1"
IDENTITY = "VT08_INDEX_R85_SOURCE_EXACT_PS_CONTINUATION_REARM_CENSUS_001"

SOURCE_R84_RUN_ID = 35520178299
SOURCE_R84_ARTIFACT_ID = 10607704304
SOURCE_R84_ARTIFACT_DIGEST = (
    "sha256:PLACEHOLDER"
)

FIVE_YEAR_DENSITY_MIN = contract.FIVE_YEAR_TRADE_RANGE[0]
FIVE_YEAR_DENSITY_MAX = contract.FIVE_YEAR_TRADE_RANGE[1]
TWO_YEAR_DENSITY_MIN = contract.TWO_YEAR_MIN_TRADES
R66_DENSITY_MIN = 1000


@dataclass(frozen=True, slots=True)
class SourcePsCandidate:
    event: r84.ProtectedSwingEvent
    source_poi: v6.SourcePoi
    confirm_index: int

    def identity(self) -> tuple[object, ...]:
        return self.event.identity()


@dataclass(frozen=True, slots=True)
class ExecutableContinuation:
    event: r84.ProtectedSwingEvent
    continuation_index: int
    continuation_at: datetime
    entry: Decimal
    model_kind: v6.H4ModelKind

    def identity(self) -> tuple[object, ...]:
        return (
            self.event.symbol,
            self.event.h4_opened_at.astimezone(UTC),
            self.event.side.value,
            self.continuation_at.astimezone(UTC),
            self.entry,
            self.event.protected_swing,
        )


def _source_ps_candidates(
    *,
    symbol: str,
    opened: datetime,
    side: DemoTradingSetupSide,
    pois: Sequence[v6.SourcePoi],
    inside: Sequence[Vt08IndexC2R1Bar],
) -> tuple[SourcePsCandidate, ...]:
    swings = r84._short_term_swings(inside, side=side)
    series_rows = r84._confirmed_opposing_series(inside, side=side)
    candidates: dict[tuple[object, ...], SourcePsCandidate] = {}

    for poi in pois:
        touches = r4._touch_indices(inside, poi, start_index=0)
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
                    inside,
                    poi=poi,
                    series=series,
                    touch_index=touch_index,
                )
                family = r84._event_family(
                    liquidity=liquidity,
                    fvg=fvg,
                )
                if family is None:
                    continue
                event = r84.ProtectedSwingEvent(
                    symbol=symbol,
                    h4_opened_at=opened,
                    side=side,
                    confirmed_at=inside[
                        series.confirm_index
                    ].closed_at.astimezone(UTC),
                    protected_swing=series.extreme,
                    series_open=series.series_open,
                    family=family,
                    source_poi_kind=poi.kind.value,
                    poi_touch_at=inside[
                        touch_index
                    ].opened_at.astimezone(UTC),
                )
                candidates.setdefault(
                    event.identity(),
                    SourcePsCandidate(
                        event=event,
                        source_poi=poi,
                        confirm_index=series.confirm_index,
                    ),
                )
    return tuple(
        sorted(
            candidates.values(),
            key=lambda row: (
                row.event.confirmed_at,
                row.event.protected_swing,
                row.event.family,
            ),
        )
    )


def _executable_from_event(
    candidate: SourcePsCandidate,
    *,
    inside: Sequence[Vt08IndexC2R1Bar],
    h4_bar: Vt08IndexC2R1Bar,
    model_kind: v6.H4ModelKind,
) -> tuple[ExecutableContinuation | None, str]:
    event = candidate.event
    continuation_index = v6._first_continuation(
        inside,
        side=event.side,
        start_index=candidate.confirm_index + 1,
        protected_swing=event.protected_swing,
    )
    if continuation_index is None:
        return None, "NO_VALID_CONTINUATION"

    continuation = inside[continuation_index]
    entry = continuation.close
    if model_kind is v6.H4ModelKind.SAME_C2:
        in_body = (
            entry > h4_bar.open
            if event.side is DemoTradingSetupSide.LONG
            else entry < h4_bar.open
        )
        if not in_body:
            return None, "SAME_C2_WICK_NOT_BODY"

    risk = (
        entry - event.protected_swing
        if event.side is DemoTradingSetupSide.LONG
        else event.protected_swing - entry
    )
    if risk <= 0:
        return None, "NON_POSITIVE_RISK"

    return (
        ExecutableContinuation(
            event=event,
            continuation_index=continuation_index,
            continuation_at=continuation.closed_at.astimezone(UTC),
            entry=entry,
            model_kind=model_kind,
        ),
        "EXECUTABLE",
    )


def _market(
    *,
    symbol: str,
    bars: Sequence[Vt08IndexC2R1Bar],
    start_date: Any,
    end_date: Any,
) -> dict[str, Any]:
    indexed = {
        bar.opened_at.astimezone(UTC): bar
        for bar in bars
    }
    h4 = v6._build_h4(indexed)
    h4_keys = tuple(sorted(h4))
    side_cache: dict[Any, DemoTradingSetupSide | None] = {}

    ps_event_count = 0
    reason_counts: Counter[str] = Counter()
    by_anchor: dict[str, Counter[str]] = {}
    by_family: dict[str, Counter[str]] = {}
    raw_executable: list[ExecutableContinuation] = []
    h4_event_counts: Counter[str] = Counter()
    h4_executable_counts: Counter[str] = Counter()

    for opened in h4_keys:
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

        pois = r6._source_pois_fast(
            indexed,
            h4,
            h4_keys,
            h4_opened_at=opened,
            side=side,
        )
        if not pois:
            continue
        inside = r6._bars_between_fast(
            indexed,
            start=opened,
            end=h4[opened].closed_at,
        )
        if not inside:
            continue

        model_kind = r6._completed_h4_model_fast(
            indexed,
            h4,
            h4_keys,
            current_h4_open=opened,
            side=side,
        )
        if model_kind is None:
            model_kind = v6.H4ModelKind.SAME_C2

        candidates = _source_ps_candidates(
            symbol=symbol,
            opened=opened,
            side=side,
            pois=pois,
            inside=inside,
        )
        ps_event_count += len(candidates)
        h4_key = opened.astimezone(UTC).isoformat()
        h4_event_counts[h4_key] = len(candidates)
        anchor = str(local.hour)
        by_anchor.setdefault(anchor, Counter())

        for candidate in candidates:
            by_family.setdefault(
                candidate.event.family,
                Counter(),
            )
            row, reason = _executable_from_event(
                candidate,
                inside=inside,
                h4_bar=h4[opened],
                model_kind=model_kind,
            )
            reason_counts[reason] += 1
            by_anchor[anchor][reason] += 1
            by_family[candidate.event.family][reason] += 1
            if row is not None:
                raw_executable.append(row)
                h4_executable_counts[h4_key] += 1

    unique: dict[tuple[object, ...], ExecutableContinuation] = {}
    for row in sorted(
        raw_executable,
        key=lambda item: (
            item.continuation_at,
            item.event.symbol,
            item.event.h4_opened_at,
            item.event.protected_swing,
        ),
    ):
        unique.setdefault(row.identity(), row)
    executable = tuple(unique.values())

    rearm_count = 0
    first_count = 0
    by_h4_rows: dict[tuple[str, datetime], list[ExecutableContinuation]] = {}
    for row in executable:
        key = (
            row.event.symbol,
            row.event.h4_opened_at.astimezone(UTC),
        )
        by_h4_rows.setdefault(key, []).append(row)
    for rows in by_h4_rows.values():
        ordered = sorted(
            rows,
            key=lambda item: (
                item.continuation_at,
                item.event.confirmed_at,
            ),
        )
        last_continuation: datetime | None = None
        for row in ordered:
            if last_continuation is None:
                first_count += 1
                last_continuation = row.continuation_at
                continue
            if row.event.confirmed_at > last_continuation:
                rearm_count += 1
                last_continuation = row.continuation_at

    return {
        "symbol": symbol,
        "source_ps_event_count": ps_event_count,
        "raw_executable_event_count": len(raw_executable),
        "deduplicated_executable_continuations": len(executable),
        "first_executable_continuations": first_count,
        "source_valid_rearm_continuations": rearm_count,
        "reason_counts": dict(sorted(reason_counts.items())),
        "by_anchor": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_anchor.items())
        },
        "by_family": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_family.items())
        },
        "h4_with_multiple_source_ps_events": sum(
            value > 1 for value in h4_event_counts.values()
        ),
        "h4_with_multiple_executable_continuations": sum(
            value > 1 for value in h4_executable_counts.values()
        ),
    }


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    _stream, bars_by_symbol, provenance = r74._load_window(
        roots=roots,
        window_id=window_id,
    )
    start_date, end_date, canonical_sample = r74._window_contract(window_id)
    markets = {
        symbol: _market(
            symbol=symbol,
            bars=bars_by_symbol[symbol],
            start_date=start_date,
            end_date=end_date,
        )
        for symbol in contract.MARKETS
    }

    total_events = sum(
        int(row["source_ps_event_count"])
        for row in markets.values()
    )
    total_executable = sum(
        int(row["deduplicated_executable_continuations"])
        for row in markets.values()
    )
    first = sum(
        int(row["first_executable_continuations"])
        for row in markets.values()
    )
    rearm = sum(
        int(row["source_valid_rearm_continuations"])
        for row in markets.values()
    )
    if total_events <= 0:
        raise ValueError(f"R85 {window_id} no source PS events")

    if window_id == "5Y":
        density_pass = (
            FIVE_YEAR_DENSITY_MIN
            <= total_executable
            <= FIVE_YEAR_DENSITY_MAX
        )
        density_requirement = (
            f"{FIVE_YEAR_DENSITY_MIN}-{FIVE_YEAR_DENSITY_MAX}"
        )
    elif window_id == "2Y":
        density_pass = total_executable >= TWO_YEAR_DENSITY_MIN
        density_requirement = f">={TWO_YEAR_DENSITY_MIN}"
    else:
        density_pass = total_executable >= R66_DENSITY_MIN
        density_requirement = f">={R66_DENSITY_MIN}"

    return {
        "window_id": window_id,
        "canonical_signal_reference": canonical_sample,
        "source_ps_event_count": total_events,
        "source_ps_events_per_canonical_signal": str(
            Decimal(total_events) / Decimal(canonical_sample)
        ),
        "deduplicated_executable_continuations": total_executable,
        "executable_fraction_of_source_ps_events": str(
            Decimal(total_executable) / Decimal(total_events)
        ),
        "first_executable_continuations": first,
        "source_valid_rearm_continuations": rearm,
        "density_requirement": density_requirement,
        "density_pass": density_pass,
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
        raise ValueError("R85 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R85 source failure decision drift")
    if r84.IDENTITY != (
        "VT08_INDEX_R84_SOURCE_EXACT_PROTECTED_SWING_EVENT_CENSUS_001"
    ):
        raise ValueError("R85 R84 identity drift")
    if tuple(r4.V7_ANCHORS) != tuple(v7.EXECUTABLE_H4_ANCHORS_NY):
        raise ValueError("R85 executable anchor contract drift")
    if 14 in r4.V7_ANCHORS:
        raise ValueError("R85 Owner-disabled 14:00 anchor unexpectedly enabled")

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
        "source_r84": {
            "identity": r84.IDENTITY,
            "run_id": SOURCE_R84_RUN_ID,
            "artifact_id": SOURCE_R84_ARTIFACT_ID,
            "artifact_digest": SOURCE_R84_ARTIFACT_DIGEST,
        },
        "execution_contract": {
            "protected_swing_layer": "R84_SOURCE_EXACT",
            "continuation": "EXACT_V6_FIRST_CONTINUATION",
            "same_c2_body_transition": "EXACT_V7",
            "executable_anchors_new_york": list(r4.V7_ANCHORS),
            "owner_disabled_14_preserved": True,
            "entry_price_used_for_pnl": False,
            "pnl_evaluated": False,
            "target_attached": False,
            "risk_allocator_applied": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "upper_bound_conclusion": {
            "five_year_density_possible_under_r84_ps_layer": bool(
                five["density_pass"]
            ),
            "recent_two_year_density_possible_under_r84_ps_layer": bool(
                two["density_pass"]
            ),
            "r66_density_possible_under_r84_ps_layer": bool(
                failed["density_pass"]
            ),
        },
        "decision": "R85_SOURCE_EXACT_PS_CONTINUATION_REARM_CENSUS_COMPLETE_NO_TRADES",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "future_information_used": False,
            "pnl_evaluated": False,
            "signals_created_for_trading": False,
            "signals_suppressed": False,
            "target_changed": False,
            "risk_changed": False,
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
                        "source_ps_event_count",
                        "deduplicated_executable_continuations",
                        "first_executable_continuations",
                        "source_valid_rearm_continuations",
                        "density_requirement",
                        "density_pass",
                    )
                },
                "recent_two_year": {
                    key: report["recent_two_year"][key]
                    for key in (
                        "source_ps_event_count",
                        "deduplicated_executable_continuations",
                        "first_executable_continuations",
                        "source_valid_rearm_continuations",
                        "density_requirement",
                        "density_pass",
                    )
                },
                "r66": {
                    key: report["r66_failed_holdout"][key]
                    for key in (
                        "source_ps_event_count",
                        "deduplicated_executable_continuations",
                        "first_executable_continuations",
                        "source_valid_rearm_continuations",
                        "density_requirement",
                        "density_pass",
                    )
                },
                "upper_bound_conclusion": report["upper_bound_conclusion"],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
