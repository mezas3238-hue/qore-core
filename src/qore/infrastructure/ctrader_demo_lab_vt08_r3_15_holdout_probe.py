"""One-time cTrader DEMO collector for the frozen VT-08 R3.15 holdout."""
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

HOLDOUT_ID = "VT08_R3_15_FINAL_INDEPENDENT_2020_2022"
ACQUISITION_OPENED_AT = datetime(2020, 6, 1, tzinfo=UTC)
EVALUATION_OPENED_AT = datetime(2020, 7, 1, tzinfo=UTC)
EVALUATION_CLOSED_AT = datetime(2022, 7, 1, tzinfo=UTC)
EXPECTED_SOURCE_CONTRACT_FINGERPRINT = (
    "403d54304f241f4a11b1ef847aa2a8b12d5ba6ffa2d9be5bb5cd9c19586943e3"
)


def _required_env(name: str, *aliases: str) -> str:
    for candidate in (name, *aliases):
        value = os.environ.get(candidate, "")
        if value:
            return value
    raise CTraderDemoLabProbeError(f"missing required environment input: {name}")


def validate_freeze() -> None:
    if (EVALUATION_CLOSED_AT - EVALUATION_OPENED_AT).days != 730:
        raise CTraderDemoLabProbeError("R3.15 holdout must be exactly 730 days")
    if ACQUISITION_OPENED_AT >= EVALUATION_OPENED_AT:
        raise CTraderDemoLabProbeError("warm-up must precede R3.15 evaluation")
    if source_contract_fingerprint() != EXPECTED_SOURCE_CONTRACT_FINGERPRINT:
        raise CTraderDemoLabProbeError("VT-08 source contract drifted before R3.15")


def main() -> None:
    validate_freeze()
    credentials = CTraderOpenApiCredentials(
        client_id=_required_env(
            "QORE_CTRADER_CLIENT_ID", "QORE_CTRADER_DEMO_CLIENT_ID"
        ),
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
            _required_env(
                "QORE_CTRADER_DEMO_ACCOUNT_ID", "QORE_CTRADER_ACCOUNT_ID"
            )
        ),
    )
    symbol = _required_env("QORE_DEMO_LAB_SYMBOL")
    software_sha = _required_env("QORE_SOFTWARE_SHA")
    if re.fullmatch(r"[0-9a-f]{40}", software_sha) is None:
        raise CTraderDemoLabProbeError("QORE_SOFTWARE_SHA must be exact")
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        evidence = collect_long_horizon_market_evidence(
            client,
            symbol_name=symbol,
            requested_opened_at=ACQUISITION_OPENED_AT,
            checked_at=EVALUATION_CLOSED_AT,
        )
        payload = evidence.sanitized_payload()
        payload.update(
            {
                "software_sha": software_sha,
                "holdout_id": HOLDOUT_ID,
                "fresh_holdout": True,
                "independent_validation_holdout": True,
                "source_contract_fingerprint": source_contract_fingerprint(),
                "acquisition_opened_at": ACQUISITION_OPENED_AT.isoformat(),
                "evaluation_opened_at": EVALUATION_OPENED_AT.isoformat(),
                "evaluation_closed_at": EVALUATION_CLOSED_AT.isoformat(),
                "evaluation_span_days": 730,
                "warmup_days": (
                    EVALUATION_OPENED_AT - ACQUISITION_OPENED_AT
                ).days,
                "coverage": _coverage_payload(evidence.bars),
            }
        )
        print(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
