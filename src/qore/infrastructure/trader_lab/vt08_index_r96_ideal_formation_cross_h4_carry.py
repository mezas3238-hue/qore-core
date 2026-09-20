"""VT08 Index R96 — Ideal Formation cross-H4 Protected-Swing carry census.

R95 proved that rebuilding the full FVG -> relevant-swing -> CISD hierarchy
inside the same H4 still leaves the primary D1->H4->M15 model far below density.

Primary TTrades Ideal Formation / Candle-3 material establishes a missing state
transition:
- when Candle 2 closes in the intended direction and simultaneously creates a
  Protected Swing, Candle 3 is the expected expansion candle;
- when Candle 3 completes the Protected Swing, Candle 4 becomes the expected
  continuation candle;
- lower-timeframe CISD/Protected-Swing evidence confirms the higher-timeframe
  closure and remains the structural invalidation.

Therefore an H4 boundary cannot universally delete a source-valid Protected
Swing. R96 tests that exact missing mechanism without PnL:
1. scan every complete H4 family candle as *context/formation*, including the
   18:00 context candle and Owner-disabled 14:00 candle;
2. require a frozen V6 C2 or C3 closure aligned with causal V7 daily bias;
3. require an R85 source-exact M15 Protected Swing inside that formation H4;
4. require that Protected Swing to survive through the formation close;
5. carry it only into the immediately following H4 candle;
6. execute only if that following H4 is Owner-authorized (22/02/06/10 NY),
   daily bias still agrees, and exact V6 M15 continuation forms before PS
   invalidation.

No stale multi-H4 deferral, no positional entry, no target, no risk and no PnL.
The report also unions these carry continuations with the R85 same-H4 primary
executions using exact mechanical identity.
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
    vt08_index_r85_source_exact_ps_continuation_rearm as r85,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r94_ttrades_timeframe_hierarchy_freeze as r94,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r95_full_dynamic_poi_hierarchy as r95,
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

SCHEMA = "qore.trader_lab.vt08_index_r96_ideal_formation_cross_h4_carry.v1"
IDENTITY = "VT08_INDEX_R96_IDEAL_FORMATION_CROSS_H4_PS_CARRY_001"

SOURCE_R95_RUN_ID = 35531957789
SOURCE_R95_ARTIFACT_ID = 10611990582
SOURCE_R95_ARTIFACT_DIGEST = (
    "sha256:1bfa717e1172768d00fc6e615cd8b37d58695fb7b41ba8fa83390cab2c3533c5"
)


@dataclass(frozen=True, slots=True)
class CarryContinuation:
    symbol: str
    formation_h4_opened_at: datetime
    execution_h4_opened_at: datetime
    side: DemoTradingSetupSide
    closure_kind: str
    protected_swing: Decimal
    ps_confirmed_at: datetime
    continuation_index: int
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


def _closure_kind(
    h4: dict[datetime, Vt08IndexC2R1Bar],
    h4_keys: tuple[datetime, ...],
    *,
    opened: datetime,
    side: DemoTradingSetupSide,
) -> str | None:
    try:
        position = h4_keys.index(opened.astimezone(UTC))
    except ValueError:
        return None
    if position >= 1 and v6._c2_side(
        h4[h4_keys[position - 1]],
        h4[opened],
    ) is side:
        return "C2"
    if position >= 2 and v6._c3_side(
        h4[h4_keys[position - 2]],
        h4[h4_keys[position - 1]],
        h4[opened],
    ) is side:
        return "C3"
    return None


def _survives_after_confirmation(
    inside: Sequence[Vt08IndexC2R1Bar],
    *,
    confirm_index: int,
    side: DemoTradingSetupSide,
    protected_swing: Decimal,
) -> bool:
    for bar in inside[confirm_index + 1 :]:
        invalidated = (
            bar.low <= protected_swing
            if side is DemoTradingSetupSide.LONG
            else bar.high >= protected_swing
        )
        if invalidated:
            return False
    return True


def _carry_from_candidate(
    *,
    symbol: str,
    formation_opened: datetime,
    execution_opened: datetime,
    closure_kind: str,
    candidate: r85.SourcePsCandidate,
    formation_inside: Sequence[Vt08IndexC2R1Bar],
    execution_inside: Sequence[Vt08IndexC2R1Bar],
) -> CarryContinuation | None:
    side = candidate.event.side
    protected_swing = candidate.event.protected_swing
    if not _survives_after_confirmation(
        formation_inside,
        confirm_index=candidate.confirm_index,
        side=side,
        protected_swing=protected_swing,
    ):
        return None

    continuation_index = v6._first_continuation(
        execution_inside,
        side=side,
        start_index=0,
        protected_swing=protected_swing,
    )
    if continuation_index is None:
        return None
    continuation = execution_inside[continuation_index]
    entry = continuation.close
    risk = (
        entry - protected_swing
        if side is DemoTradingSetupSide.LONG
        else protected_swing - entry
    )
    if risk <= 0:
        return None

    return CarryContinuation(
        symbol=symbol,
        formation_h4_opened_at=formation_opened,
        execution_h4_opened_at=execution_opened,
        side=side,
        closure_kind=closure_kind,
        protected_swing=protected_swing,
        ps_confirmed_at=candidate.event.confirmed_at,
        continuation_index=continuation_index,
        continuation_at=continuation.closed_at.astimezone(UTC),
        entry=entry,
    )


def _intra_h4_executables(
    *,
    symbol: str,
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    h4: dict[datetime, Vt08IndexC2R1Bar],
    h4_keys: tuple[datetime, ...],
    opened: datetime,
    side: DemoTradingSetupSide,
) -> tuple[r85.ExecutableContinuation, ...]:
    if opened.astimezone(v7._NY).hour not in r4.V7_ANCHORS:
        return ()
    pois = r6._source_pois_fast(
        indexed,
        h4,
        h4_keys,
        h4_opened_at=opened,
        side=side,
    )
    if not pois:
        return ()
    inside = r6._bars_between_fast(
        indexed,
        start=opened,
        end=h4[opened].closed_at,
    )
    if not inside:
        return ()
    model_kind = r6._completed_h4_model_fast(
        indexed,
        h4,
        h4_keys,
        current_h4_open=opened,
        side=side,
    )
    if model_kind is None:
        model_kind = v6.H4ModelKind.SAME_C2

    rows: dict[tuple[object, ...], r85.ExecutableContinuation] = {}
    for candidate in r85._source_ps_candidates(
        symbol=symbol,
        opened=opened,
        side=side,
        pois=pois,
        inside=inside,
    ):
        row, reason = r85._executable_from_event(
            candidate,
            inside=inside,
            h4_bar=h4[opened],
            model_kind=model_kind,
        )
        if row is not None and reason == "EXECUTABLE":
            rows.setdefault(row.identity(), row)
    return tuple(rows.values())


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

    intra: dict[tuple[object, ...], r85.ExecutableContinuation] = {}
    carry: dict[tuple[object, ...], CarryContinuation] = {}
    carry_by_closure: Counter[str] = Counter()
    carry_by_formation_anchor: Counter[str] = Counter()
    formation_counts: Counter[str] = Counter()

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
        if side is None:
            continue

        for row in _intra_h4_executables(
            symbol=symbol,
            indexed=indexed,
            h4=h4,
            h4_keys=h4_keys,
            opened=opened,
            side=side,
        ):
            key = (
                row.event.symbol,
                row.continuation_at.astimezone(UTC),
                row.event.side.value,
                row.entry,
                row.event.protected_swing,
            )
            intra.setdefault(key, row)

        closure = _closure_kind(
            h4,
            h4_keys,
            opened=opened,
            side=side,
        )
        if closure is None:
            continue
        formation_counts[f"{closure}_H4_CLOSURES"] += 1

        formation_pois = r6._source_pois_fast(
            indexed,
            h4,
            h4_keys,
            h4_opened_at=opened,
            side=side,
        )
        if not formation_pois:
            continue
        formation_inside = r6._bars_between_fast(
            indexed,
            start=opened,
            end=h4[opened].closed_at,
        )
        if not formation_inside:
            continue

        candidates = r85._source_ps_candidates(
            symbol=symbol,
            opened=opened,
            side=side,
            pois=formation_pois,
            inside=formation_inside,
        )
        if not candidates:
            continue
        formation_counts["CLOSURES_WITH_SOURCE_PS"] += 1

        next_open = h4[opened].closed_at.astimezone(UTC)
        execution_h4 = h4.get(next_open)
        if execution_h4 is None:
            formation_counts["NO_IMMEDIATE_NEXT_COMPLETE_H4"] += 1
            continue
        next_local = next_open.astimezone(v7._NY)
        if next_local.hour not in r4.V7_ANCHORS:
            formation_counts[
                f"NEXT_H4_NOT_EXECUTABLE:{next_local.hour}"
            ] += 1
            continue
        if not (start_date <= next_local.date() < end_date):
            formation_counts["NEXT_H4_OUTSIDE_WINDOW"] += 1
            continue

        next_side = v7._daily_bias(indexed, before=next_open)
        if next_side is not side:
            formation_counts["BIAS_CHANGED_BEFORE_EXPANSION"] += 1
            continue
        execution_inside = r6._bars_between_fast(
            indexed,
            start=next_open,
            end=execution_h4.closed_at,
        )
        if not execution_inside:
            continue

        for candidate in candidates:
            row = _carry_from_candidate(
                symbol=symbol,
                formation_opened=opened,
                execution_opened=next_open,
                closure_kind=closure,
                candidate=candidate,
                formation_inside=formation_inside,
                execution_inside=execution_inside,
            )
            if row is None:
                continue
            carry.setdefault(row.identity(), row)

    for row in carry.values():
        carry_by_closure[row.closure_kind] += 1
        carry_by_formation_anchor[
            str(row.formation_h4_opened_at.astimezone(v7._NY).hour)
        ] += 1

    exact_overlap = len(set(intra) & set(carry))
    union = set(intra) | set(carry)
    return {
        "symbol": symbol,
        "same_h4_source_exact_executions": len(intra),
        "cross_h4_carry_continuations": len(carry),
        "exact_overlap_same_vs_carry": exact_overlap,
        "exact_union_count": len(union),
        "carry_by_closure": dict(sorted(carry_by_closure.items())),
        "carry_by_formation_anchor": dict(
            sorted(carry_by_formation_anchor.items())
        ),
        "formation_diagnostics": dict(sorted(formation_counts.items())),
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
    carry = sum(
        int(row["cross_h4_carry_continuations"])
        for row in markets.values()
    )
    overlap = sum(
        int(row["exact_overlap_same_vs_carry"])
        for row in markets.values()
    )
    union = sum(int(row["exact_union_count"]) for row in markets.values())

    if union != same + carry - overlap:
        raise ValueError(f"R96 {window_id} union arithmetic drift")

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
        "cross_h4_carry_continuations": carry,
        "exact_overlap_same_vs_carry": overlap,
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
        raise ValueError("R96 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R96 source failure decision drift")
    if r94.IDENTITY != (
        "VT08_INDEX_R94_TTRADES_TIMEFRAME_HIERARCHY_FREEZE_001"
    ):
        raise ValueError("R96 R94 hierarchy freeze drift")
    if r95.IDENTITY != (
        "VT08_INDEX_R95_FULL_DYNAMIC_CONTINUATION_POI_HIERARCHY_001"
    ):
        raise ValueError("R96 R95 identity drift")
    if 14 in r4.V7_ANCHORS or 18 in r4.V7_ANCHORS:
        raise ValueError("R96 execution anchor contract drift")

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
        "source_r95": {
            "run_id": SOURCE_R95_RUN_ID,
            "artifact_id": SOURCE_R95_ARTIFACT_ID,
            "artifact_digest": SOURCE_R95_ARTIFACT_DIGEST,
        },
        "source_contract": {
            "primary_model": "D1_H4_M15",
            "formation_h4_may_be_context_only": True,
            "formation_requires_c2_or_c3_closure": True,
            "formation_requires_source_exact_m15_ps": True,
            "ps_must_survive_formation_close": True,
            "carry_scope": "IMMEDIATE_NEXT_H4_ONLY",
            "execution_h4_must_be_owner_authorized": True,
            "owner_execution_anchors_ny": list(r4.V7_ANCHORS),
            "owner_disabled_14_preserved": True,
            "context_only_18_preserved": True,
            "bias_must_persist": True,
            "execution": "EXACT_V6_M15_CONTINUATION",
            "positional_entry_added": False,
            "stale_multi_h4_deferral": False,
            "pnl_evaluated": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": "R96_IDEAL_FORMATION_CROSS_H4_CARRY_CENSUS_COMPLETE_NO_TRADES",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "source_primary_model_only": True,
            "future_information_used": False,
            "pnl_evaluated": False,
            "risk_changed": False,
            "target_changed": False,
            "anchors_changed": False,
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
                        "cross_h4_carry_continuations",
                        "exact_union_count",
                        "density_pass",
                    )
                },
                "recent_two_year": {
                    key: report["recent_two_year"][key]
                    for key in (
                        "same_h4_source_exact_executions",
                        "cross_h4_carry_continuations",
                        "exact_union_count",
                        "density_pass",
                    )
                },
                "r66": {
                    key: report["r66_failed_holdout"][key]
                    for key in (
                        "same_h4_source_exact_executions",
                        "cross_h4_carry_continuations",
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
