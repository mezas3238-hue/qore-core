"""Direct-provider revalidation of true-2R historical M1 causal windows.

This research-only audit re-queries each frozen H1-open -> entry window and
compares the returned M1 timestamps with the immutable provider-native clone.
It never reads trade outcomes and never sends orders.

For every trade it requires a non-truncated provider response, exact timestamp
agreement between the retained clone and the fresh provider response, and the
entry minute present in both sources. Calendar minutes absent from both sources
are valid provider-semantic no-trendbar minutes.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.ctrader_open_api_client import SpotwareCTraderOpenApiClient
from qore.infrastructure.trader_lab import capitalizer_cibo_10y_m1_clone_v1 as clone
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_economic_rebase_2r_v1 as rebase,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import iter_cibo_m1
from qore.kernel.result import Failure

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_PROVIDER_BAR_REVALIDATION_2R_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_COGNITIVE_PROVIDER_BAR_REVALIDATION_2R_V1"
SOURCE_REBASE_RUN_ID = 36078677895
SOURCE_REBASE_SHA = "cfc04849c8bbfd6565310d89456f5e367ea880f7"
SOURCE_M1_RUN_ID = 35548099334
SOURCE_M1_SHA = "18c338aedd5013ce65a6cb6408ffbc2e904a6217"
REQUEST_THROTTLE_SECONDS = 0.22
EXPECTED_SYMBOLS = set(clone.TARGET_SYMBOLS)


class ProviderBarState(StrEnum):
    SUPPORTED_TRUE = "SUPPORTED_TRUE"
    SUPPORTED_FALSE = "SUPPORTED_FALSE"
    UNBOUND = "UNBOUND"


@dataclass(frozen=True, slots=True)
class ProviderBarRevalidationRow:
    symbol: str
    session: str
    operating_date: str
    h1_open: str
    entry_at: str
    expected_calendar_minutes: int
    frozen_clone_bars: int
    current_provider_bars: int
    shared_bars: int
    frozen_only_bars: int
    provider_only_bars: int
    frozen_missing_calendar_minutes: int
    provider_missing_calendar_minutes: int
    provider_has_more: bool
    frozen_entry_bar_present: bool
    provider_entry_bar_present: bool
    exact_timestamp_match: bool
    state: ProviderBarState
    current_trade_outcome_visible_to_binding: bool = False


def _aware(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be ISO timestamp string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    if parsed.second != 0 or parsed.microsecond != 0:
        raise ValueError(f"{field} must be minute-aligned")
    return parsed


def _minute(value: datetime) -> int:
    return int(value.timestamp() // 60)


def _load_rebase(root: Path) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    reports = sorted(root.rglob("capitalizer-cognitive-economic-rebase-2r-v1.json"))
    row_paths = sorted(root.rglob("capitalizer-cognitive-economic-rebase-2r-v1-rows.jsonl"))
    if len(reports) != 1 or len(row_paths) != 1:
        raise ValueError("provider revalidation requires one true-2R rebase artifact")
    report = json.loads(reports[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != rebase.IDENTITY:
        raise ValueError("unexpected true-2R rebase identity")

    rows: list[dict[str, Any]] = []
    with row_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("rebase row must be object")
            if raw.get("source_timestamps_causal") is not True:
                raise ValueError("provider revalidation rejects non-causal source row")
            rows.append(raw)
    if len(rows) != rebase.EXPECTED_TRADES:
        raise ValueError("provider revalidation rebase population mismatch")
    return report, tuple(rows)


def _resolve_clone_root(root: Path, *, symbol: str) -> Path:
    manifests = sorted(root.rglob("m1-clone-manifest.json"))
    if len(manifests) != 1:
        raise ValueError("provider revalidation requires one M1 clone manifest")
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("M1 clone manifest must be object")
    if str(manifest.get("canonical_symbol")) != symbol:
        raise ValueError("M1 clone symbol mismatch")
    if manifest.get("provider_native_m1") is not True:
        raise ValueError("provider-native M1 required")
    if manifest.get("synthetic_m1") is not False:
        raise ValueError("synthetic M1 forbidden")
    if manifest.get("interpolated_m1") is not False:
        raise ValueError("interpolated M1 forbidden")
    if int(manifest.get("contradictory_m1", -1)) != 0:
        raise ValueError("contradictory retained M1")
    return manifests[0].parent


def _window_minutes(opened: datetime, entry: datetime) -> tuple[int, int, int]:
    start = _minute(opened)
    end = _minute(entry)
    if end < start:
        raise ValueError("entry cannot precede H1 open")
    return start, end, end - start + 1


def _provider_window(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol: str,
    provider_symbol: str,
    symbol_id: int,
    digits: int,
    h1_open: datetime,
    entry_at: datetime,
) -> tuple[set[int], bool]:
    start, end, expected = _window_minutes(h1_open, entry_at)
    requested_end = entry_at + timedelta(minutes=1)
    result = client.request(
        "ProtoOAGetTrendbarsReq",
        {
            "ctidTraderAccountId": client.account_id,
            "fromTimestamp": int(h1_open.timestamp() * 1000),
            "period": clone.PERIOD_M1,
            "symbolId": symbol_id,
            "toTimestamp": int(requested_end.timestamp() * 1000) - 1,
            "count": expected + 2,
        },
        client_msg_id=f"capitalizer-bar-revalidation:{symbol}:{start}:{end}",
        timeout_seconds=60.0,
    )
    if isinstance(result, Failure):
        raise RuntimeError(f"provider M1 revalidation failed for {symbol}: {result.error}")

    response = result.value
    has_more = bool(getattr(response, "hasMore", False))
    native = tuple(cast(Iterable[object], getattr(response, "trendbar", ())))
    minutes: set[int] = set()
    for raw in native:
        bar = clone._provider_bar(
            raw,
            canonical_symbol=symbol,
            provider_symbol=provider_symbol,
            symbol_id=symbol_id,
            digits=digits,
        )
        observed = _minute(datetime.fromisoformat(bar.opened_at))
        if start <= observed <= end:
            minutes.add(observed)
    return minutes, has_more


def _compare(
    *,
    symbol: str,
    session: str,
    operating_date: str,
    h1_open: datetime,
    entry_at: datetime,
    frozen_minutes: set[int],
    provider_minutes: set[int],
    provider_has_more: bool,
) -> ProviderBarRevalidationRow:
    start, end, expected = _window_minutes(h1_open, entry_at)
    frozen = {minute for minute in frozen_minutes if start <= minute <= end}
    provider = {minute for minute in provider_minutes if start <= minute <= end}
    shared = frozen & provider
    frozen_only = frozen - provider
    provider_only = provider - frozen
    frozen_entry = end in frozen
    provider_entry = end in provider
    exact = frozen == provider

    if provider_has_more or not frozen_entry or not provider_entry:
        state = ProviderBarState.SUPPORTED_FALSE
    elif exact:
        state = ProviderBarState.SUPPORTED_TRUE
    else:
        state = ProviderBarState.UNBOUND

    return ProviderBarRevalidationRow(
        symbol=symbol,
        session=session,
        operating_date=operating_date,
        h1_open=h1_open.isoformat(),
        entry_at=entry_at.isoformat(),
        expected_calendar_minutes=expected,
        frozen_clone_bars=len(frozen),
        current_provider_bars=len(provider),
        shared_bars=len(shared),
        frozen_only_bars=len(frozen_only),
        provider_only_bars=len(provider_only),
        frozen_missing_calendar_minutes=expected - len(frozen),
        provider_missing_calendar_minutes=expected - len(provider),
        provider_has_more=provider_has_more,
        frozen_entry_bar_present=frozen_entry,
        provider_entry_bar_present=provider_entry,
        exact_timestamp_match=exact,
        state=state,
    )


def build_market_report(
    rebase_root: Path,
    m1_root: Path,
    *,
    symbol: str,
) -> tuple[dict[str, Any], tuple[ProviderBarRevalidationRow, ...]]:
    if symbol not in EXPECTED_SYMBOLS:
        raise ValueError("symbol outside Capitalizer universe")
    rebase_report, all_rows = _load_rebase(rebase_root)
    source_rows = tuple(row for row in all_rows if str(row["symbol"]) == symbol)
    if not source_rows:
        raise ValueError("no true-2R rows for symbol")

    native_root = _resolve_clone_root(m1_root, symbol=symbol)
    frozen_minutes = {_minute(bar.opened_at) for bar in iter_cibo_m1(native_root)}

    client = SpotwareCTraderOpenApiClient(
        credentials=clone._credentials(),
        request_timeout_seconds=30.0,
    )
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(f"cTrader DEMO authentication failed: {ready.error}")
        provider_symbol, symbol_id, digits = clone._selected_symbol(client, symbol)

        rows: list[ProviderBarRevalidationRow] = []
        for index, source in enumerate(source_rows):
            h1_open = _aware(source["h1_open"], field="h1_open")
            entry_at = _aware(source["entry_at"], field="entry_at")
            provider_minutes, has_more = _provider_window(
                client,
                symbol=symbol,
                provider_symbol=provider_symbol,
                symbol_id=symbol_id,
                digits=digits,
                h1_open=h1_open,
                entry_at=entry_at,
            )
            rows.append(
                _compare(
                    symbol=symbol,
                    session=str(source["session"]),
                    operating_date=str(source["operating_date"]),
                    h1_open=h1_open,
                    entry_at=entry_at,
                    frozen_minutes=frozen_minutes,
                    provider_minutes=provider_minutes,
                    provider_has_more=has_more,
                )
            )
            if index + 1 < len(source_rows):
                time.sleep(REQUEST_THROTTLE_SECONDS)
    finally:
        client.close()

    ordered = tuple(sorted(rows, key=lambda item: item.entry_at))
    counts = Counter(row.state.value for row in ordered)
    exact = sum(row.exact_timestamp_match for row in ordered)
    provider_has_more = sum(row.provider_has_more for row in ordered)
    semantic_gaps = sum(
        row.state is ProviderBarState.SUPPORTED_TRUE
        and row.frozen_missing_calendar_minutes > 0
        for row in ordered
    )
    report: dict[str, Any] = {
        "identity": IDENTITY,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "source_m1_sha": SOURCE_M1_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": "2.00",
        "symbol": symbol,
        "control_trades": len(ordered),
        "state_counts": {
            state.value: counts.get(state.value, 0) for state in ProviderBarState
        },
        "exact_timestamp_match_trades": exact,
        "provider_has_more_trades": provider_has_more,
        "provider_semantic_calendar_gap_trades": semantic_gaps,
        "provider_revalidated_all_trades": (
            counts.get(ProviderBarState.SUPPORTED_TRUE.value, 0) == len(ordered)
        ),
        "fresh_provider_query_used": True,
        "provider_count_exceeds_calendar_capacity": True,
        "provider_native_m1": True,
        "synthetic_m1_used": False,
        "interpolated_m1_used": False,
        "current_trade_outcome_visible_to_binding": False,
        "rebase_control_reproduced": int(rebase_report["control_trades"]) == len(all_rows),
        "strategy_rules_changed": False,
        "cognitive_rules_changed": False,
        "entry_changed": False,
        "stop_changed": False,
        "target_changed": False,
        "max3_changed": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }
    return report, ordered


def write_market(
    report: dict[str, Any],
    rows: tuple[ProviderBarRevalidationRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-cognitive-provider-bar-revalidation-2r-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def build_matrix(root: Path) -> dict[str, Any]:
    paths = sorted(
        path
        for path in root.rglob(
            "capitalizer-*-cognitive-provider-bar-revalidation-2r-v1.json"
        )
        if "nine-market" not in path.name
    )
    if len(paths) != 9:
        raise ValueError(f"provider revalidation matrix requires 9 reports, got {len(paths)}")
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    if {str(item["symbol"]) for item in reports} != EXPECTED_SYMBOLS:
        raise ValueError("provider revalidation universe mismatch")

    counts: Counter[str] = Counter()
    for item in reports:
        for state, value in dict(item["state_counts"]).items():
            counts[str(state)] += int(value)
    control = sum(int(item["control_trades"]) for item in reports)
    if control != rebase.EXPECTED_TRADES:
        raise ValueError("provider revalidation population mismatch")

    supported = counts[ProviderBarState.SUPPORTED_TRUE.value]
    globally_revalidated = supported == control
    return {
        "identity": MATRIX_IDENTITY,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "source_m1_sha": SOURCE_M1_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": "2.00",
        "market_count": 9,
        "control_trades": control,
        "state_counts": {
            state.value: counts.get(state.value, 0) for state in ProviderBarState
        },
        "provider_has_more_trades": sum(
            int(item["provider_has_more_trades"]) for item in reports
        ),
        "exact_timestamp_match_trades": sum(
            int(item["exact_timestamp_match_trades"]) for item in reports
        ),
        "provider_semantic_calendar_gap_trades": sum(
            int(item["provider_semantic_calendar_gap_trades"]) for item in reports
        ),
        "historical_bars_complete_provider_revalidated": globally_revalidated,
        "fresh_provider_query_used": True,
        "current_trade_outcome_visible_to_binding": False,
        "strategy_rules_changed": False,
        "cognitive_rules_changed": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "PROMOTE_PROVIDER_REVALIDATED_BARS_COMPLETE_TO_PERCEPTION_V2"
            if globally_revalidated
            else "INVESTIGATE_PROVIDER_HISTORY_DRIFT_OR_TRUNCATION"
        ),
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output
        / "capitalizer-nine-market-cognitive-provider-bar-revalidation-2r-v1.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("rebase_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    market.add_argument("--symbol", required=True, choices=sorted(EXPECTED_SYMBOLS))
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "market":
        report, rows = build_market_report(
            args.rebase_root,
            args.m1_root,
            symbol=args.symbol,
        )
        write_market(report, rows, args.output)
        print(json.dumps(report, sort_keys=True))
        return
    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
