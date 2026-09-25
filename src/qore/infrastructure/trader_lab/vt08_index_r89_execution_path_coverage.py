"""VT08 Index R89 — source execution-path coverage census.

R88 proved that adding a separate H1->M5 nested path is still structurally
insufficient. R89 returns to the frozen source execution techniques and keeps
setup identity separate from execution choice.

Source contract:
- continuation close and continuation retest are alternate executions of the
  same already-valid continuation; a retest never creates a second setup;
- positional entry is an optional advanced path at the next HTF open, only
  after the full H4 model and Protected Swing already exist;
- positional entry may rescue a source-valid setup that had no valid standard
  continuation execution inside the completed H4;
- Owner-disabled 14:00 remains disabled, and context-only 18:00 cannot be used
  as positional execution. No stale deferral to a later H4 open is allowed.

R89 is a no-PnL census. It measures:
1. standard continuation-close coverage from the R84 source-exact PS layer;
2. how many standard continuations also offer a causal retest fill before
   invalidation/H4 end (alternative fill only);
3. how many non-standard-executed PS events can be rescued by an immediate-next
   authorized positional open after the completed fractal model.

No target, risk allocator or economic selection is attached.
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
    vt08_index_r88_nested_h1_m5_density as r88,
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

SCHEMA = "qore.trader_lab.vt08_index_r89_execution_path_coverage.v1"
IDENTITY = "VT08_INDEX_R89_SOURCE_EXECUTION_PATH_COVERAGE_CENSUS_001"

SOURCE_R85_RUN_ID = 35525680874
SOURCE_R88_RUN_ID = 35526661105


@dataclass(frozen=True, slots=True)
class PositionalRescue:
    symbol: str
    source_h4_opened_at: datetime
    next_h4_opened_at: datetime
    side: DemoTradingSetupSide
    protected_swing: Decimal
    entry: Decimal
    family: str

    def identity(self) -> tuple[object, ...]:
        return (
            self.symbol,
            self.source_h4_opened_at.astimezone(UTC),
            self.next_h4_opened_at.astimezone(UTC),
            self.side.value,
            self.protected_swing,
            self.entry,
        )


def _continuation_breakout_level(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    continuation_index: int,
    side: DemoTradingSetupSide,
) -> Decimal:
    if continuation_index <= 0:
        raise ValueError("R89 continuation must have a prior bar")
    prior = bars[continuation_index - 1]
    return (
        prior.high
        if side is DemoTradingSetupSide.LONG
        else prior.low
    )


def _retest_fill_index(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    continuation_index: int,
    side: DemoTradingSetupSide,
    protected_swing: Decimal,
    model_kind: v6.H4ModelKind,
    h4_open: Decimal,
) -> int | None:
    level = _continuation_breakout_level(
        bars,
        continuation_index=continuation_index,
        side=side,
    )
    if model_kind is v6.H4ModelKind.SAME_C2:
        in_body = (
            level > h4_open
            if side is DemoTradingSetupSide.LONG
            else level < h4_open
        )
        if not in_body:
            return None

    for index in range(continuation_index + 1, len(bars)):
        bar = bars[index]
        invalidated = (
            bar.low <= protected_swing
            if side is DemoTradingSetupSide.LONG
            else bar.high >= protected_swing
        )
        if invalidated:
            return None
        if bar.low <= level <= bar.high:
            return index
    return None


def _ps_survives_until(
    bars: Sequence[Vt08IndexC2R1Bar],
    *,
    confirmed_at: datetime,
    boundary: datetime,
    side: DemoTradingSetupSide,
    protected_swing: Decimal,
) -> bool:
    for bar in bars:
        opened = bar.opened_at.astimezone(UTC)
        if opened < confirmed_at.astimezone(UTC):
            continue
        if opened >= boundary.astimezone(UTC):
            break
        invalidated = (
            bar.low <= protected_swing
            if side is DemoTradingSetupSide.LONG
            else bar.high >= protected_swing
        )
        if invalidated:
            return False
    return True


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
    key_position = {key: index for index, key in enumerate(h4_keys)}
    side_cache: dict[Any, DemoTradingSetupSide | None] = {}

    source_events = 0
    close_exec: dict[tuple[object, ...], r85.ExecutableContinuation] = {}
    close_with_retest = 0
    retest_reason: Counter[str] = Counter()
    positional_rescues: dict[tuple[object, ...], PositionalRescue] = {}
    positional_alternates = 0
    positional_reason: Counter[str] = Counter()
    by_anchor: dict[str, Counter[str]] = {}

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

        candidates = r85._source_ps_candidates(
            symbol=symbol,
            opened=opened,
            side=side,
            pois=pois,
            inside=inside,
        )
        source_events += len(candidates)
        anchor = str(local.hour)
        by_anchor.setdefault(anchor, Counter())

        for candidate in candidates:
            standard, standard_reason = r85._executable_from_event(
                candidate,
                inside=inside,
                h4_bar=h4[opened],
                model_kind=model_kind,
            )
            standard_exists = standard is not None
            if standard is not None:
                close_exec.setdefault(standard.identity(), standard)
                retest = _retest_fill_index(
                    inside,
                    continuation_index=standard.continuation_index,
                    side=side,
                    protected_swing=candidate.event.protected_swing,
                    model_kind=model_kind,
                    h4_open=h4[opened].open,
                )
                if retest is not None:
                    close_with_retest += 1
                    retest_reason["RETEST_AVAILABLE"] += 1
                    by_anchor[anchor]["RETEST_AVAILABLE"] += 1
                else:
                    retest_reason["NO_CAUSAL_RETEST"] += 1
                    by_anchor[anchor]["NO_CAUSAL_RETEST"] += 1
            else:
                retest_reason[f"NO_STANDARD:{standard_reason}"] += 1

            current_pos = key_position[opened]
            if current_pos + 1 >= len(h4_keys):
                positional_reason["NO_NEXT_H4"] += 1
                continue
            next_open = h4_keys[current_pos + 1]
            next_local = next_open.astimezone(v7._NY)
            if next_local.hour not in r4.V7_ANCHORS:
                positional_reason[
                    f"NEXT_H4_NOT_EXECUTABLE:{next_local.hour}"
                ] += 1
                continue
            if not (
                start_date
                <= next_local.date()
                < end_date
            ):
                positional_reason["NEXT_H4_OUTSIDE_WINDOW"] += 1
                continue

            completed_model = r6._completed_h4_model_fast(
                indexed,
                h4,
                h4_keys,
                current_h4_open=next_open,
                side=side,
            )
            if completed_model is None:
                positional_reason["NO_COMPLETED_FRACTAL_MODEL"] += 1
                continue

            if not _ps_survives_until(
                bars,
                confirmed_at=candidate.event.confirmed_at,
                boundary=next_open,
                side=side,
                protected_swing=candidate.event.protected_swing,
            ):
                positional_reason["PS_INVALIDATED_BEFORE_NEXT_H4"] += 1
                continue

            entry = h4[next_open].open
            risk = (
                entry - candidate.event.protected_swing
                if side is DemoTradingSetupSide.LONG
                else candidate.event.protected_swing - entry
            )
            if risk <= 0:
                positional_reason["NON_POSITIVE_POSITIONAL_RISK"] += 1
                continue

            row = PositionalRescue(
                symbol=symbol,
                source_h4_opened_at=opened,
                next_h4_opened_at=next_open,
                side=side,
                protected_swing=candidate.event.protected_swing,
                entry=entry,
                family=candidate.event.family,
            )
            if standard_exists:
                positional_alternates += 1
                positional_reason["POSITIONAL_ALTERNATE_STANDARD_EXISTS"] += 1
                by_anchor[anchor][
                    "POSITIONAL_ALTERNATE_STANDARD_EXISTS"
                ] += 1
            else:
                positional_rescues.setdefault(row.identity(), row)
                positional_reason["POSITIONAL_RESCUE"] += 1
                by_anchor[anchor]["POSITIONAL_RESCUE"] += 1

    combined_unique = len(close_exec) + len(positional_rescues)
    return {
        "symbol": symbol,
        "source_ps_event_count": source_events,
        "standard_close_executions": len(close_exec),
        "standard_close_with_retest_available": close_with_retest,
        "retest_is_alternate_not_new_setup": True,
        "positional_rescue_unique_setups": len(positional_rescues),
        "positional_alternate_when_standard_exists": positional_alternates,
        "combined_standard_plus_positional_rescue": combined_unique,
        "retest_diagnostics": dict(sorted(retest_reason.items())),
        "positional_diagnostics": dict(sorted(positional_reason.items())),
        "by_anchor": {
            key: dict(sorted(value.items()))
            for key, value in sorted(by_anchor.items())
        },
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

    close_count = sum(
        int(row["standard_close_executions"])
        for row in markets.values()
    )
    retest_count = sum(
        int(row["standard_close_with_retest_available"])
        for row in markets.values()
    )
    positional_rescue = sum(
        int(row["positional_rescue_unique_setups"])
        for row in markets.values()
    )
    combined = close_count + positional_rescue

    if window_id == "5Y":
        minimum, maximum = contract.FIVE_YEAR_TRADE_RANGE
        density_pass = minimum <= combined <= maximum
    elif window_id == "2Y":
        minimum = contract.TWO_YEAR_MIN_TRADES
        maximum = None
        density_pass = combined >= minimum
    else:
        minimum = 1000
        maximum = None
        density_pass = combined >= minimum

    return {
        "window_id": window_id,
        "canonical_signal_reference": canonical_reference,
        "standard_close_executions": close_count,
        "standard_close_with_retest_available": retest_count,
        "retest_fill_coverage_of_standard": (
            str(Decimal(retest_count) / Decimal(close_count))
            if close_count
            else "0"
        ),
        "positional_rescue_unique_setups": positional_rescue,
        "combined_standard_plus_positional_rescue": combined,
        "density_minimum": minimum,
        "density_maximum": maximum,
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
        raise ValueError("R89 frozen R58/R59 dependency drift")
    if r67.SOURCE_R66_DECISION != (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    ):
        raise ValueError("R89 source failure decision drift")
    if r85.IDENTITY != (
        "VT08_INDEX_R85_SOURCE_EXACT_PS_CONTINUATION_REARM_CENSUS_001"
    ):
        raise ValueError("R89 R85 identity drift")
    if r88.IDENTITY != (
        "VT08_INDEX_R88_NESTED_H1_M5_SOURCE_DENSITY_CENSUS_001"
    ):
        raise ValueError("R89 R88 identity drift")
    if 14 in r4.V7_ANCHORS:
        raise ValueError("R89 Owner-disabled 14:00 unexpectedly enabled")
    if 18 in r4.V7_ANCHORS:
        raise ValueError("R89 context-only 18:00 unexpectedly executable")

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
        "source_predecessors": {
            "r85_run_id": SOURCE_R85_RUN_ID,
            "r88_run_id": SOURCE_R88_RUN_ID,
        },
        "execution_contract": {
            "continuation_close": "PRIMARY_STANDARD",
            "continuation_retest": "ALTERNATE_FILL_SAME_SETUP",
            "retest_creates_new_setup": False,
            "positional_entry": "OPTIONAL_ADVANCED_RESCUE",
            "positional_requires_completed_fractal_model": True,
            "positional_requires_existing_valid_protected_swing": True,
            "positional_requires_immediate_next_h4": True,
            "stale_deferral_allowed": False,
            "owner_disabled_14_preserved": True,
            "context_only_18_preserved": True,
            "pnl_evaluated": False,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "decision": "R89_SOURCE_EXECUTION_PATH_COVERAGE_COMPLETE_NO_TRADES",
        "governance": {
            "forensics_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "future_information_used": False,
            "retest_double_counted_as_setup": False,
            "pnl_evaluated": False,
            "target_changed": False,
            "risk_changed": False,
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
                        "standard_close_executions",
                        "standard_close_with_retest_available",
                        "positional_rescue_unique_setups",
                        "combined_standard_plus_positional_rescue",
                        "density_pass",
                    )
                },
                "recent_two_year": {
                    key: report["recent_two_year"][key]
                    for key in (
                        "standard_close_executions",
                        "standard_close_with_retest_available",
                        "positional_rescue_unique_setups",
                        "combined_standard_plus_positional_rescue",
                        "density_pass",
                    )
                },
                "r66": {
                    key: report["r66_failed_holdout"][key]
                    for key in (
                        "standard_close_executions",
                        "standard_close_with_retest_available",
                        "positional_rescue_unique_setups",
                        "combined_standard_plus_positional_rescue",
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
