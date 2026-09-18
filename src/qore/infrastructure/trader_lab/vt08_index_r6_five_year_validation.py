"""VT08 Index R6 frozen candidate — five-year out-of-tuning validation replay.

This module replays the exact frozen VT08_INDEX_R6_GOVERNED_657_001 contract
without tuning on a contiguous five-year window that starts immediately after
the 2Y tuning window:

    2018-09-15 <= New York source date < 2023-09-15

The window is out-of-tuning but NOT claimed fresh for certification because
parts of the same historical period were consumed by earlier VT08 research.

Hard validation contract:
- preserve the frozen R6 opportunity generator, management map and governor;
- 1500 <= executed trades <= 1600;
- governed PF >= 1.50 and governed DD <= 6R at -0.05R/trade;
- governed PF >= 1.30 and governed DD <= 8R at -0.10R/trade;
- no zero-risk trades and no post-hoc rule changes.
"""

from __future__ import annotations

import argparse
import json
from bisect import bisect_left
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_density_round4 as r4
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_management_round5 as r5
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_specialist_risk_round6 as r6
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_tuning_round1 as r1
from qore.infrastructure.trader_lab import vt08_index_r6_governed_candidate_freeze as freeze
from qore.infrastructure.trader_lab import vt08_index_v6_ttrades_source_faithful as v6
from qore.infrastructure.trader_lab import vt08_index_v7_ttrades_source_corrected as v7
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_r6_five_year_validation.v1"
IDENTITY = "VT08_INDEX_R6_GOVERNED_657_5Y_VALIDATION_001"
START_DATE = date(2018, 9, 15)
END_DATE_EXCLUSIVE = date(2023, 9, 15)
MIN_TRADES = 1500
MAX_TRADES = 1600
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
PRIMARY_PF_MIN = Decimal("1.50")
PRIMARY_DD_MAX = Decimal("6")
SECONDARY_PF_MIN = Decimal("1.30")
SECONDARY_DD_MAX = Decimal("8")
_NY = ZoneInfo("America/New_York")



def _load_cibo_m15_5y(
    root: Path,
    *,
    symbol: str,
) -> tuple[tuple[Vt08IndexC2R1Bar, ...], dict[str, Any]]:
    manifest = r1._read_json(r1._single(root, "symbol-consumption-manifest.json"))
    if manifest.get("identity") != r1.SOURCE_IDENTITY:
        raise ValueError(f"CIBO source identity drift for {symbol}")
    if manifest.get("canonical_symbol") != symbol:
        raise ValueError(f"CIBO canonical symbol drift for {symbol}")
    if not bool(manifest.get("read_only")):
        raise ValueError(f"CIBO source must be read-only for {symbol}")
    if bool(manifest.get("live_authorized")) or bool(
        manifest.get("real_capital_authorized")
    ):
        raise ValueError(f"CIBO source authority drift for {symbol}")

    context_start_local = datetime.combine(
        START_DATE - timedelta(days=7),
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

    buckets: dict[datetime, list[tuple[datetime, dict[str, Any]]]] = defaultdict(list)
    retained_rows = 0
    for year in range(start_dt.year, end_dt.year + 1):
        path = root / "RAW_M5_LEDGER" / f"{year}.jsonl"
        if not path.is_file():
            raise ValueError(f"missing raw CIBO M5 partition {year} for {symbol}")
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
                    raise ValueError(f"unaligned raw M5 timestamp for {symbol}")
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
            raise ValueError(f"unexpected M5 multiplicity in {symbol} M15 bucket")
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
        raise ValueError(f"no reconstructed 5Y M15 bars for {symbol}")
    return tuple(bars), {
        "source_run_id": r1.SOURCE_CIBO_RUN_ID,
        "source_git_sha": r1.SOURCE_CIBO_GIT_SHA,
        "source_identity": r1.SOURCE_IDENTITY,
        "reconstruction_policy": (
            "5Y_AGGREGATE_ALL_OBSERVED_PROVIDER_M5_WITHIN_M15_NO_INTERPOLATION"
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


def _bars_between_fast(
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    *,
    start: datetime,
    end: datetime,
) -> tuple[Vt08IndexC2R1Bar, ...]:
    cursor = start.astimezone(UTC)
    end_utc = end.astimezone(UTC)
    result: list[Vt08IndexC2R1Bar] = []
    while cursor < end_utc:
        bar = indexed.get(cursor)
        if bar is not None:
            result.append(bar)
        cursor += timedelta(minutes=15)
    return tuple(result)


def _prior_h4_keys_fast(
    h4_keys: tuple[datetime, ...],
    *,
    before: datetime,
    count: int,
) -> tuple[datetime, ...]:
    index = bisect_left(h4_keys, before.astimezone(UTC))
    return h4_keys[max(0, index - count) : index]


def _source_pois_fast(
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    h4: dict[datetime, Vt08IndexC2R1Bar],
    h4_keys: tuple[datetime, ...],
    *,
    h4_opened_at: datetime,
    side: DemoTradingSetupSide,
) -> tuple[v6.SourcePoi, ...]:
    prior_keys = _prior_h4_keys_fast(
        h4_keys,
        before=h4_opened_at,
        count=3,
    )
    if len(prior_keys) < 3:
        return ()
    a, b, c_bar = (h4[key] for key in prior_keys)
    result: list[v6.SourcePoi] = []

    if side is DemoTradingSetupSide.LONG and a.high < c_bar.low:
        result.append(
            v6.SourcePoi(v6.PoiKind.FVG, a.high, c_bar.low, c_bar.closed_at)
        )
    if side is DemoTradingSetupSide.SHORT and a.low > c_bar.high:
        result.append(
            v6.SourcePoi(v6.PoiKind.FVG, c_bar.high, a.low, c_bar.closed_at)
        )

    if (
        side is DemoTradingSetupSide.LONG
        and b.low < a.low
        and b.low < c_bar.low
    ):
        result.append(
            v6.SourcePoi(
                v6.PoiKind.RELEVANT_SWING,
                b.low,
                b.low,
                c_bar.closed_at,
            )
        )
    if (
        side is DemoTradingSetupSide.SHORT
        and b.high > a.high
        and b.high > c_bar.high
    ):
        result.append(
            v6.SourcePoi(
                v6.PoiKind.RELEVANT_SWING,
                b.high,
                b.high,
                c_bar.closed_at,
            )
        )

    last_key = prior_keys[-1]
    last_bars = _bars_between_fast(
        indexed,
        start=last_key,
        end=h4[last_key].closed_at,
    )
    cisd = v6._last_cisd_poi(last_bars, side=side)
    if cisd is not None:
        result.append(cisd)

    unique: dict[tuple[object, ...], v6.SourcePoi] = {}
    for poi in result:
        key = (
            poi.kind.value,
            poi.low,
            poi.high,
            poi.observed_at.astimezone(UTC),
        )
        unique[key] = poi
    return tuple(unique.values())


def _priority_source_poi_fast(
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    h4: dict[datetime, Vt08IndexC2R1Bar],
    h4_keys: tuple[datetime, ...],
    *,
    h4_opened_at: datetime,
    side: DemoTradingSetupSide,
) -> v6.SourcePoi | None:
    pois = _source_pois_fast(
        indexed,
        h4,
        h4_keys,
        h4_opened_at=h4_opened_at,
        side=side,
    )
    return pois[0] if pois else None


def _completed_h4_model_fast(
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    h4: dict[datetime, Vt08IndexC2R1Bar],
    h4_keys: tuple[datetime, ...],
    *,
    current_h4_open: datetime,
    side: DemoTradingSetupSide,
) -> v6.H4ModelKind | None:
    keys = _prior_h4_keys_fast(
        h4_keys,
        before=current_h4_open,
        count=3,
    )
    if len(keys) < 2:
        return None
    prior_open = keys[-1]
    if v6._c2_side(h4[keys[-2]], h4[prior_open]) is side:
        poi = _priority_source_poi_fast(
            indexed,
            h4,
            h4_keys,
            h4_opened_at=prior_open,
            side=side,
        )
        bars = _bars_between_fast(
            indexed,
            start=prior_open,
            end=h4[prior_open].closed_at,
        )
        if poi is not None and v6._poi_touch_index(bars, poi) is not None:
            return v6.H4ModelKind.C2_EXPANSION
    if len(keys) == 3 and v6._c3_side(
        h4[keys[-3]],
        h4[keys[-2]],
        h4[keys[-1]],
    ) is side:
        poi = _priority_source_poi_fast(
            indexed,
            h4,
            h4_keys,
            h4_opened_at=prior_open,
            side=side,
        )
        bars = _bars_between_fast(
            indexed,
            start=prior_open,
            end=h4[prior_open].closed_at,
        )
        if poi is not None and v6._poi_touch_index(bars, poi) is not None:
            return v6.H4ModelKind.C3_EXPANSION
    return None


def _opportunities_for_h4_fast(
    *,
    symbol: str,
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    h4: dict[datetime, Vt08IndexC2R1Bar],
    h4_keys: tuple[datetime, ...],
    h4_opened_at: datetime,
    side: DemoTradingSetupSide,
) -> tuple[r4.ExpandedOpportunity, ...]:
    h4_bar = h4.get(h4_opened_at.astimezone(UTC))
    if h4_bar is None:
        return ()
    pois = _source_pois_fast(
        indexed,
        h4,
        h4_keys,
        h4_opened_at=h4_opened_at,
        side=side,
    )
    if not pois:
        return ()

    bars = _bars_between_fast(
        indexed,
        start=h4_opened_at,
        end=h4_bar.closed_at,
    )
    if not bars:
        return ()
    model_kind = _completed_h4_model_fast(
        indexed,
        h4,
        h4_keys,
        current_h4_open=h4_opened_at,
        side=side,
    )
    if model_kind is None:
        model_kind = v6.H4ModelKind.SAME_C2

    result: list[r4.ExpandedOpportunity] = []
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
            built = r4._candidate_from_sequence(
                symbol=symbol,
                h4_bar=h4_bar,
                h4_opened_at=h4_opened_at,
                bars=bars,
                poi=poi,
                side=side,
                model_kind=model_kind,
                touch_index=touch_index,
            )
            if built is None:
                cursor = touch_index + 1
                continue
            signal, continuation_index = built
            result.append(
                r4.ExpandedOpportunity(
                    signal=signal,
                    source_poi_kind=poi.kind.value,
                    poi_touch_at=bars[touch_index].opened_at.astimezone(UTC),
                    rearm_index=rearm_index,
                )
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
    return tuple(deduped.values())


def _build_surface_5y(
    *,
    symbol: str,
    bars: Sequence[Vt08IndexC2R1Bar],
) -> tuple[r4.ExpandedOpportunity, ...]:
    indexed = {bar.opened_at.astimezone(UTC): bar for bar in bars}
    h4 = v6._build_h4(indexed)
    h4_keys = tuple(sorted(h4))
    side_cache: dict[date, DemoTradingSetupSide | None] = {}
    opportunities: list[r4.ExpandedOpportunity] = []
    for opened in h4_keys:
        local_date = opened.astimezone(_NY).date()
        if not (START_DATE <= local_date < END_DATE_EXCLUSIVE):
            continue
        if opened.astimezone(_NY).hour not in r4.V7_ANCHORS:
            continue
        if local_date not in side_cache:
            side_cache[local_date] = v7._daily_bias(indexed, before=opened)
        side = side_cache[local_date]
        if side is None:
            continue
        opportunities.extend(
            _opportunities_for_h4_fast(
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
        )
    )
    return tuple(opportunities)

def _frozen_admissions_5y(
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> tuple[v6.CandidateSignal, ...]:
    baseline_policy = r5.Policy(
        target_r=Decimal("2.5"),
        soft_close_loss_r=None,
        soft_close_until_mfe_r=None,
        deadline_bars=None,
        deadline_min_mfe_r=None,
        trail_name="OFF",
        trail_steps=(),
    )
    selected: list[v6.CandidateSignal] = []
    for symbol in r1.SYMBOLS:
        bars = bars_by_symbol[symbol]
        opened = tuple(bar.opened_at.astimezone(UTC) for bar in bars)
        candidates = [
            (
                item.signal,
                r5._manage_trade(
                    item.signal,
                    bars=bars,
                    opened=opened,
                    policy=baseline_policy,
                ),
            )
            for item in _build_surface_5y(symbol=symbol, bars=bars)
        ]
        last_exit: datetime | None = None
        for signal, outcome in sorted(
            candidates,
            key=lambda item: item[0].signal_at,
        ):
            if last_exit is not None and signal.signal_at < last_exit:
                continue
            selected.append(signal)
            last_exit = outcome.exited_at
    selected.sort(key=lambda signal: (signal.signal_at, signal.symbol))
    return tuple(selected)


def _frozen_policy_map() -> dict[str, r5.Policy]:
    policies = {policy.policy_id: policy for policy in r5._policy_grid()}
    result: dict[str, r5.Policy] = {}
    for cell, raw_payload in freeze.MANAGEMENT_BY_CELL.items():
        payload = cast(dict[str, object], raw_payload)
        policy_id = str(payload["policy_id"])
        policy = policies.get(policy_id)
        if policy is None:
            raise ValueError(f"frozen R6 policy missing from grid: {cell} {policy_id}")
        result[cell] = policy
    return result


def _managed_outcomes(
    signals: Sequence[v6.CandidateSignal],
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    opened_by_symbol: dict[str, tuple[datetime, ...]],
) -> tuple[r5.ManagedTrade, ...]:
    policy_by_cell = _frozen_policy_map()
    outcomes: list[r5.ManagedTrade] = []
    for signal in signals:
        cell = f"{signal.symbol}:{signal.side.value}"
        policy = policy_by_cell[cell]
        outcomes.append(
            r5._manage_trade(
                signal,
                bars=bars_by_symbol[signal.symbol],
                opened=opened_by_symbol[signal.symbol],
                policy=policy,
            )
        )
    return tuple(outcomes)


def _frozen_governor() -> r6.RiskGovernor:
    weights = cast(dict[str, str], freeze.RISK_GOVERNOR["market_weights"])
    return r6.RiskGovernor(
        nas100_weight=Decimal(weights["NAS100"]),
        sp500_weight=Decimal(weights["SP500"]),
        us30_weight=Decimal(weights["US30"]),
        warn_dd_r=Decimal(str(freeze.RISK_GOVERNOR["warn_dd_r"])),
        warn_multiplier=Decimal(str(freeze.RISK_GOVERNOR["warn_multiplier"])),
        hard_dd_r=Decimal(str(freeze.RISK_GOVERNOR["hard_dd_r"])),
        hard_multiplier=Decimal(str(freeze.RISK_GOVERNOR["hard_multiplier"])),
        loss_streak_trigger=int(
            str(freeze.RISK_GOVERNOR["loss_streak_trigger"])
        ),
        loss_streak_multiplier=Decimal(
            str(freeze.RISK_GOVERNOR["loss_streak_multiplier"])
        ),
    )


def _by_market(
    signals: Sequence[v6.CandidateSignal],
    values: Sequence[Decimal],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for symbol in r1.SYMBOLS:
        subset = tuple(
            value
            for signal, value in zip(signals, values, strict=True)
            if signal.symbol == symbol
        )
        result[symbol] = r6._basic_metrics(subset)
    return result


def _by_year(
    signals: Sequence[v6.CandidateSignal],
    values: Sequence[Decimal],
) -> dict[str, Any]:
    grouped: dict[int, list[Decimal]] = defaultdict(list)
    for signal, value in zip(signals, values, strict=True):
        grouped[signal.signal_at.astimezone(_NY).year].append(value)
    return {
        str(year): r6._basic_metrics(tuple(grouped[year]))
        for year in sorted(grouped)
    }


def _half_metrics(
    signals: Sequence[v6.CandidateSignal],
    values: Sequence[Decimal],
) -> dict[str, Any]:
    midpoint = datetime(2021, 3, 15, tzinfo=_NY)
    first = tuple(
        value
        for signal, value in zip(signals, values, strict=True)
        if signal.signal_at.astimezone(_NY) < midpoint
    )
    second = tuple(
        value
        for signal, value in zip(signals, values, strict=True)
        if signal.signal_at.astimezone(_NY) >= midpoint
    )
    return {
        "first_half": r6._basic_metrics(first),
        "second_half": r6._basic_metrics(second),
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]] = {}
    opened_by_symbol: dict[str, tuple[datetime, ...]] = {}
    provenance: dict[str, Any] = {}
    for symbol in r1.SYMBOLS:
        bars, source = _load_cibo_m15_5y(roots[symbol], symbol=symbol)
        bars_by_symbol[symbol] = bars
        opened_by_symbol[symbol] = tuple(
            bar.opened_at.astimezone(UTC) for bar in bars
        )
        provenance[symbol] = source

    signals = _frozen_admissions_5y(bars_by_symbol=bars_by_symbol)
    outcomes = _managed_outcomes(
        signals,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
    )
    governor = _frozen_governor()

    raw_primary = tuple(
        outcome.r_multiple - PRIMARY_STRESS for outcome in outcomes
    )
    raw_secondary = tuple(
        outcome.r_multiple - SECONDARY_STRESS for outcome in outcomes
    )
    governed_primary, primary_diag = r6._governed_values(
        signals,
        outcomes,
        governor=governor,
        stress=PRIMARY_STRESS,
    )
    governed_secondary, secondary_diag = r6._governed_values(
        signals,
        outcomes,
        governor=governor,
        stress=SECONDARY_STRESS,
    )

    primary_metrics = r6._basic_metrics(governed_primary)
    secondary_metrics = r6._basic_metrics(governed_secondary)
    density_pass = MIN_TRADES <= len(signals) <= MAX_TRADES
    performance_pass = (
        Decimal(str(primary_metrics["profit_factor"] or "0")) >= PRIMARY_PF_MIN
        and Decimal(str(primary_metrics["max_drawdown_r"])) <= PRIMARY_DD_MAX
        and Decimal(str(secondary_metrics["profit_factor"] or "0"))
        >= SECONDARY_PF_MIN
        and Decimal(str(secondary_metrics["max_drawdown_r"])) <= SECONDARY_DD_MAX
    )
    no_zero_risk = (
        int(primary_diag["zero_weight_trades"]) == 0
        and int(secondary_diag["zero_weight_trades"]) == 0
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate": {
            "candidate_id": freeze.CANDIDATE_ID,
            "rule_fingerprint": freeze.RULE_FINGERPRINT,
            "source_run_id": freeze.SOURCE_RUN_ID,
            "source_artifact_id": freeze.SOURCE_ARTIFACT_ID,
            "management_id": freeze.MANAGEMENT_ID,
            "governor_id": freeze.GOVERNOR_ID,
            "rules_changed_for_5y": False,
        },
        "window": {
            "start_date": START_DATE.isoformat(),
            "end_date_exclusive": END_DATE_EXCLUSIVE.isoformat(),
            "years": 5,
            "relation_to_tuning": "OUT_OF_TUNING",
            "fresh_certification_holdout": False,
            "historical_status": "PARTIALLY_CONSUMED_BY_PRIOR_VT08_RESEARCH",
        },
        "hard_contract": {
            "minimum_trades": MIN_TRADES,
            "maximum_trades": MAX_TRADES,
            "primary_pf_minimum": str(PRIMARY_PF_MIN),
            "primary_dd_max_r": str(PRIMARY_DD_MAX),
            "secondary_pf_minimum": str(SECONDARY_PF_MIN),
            "secondary_dd_max_r": str(SECONDARY_DD_MAX),
            "zero_risk_trades_allowed": False,
        },
        "trade_count": len(signals),
        "trade_count_by_market": {
            symbol: sum(signal.symbol == symbol for signal in signals)
            for symbol in r1.SYMBOLS
        },
        "raw_primary": r6._basic_metrics(raw_primary),
        "raw_secondary": r6._basic_metrics(raw_secondary),
        "governed_primary": primary_metrics,
        "governed_secondary": secondary_metrics,
        "governor_primary_diagnostics": primary_diag,
        "governor_secondary_diagnostics": secondary_diag,
        "governed_primary_by_market": _by_market(signals, governed_primary),
        "governed_secondary_by_market": _by_market(signals, governed_secondary),
        "governed_primary_by_year": _by_year(signals, governed_primary),
        "governed_secondary_by_year": _by_year(signals, governed_secondary),
        "governed_primary_halves": _half_metrics(signals, governed_primary),
        "governed_secondary_halves": _half_metrics(signals, governed_secondary),
        "decision": {
            "density_pass": density_pass,
            "performance_pass": performance_pass,
            "no_zero_risk_pass": no_zero_risk,
            "five_year_contract_pass": (
                density_pass and performance_pass and no_zero_risk
            ),
        },
        "provenance": provenance,
        "governance": {
            "research_validation_only": True,
            "candidate_frozen_before_replay": True,
            "retuning_permitted": False,
            "fresh_holdout_claim": False,
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
                "trade_count": report["trade_count"],
                "governed_primary": report["governed_primary"],
                "governed_secondary": report["governed_secondary"],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
