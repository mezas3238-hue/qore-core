"""Read-only cTrader DEMO acquisition for the VT-08 Index V3 older holdout."""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime, timedelta

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import _required_env
from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.ctrader_demo_lab_vt08_v2_probe import collect_vt08_v2_evidence
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)

FROZEN_LOOKBACK_DAYS = 1460


def frozen_lookback_days(value: str | None) -> int:
    raw = str(FROZEN_LOOKBACK_DAYS) if value is None else value
    try:
        result = int(raw)
    except ValueError as error:
        raise CTraderDemoLabProbeError("VT-08 Index V3 lookback must be integer") from error
    if result != FROZEN_LOOKBACK_DAYS:
        raise CTraderDemoLabProbeError("VT-08 Index V3 lookback must equal 1460 days")
    return result


def main() -> None:
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
    software_sha = _required_env("QORE_SOFTWARE_SHA")
    if re.fullmatch(r"[0-9a-f]{40}", software_sha) is None:
        raise CTraderDemoLabProbeError("QORE_SOFTWARE_SHA must be exact lowercase Git SHA")
    canonical_symbol = _required_env("QORE_DEMO_LAB_SYMBOL")
    lookback_days = frozen_lookback_days(os.environ.get("QORE_DEMO_LAB_LOOKBACK_DAYS"))
    checked_at = datetime.now(UTC)
    requested_opened_at = checked_at - timedelta(days=lookback_days)
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        payload = collect_vt08_v2_evidence(
            client,
            canonical_symbol=canonical_symbol,
            requested_opened_at=requested_opened_at,
            checked_at=checked_at,
        )
        payload["requested_lookback_days"] = lookback_days
        payload["software_sha"] = software_sha
        payload["v3_holdout_acquisition"] = {
            "candidate_id": "VT08_INDEX_V3_QORE_GEOMETRY_001",
            "holdout_start_new_york": "2022-09-15",
            "holdout_end_exclusive_new_york": "2023-09-15",
            "freshness_claim": "unseen-before-v3-freeze",
        }
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
