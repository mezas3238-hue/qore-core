"""GitHub-hosted read-only bootstrap for CIBO Phase20D forward collection.

This probe proves that the exact CIBO branch can authenticate to the authorized
cTrader DEMO account, resolve every account-wide CIBO contract and collect
provider-native closed market data without mutating broker state.

It is deliberately NOT Phase20D qualification evidence: no order is submitted,
no fill or settlement is invented, and fresh forward decision/outcome counts
remain zero.  Its purpose is to remove connectivity/credential uncertainty
before a separately governed DEMO execution collector is activated.
"""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime, timedelta

from qore.infrastructure.ctrader_demo_free_binding import (  # type: ignore[import-untyped]
    binding_fingerprint,
    discover_free_account_binding,
)
from qore.infrastructure.ctrader_demo_lab_probe import (  # type: ignore[import-untyped]
    collect_ctrader_demo_lab_market_evidence,
)
from qore.infrastructure.ctrader_open_api_client import (  # type: ignore[import-untyped]
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)

_REQUIRED_QORE_SYMBOLS = (
    "AUDJPY",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "NAS100",
    "XAUUSD",
)
_REQUIRED_CMA_LINEAGES = (
    "VT08_FOREX",
    "R34_XAUUSD",
    "R38_EURUSD",
    "R43_GBPUSD",
    "R38_GBPJPY",
    "R42_AUDJPY",
    "VT31_NAS100",
)
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


def _required_env(name: str, *aliases: str) -> str:
    for candidate in (name, *aliases):
        value = os.environ.get(candidate, "")
        if value:
            return value
    raise RuntimeError(f"missing required environment input: {name}")


def _git_sha() -> str:
    value = _required_env("GITHUB_SHA").strip()
    if _SHA1_RE.fullmatch(value) is None:
        raise RuntimeError("GITHUB_SHA must be lowercase 40-hex")
    return value


def _lookback_days() -> int:
    raw = os.environ.get("QORE_CIBO_FORWARD_BOOTSTRAP_LOOKBACK_DAYS", "30")
    try:
        value = int(raw)
    except ValueError as error:
        raise RuntimeError("bootstrap lookback must be int") from error
    if value < 7 or value > 90:
        raise RuntimeError("bootstrap lookback must be between 7 and 90 days")
    return value


def main() -> None:
    checked_at = datetime.now(UTC)
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
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        binding = discover_free_account_binding(client, bound_at=checked_at)
        contracts = {
            item.qore_symbol: item for item in binding.contracts
        }
        if tuple(sorted(contracts)) != _REQUIRED_QORE_SYMBOLS:
            raise RuntimeError(
                "cTrader DEMO binding does not cover exact CIBO symbol set"
            )

        account_fingerprint: str | None = None
        market: list[dict[str, object]] = []
        opened_at = checked_at - timedelta(days=_lookback_days())
        for qore_symbol in _REQUIRED_QORE_SYMBOLS:
            contract = contracts[qore_symbol]
            evidence = collect_ctrader_demo_lab_market_evidence(
                client,
                symbol_name=contract.symbol_name,
                opened_at=opened_at,
                checked_at=checked_at,
            )
            if evidence.symbol.symbol_id != contract.symbol_id:
                raise RuntimeError(
                    f"binding/evidence symbol id mismatch: {qore_symbol}"
                )
            if account_fingerprint is None:
                account_fingerprint = evidence.account_fingerprint
            elif evidence.account_fingerprint != account_fingerprint:
                raise RuntimeError(
                    "cTrader DEMO account fingerprint drift across symbols"
                )

            payload = evidence.sanitized_payload()
            periods = payload["periods"]
            if not isinstance(periods, dict):
                raise RuntimeError("market evidence periods must be object")
            period_summary: dict[str, dict[str, object]] = {}
            for period in ("M1", "M5", "M15", "H4"):
                rows = periods.get(period)
                if not isinstance(rows, list) or not rows:
                    raise RuntimeError(
                        f"missing closed {period} evidence for {qore_symbol}"
                    )
                latest = rows[-1]
                if not isinstance(latest, dict):
                    raise RuntimeError("latest trendbar must be object")
                period_summary[period] = {
                    "closed_bars": len(rows),
                    "latest_closed_at": latest.get("closed_at"),
                }

            market.append(
                {
                    "qore_symbol": qore_symbol,
                    "provider_symbol": contract.symbol_name,
                    "symbol_id": contract.symbol_id,
                    "digits": contract.digits,
                    "min_volume_units": contract.min_volume_units,
                    "max_volume_units": contract.max_volume_units,
                    "step_volume_units": contract.step_volume_units,
                    "lot_size_units": format(
                        contract.lot_size_units,
                        "f",
                    ),
                    "periods": period_summary,
                }
            )

        if account_fingerprint is None:
            raise RuntimeError("cTrader DEMO account fingerprint unavailable")

        report = {
            "schema": "qore.cibo.phase20d.github_forward_bootstrap.v1",
            "status": "READ_ONLY_MARKET_BOOTSTRAP_READY",
            "git_sha": _git_sha(),
            "checked_at": checked_at.isoformat(),
            "environment": "demo",
            "read_only": True,
            "broker_mutation_performed": False,
            "account_fingerprint": account_fingerprint,
            "binding_fingerprint": binding_fingerprint(binding),
            "required_cma_lineages": list(_REQUIRED_CMA_LINEAGES),
            "required_qore_symbols": list(_REQUIRED_QORE_SYMBOLS),
            "market": market,
            "phase20d": {
                "fresh_forward_decisions_claimed": 0,
                "candidate_outcomes_claimed": 0,
                "selected_outcomes_claimed": 0,
                "qualification_evidence_claimed": False,
                "execution_evidence_ready": False,
                "blockers": [
                    "DEMO_EXECUTION_FORWARD_COLLECTOR_NOT_ACTIVATED"
                ],
            },
            "governance": {
                "fundednext_touched": False,
                "vps_touched": False,
                "live_authorized": False,
                "real_capital_authorized": False,
                "merge_authorized": False,
            },
        }
        print(
            json.dumps(
                report,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
