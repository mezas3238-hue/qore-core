"""Run the WP-05 post-V14 source-only cTrader provider catalogue audit."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from qore.infrastructure.core_stack_v2.active_perception_post_v14_sensor_catalog import (
    POST_V14_PROVIDER_CATALOG_IDENTITY,
    freeze_enabled_provider_catalog,
    provider_catalog_sha256,
)
from qore.infrastructure.ctrader_demo_lab_probe import (
    compute_ctrader_demo_lab_account_fingerprint,
)
from qore.infrastructure.ctrader_historical_tick_collector import (
    CTraderHistoricalReadOnlyMessageClient,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    CTraderOpenApiPermissionScope,
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure


class PostV14ProviderCatalogAuditError(RuntimeError):
    """The post-V14 provider catalogue audit failed closed."""


def _required_env(name: str, *aliases: str) -> str:
    for candidate in (name, *aliases):
        value = os.environ.get(candidate, "")
        if value:
            return value
    raise PostV14ProviderCatalogAuditError(
        f"missing required environment input: {name}"
    )


def _enabled_rows(
    client: CTraderHistoricalReadOnlyMessageClient,
) -> tuple[tuple[int, str, bool], ...]:
    listed = client.request(
        "ProtoOASymbolsListReq",
        {
            "ctidTraderAccountId": client.account_id,
            "includeArchivedSymbols": False,
        },
        client_msg_id="wp05-post-v14-provider-catalogue",
        timeout_seconds=10.0,
    )
    if isinstance(listed, Failure):
        raise PostV14ProviderCatalogAuditError(
            "cTrader enabled-symbol catalogue request failed"
        )
    if getattr(listed.value, "ctidTraderAccountId", None) != client.account_id:
        raise PostV14ProviderCatalogAuditError(
            "cTrader enabled-symbol catalogue account mismatch"
        )
    native_symbols = getattr(listed.value, "symbol", None)
    if native_symbols is None:
        raise PostV14ProviderCatalogAuditError(
            "cTrader enabled-symbol catalogue missing"
        )

    rows: list[tuple[int, str, bool]] = []
    for item in native_symbols:
        enabled = getattr(item, "enabled", None)
        symbol_id = getattr(item, "symbolId", None)
        symbol_name = getattr(item, "symbolName", None)
        if enabled is not True:
            continue
        if type(symbol_id) is not int:
            raise PostV14ProviderCatalogAuditError(
                "enabled provider symbol id is invalid"
            )
        if not isinstance(symbol_name, str):
            raise PostV14ProviderCatalogAuditError(
                "enabled provider symbol name is invalid"
            )
        rows.append((symbol_id, symbol_name, True))
    return tuple(rows)


def run(*, output_path: Path) -> dict[str, Any]:
    credentials = CTraderOpenApiCredentials(
        client_id=_required_env(
            "QORE_CTRADER_CLIENT_ID",
            "QORE_CTRADER_DEMO_CLIENT_ID",
        ),
        client_secret=_required_env(
            "QORE_CTRADER_CLIENT_SECRET",
            "QORE_CTRADER_DEMO_CLIENT_SECRET",
        ),
        access_token=_required_env(
            "QORE_CTRADER_ACCESS_TOKEN",
            "QORE_CTRADER_DEMO_ACCESS_TOKEN",
        ),
        refresh_token=_required_env(
            "QORE_CTRADER_REFRESH_TOKEN",
            "QORE_CTRADER_DEMO_REFRESH_TOKEN",
        ),
        ctid_trader_account_id=int(
            _required_env(
                "QORE_CTRADER_DEMO_ACCOUNT_ID",
                "QORE_CTRADER_ACCOUNT_ID",
            )
        ),
    )
    native_client = SpotwareCTraderOpenApiClient(
        credentials=credentials,
        required_permission_scope=CTraderOpenApiPermissionScope.TRADE,
    )
    read_only_client = CTraderHistoricalReadOnlyMessageClient(native_client)

    try:
        ready = read_only_client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise PostV14ProviderCatalogAuditError(
                "cTrader DEMO authentication failed for source-only catalogue"
            )
        entries = freeze_enabled_provider_catalog(
            _enabled_rows(read_only_client)
        )
        report: dict[str, Any] = {
            "identity": POST_V14_PROVIDER_CATALOG_IDENTITY,
            "partition": "provider_catalog_source_only",
            "enabled_symbol_count": len(entries),
            "provider_catalog_sha256": provider_catalog_sha256(entries),
            "enabled_symbols": [
                {
                    "provider_symbol_id": item.provider_symbol_id,
                    "provider_symbol": item.provider_symbol,
                    "normalized_symbol": item.normalized_symbol,
                }
                for item in entries
            ],
            "ustec_control_present": any(
                item.provider_symbol == "USTEC" for item in entries
            ),
            "account_fingerprint": compute_ctrader_demo_lab_account_fingerprint(
                read_only_client.account_id
            ),
            "permission_scope_required": "trade",
            "read_only_message_firewall": True,
            "candidate_selection_performed": False,
            "historical_market_data_read": False,
            "target_or_outcome_read": False,
            "r6_r5_read": False,
            "fresh_holdout_opened": False,
            "scientific_v15_opened": False,
            "shared_methodology_authority": False,
            "shared_sizing_authority": False,
            "shared_risk_authority": False,
            "shared_order_authority": False,
            "shared_execution_authority": False,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        return report
    finally:
        read_only_client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(output_path=args.output)
    print(
        json.dumps(
            {
                "identity": report["identity"],
                "enabled_symbol_count": report["enabled_symbol_count"],
                "provider_catalog_sha256": report["provider_catalog_sha256"],
                "ustec_control_present": report["ustec_control_present"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
