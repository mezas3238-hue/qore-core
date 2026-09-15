"""One-shot historical cTrader collector for frozen VT-31 R7 evidence."""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime, timedelta

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import _required_env
from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.ctrader_demo_lab_vt31_v2_probe import (
    _RESEARCH_MARKETS,
    collect_vt31_v2_m1_evidence,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)

FRESH_END_AT = datetime(2018, 5, 19, tzinfo=UTC)
FRESH_LOOKBACK_DAYS = 760
CANDIDATE_ID = "VT31_R7_SILVER_BULLET_RAID_RESOLUTION_001"


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
        raise CTraderDemoLabProbeError("QORE_SOFTWARE_SHA must be exact Git SHA")
    market = os.environ.get("QORE_DEMO_LAB_SYMBOL", "")
    if market not in _RESEARCH_MARKETS:
        raise CTraderDemoLabProbeError("fresh market must be NAS100, SP500 or US30")
    requested = FRESH_END_AT - timedelta(days=FRESH_LOOKBACK_DAYS)
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        payload = collect_vt31_v2_m1_evidence(
            client,
            requested_opened_at=requested,
            checked_at=FRESH_END_AT,
            market=market,
        )
        coverage = payload["coverage"]
        if not isinstance(coverage, dict):
            raise CTraderDemoLabProbeError("fresh coverage payload is invalid")
        first = datetime.fromisoformat(str(coverage["first_opened_at"]))
        last = datetime.fromisoformat(str(coverage["last_closed_at"]))
        if last > FRESH_END_AT:
            raise CTraderDemoLabProbeError("fresh evidence crosses consumed boundary")
        payload.update(
            {
                "evidence_purpose": "VT31_R7_ONE_SHOT_FRESH_VALIDATION",
                "fresh_partition_end_exclusive": FRESH_END_AT.isoformat(),
                "requested_lookback_days": FRESH_LOOKBACK_DAYS,
                "actual_calendar_span_days": (last - first).days,
                "historical_fresh_minimum_days": 730,
                "historical_fresh_coverage_sufficient": (last - first).days >= 730,
                "software_sha": software_sha,
                "candidate_id": CANDIDATE_ID,
            }
        )
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    finally:
        client.close()


if __name__ == "__main__":
    main()
