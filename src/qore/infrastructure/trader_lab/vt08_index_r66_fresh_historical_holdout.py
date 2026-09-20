"""VT08 Index R66 — preregistered fresh historical holdout.

This module evaluates the exact frozen R58/R59 candidate on the complete
provider-backed pre-development region that is both available in the frozen
CIBO 10Y Atlas and disjoint from the consumed 5Y window:

    2016-09-17 <= New York source date < 2018-09-15

The source Atlas starts at 2016-09-17T00:00:00Z and the consumed 5Y candidate
window starts on 2018-09-15. R66 therefore uses the full non-overlapping region
available between those boundaries. The 728-day interval is preregistered as
two contiguous 364-day blocks split at 2017-09-16.

The candidate was frozen before this holdout execution. R66 does not retune
entry, stop, target, POI, rearm, risk allocation, concurrency, or any
calendar/year runtime feature after observing the holdout result.

Preregistered gate:
- sample >= 1000 trades;
- PF >= 1.50 at -0.05R/trade;
- PF >= 1.30 at -0.10R/trade;
- conservative portfolio MTM DD <= 6R at both stresses;
- both preregistered 364-day blocks positive at both stresses.

Failure rejects certification for this exact frozen identity. It must not be
retuned in place.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_density_round4 as r4,
)
from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_management_round5 as r5,
)
from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_tuning_round1 as r1,
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
    vt08_index_r15_concurrent_portfolio_validation as r15,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as r31,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r59_candidate_freeze as freeze,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r60_core_robustness_suite as r60,
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

SCHEMA = "qore.trader_lab.vt08_index_r66_fresh_holdout.v1"
IDENTITY = "VT08_INDEX_R66_R58_FRESH_HISTORICAL_HOLDOUT_001"

START_DATE = date(2016, 9, 17)
BLOCK_BOUNDARY = date(2017, 9, 16)
END_DATE_EXCLUSIVE = date(2018, 9, 15)
HOLDOUT_DAYS = 728
BLOCK_DAYS = 364

ATLAS_TARGET_START = "2016-09-17T00:00:00+00:00"
ATLAS_TARGET_END_EXCLUSIVE = "2026-09-17T00:00:00+00:00"
ATLAS_SOURCE_HEAD = "ab782b8e9f890f86a2b6500070f0556b4b685e3d"
ATLAS_SOURCE_RUN_ID = 35166210458

PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
PRIMARY_PF_MIN = Decimal("1.50")
SECONDARY_PF_MIN = Decimal("1.30")
PORTFOLIO_DD_MAX_R = Decimal("6")
MIN_TRADES = 1000
_NY = ZoneInfo("America/New_York")


def _load_cibo_m15_holdout(
    root: Path,
    *,
    symbol: str,
) -> tuple[tuple[Vt08IndexC2R1Bar, ...], dict[str, Any]]:
    manifest = r1._read_json(r1._single(root, "symbol-consumption-manifest.json"))
    if manifest.get("identity") != r1.SOURCE_IDENTITY:
        raise ValueError(f"CIBO source identity drift for {symbol}")
    if manifest.get("canonical_symbol") != symbol:
        raise ValueError(f"CIBO canonical symbol drift for {symbol}")
    if manifest.get("target_start") != ATLAS_TARGET_START:
        raise ValueError(f"CIBO Atlas start drift for {symbol}")
    if manifest.get("target_end_exclusive") != ATLAS_TARGET_END_EXCLUSIVE:
        raise ValueError(f"CIBO Atlas end drift for {symbol}")
    if not bool(manifest.get("read_only")):
        raise ValueError(f"CIBO source must be read-only for {symbol}")
    if bool(manifest.get("live_authorized")) or bool(
        manifest.get("real_capital_authorized")
    ):
        raise ValueError(f"CIBO source authority drift for {symbol}")

    context_start_local = datetime.combine(
        START_DATE,
        time.min,
        tzinfo=_NY,
    )
    end_local = datetime.combine(
        END_DATE_EXCLUSIVE,
        time.min,
        tzinfo=_NY,
    )
    start_dt = context_start_local.astimezone(UTC)
    end_dt = end_local.astimezone(UTC)

    buckets: dict[
        datetime,
        list[tuple[datetime, dict[str, Any]]],
    ] = defaultdict(list)
    retained_rows = 0
    for year in range(start_dt.year, end_dt.year + 1):
        path = root / "RAW_M5_LEDGER" / f"{year}.jsonl"
        if not path.is_file():
            raise ValueError(
                f"missing raw CIBO M5 partition {year} for {symbol}"
            )
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                decoded = json.loads(line)
                if not isinstance(decoded, dict):
                    raise ValueError("raw CIBO M5 row must be an object")
                row = cast(dict[str, Any], decoded)
                if row.get("schema") != r1.RAW_SCHEMA:
                    raise ValueError(f"raw CIBO schema drift for {symbol}")
                if row.get("identity") != r1.SOURCE_IDENTITY:
                    raise ValueError(f"raw CIBO identity drift for {symbol}")
                if row.get("canonical_symbol") != symbol:
                    raise ValueError(f"raw CIBO symbol drift for {symbol}")
                opened = r1._parse_time(row.get("opened_at"))
                if opened < start_dt or opened >= end_dt:
                    continue
                if opened.minute % 5 != 0 or opened.second != 0:
                    raise ValueError(
                        f"unaligned raw M5 timestamp for {symbol}"
                    )
                retained_rows += 1
                bucket = opened.replace(
                    minute=(opened.minute // 15) * 15,
                    second=0,
                    microsecond=0,
                )
                buckets[bucket].append((opened, row))

    bars: list[Vt08IndexC2R1Bar] = []
    bucket_sizes: dict[str, int] = {"1": 0, "2": 0, "3": 0}
    for bucket in sorted(buckets):
        entries = sorted(buckets[bucket], key=lambda item: item[0])
        if len(entries) not in (1, 2, 3):
            raise ValueError(
                f"unexpected M5 multiplicity in {symbol} M15 bucket"
            )
        bucket_sizes[str(len(entries))] += 1
        rows = [item[1] for item in entries]
        opens = [r1._price(row["open_relative"]) for row in rows]
        highs = [r1._price(row["high_relative"]) for row in rows]
        lows = [r1._price(row["low_relative"]) for row in rows]
        closes = [r1._price(row["close_relative"]) for row in rows]
        bars.append(
            Vt08IndexC2R1Bar(
                opened_at=bucket,
                closed_at=bucket + timedelta(minutes=15),
                open=opens[0],
                high=max(highs),
                low=min(lows),
                close=closes[-1],
            )
        )

    if not bars:
        raise ValueError(f"no reconstructed fresh M15 bars for {symbol}")
    return tuple(bars), {
        "source_run_id": ATLAS_SOURCE_RUN_ID,
        "source_git_sha": ATLAS_SOURCE_HEAD,
        "source_identity": r1.SOURCE_IDENTITY,
        "reconstruction_policy": (
            "FRESH_PRE5Y_AGGREGATE_ALL_OBSERVED_PROVIDER_M5_WITHIN_M15_"
            "NO_INTERPOLATION"
        ),
        "context_start_utc": start_dt.isoformat(),
        "end_utc_exclusive": end_dt.isoformat(),
        "raw_m5_rows_loaded": retained_rows,
        "m15_buckets": len(bars),
        "m15_bucket_size_counts": bucket_sizes,
        "synthetic_prices": 0,
        "interpolated_prices": 0,
        "first_m15": bars[0].opened_at.isoformat(),
        "last_m15": bars[-1].opened_at.isoformat(),
    }


def _build_surface(
    *,
    symbol: str,
    bars: Sequence[Vt08IndexC2R1Bar],
) -> tuple[Any, ...]:
    indexed = {bar.opened_at.astimezone(UTC): bar for bar in bars}
    h4 = v6._build_h4(indexed)
    h4_keys = tuple(sorted(h4))
    side_cache: dict[date, DemoTradingSetupSide | None] = {}
    opportunities: list[Any] = []

    for opened in h4_keys:
        local = opened.astimezone(_NY)
        local_date = local.date()
        if not (START_DATE <= local_date < END_DATE_EXCLUSIVE):
            continue
        if local.hour not in r4.V7_ANCHORS:
            continue
        if local_date not in side_cache:
            side_cache[local_date] = v7._daily_bias(indexed, before=opened)
        side = side_cache[local_date]
        if side is None:
            continue
        opportunities.extend(
            r6._opportunities_for_h4_fast(
                symbol=symbol,
                indexed=indexed,
                h4=h4,
                h4_keys=h4_keys,
                h4_opened_at=opened,
                side=side,
            )
        )

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
        raise ValueError(
            f"duplicate fresh structural opportunity identity for {symbol}"
        )
    return tuple(opportunities)


def _build_stream(
    *,
    roots: dict[str, Path],
) -> tuple[
    tuple[tuple[Any, r5.ManagedTrade], ...],
    dict[str, Sequence[Vt08IndexC2R1Bar]],
    dict[str, tuple[datetime, ...]],
    dict[str, Any],
]:
    stream: list[tuple[Any, r5.ManagedTrade]] = []
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]] = {}
    opened_by_symbol: dict[str, tuple[datetime, ...]] = {}
    provenance: dict[str, Any] = {}
    policy = r8._target_policy(r31.TARGET_R)

    for symbol in contract.MARKETS:
        bars, source = _load_cibo_m15_holdout(
            roots[symbol],
            symbol=symbol,
        )
        opened = tuple(bar.opened_at.astimezone(UTC) for bar in bars)
        opportunities = _build_surface(symbol=symbol, bars=bars)
        for opportunity in opportunities:
            stream.append(
                (
                    opportunity,
                    r5._manage_trade(
                        opportunity.signal,
                        bars=bars,
                        opened=opened,
                        policy=policy,
                    ),
                )
            )
        bars_by_symbol[symbol] = bars
        opened_by_symbol[symbol] = opened
        provenance[symbol] = source

    stream.sort(
        key=lambda item: (
            item[0].signal.signal_at,
            item[0].signal.symbol,
            item[0].signal.entry,
            item[0].signal.stop,
            item[0].rearm_index,
        )
    )
    identities = [item[0].identity() for item in stream]
    if len(set(identities)) != len(identities):
        raise ValueError("fresh cross-market opportunity identity collision")
    return tuple(stream), bars_by_symbol, opened_by_symbol, provenance


def _holdout_blocks(
    assigned: Sequence[r15.AssignedTrade],
    *,
    stress: Decimal,
) -> dict[str, dict[str, Any]]:
    boundaries = (START_DATE, BLOCK_BOUNDARY, END_DATE_EXCLUSIVE)
    result: dict[str, dict[str, Any]] = {}
    for index in range(2):
        start = boundaries[index]
        end = boundaries[index + 1]
        items = tuple(
            item
            for item in assigned
            if start <= item.exited_at.astimezone(_NY).date() < end
        )
        values = tuple(
            (item.outcome.r_multiple - stress) * item.weight
            for item in items
        )
        result[f"B{index + 1}"] = {
            "start_date": start.isoformat(),
            "end_date_exclusive": end.isoformat(),
            "days": (end - start).days,
            **fx._metrics(values),
        }
    return result


def _blocks_positive(blocks: dict[str, dict[str, Any]]) -> bool:
    return len(blocks) == 2 and all(
        int(block["days"]) == BLOCK_DAYS
        and int(block["sample"]) > 0
        and Decimal(str(block["total_r"])) > 0
        for block in blocks.values()
    )


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, object]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R66 frozen R59/R58 dependency drift")
    if (END_DATE_EXCLUSIVE - START_DATE).days != HOLDOUT_DAYS:
        raise ValueError("R66 preregistered holdout length drift")
    if (BLOCK_BOUNDARY - START_DATE).days != BLOCK_DAYS:
        raise ValueError("R66 first block length drift")
    if (END_DATE_EXCLUSIVE - BLOCK_BOUNDARY).days != BLOCK_DAYS:
        raise ValueError("R66 second block length drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    stream, bars_by_symbol, opened_by_symbol, provenance = _build_stream(
        roots=roots
    )
    assigned = r60._candidate(
        stream,
        bars_by_symbol=bars_by_symbol,
    )

    primary = fx._metrics(
        r15._realized_values(tuple(assigned), stress=PRIMARY_STRESS)
    )
    secondary = fx._metrics(
        r15._realized_values(tuple(assigned), stress=SECONDARY_STRESS)
    )
    primary_mtm = r15._portfolio_mark_to_market(
        tuple(assigned),
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        stress=PRIMARY_STRESS,
        adverse=True,
    )
    secondary_mtm = r15._portfolio_mark_to_market(
        tuple(assigned),
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        stress=SECONDARY_STRESS,
        adverse=True,
    )
    primary_blocks = _holdout_blocks(
        assigned,
        stress=PRIMARY_STRESS,
    )
    secondary_blocks = _holdout_blocks(
        assigned,
        stress=SECONDARY_STRESS,
    )

    density_pass = len(assigned) >= MIN_TRADES
    primary_blocks_pass = _blocks_positive(primary_blocks)
    secondary_blocks_pass = _blocks_positive(secondary_blocks)
    gate_pass = (
        density_pass
        and Decimal(str(primary["profit_factor"] or "0"))
        >= PRIMARY_PF_MIN
        and Decimal(str(secondary["profit_factor"] or "0"))
        >= SECONDARY_PF_MIN
        and Decimal(str(primary_mtm["max_drawdown_r"]))
        <= PORTFOLIO_DD_MAX_R
        and Decimal(str(secondary_mtm["max_drawdown_r"]))
        <= PORTFOLIO_DD_MAX_R
        and primary_blocks_pass
        and secondary_blocks_pass
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate": {
            "candidate_id": freeze.CANDIDATE_ID,
            "rule_fingerprint": freeze.CANDIDATE_RULE_FINGERPRINT,
            "freeze_id": freeze.FREEZE_ID,
            "candidate_retuned": False,
        },
        "window": {
            "start_date": START_DATE.isoformat(),
            "block_boundary": BLOCK_BOUNDARY.isoformat(),
            "end_date_exclusive": END_DATE_EXCLUSIVE.isoformat(),
            "days": HOLDOUT_DAYS,
            "block_days": BLOCK_DAYS,
            "status": "PREREGISTERED_FRESH_HISTORICAL_HOLDOUT",
            "source_atlas_starts_at_holdout_boundary": True,
            "disjoint_from_frozen_5y": True,
            "disjoint_from_recent_2y": True,
        },
        "pre_registered_gate": {
            "minimum_trades": MIN_TRADES,
            "primary_stress_r": str(PRIMARY_STRESS),
            "primary_pf_minimum": str(PRIMARY_PF_MIN),
            "secondary_stress_r": str(SECONDARY_STRESS),
            "secondary_pf_minimum": str(SECONDARY_PF_MIN),
            "portfolio_dd_max_r": str(PORTFOLIO_DD_MAX_R),
            "both_364d_blocks_positive_both_stresses": True,
            "same_frozen_identity_required": True,
            "retuning_after_holdout_forbidden": True,
        },
        "sample": len(assigned),
        "trade_count_by_market": {
            symbol: sum(item.symbol == symbol for item in assigned)
            for symbol in contract.MARKETS
        },
        "primary": primary,
        "secondary": secondary,
        "primary_conservative_mark_to_market": primary_mtm,
        "secondary_conservative_mark_to_market": secondary_mtm,
        "holdout_blocks_primary": primary_blocks,
        "holdout_blocks_secondary": secondary_blocks,
        "all_holdout_blocks_primary_positive": primary_blocks_pass,
        "all_holdout_blocks_secondary_positive": secondary_blocks_pass,
        "fresh_holdout_gate_pass": gate_pass,
        "decision": (
            "PASS_R66_FRESH_HOLDOUT_CERTIFICATION_EVIDENCE"
            if gate_pass
            else "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
        ),
        "provenance": provenance,
        "governance": {
            "preregistered_before_execution": True,
            "fresh_holdout_claim": True,
            "candidate_holdout_scoring_previously_consumed": False,
            "raw_market_memory_preexisted": True,
            "candidate_retuned": False,
            "signals_suppressed": False,
            "calendar_or_year_runtime_feature": False,
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
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "candidate": report["candidate"],
                "window": report["window"],
                "sample": report["sample"],
                "primary": report["primary"],
                "secondary": report["secondary"],
                "fresh_holdout_gate_pass": report[
                    "fresh_holdout_gate_pass"
                ],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
