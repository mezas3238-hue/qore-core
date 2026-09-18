"""One-time two-year calibration collector for VT31_NAS100.

The first successful acquisition opens the pre-CIBO window
[2014-04-19, 2016-04-19). From that moment the interval is permanently
CONSUMED_FOR_TUNING and may be reused for iterative calibration, but it must
never again be described as a fresh holdout.

This collector is NAS100-only and does not authorize live or production use.
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

CANDIDATE_ID = "VT31_NAS100_SPECIALIST_R1"
MARKET = "NAS100"
CALIBRATION_ID = "VT31_NAS100_2Y_CALIBRATION_001"
START_AT = datetime(2014, 4, 14, tzinfo=UTC)
END_EXCLUSIVE = datetime(2016, 4, 19, tzinfo=UTC)
REQUESTED_CALENDAR_DAYS = (END_EXCLUSIVE - START_AT).days
MINIMUM_CALENDAR_SPAN_DAYS = 700


def self_test() -> None:
    assert MARKET == "NAS100"
    assert START_AT < END_EXCLUSIVE
    assert REQUESTED_CALENDAR_DAYS == 736
    assert END_EXCLUSIVE == datetime(2016, 4, 19, tzinfo=UTC)


def main() -> None:
    import sys

    if sys.argv[1:] == ["--self-test"]:
        self_test()
        print(
            json.dumps(
                {
                    "candidate_id": CANDIDATE_ID,
                    "calibration_id": CALIBRATION_ID,
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
            raise CTraderDemoLabProbeError(
                "2Y calibration coverage payload is invalid"
            )
        first = datetime.fromisoformat(str(coverage["first_opened_at"]))
        last = datetime.fromisoformat(str(coverage["last_closed_at"]))
        if first < START_AT:
            raise CTraderDemoLabProbeError(
                "2Y evidence starts before calibration boundary"
            )
        if last > END_EXCLUSIVE:
            raise CTraderDemoLabProbeError(
                "2Y evidence crosses consumed CIBO boundary"
            )
        span_days = (last - first).days
        payload.update(
            {
                "evidence_purpose": CALIBRATION_ID,
                "candidate_id": CANDIDATE_ID,
                "market": MARKET,
                "calibration_start_at": START_AT.isoformat(),
                "calibration_end_exclusive": END_EXCLUSIVE.isoformat(),
                "requested_calendar_days": REQUESTED_CALENDAR_DAYS,
                "actual_calendar_span_days": span_days,
                "minimum_calendar_span_days": MINIMUM_CALENDAR_SPAN_DAYS,
                "coverage_sufficient": (
                    span_days >= MINIMUM_CALENDAR_SPAN_DAYS
                ),
                "opened_as_holdout_once": True,
                "consumed_for_tuning_after_this_run": True,
                "fresh_status_after_this_run": "CONSUMED_FOR_TUNING",
                "may_be_reused_for_iterative_calibration": True,
                "may_be_called_fresh_again": False,
                "final_certification_requires_other_unseen_evidence": True,
                "software_sha": software_sha,
                "live_authorized": False,
                "production_authorized": False,
            }
        )
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    finally:
        client.close()


if __name__ == "__main__":
    main()
