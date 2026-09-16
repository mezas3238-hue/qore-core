"""One-shot read-only cTrader DEMO acquisition for the VT-08 Index V7 holdout."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import _required_env
from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.ctrader_demo_lab_vt08_v2_probe import collect_vt08_v2_evidence
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)

CANDIDATE_ID = "VT08_INDEX_V7_TTRADES_SOURCE_CORRECTED_001"
_NY = ZoneInfo("America/New_York")
ACQUISITION_START_NY = datetime(2018, 8, 1, 0, 0, tzinfo=_NY)
HOLDOUT_START_NY = datetime(2018, 9, 15, 0, 0, tzinfo=_NY)
HOLDOUT_END_EXCLUSIVE_NY = datetime(2020, 9, 15, 0, 0, tzinfo=_NY)


def fixed_acquisition_window_utc() -> tuple[datetime, datetime]:
    return ACQUISITION_START_NY.astimezone(UTC), HOLDOUT_END_EXCLUSIVE_NY.astimezone(UTC)


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
    requested_opened_at, checked_at = fixed_acquisition_window_utc()

    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        payload = collect_vt08_v2_evidence(
            client,
            canonical_symbol=canonical_symbol,
            requested_opened_at=requested_opened_at,
            checked_at=checked_at,
        )
        payload["software_sha"] = software_sha
        payload["v7_holdout_acquisition"] = {
            "candidate_id": CANDIDATE_ID,
            "acquisition_start_new_york": ACQUISITION_START_NY.date().isoformat(),
            "holdout_start_new_york": HOLDOUT_START_NY.date().isoformat(),
            "holdout_end_exclusive_new_york": HOLDOUT_END_EXCLUSIVE_NY.date().isoformat(),
            "requested_data_after_holdout_end": False,
            "freshness_claim": "unseen-before-v7-freeze",
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
