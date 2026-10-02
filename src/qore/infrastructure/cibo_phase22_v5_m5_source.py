"""Full source-only M5 corpus collector for the next CIBO Phase22 exam.

The collector preserves canonical Market Atlas RAW_M5_LEDGER row identity while
binding the mechanically preregistered V5 candidate. It reads cTrader DEMO
trendbars only. No Trader methodology, policy decision, trade outcome or broker
mutation is executed here.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from time import sleep
from typing import cast

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_holdout_registry import (
    candidate_is_burn_clean_for_all_lineages,
)
from qore.infrastructure.cibo_phase22_v5_governance import (
    PHASE22_V5_CANDIDATE,
)
from qore.infrastructure.ctrader_open_api_client import (
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.trader_lab import (
    cibo_market_atlas_10y_m5_consumer_v1 as base,
)
from qore.kernel.result import Failure

IDENTITY = "CIBO_PHASE22_NEXT_EXAM_M5_SOURCE_V1"
REQUIRED_SYMBOLS = (
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "NAS100",
    "USDCAD",
    "USDJPY",
    "XAUUSD",
)
MAX_CALENDAR_M5_BARS_PER_CHUNK = (
    base.CHUNK_DAYS * 24 * 60 // base.PERIOD_M5
)


def v5_partition_grid() -> tuple[base.Partition, ...]:
    candidate = PHASE22_V5_CANDIDATE
    expected_start = datetime(2014, 4, 19, tzinfo=UTC)
    expected_end = datetime(2014, 10, 19, tzinfo=UTC)
    if (
        candidate.start_at != expected_start
        or candidate.end_exclusive_at != expected_end
    ):
        raise CiboCapitalManagementError(
            "next-exam V5 holdout window drift"
        )
    if not candidate_is_burn_clean_for_all_lineages(candidate):
        raise CiboCapitalManagementError(
            "next-exam V5 candidate is not burn-clean"
        )
    boundary = datetime(2014, 7, 19, tzinfo=UTC)
    return (
        base.Partition(
            "2014-v5-a",
            candidate.start_at,
            boundary,
        ),
        base.Partition(
            "2014-v5-b",
            boundary,
            candidate.end_exclusive_at,
        ),
    )


def read_strict_chunk(
    client: SpotwareCTraderOpenApiClient,
    *,
    account_id: int,
    symbol_id: int,
    opened_at: datetime,
    closed_at: datetime,
    client_msg_id: str,
) -> tuple[object, ...]:
    """Read one strict provider M5 window without count ambiguity."""

    sleep(base.REQUEST_PAUSE_SECONDS)
    result = client.request(
        "ProtoOAGetTrendbarsReq",
        {
            "ctidTraderAccountId": account_id,
            "fromTimestamp": int(opened_at.timestamp() * 1000),
            "period": base.PERIOD_M5,
            "symbolId": symbol_id,
            "toTimestamp": int(closed_at.timestamp() * 1000) - 1,
        },
        client_msg_id=client_msg_id,
        timeout_seconds=60.0,
    )
    if isinstance(result, Failure):
        raise RuntimeError(
            f"cTrader V5 M5 source read failed: {result.error}"
        )
    bars = tuple(
        cast(Iterable[object], getattr(result.value, "trendbar", ()))
    )
    if len(bars) > MAX_CALENDAR_M5_BARS_PER_CHUNK:
        raise RuntimeError(
            "provider returned more V5 M5 bars than calendar permits"
        )
    return bars


def consume_v5_symbol(
    canonical_symbol: str,
    output: Path,
) -> base.SymbolConsumptionManifest:
    if canonical_symbol not in REQUIRED_SYMBOLS:
        raise CiboCapitalManagementError(
            "symbol outside V5 holdout source scope"
        )
    candidate = PHASE22_V5_CANDIDATE
    if not candidate_is_burn_clean_for_all_lineages(candidate):
        raise CiboCapitalManagementError(
            "V5 source collection requires burn-clean candidate"
        )

    output.mkdir(parents=True, exist_ok=True)
    original_reader = base.__dict__["_read_chunk"]
    base.__dict__["_read_chunk"] = read_strict_chunk
    client = SpotwareCTraderOpenApiClient(
        credentials=base._credentials()
    )
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(
                f"cTrader DEMO authentication failed: {ready.error}"
            )
        (
            provider_symbol,
            symbol_id,
            digits,
            pip_position,
        ) = base._selected_symbol(
            client,
            canonical_symbol=canonical_symbol,
        )
        manifests = tuple(
            base._consume_partition(
                client,
                account_id=client.account_id,
                canonical_symbol=canonical_symbol,
                provider_symbol=provider_symbol,
                provider_symbol_id=symbol_id,
                digits=digits,
                pip_position=pip_position,
                partition=partition,
                output=output,
            )
            for partition in v5_partition_grid()
        )
    finally:
        client.close()
        base.__dict__["_read_chunk"] = original_reader

    if (
        not manifests
        or sum(item.retained_bars for item in manifests) <= 0
    ):
        raise CiboCapitalManagementError(
            "V5 M5 corpus is empty"
        )
    if any(
        item.raw_integrity_status != "CLEAN_PROVIDER_PAYLOAD"
        for item in manifests
    ):
        raise CiboCapitalManagementError(
            "V5 M5 corpus failed provider integrity"
        )

    observed = tuple(
        item
        for item in manifests
        if item.first_observed_m5 is not None
    )
    if not observed:
        raise CiboCapitalManagementError(
            "V5 M5 corpus has no observed partitions"
        )

    manifest = base.SymbolConsumptionManifest(
        schema=f"{base.SCHEMA}.phase22-v5-symbol",
        identity=base.IDENTITY,
        parent_identity=base.PARENT_IDENTITY,
        canonical_symbol=canonical_symbol,
        provider_symbol=provider_symbol,
        provider_symbol_id=symbol_id,
        digits=digits,
        pip_position=pip_position,
        target_start=candidate.start_at.isoformat(),
        target_end_exclusive=candidate.end_exclusive_at.isoformat(),
        earliest_observed_m5=observed[0].first_observed_m5,
        latest_observed_m5=observed[-1].last_observed_m5,
        retained_bars=sum(
            item.retained_bars for item in manifests
        ),
        partitions=tuple(
            asdict(item) for item in manifests
        ),
        raw_integrity_status="CLEAN_PROVIDER_PAYLOAD",
        expected_open_calendar_status=(
            "UNVERIFIED_PROVIDER_SESSION_CALENDAR"
        ),
        research_evidence_consumed=True,
        read_only=True,
        demo_eligible=False,
        live_authorized=False,
        real_capital_authorized=False,
        production_authorized=False,
    )
    base._write_json(
        output / "symbol-consumption-manifest.json",
        asdict(manifest),
    )
    base.write_root_hashes(output)

    payload = {
        "schema": "qore.cibo.phase22.next-exam-m5-source.v1",
        "identity": IDENTITY,
        "candidate_id": candidate.candidate_id,
        "window": {
            "start": candidate.start_at.isoformat(),
            "end_exclusive": candidate.end_exclusive_at.isoformat(),
        },
        "symbol": canonical_symbol,
        "market_atlas_row_identity": base.IDENTITY,
        "retained_bars": manifest.retained_bars,
        "raw_integrity_status": manifest.raw_integrity_status,
        "allowed_broker_request_types": [
            "ProtoOAGetTrendbarsReq",
            "ProtoOASymbolsListReq",
        ],
        "trader_logic_executed": False,
        "outcomes_inspected": False,
        "broker_mutation": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
        "productive_authority": False,
    }
    base._write_json(
        output / "phase22-v5-source-manifest.json",
        payload,
    )
    (output / "PHASE22_SHA256SUMS.txt").write_text(
        f"{base._sha256(output / 'symbol-consumption-manifest.json')}  "
        "symbol-consumption-manifest.json\n"
        f"{base._sha256(output / 'MANIFEST_SHA256SUMS.txt')}  "
        "MANIFEST_SHA256SUMS.txt\n"
        f"{base._sha256(output / 'phase22-v5-source-manifest.json')}  "
        "phase22-v5-source-manifest.json\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", choices=REQUIRED_SYMBOLS)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    manifest = consume_v5_symbol(args.symbol, args.output)
    print(json.dumps(asdict(manifest), sort_keys=True))


if __name__ == "__main__":
    main()
