"""VT08 Index R97 — persistent Protected-Swing lifecycle census.

R96 proved that carrying an Ideal-Formation Protected Swing into only the
immediate next H4 recovers real source-valid continuations, but still leaves the
primary D1->H4->M15 model below density.

Primary TTrades material establishes a stateful lifecycle:
- a protected swing is the structural invalidation until price trades through it;
- retracements into important levels can create new protected swings;
- those newer protected swings become continuation "stepping stones";
- the point-of-interest process should adjust to the newest protected swing.

R97 tests the missing lifecycle without an arbitrary H4 TTL.

State machine
-------------
1. A lifecycle may START only after a complete H4 C2/C3 Ideal Formation:
   causal V7 daily bias + C2/C3 closure + source-exact R85 M15 Protected Swing
   that survives the H4 close.
2. The active Protected Swing persists across H4 boundaries while:
   - daily bias remains on the same side;
   - price does not invalidate the swing.
3. Once a lifecycle exists, a newer source-exact M15 Protected Swing may replace
   the active swing as a stepping stone. One active swing can create at most one
   continuation execution; a newer swing rearms the lifecycle.
4. Execution is allowed only inside Owner-authorized H4 anchors
   (22/02/06/10 NY) using exact V6 M15 continuation.
5. No stale numeric TTL exists. Lifecycle ends only on invalidation, daily-bias
   change/ambiguity, or ambiguous same-timestamp replacement.
6. If multiple distinct newest Protected Swings confirm at exactly the same
   timestamp, R97 fails closed for that lifecycle rather than selecting one.

R97 is a no-PnL consumed-evidence census. Same-H4 R85 executions are unioned
with lifecycle executions by exact mechanical identity only.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, replace
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
    vt08_index_r85_source_exact_ps_continuation_rearm as r85,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r94_ttrades_timeframe_hierarchy_freeze as r94,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r96_ideal_formation_cross_h4_carry as r96,
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

SCHEMA = "qore.trader_lab.vt08_index_r97_persistent_ps_lifecycle.v1"
IDENTITY = "VT08_INDEX_R97_PERSISTENT_PROTECTED_SWING_LIFECYCLE_001"

SOURCE_R96_RUN_ID = 35532300657
SOURCE_R96_ARTIFACT_ID = 10612280518
SOURCE_R96_ARTIFACT_DIGEST = (
    "sha256:7d3a61fe6d32b94585e370b70036ac5d3eb99330bc3524250965e53bc83ea861"
)


@dataclass(frozen=True, slots=True)
class ActiveProtectedSwing:
    side: DemoTradingSetupSide
    protected_swing: Decimal
    confirmed_at: datetime
    source_h4_opened_at: datetime
    source_kind: str
    consumed: bool = False


@dataclass(frozen=True, slots=True)
class LifecycleExecution:
    symbol: str
    h4_opened_at: datetime
    side: DemoTradingSetupSide
    protected_swing: Decimal
    ps_confirmed_at: datetime
    continuation_index: int
    continuation_at: datetime
    entry: Decimal
    source_kind: str

    def identity(self) -> tuple[object, ...]:
        return (
            self.symbol,
            self.continuation_at.astimezone(UTC),
            self.side.value,
            self.entry,
            self.protected_swing,
        )


def _candidate_groups(
    candidates: Sequence[r85.SourcePsCandidate],
) -> dict[int, tuple[r85.SourcePsCandidate, ...]]:
    grouped: dict[int, list[r85.SourcePsCandidate]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.confirm_index].append(candidate)
    return {
        index: tuple(rows)
        for index, rows in grouped.items()
    }


def _select_unique_newest(
    candidates: Sequence[r85.SourcePsCandidate],
) -> tuple[r85.SourcePsCandidate | None, bool]:
    """Select latest confirmation; fail closed if latest extremes disagree."""
    if not candidates:
        return None, False
    newest_index = max(row.confirm_index for row in candidates)
    newest = tuple(
        row for row in candidates if row.confirm_index == newest_index
    )
    by_swing: dict[Decimal, r85.SourcePsCandidate] = {}
    for row in newest:
        by_swing.setdefault(row.event.protected_swing, row)
    if len(by_swing) != 1:
        return None, True
    return next(iter(by_swing.values())), False


def _invalidated(
    bar: Vt08IndexC2R1Bar,
    *,
    state: ActiveProtectedSwing,
) -> bool:
    return (
        bar.low <= state.protected_swing
        if state.side is DemoTradingSetupSide.LONG
        else bar.high >= state.protected_swing
    )


def _is_continuation(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    index: int,
    side: DemoTradingSetupSide,
) -> bool:
    if index <= 0:
        return False
    bar = bars[index]
    previous = bars[index - 1]
    return (
        bar.high > previous.high and bar.close > previous.high
        if side is DemoTradingSetupSide.LONG
        else bar.low < previous.low and bar.close < previous.low
    )


def _state_from_candidate(
    candidate: r85.SourcePsCandidate,
    *,
    source_kind: str,
    consumed: bool = False,
) -> ActiveProtectedSwing:
    return ActiveProtectedSwing(
        side=candidate.event.side,
        protected_swing=candidate.event.protected_swing,
        confirmed_at=candidate.event.confirmed_at.astimezone(UTC),
        source_h4_opened_at=candidate.event.h4_opened_at.astimezone(UTC),
        source_kind=source_kind,
        consumed=consumed,
    )


def _same_h4_identity(row: r85.ExecutableContinuation) -> tuple[object, ...]:
    return (
        row.event.symbol,
        row.continuation_at.astimezone(UTC),
        row.event.side.value,
        row.entry,
        row.event.protected_swing,
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

    state: ActiveProtectedSwing | None = None
    same_h4: dict[tuple[object, ...], r85.ExecutableContinuation] = {}
    lifecycle: dict[tuple[object, ...], LifecycleExecution] = {}
    diagnostics: Counter[str] = Counter()
    by_source_kind: Counter[str] = Counter()
    by_anchor: Counter[str] = Counter()
    lifetime_h4_lengths: Counter[int] = Counter()
    state_age_h4 = 0

    for opened in h4_keys:
        local = opened.astimezone(v7._NY)
        local_date = local.date()
        if not (start_date <= local_date < end_date):
            continue

        if local_date not in side_cache:
            side_cache[local_date] = v7._daily_bias(
                indexed,
                before=opened,
            )
        side = side_cache[local_date]

        if state is not None:
            if side is None or side is not state.side:
                diagnostics["STATE_ENDED_BIAS_CHANGE_OR_AMBIGUITY"] += 1
                lifetime_h4_lengths[state_age_h4] += 1
                state = None
                state_age_h4 = 0
            else:
                state_age_h4 += 1

        inside = r6._bars_between_fast(
            indexed,
            start=opened,
            end=h4[opened].closed_at,
        )
        if not inside or side is None:
            continue

        pois = r6._source_pois_fast(
            indexed,
            h4,
            h4_keys,
            h4_opened_at=opened,
            side=side,
        )
        candidates = (
            r85._source_ps_candidates(
                symbol=symbol,
                opened=opened,
                side=side,
                pois=pois,
                inside=inside,
            )
            if pois
            else ()
        )
        groups = _candidate_groups(candidates)

        if local.hour in r4.V7_ANCHORS and pois:
            model_kind = r6._completed_h4_model_fast(
                indexed,
                h4,
                h4_keys,
                current_h4_open=opened,
                side=side,
            )
            if model_kind is None:
                model_kind = v6.H4ModelKind.SAME_C2
            for candidate in candidates:
                intra_row, reason = r85._executable_from_event(
                    candidate,
                    inside=inside,
                    h4_bar=h4[opened],
                    model_kind=model_kind,
                )
                if intra_row is not None and reason == "EXECUTABLE":
                    same_h4.setdefault(
                        _same_h4_identity(intra_row),
                        intra_row,
                    )

        lifecycle_started_before_h4 = state is not None

        for index, bar in enumerate(inside):
            if state is not None and _invalidated(bar, state=state):
                diagnostics["STATE_ENDED_INVALIDATION"] += 1
                lifetime_h4_lengths[state_age_h4] += 1
                state = None
                state_age_h4 = 0

            replacements = groups.get(index, ())
            if state is not None and replacements:
                replacement, ambiguous = _select_unique_newest(replacements)
                if ambiguous:
                    diagnostics["STATE_ENDED_AMBIGUOUS_REPLACEMENT"] += 1
                    lifetime_h4_lengths[state_age_h4] += 1
                    state = None
                    state_age_h4 = 0
                    continue
                if replacement is not None:
                    state = _state_from_candidate(
                        replacement,
                        source_kind="STEPPING_STONE",
                    )
                    state_age_h4 = 0
                    diagnostics["STATE_REPLACED_BY_NEW_PS"] += 1
                    continue

            if (
                state is not None
                and not state.consumed
                and lifecycle_started_before_h4
                and local.hour in r4.V7_ANCHORS
                and state.confirmed_at
                <= bar.opened_at.astimezone(UTC)
                and _is_continuation(
                    inside,
                    index=index,
                    side=state.side,
                )
            ):
                entry = bar.close
                risk = (
                    entry - state.protected_swing
                    if state.side is DemoTradingSetupSide.LONG
                    else state.protected_swing - entry
                )
                if risk > 0:
                    lifecycle_row = LifecycleExecution(
                        symbol=symbol,
                        h4_opened_at=opened,
                        side=state.side,
                        protected_swing=state.protected_swing,
                        ps_confirmed_at=state.confirmed_at,
                        continuation_index=index,
                        continuation_at=bar.closed_at.astimezone(UTC),
                        entry=entry,
                        source_kind=state.source_kind,
                    )
                    lifecycle.setdefault(
                        lifecycle_row.identity(),
                        lifecycle_row,
                    )
                    state = replace(state, consumed=True)
                    diagnostics["LIFECYCLE_EXECUTED"] += 1
                    by_source_kind[lifecycle_row.source_kind] += 1
                    by_anchor[str(local.hour)] += 1

        closure = r96._closure_kind(
            h4,
            h4_keys,
            opened=opened,
            side=side,
        )
        if closure is None or not candidates:
            continue
        surviving = tuple(
            candidate
            for candidate in candidates
            if r96._survives_after_confirmation(
                inside,
                confirm_index=candidate.confirm_index,
                side=side,
                protected_swing=candidate.event.protected_swing,
            )
        )
        selected, ambiguous = _select_unique_newest(surviving)
        if ambiguous:
            diagnostics["IDEAL_FORMATION_AMBIGUOUS_AT_CLOSE"] += 1
            if state is not None:
                lifetime_h4_lengths[state_age_h4] += 1
            state = None
            state_age_h4 = 0
            continue
        if selected is not None:
            if state is not None:
                lifetime_h4_lengths[state_age_h4] += 1
            state = _state_from_candidate(
                selected,
                source_kind=f"IDEAL_{closure}",
            )
            state_age_h4 = 0
            diagnostics[f"STATE_STARTED_IDEAL_{closure}"] += 1

    if state is not None:
        lifetime_h4_lengths[state_age_h4] += 1

    overlap = len(set(same_h4) & set(lifecycle))
    union = set(same_h4) | set(lifecycle)
    return {
        "symbol": symbol,
        "same_h4_source_exact_executions": len(same_h4),
        "persistent_lifecycle_executions": len(lifecycle),
        "exact_overlap_same_vs_lifecycle": overlap,
        "exact_union_count": len(union),
        "lifecycle_by_source_kind": dict(sorted(by_source_kind.items())),
        "lifecycle_by_execution_anchor": dict(sorted(by_anchor.items())),
        "lifecycle_h4_age_histogram": {
            str(key): value
            for key, value in sorted(lifetime_h4_lengths.items())
        },
        "diagnostics": dict(sorted(diagnostics.items())),
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
    start_date, end_date, canonical_reference = r74._window_contract(window_id)
    markets = {
        symbol: _market(
            symbol=symbol,
            bars=bars_by_symbol[symbol],
            start_date=start_date,
            end_date=end_date,
        )
        for symbol in contract.MARKETS
    }

    same = sum(
        int(row["same_h4_source_exact_executions"])
        for row in markets.values()
    )
    lifecycle = sum(
        int(row["persistent_lifecycle_executions"])
        for row in markets.values()
    )
    overlap = sum(
        int(row["exact_overlap_same_vs_lifecycle"])
        for row in markets.values()
    )
    union = sum(int(row["exact_union_count"]) for row in markets.values())
    if union != same + lifecycle - overlap:
        raise ValueError(f"R97 {window_id} union arithmetic drift")

    if window_id == "5Y":
        density_min = contract.FIVE_YEAR_TRADE_RANGE[0]
        five_year_max = contract.FIVE_YEAR_TRADE_RANGE[1]
        density_max: int | None = five_year_max
        density_pass = density_min <= union <= five_year_max
    elif window_id == "2Y":
        density_min = contract.TWO_YEAR_MIN_TRADES
        density_max = None
        density_pass = union >= density_min
    else:
        density_min = 1000
        density_max = None
        density_pass = union >= density_min

    return {
        "window_id": window_id,
        "canonical_signal_reference": canonical_reference,
        "same_h4_source_exact_executions": same,
        "persistent_lifecycle_executions": lifecycle,
        "exact_overlap_same_vs_lifecycle": overlap,
        "exact_union_count": union,
        "density_minimum": density_min,
        "density_maximum": density_max,
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
        raise ValueError("R97 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R97 source failure decision drift")
    if r94.IDENTITY != (
        "VT08_INDEX_R94_TTRADES_TIMEFRAME_HIERARCHY_FREEZE_001"
    ):
        raise ValueError("R97 R94 hierarchy freeze drift")
    if r96.IDENTITY != (
        "VT08_INDEX_R96_IDEAL_FORMATION_CROSS_H4_PS_CARRY_001"
    ):
        raise ValueError("R97 R96 identity drift")
    if 14 in r4.V7_ANCHORS or 18 in r4.V7_ANCHORS:
        raise ValueError("R97 execution anchor contract drift")

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
        "source_r96": {
            "run_id": SOURCE_R96_RUN_ID,
            "artifact_id": SOURCE_R96_ARTIFACT_ID,
            "artifact_digest": SOURCE_R96_ARTIFACT_DIGEST,
        },
        "lifecycle_contract": {
            "primary_model": "D1_H4_M15",
            "start_requires_closed_ideal_formation": True,
            "numeric_h4_ttl": None,
            "state_ends_on_invalidation": True,
            "state_ends_on_daily_bias_change_or_ambiguity": True,
            "new_source_exact_ps_replaces_state": True,
            "one_execution_per_protected_swing": True,
            "new_protected_swing_rearms": True,
            "same_timestamp_conflicting_replacement": "FAIL_CLOSED",
            "execution_anchors_ny": list(r4.V7_ANCHORS),
            "owner_disabled_14_preserved": True,
            "context_only_18_preserved": True,
            "continuation": "EXACT_V6_M15_BREAK_CLOSE",
            "h1_m5_independent_signals_added": False,
            "m15_m1_independent_signals_added": False,
            "pnl_evaluated": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": "R97_PERSISTENT_PS_LIFECYCLE_CENSUS_COMPLETE_NO_TRADES",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "source_primary_model_only": True,
            "future_information_used": False,
            "numeric_ttl_search": False,
            "pnl_evaluated": False,
            "risk_changed": False,
            "target_changed": False,
            "anchors_changed": False,
            "market_or_anchor_selection_by_outcome": False,
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
                        "same_h4_source_exact_executions",
                        "persistent_lifecycle_executions",
                        "exact_union_count",
                        "density_pass",
                    )
                },
                "recent_two_year": {
                    key: report["recent_two_year"][key]
                    for key in (
                        "same_h4_source_exact_executions",
                        "persistent_lifecycle_executions",
                        "exact_union_count",
                        "density_pass",
                    )
                },
                "r66": {
                    key: report["r66_failed_holdout"][key]
                    for key in (
                        "same_h4_source_exact_executions",
                        "persistent_lifecycle_executions",
                        "exact_union_count",
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
