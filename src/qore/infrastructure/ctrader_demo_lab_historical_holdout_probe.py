"""Preregistered historical cTrader DEMO collector for the VT-08 fresh holdout."""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import (
    _coverage_payload,
    collect_long_horizon_market_evidence,
)
from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.traders.vt08_b01_source_contract_r3_9 import (
    source_contract_fingerprint,
)

HOLDOUT_ID = "VT08_R3_10_FRESH_HOLDOUT_2022_2024"
ACQUISITION_OPENED_AT = datetime(2022, 7, 14, tzinfo=UTC)
EVALUATION_OPENED_AT = datetime(2022, 8, 13, tzinfo=UTC)
EVALUATION_CLOSED_AT = datetime(2024, 8, 12, tzinfo=UTC)
CONSUMED_BASELINE_BOUNDARY = datetime(2024, 8, 13, tzinfo=UTC)
EXPECTED_SOURCE_CONTRACT_FINGERPRINT = (
    "403d54304f241f4a11b1ef847aa2a8b12d5ba6ffa2d9be5bb5cd9c19586943e3"
)


def _required_env(name: str, *aliases: str) -> str:
    for candidate in (name, *aliases):
        value = os.environ.get(candidate, "")
        if value:
            return value
    raise CTraderDemoLabProbeError(f"missing required environment input: {name}")


def _validate_preregistration() -> None:
    if EVALUATION_CLOSED_AT - EVALUATION_OPENED_AT != (
        CONSUMED_BASELINE_BOUNDARY - EVALUATION_OPENED_AT
    ) - (CONSUMED_BASELINE_BOUNDARY - EVALUATION_CLOSED_AT):
        raise CTraderDemoLabProbeError("invalid holdout interval arithmetic")
    if (EVALUATION_CLOSED_AT - EVALUATION_OPENED_AT).days != 730:
        raise CTraderDemoLabProbeError("fresh holdout core must be exactly 730 days")
    if ACQUISITION_OPENED_AT >= EVALUATION_OPENED_AT:
        raise CTraderDemoLabProbeError("acquisition warm-up must precede evaluation")
    if EVALUATION_CLOSED_AT >= CONSUMED_BASELINE_BOUNDARY:
        raise CTraderDemoLabProbeError("fresh holdout overlaps consumed baseline boundary")
    fingerprint = source_contract_fingerprint()
    if fingerprint != EXPECTED_SOURCE_CONTRACT_FINGERPRINT:
        raise CTraderDemoLabProbeError("R3.9 source-contract fingerprint drifted")


def main() -> None:
    """Collect the frozen historical interval without moving either boundary."""
    _validate_preregistration()
    credentials = CTraderOpenApiCredentials(
        client_id=_required_env("QORE_CTRADER_CLIENT_ID", "QORE_CTRADER_DEMO_CLIENT_ID"),
        client_secret=_required_env(
            "QORE_CTRADER_CLIENT_SECRET", "QORE_CTRADER_DEMO_CLIENT_SECRET"
        ),
        access_token=_required_env(
            "QORE_CTRADER_ACCESS_TOKEN", "QORE_CTRADER_DEMO_ACCESS_TOKEN"
        ),
        refresh_token=_required_env(
            "QORE_CTRADER_REFRESH_TOKEN", "QORE_CTRADER_DEMO_REFRESH_TOKEN"
        ),
        ctid_trader_account_id=int(
            _required_env("QORE_CTRADER_DEMO_ACCOUNT_ID", "QORE_CTRADER_ACCOUNT_ID")
        ),
    )
    symbol_name = _required_env("QORE_DEMO_LAB_SYMBOL")
    software_sha = _required_env("QORE_SOFTWARE_SHA")
    if re.fullmatch(r"[0-9a-f]{40}", software_sha) is None:
        raise CTraderDemoLabProbeError(
            "QORE_SOFTWARE_SHA must be the exact lowercase 40-character Git SHA"
        )

    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        evidence = collect_long_horizon_market_evidence(
            client,
            symbol_name=symbol_name,
            requested_opened_at=ACQUISITION_OPENED_AT,
            checked_at=EVALUATION_CLOSED_AT,
        )
        payload = evidence.sanitized_payload()
        payload["software_sha"] = software_sha
        payload["holdout_id"] = HOLDOUT_ID
        payload["fresh_holdout"] = True
        payload["source_contract_fingerprint"] = source_contract_fingerprint()
        payload["acquisition_opened_at"] = ACQUISITION_OPENED_AT.isoformat()
        payload["evaluation_opened_at"] = EVALUATION_OPENED_AT.isoformat()
        payload["evaluation_closed_at"] = EVALUATION_CLOSED_AT.isoformat()
        payload["consumed_baseline_boundary"] = CONSUMED_BASELINE_BOUNDARY.isoformat()
        payload["evaluation_span_days"] = 730
        payload["warmup_days"] = (
            EVALUATION_OPENED_AT - ACQUISITION_OPENED_AT
        ).days
        payload["no_consumed_baseline_overlap"] = (
            EVALUATION_CLOSED_AT < CONSUMED_BASELINE_BOUNDARY
        )
        payload["coverage"] = _coverage_payload(evidence.bars)
        print(
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
