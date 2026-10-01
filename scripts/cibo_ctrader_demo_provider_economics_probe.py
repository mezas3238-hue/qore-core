"""Collect sanitized cTrader DEMO provider-economics calibration evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ctrader_demo_provider_economics import (
    collect_ctrader_demo_provider_economics,
)
from qore.infrastructure.ctrader_demo_free_sink import (
    credentials_from_environment,
)
from qore.infrastructure.ctrader_open_api_client import (
    SpotwareCTraderOpenApiClient,
)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def build_report() -> dict[str, object]:
    client = SpotwareCTraderOpenApiClient(
        credentials=credentials_from_environment(),
    )
    try:
        probe = collect_ctrader_demo_provider_economics(client)
    finally:
        client.close()

    symbols = {}
    blockers: list[str] = []
    for row in probe.symbols:
        payload = _jsonable(asdict(row))
        symbols[row.qore_symbol] = payload
        if not row.margin_native_ready:
            blockers.append(f"{row.qore_symbol}:EXPECTED_MARGIN_INCOMPLETE")
        if not row.spread_native_ready:
            blockers.append(f"{row.qore_symbol}:SPREAD_UNAVAILABLE")
        if not row.commission_native_ready:
            blockers.append(f"{row.qore_symbol}:COMMISSION_TERMS_INCOMPLETE")

    provider_terms_ready = probe.provider_terms_ready
    status = (
        "PROVIDER_TERMS_READY_SLIPPAGE_CALIBRATION_PENDING"
        if provider_terms_ready
        else "PROVIDER_TERMS_INCOMPLETE"
    )
    account_fingerprint = hashlib.sha256(
        f"ctrader-demo:{probe.account_ref}".encode("utf-8")
    ).hexdigest()
    return {
        "schema": "qore.cibo.ctrader_demo.provider_economics_probe.v1",
        "status": status,
        "provider_key": "ctrader-demo",
        "environment": "demo",
        "account_fingerprint_sha256": account_fingerprint,
        "observed_at": probe.observed_at.isoformat(),
        "provider_terms_ready": provider_terms_ready,
        "slippage_empirically_calibrated": False,
        "execution_model_ready": False,
        "historical_exact_claimed": False,
        "holdout_outcomes_used": False,
        "target_aware": False,
        "broker_mutation_performed": False,
        "blockers": sorted(blockers),
        "symbols": symbols,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
