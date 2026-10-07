#!/usr/bin/env python3
"""Owner-designated single three-year NAS100 evidence collector for VT31.

The first successful acquisition creates the canonical contiguous 3Y base used
for current VT31 research. Once inspected or used to modify the strategy, this
base is consumed development evidence and must never be represented as fresh
independent certification evidence.

No R5/R6/R8 fold identity is used by this collector.
"""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import _required_env
from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.ctrader_demo_lab_vt31_v2_probe import (
    collect_vt31_v2_m1_evidence,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)

BASE_ID = "VT31_NAS100_OWNER_3Y_BASE_001"
MARKET = "NAS100"
START_AT = datetime(2023, 10, 1, tzinfo=UTC)
END_EXCLUSIVE = datetime(2026, 10, 1, tzinfo=UTC)
REQUESTED_CALENDAR_DAYS = (END_EXCLUSIVE - START_AT).days
MINIMUM_CALENDAR_SPAN_DAYS = 1080


def self_test() -> None:
    assert MARKET == "NAS100"
    assert START_AT < END_EXCLUSIVE
    assert REQUESTED_CALENDAR_DAYS == 1096
    assert END_EXCLUSIVE <= datetime(2026, 10, 7, tzinfo=UTC)


def main() -> None:
    import sys

    if sys.argv[1:] == ["--self-test"]:
        self_test()
        print(
            json.dumps(
                {
                    "base_id": BASE_ID,
                    "market": MARKET,
                    "start_at": START_AT.isoformat(),
                    "end_exclusive": END_EXCLUSIVE.isoformat(),
                    "requested_calendar_days": REQUESTED_CALENDAR_DAYS,
                },
                sort_keys=True,
            )
        )
        return

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
    software_sha = _required_env("QORE_SOFTWARE_SHA")
    if re.fullmatch(r"[0-9a-f]{40}", software_sha) is None:
        raise CTraderDemoLabProbeError(
            "QORE_SOFTWARE_SHA must be exact Git SHA"
        )

    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        payload = collect_vt31_v2_m1_evidence(
            client,
            requested_opened_at=START_AT,
            checked_at=END_EXCLUSIVE,
            market=MARKET,
        )
        coverage = payload.get("coverage")
        if not isinstance(coverage, dict):
            raise CTraderDemoLabProbeError("3Y base coverage payload is invalid")

        first = datetime.fromisoformat(str(coverage["first_opened_at"]))
        last = datetime.fromisoformat(str(coverage["last_closed_at"]))
        if first < START_AT:
            raise CTraderDemoLabProbeError(
                "3Y evidence starts before frozen base boundary"
            )
        if last > END_EXCLUSIVE:
            raise CTraderDemoLabProbeError(
                "3Y evidence crosses frozen base boundary"
            )

        span_days = (last - first).days
        payload.update(
            {
                "evidence_purpose": BASE_ID,
                "base_id": BASE_ID,
                "market": MARKET,
                "base_start_at": START_AT.isoformat(),
                "base_end_exclusive": END_EXCLUSIVE.isoformat(),
                "requested_calendar_days": REQUESTED_CALENDAR_DAYS,
                "actual_calendar_span_days": span_days,
                "minimum_calendar_span_days": MINIMUM_CALENDAR_SPAN_DAYS,
                "coverage_sufficient": (
                    span_days >= MINIMUM_CALENDAR_SPAN_DAYS
                ),
                "owner_designated_single_3y_base": True,
                "legacy_r5_r6_r8_operating_folds_used": False,
                "consumed_for_development_after_first_inspection": True,
                "fresh_status_after_first_inspection": (
                    "CONSUMED_OWNER_3Y_BASE"
                ),
                "may_be_called_fresh_again": False,
                "final_independent_certification_requires_other_unseen_evidence": True,
                "software_sha": software_sha,
                "live_authorized": False,
                "real_capital_authorized": False,
                "production_authorized": False,
            }
        )
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    finally:
        client.close()


if __name__ == "__main__":
    main()
