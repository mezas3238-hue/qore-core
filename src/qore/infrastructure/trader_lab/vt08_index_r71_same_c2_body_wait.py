"""VT08 Index R71 — SAME_C2 causal body-transition WAIT experiment.

R70 isolated the largest R66 density conversion break in SP500, especially the
06:00 NY anchor: many setups reach a valid CISD and continuation, but the first
continuation remains on the wick side of the current H4 open and the existing
generator rejects that attempt immediately.

The frozen V7 source material already encodes both:
- source ref: "let-wick-form-trade-body:2026-08-29";
- SAME_C2 body transition: long close above H4 open / short close below H4 open.

R71 tests one bounded causal interpretation only:

    after a valid POI touch -> CISD -> Protected Swing, if a continuation
    occurs while SAME_C2 is still in wick, keep the setup in WAIT and scan
    forward causally for the first later continuation that closes in the body,
    provided the same Protected Swing has not invalidated.

No future data authorizes an earlier signal. No anchor, POI family, stop,
target family, calendar feature or risk rule changes. R71 is consumed-evidence
research only and creates no promoted candidate.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_density_round4 as r4,
)
from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_management_round5 as r5,
)
from qore.infrastructure.trader_lab import (
    vt08_index_concurrent_market_contract as contract,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r6_5y_failure_forensics as fx,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r6_five_year_validation as r6,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r8_priority_poi_rearm_reset as r8,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as r31,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r45_frozen_recent_2y_reproduction as r45,
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
    vt08_index_r70_source_complete_funnel_transport as r70,
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

SCHEMA = "qore.trader_lab.vt08_index_r71_same_c2_body_wait.v1"
IDENTITY = "VT08_INDEX_R71_SAME_C2_BODY_TRANSITION_WAIT_RESEARCH_001"
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
TARGET_R = r31.TARGET_R
SOURCE_REF = "ttrades:let-wick-form-trade-body:2026-08-29"


def _window_contract(window_id: str) -> tuple[date, date, int]:
    return r70._window_contract(window_id)


def _load_window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> tuple[
    tuple[tuple[Any, r5.ManagedTrade], ...],
    dict[str, Sequence[Vt08IndexC2R1Bar]],
    dict[str, Any],
]:
    if window_id == "5Y":
        stream, bars, _opened, provenance = (
            r31._build_source_complete_stream(roots=roots)
        )
    elif window_id == "2Y":
        stream, bars, _opened, provenance = (
            r45._build_source_complete_stream_2y(roots=roots)
        )
    elif window_id == "R66":
        stream, bars, _opened, provenance = r66._build_stream(roots=roots)
    else:
        raise ValueError(f"unsupported R71 window: {window_id}")
    if len(stream) != _window_contract(window_id)[2]:
        raise ValueError(f"R71 {window_id} canonical sample drift")
    return stream, bars, provenance


def _body_side_pass(
    *,
    side: DemoTradingSetupSide,
    close: Decimal,
    h4_open: Decimal,
) -> bool:
    return (
        close > h4_open
        if side is DemoTradingSetupSide.LONG
        else close < h4_open
    )


def _wait_body_continuation(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    side: DemoTradingSetupSide,
    start_index: int,
    protected_swing: Decimal,
    h4_open: Decimal,
) -> tuple[int | None, int]:
    """Return first causal body-side continuation and wick continuations seen."""
    wick_continuations = 0
    for index in range(start_index, len(bars)):
        bar = bars[index]
        invalidated = (
            bar.low <= protected_swing
            if side is DemoTradingSetupSide.LONG
            else bar.high >= protected_swing
        )
        if invalidated:
            return None, wick_continuations
        if index == 0:
            continue
        previous = bars[index - 1]
        continuation = (
            bar.high > previous.high and bar.close > previous.high
            if side is DemoTradingSetupSide.LONG
            else bar.low < previous.low and bar.close < previous.low
        )
        if not continuation:
            continue
        if _body_side_pass(
            side=side,
            close=bar.close,
            h4_open=h4_open,
        ):
            return index, wick_continuations
        wick_continuations += 1
    return None, wick_continuations


def _opportunities_for_h4_wait(
    *,
    symbol: str,
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    h4: dict[datetime, Vt08IndexC2R1Bar],
    h4_keys: tuple[datetime, ...],
    h4_opened_at: datetime,
    side: DemoTradingSetupSide,
) -> tuple[tuple[r4.ExpandedOpportunity, ...], dict[str, int]]:
    h4_bar = h4.get(h4_opened_at.astimezone(UTC))
    if h4_bar is None:
        return (), {}
    pois = r6._source_pois_fast(
        indexed,
        h4,
        h4_keys,
        h4_opened_at=h4_opened_at,
        side=side,
    )
    if not pois:
        return (), {}

    bars = r6._bars_between_fast(
        indexed,
        start=h4_opened_at,
        end=h4_bar.closed_at,
    )
    if not bars:
        return (), {}

    model_kind = r6._completed_h4_model_fast(
        indexed,
        h4,
        h4_keys,
        current_h4_open=h4_opened_at,
        side=side,
    )
    if model_kind is None:
        model_kind = v6.H4ModelKind.SAME_C2

    result: list[r4.ExpandedOpportunity] = []
    diagnostics: Counter[str] = Counter()

    for poi in pois:
        cursor = 0
        rearm_index = 0
        while cursor < len(bars):
            touches = r4._touch_indices(
                bars,
                poi,
                start_index=cursor,
            )
            if not touches:
                break
            touch_index = touches[0]
            cisd = v6._first_cisd(
                bars,
                side=side,
                start_index=touch_index,
            )
            if cisd is None:
                cursor = touch_index + 1
                continue
            cisd_index, cisd_level, protected_swing = cisd

            wick_count = 0
            if model_kind is v6.H4ModelKind.SAME_C2:
                continuation_index, wick_count = _wait_body_continuation(
                    bars,
                    side=side,
                    start_index=cisd_index + 1,
                    protected_swing=protected_swing,
                    h4_open=h4_bar.open,
                )
                diagnostics["wick_continuations_waited"] += wick_count
                diagnostics["wait_sequences"] += int(wick_count > 0)
            else:
                continuation_index = v6._first_continuation(
                    bars,
                    side=side,
                    start_index=cisd_index + 1,
                    protected_swing=protected_swing,
                )

            if continuation_index is None:
                diagnostics["wait_or_continuation_failed"] += 1
                cursor = touch_index + 1
                continue

            continuation = bars[continuation_index]
            entry = continuation.close
            risk = (
                entry - protected_swing
                if side is DemoTradingSetupSide.LONG
                else protected_swing - entry
            )
            if risk <= 0:
                cursor = touch_index + 1
                continue
            target = (
                entry + Decimal("2") * risk
                if side is DemoTradingSetupSide.LONG
                else entry - Decimal("2") * risk
            )
            if target <= 0:
                cursor = touch_index + 1
                continue

            signal = v6.CandidateSignal(
                symbol=symbol,
                side=side,
                model_kind=model_kind,
                h4_opened_at=h4_opened_at,
                signal_at=continuation.closed_at,
                entry=entry,
                stop=protected_swing,
                target=target,
                poi=poi,
                cisd_level=cisd_level,
                cisd_confirmed_at=bars[cisd_index].closed_at,
                protected_swing_extreme=protected_swing,
            )
            result.append(
                r4.ExpandedOpportunity(
                    signal=signal,
                    source_poi_kind=poi.kind.value,
                    poi_touch_at=bars[touch_index].opened_at.astimezone(UTC),
                    rearm_index=rearm_index,
                )
            )
            diagnostics["signals"] += 1
            diagnostics["signals_after_wait"] += int(
                model_kind is v6.H4ModelKind.SAME_C2
                and wick_count > 0
            )
            rearm_index += 1
            cursor = continuation_index + 1

    poi_priority = {
        v6.PoiKind.FVG.value: 0,
        v6.PoiKind.RELEVANT_SWING.value: 1,
        v6.PoiKind.CISD.value: 2,
    }
    deduped: dict[tuple[object, ...], r4.ExpandedOpportunity] = {}
    for item in sorted(
        result,
        key=lambda value: (
            value.signal.signal_at,
            poi_priority.get(value.source_poi_kind, 99),
            value.rearm_index,
        ),
    ):
        deduped.setdefault(item.identity(), item)
    diagnostics["deduplicated_signals"] = len(deduped)
    return tuple(deduped.values()), dict(diagnostics)


def _build_wait_surface(
    *,
    symbol: str,
    bars: Sequence[Vt08IndexC2R1Bar],
    start_date: date,
    end_date_exclusive: date,
) -> tuple[tuple[r4.ExpandedOpportunity, ...], dict[str, int]]:
    indexed = {bar.opened_at.astimezone(UTC): bar for bar in bars}
    h4 = v6._build_h4(indexed)
    h4_keys = tuple(sorted(h4))
    side_cache: dict[date, DemoTradingSetupSide | None] = {}
    opportunities: list[r4.ExpandedOpportunity] = []
    diagnostics: Counter[str] = Counter()

    for opened in h4_keys:
        local = opened.astimezone(r70._NY)
        local_date = local.date()
        if not (start_date <= local_date < end_date_exclusive):
            continue
        if local.hour not in r4.V7_ANCHORS:
            continue
        if local_date not in side_cache:
            side_cache[local_date] = v7._daily_bias(indexed, before=opened)
        side = side_cache[local_date]
        if side is None:
            continue
        rows, diag = _opportunities_for_h4_wait(
            symbol=symbol,
            indexed=indexed,
            h4=h4,
            h4_keys=h4_keys,
            h4_opened_at=opened,
            side=side,
        )
        opportunities.extend(rows)
        diagnostics.update(diag)

    opportunities.sort(
        key=lambda item: (
            item.signal.signal_at,
            item.signal.symbol,
            item.signal.entry,
            item.signal.stop,
            item.rearm_index,
        )
    )
    identities = [item.identity() for item in opportunities]
    if len(set(identities)) != len(identities):
        raise ValueError(f"R71 duplicate WAIT identity for {symbol}")
    diagnostics["surface_signals"] = len(opportunities)
    return tuple(opportunities), dict(diagnostics)


def _manage(
    opportunities: Sequence[r4.ExpandedOpportunity],
    *,
    bars: Sequence[Vt08IndexC2R1Bar],
) -> tuple[tuple[r4.ExpandedOpportunity, r5.ManagedTrade], ...]:
    opened = tuple(bar.opened_at.astimezone(UTC) for bar in bars)
    policy = r8._target_policy(TARGET_R)
    return tuple(
        (
            opportunity,
            r5._manage_trade(
                opportunity.signal,
                bars=bars,
                opened=opened,
                policy=policy,
            ),
        )
        for opportunity in opportunities
    )


def _metrics(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    ordered = sorted(
        stream,
        key=lambda item: (
            item[1].exited_at.astimezone(UTC),
            item[0].signal.symbol,
            item[0].signal.signal_at,
        ),
    )
    return fx._metrics(
        tuple(item[1].r_multiple - stress for item in ordered)
    )


def _market_counts(
    stream: Sequence[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]],
) -> dict[str, int]:
    counts = Counter(str(item[0].signal.symbol) for item in stream)
    return dict(sorted(counts.items()))


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, Any]:
    canonical, bars_by_symbol, provenance = _load_window(
        roots=roots,
        window_id=window_id,
    )
    start_date, end_date, expected = _window_contract(window_id)
    canonical_by_id = {item[0].identity(): item for item in canonical}
    if len(canonical_by_id) != expected:
        raise ValueError(f"R71 {window_id} canonical identity drift")

    wait_stream: list[tuple[r4.ExpandedOpportunity, r5.ManagedTrade]] = []
    diagnostics: dict[str, Any] = {}
    for symbol in contract.MARKETS:
        wait_surface, diag = _build_wait_surface(
            symbol=symbol,
            bars=bars_by_symbol[symbol],
            start_date=start_date,
            end_date_exclusive=end_date,
        )
        diagnostics[symbol] = diag
        wait_stream.extend(
            _manage(wait_surface, bars=bars_by_symbol[symbol])
        )

    wait_stream.sort(
        key=lambda item: (
            item[0].signal.signal_at,
            item[0].signal.symbol,
            item[0].signal.entry,
            item[0].signal.stop,
        )
    )
    wait_by_id = {item[0].identity(): item for item in wait_stream}
    if len(wait_by_id) != len(wait_stream):
        raise ValueError(f"R71 {window_id} WAIT identity collision")

    canonical_ids = set(canonical_by_id)
    wait_ids = set(wait_by_id)
    added_ids = wait_ids - canonical_ids
    lost_ids = canonical_ids - wait_ids
    common_ids = canonical_ids & wait_ids

    recovered = [wait_by_id[key] for key in added_ids]
    lost = [canonical_by_id[key] for key in lost_ids]

    union_by_id = dict(canonical_by_id)
    for key in added_ids:
        union_by_id[key] = wait_by_id[key]
    union = sorted(
        union_by_id.values(),
        key=lambda item: (
            item[0].signal.signal_at,
            item[0].signal.symbol,
            item[0].signal.entry,
            item[0].signal.stop,
        ),
    )

    return {
        "canonical_sample": len(canonical),
        "wait_replacement_sample": len(wait_stream),
        "union_sample": len(union),
        "common_identity_count": len(common_ids),
        "added_wait_identity_count": len(added_ids),
        "lost_canonical_identity_count": len(lost_ids),
        "canonical_market_counts": _market_counts(canonical),
        "wait_market_counts": _market_counts(wait_stream),
        "union_market_counts": _market_counts(union),
        "recovered_market_counts": _market_counts(recovered),
        "lost_market_counts": _market_counts(lost),
        "canonical": {
            "primary": _metrics(canonical, stress=PRIMARY_STRESS),
            "secondary": _metrics(canonical, stress=SECONDARY_STRESS),
        },
        "wait_replacement": {
            "primary": _metrics(wait_stream, stress=PRIMARY_STRESS),
            "secondary": _metrics(wait_stream, stress=SECONDARY_STRESS),
        },
        "union": {
            "primary": _metrics(union, stress=PRIMARY_STRESS),
            "secondary": _metrics(union, stress=SECONDARY_STRESS),
        },
        "recovered_only": {
            "primary": _metrics(recovered, stress=PRIMARY_STRESS),
            "secondary": _metrics(recovered, stress=SECONDARY_STRESS),
        },
        "lost_only": {
            "primary": _metrics(lost, stress=PRIMARY_STRESS),
            "secondary": _metrics(lost, stress=SECONDARY_STRESS),
        },
        "wait_diagnostics": diagnostics,
        "provenance": provenance,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R71 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R71 source failure decision drift")
    if SOURCE_REF not in v6.SOURCE_REFS:
        raise ValueError("R71 source-faithful WAIT reference missing")
    if v7._RULE_MATERIAL["same_c2_body_transition"] != (
        "long-close-above-h4-open-short-close-below-h4-open"
    ):
        raise ValueError("R71 V7 SAME_C2 body transition contract drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five = _window(roots=roots, window_id="5Y")
    two = _window(roots=roots, window_id="2Y")
    failed = _window(roots=roots, window_id="R66")

    five_low, five_high = contract.FIVE_YEAR_TRADE_RANGE
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_failure": {
            "decision": r67.SOURCE_R66_DECISION,
            "r66_density_gate": r66.MIN_TRADES,
        },
        "source_contract": {
            "source_ref": SOURCE_REF,
            "same_c2_body_transition": v7._RULE_MATERIAL[
                "same_c2_body_transition"
            ],
            "anchors_new_york": list(r4.V7_ANCHORS),
            "poi_families": [
                v6.PoiKind.FVG.value,
                v6.PoiKind.RELEVANT_SWING.value,
                v6.PoiKind.CISD.value,
            ],
            "protected_swing_preserved": True,
            "new_touch_required_after_wick_continuation": False,
            "same_cisd_remains_valid_only_until_ps_invalidation": True,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "density_contract": {
            "five_year_minimum": five_low,
            "five_year_maximum": five_high,
            "recent_two_year_minimum": contract.TWO_YEAR_MIN_TRADES,
            "r66_preregistered_minimum": r66.MIN_TRADES,
            "wait_replacement_five_year_in_range": (
                five_low <= five["wait_replacement_sample"] <= five_high
            ),
            "wait_replacement_recent_two_year_pass": (
                two["wait_replacement_sample"]
                >= contract.TWO_YEAR_MIN_TRADES
            ),
            "wait_replacement_r66_pass": (
                failed["wait_replacement_sample"] >= r66.MIN_TRADES
            ),
            "union_five_year_in_range": (
                five_low <= five["union_sample"] <= five_high
            ),
            "union_recent_two_year_pass": (
                two["union_sample"] >= contract.TWO_YEAR_MIN_TRADES
            ),
            "union_r66_pass": (
                failed["union_sample"] >= r66.MIN_TRADES
            ),
        },
        "decision": "R71_WAIT_RESEARCH_COMPLETE_NO_CANDIDATE",
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "bounded_single_hypothesis": True,
            "future_information_used": False,
            "calendar_or_year_runtime_feature": False,
            "anchors_changed": False,
            "poi_families_changed": False,
            "protected_swing_changed": False,
            "target_changed": False,
            "risk_changed": False,
            "signal_suppression_performed": False,
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
                        "canonical_sample",
                        "wait_replacement_sample",
                        "union_sample",
                        "added_wait_identity_count",
                        "lost_canonical_identity_count",
                        "recovered_market_counts",
                    )
                },
                "recent_two_year": {
                    key: report["recent_two_year"][key]
                    for key in (
                        "canonical_sample",
                        "wait_replacement_sample",
                        "union_sample",
                        "added_wait_identity_count",
                        "lost_canonical_identity_count",
                        "recovered_market_counts",
                    )
                },
                "r66": {
                    key: report["r66_failed_holdout"][key]
                    for key in (
                        "canonical_sample",
                        "wait_replacement_sample",
                        "union_sample",
                        "added_wait_identity_count",
                        "lost_canonical_identity_count",
                        "recovered_market_counts",
                    )
                },
                "density_contract": report["density_contract"],
                "recovered_economics": {
                    "five_year": report["five_year"]["recovered_only"],
                    "recent_two_year": report["recent_two_year"][
                        "recovered_only"
                    ],
                    "r66": report["r66_failed_holdout"]["recovered_only"],
                },
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
