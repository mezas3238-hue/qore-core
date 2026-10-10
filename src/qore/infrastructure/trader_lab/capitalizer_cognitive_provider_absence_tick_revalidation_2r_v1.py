"""Revalidate historical native-M1 absences against cTrader tick history.

The historical bar-completeness audit found exactly two AUDJPY decision spans
with five absent calendar M1 bars. cTrader does not create a trendbar when no
ticks arrive, so an absent calendar minute is not by itself evidence of corrupt
market data. This read-only audit queries BID and ASK tick history for every
absent minute and distinguishes:
- PROVIDER_NO_TICKS: zero BID and zero ASK ticks;
- CONTRADICTION_TICKS_WITHOUT_TRENDBAR: ticks exist despite the retained
  native-M1 clone lacking the corresponding trendbar.

No trade outcome or future decision evidence is read.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.ctrader_open_api_client import (
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cibo_10y_m1_clone_v1 as clone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_historical_bar_completeness_audit_2r_v1 as bars,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import iter_cibo_m1
from qore.kernel.result import Failure

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_PROVIDER_ABSENCE_TICK_REVALIDATION_2R_V1"
SOURCE_BAR_RUN_ID = 36174145194
SOURCE_BAR_SHA = "0595c3b9e22c381aba04a5c69ea9eb97065b6aa8"
SOURCE_M1_RUN_ID = 35548099334
SOURCE_M1_SHA = "18c338aedd5013ce65a6cb6408ffbc2e904a6217"
SYMBOL = "AUDJPY"
BID = 1
ASK = 2


@dataclass(frozen=True, slots=True)
class MissingMinuteTickEvidence:
    symbol: str
    entry_at: str
    minute: str
    bid_ticks: int
    ask_ticks: int
    bid_has_more: bool
    ask_has_more: bool
    provider_no_ticks: bool
    contradiction_ticks_without_trendbar: bool
    current_trade_outcome_visible_to_audit: bool = False


def _aware(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO timestamp string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    if parsed.second != 0 or parsed.microsecond != 0:
        raise ValueError(f"{field} must be minute-aligned")
    return parsed


def _load_unbound_rows(root: Path) -> tuple[dict[str, Any], ...]:
    reports = sorted(
        root.rglob(
            "capitalizer-audjpy-cognitive-historical-"
            "bar-completeness-audit-2r-v1.json"
        )
    )
    rows_paths = sorted(
        root.rglob(
            "capitalizer-audjpy-cognitive-historical-"
            "bar-completeness-audit-2r-v1-rows.jsonl"
        )
    )
    if len(reports) != 1 or len(rows_paths) != 1:
        raise ValueError("tick revalidation requires one AUDJPY bar audit artifact")
    report = json.loads(reports[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != bars.IDENTITY:
        raise ValueError("unexpected historical bar audit identity")
    if report.get("symbol") != SYMBOL:
        raise ValueError("tick revalidation requires AUDJPY")
    if int(report["hard_missing_entry_bar_trades"]) != 0:
        raise ValueError("hard missing entry bars must not be reclassified")
    if int(report["state_counts"]["UNBOUND"]) <= 0:
        raise ValueError("tick revalidation requires UNBOUND spans")

    selected: list[dict[str, Any]] = []
    with rows_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("historical bar row must be object")
            if raw.get("state") == bars.BarCompletenessState.UNBOUND.value:
                if raw.get("entry_bar_present") is not True:
                    raise ValueError("UNBOUND row unexpectedly lacks entry bar")
                selected.append(raw)
    if len(selected) != int(report["state_counts"]["UNBOUND"]):
        raise ValueError("UNBOUND row count drift")
    return tuple(selected)


def _observed_minutes(m1_root: Path) -> set[int]:
    native_root, manifest = bars._resolve_m1_root(m1_root, symbol=SYMBOL)
    if manifest.get("provider_native_m1") is not True:
        raise ValueError("tick revalidation requires native M1")
    return {bars._minute(item.opened_at) for item in iter_cibo_m1(native_root)}


def _missing_minutes(
    row: dict[str, Any],
    *,
    observed: set[int],
) -> tuple[datetime, ...]:
    start_at = _aware(row["h1_open"], field="h1_open")
    entry_at = _aware(row["entry_at"], field="entry_at")
    start = bars._minute(start_at)
    end = bars._minute(entry_at)
    missing = tuple(
        datetime.fromtimestamp(minute * 60, tz=start_at.tzinfo)
        for minute in range(start, end + 1)
        if minute not in observed
    )
    if len(missing) != int(row["missing_calendar_minutes"]):
        raise ValueError("missing-minute reconstruction drift")
    if end not in observed:
        raise ValueError("entry minute cannot be absent in UNBOUND row")
    return missing


def _tick_count(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol_id: int,
    minute: datetime,
    quote_type: int,
) -> tuple[int, bool]:
    start_ms = int(minute.timestamp() * 1000)
    end_ms = int((minute + timedelta(minutes=1)).timestamp() * 1000) - 1
    result = client.request(
        "ProtoOAGetTickDataReq",
        {
            "ctidTraderAccountId": client.account_id,
            "symbolId": symbol_id,
            "type": quote_type,
            "fromTimestamp": start_ms,
            "toTimestamp": end_ms,
        },
        client_msg_id=(
            f"capitalizer-tick-revalidation:{SYMBOL}:"
            f"{quote_type}:{start_ms}"
        ),
        timeout_seconds=30.0,
    )
    if isinstance(result, Failure):
        raise RuntimeError(f"historical tick request failed: {result.error}")
    payload = result.value
    ticks = tuple(cast(tuple[object, ...], getattr(payload, "tickData", ())))
    return len(ticks), bool(getattr(payload, "hasMore", False))


def build_report(
    bar_root: Path,
    m1_root: Path,
) -> tuple[dict[str, Any], tuple[MissingMinuteTickEvidence, ...]]:
    unbound = _load_unbound_rows(bar_root)
    observed = _observed_minutes(m1_root)

    credentials = clone._credentials()
    client = SpotwareCTraderOpenApiClient(
        credentials=credentials,
        request_timeout_seconds=30.0,
    )
    evidence: list[MissingMinuteTickEvidence] = []
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(f"cTrader DEMO authentication failed: {ready.error}")
        provider_symbol, symbol_id, _digits = clone._selected_symbol(client, SYMBOL)
        if provider_symbol != clone.PROVIDER_SYMBOL_MAP[SYMBOL]:
            raise ValueError("provider symbol mapping drift")

        for row in unbound:
            for minute in _missing_minutes(row, observed=observed):
                bid_count, bid_more = _tick_count(
                    client,
                    symbol_id=symbol_id,
                    minute=minute,
                    quote_type=BID,
                )
                ask_count, ask_more = _tick_count(
                    client,
                    symbol_id=symbol_id,
                    minute=minute,
                    quote_type=ASK,
                )
                no_ticks = bid_count == 0 and ask_count == 0
                evidence.append(
                    MissingMinuteTickEvidence(
                        symbol=SYMBOL,
                        entry_at=str(row["entry_at"]),
                        minute=minute.isoformat(),
                        bid_ticks=bid_count,
                        ask_ticks=ask_count,
                        bid_has_more=bid_more,
                        ask_has_more=ask_more,
                        provider_no_ticks=no_ticks,
                        contradiction_ticks_without_trendbar=not no_ticks,
                    )
                )
    finally:
        client.close()

    rows = tuple(sorted(evidence, key=lambda item: (item.entry_at, item.minute)))
    contradiction_count = sum(
        item.contradiction_ticks_without_trendbar for item in rows
    )
    no_tick_count = sum(item.provider_no_ticks for item in rows)
    expected_missing = sum(int(row["missing_calendar_minutes"]) for row in unbound)
    if len(rows) != expected_missing:
        raise ValueError("tick revalidation minute population mismatch")

    all_absences_explained = contradiction_count == 0 and no_tick_count == len(rows)
    report: dict[str, Any] = {
        "identity": IDENTITY,
        "source_bar_run_id": SOURCE_BAR_RUN_ID,
        "source_bar_sha": SOURCE_BAR_SHA,
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "source_m1_sha": SOURCE_M1_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "symbol": SYMBOL,
        "unbound_trade_spans": len(unbound),
        "missing_calendar_minutes": len(rows),
        "provider_no_tick_minutes": no_tick_count,
        "contradiction_ticks_without_trendbar_minutes": contradiction_count,
        "all_native_m1_absences_explained_by_no_ticks": all_absences_explained,
        "historical_bars_complete_semantically_bindable": all_absences_explained,
        "provider_tick_history_queried": True,
        "bid_and_ask_queried": True,
        "current_trade_outcome_visible_to_audit": False,
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
        "next_phase": (
            "PROMOTE_BARS_COMPLETE_BINDING_IN_PERCEPTION_V2"
            if all_absences_explained
            else "RETAIN_BARS_COMPLETE_UNBOUND_AND_REPAIR_NATIVE_M1_PROVENANCE"
        ),
    }
    return report, rows


def write_report(
    report: dict[str, Any],
    rows: tuple[MissingMinuteTickEvidence, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-cognitive-provider-absence-tick-revalidation-2r-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output
        / "capitalizer-cognitive-provider-absence-tick-revalidation-2r-v1-rows.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bar_root", type=Path)
    parser.add_argument("m1_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, rows = build_report(args.bar_root, args.m1_root)
    write_report(report, rows, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
