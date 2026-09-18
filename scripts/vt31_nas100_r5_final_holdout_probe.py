"""One-shot final fresh-holdout collector for frozen VT31_NAS100_R5.

The final certification interval is selected before acquisition and sits fully
after all consumed VT31/CIBO development evidence:

    [2022-07-18, 2024-07-18)

The first successful acquisition permanently consumes this interval as final
certification evidence.  It may never be called fresh again afterward.
"""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime

import vt31_nas100_r5_certification_candidate as candidate

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import _required_env
from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.ctrader_demo_lab_vt31_v2_probe import (
    collect_vt31_v2_m1_evidence,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)

HOLDOUT_ID = candidate.FINAL_HOLDOUT_ID
START_AT = datetime.fromisoformat(candidate.FINAL_HOLDOUT_START)
END_EXCLUSIVE = datetime.fromisoformat(candidate.FINAL_HOLDOUT_END_EXCLUSIVE)
REQUESTED_CALENDAR_DAYS = (END_EXCLUSIVE - START_AT).days
MINIMUM_CALENDAR_SPAN_DAYS = 730


def self_test() -> None:
    assert candidate.CANDIDATE_ID == "VT31_NAS100_R5"
    assert candidate.MARKET == "NAS100"
    assert START_AT == datetime(2022, 7, 18, tzinfo=UTC)
    assert END_EXCLUSIVE == datetime(2024, 7, 18, tzinfo=UTC)
    assert REQUESTED_CALENDAR_DAYS == 731
    assert START_AT > datetime(2022, 7, 15, tzinfo=UTC)


def main() -> None:
    import sys

    if sys.argv[1:] == ["--self-test"]:
        self_test()
        print(
            json.dumps(
                {
                    "candidate_id": candidate.CANDIDATE_ID,
                    "contract_fingerprint": candidate.contract_fingerprint(),
                    "holdout_id": HOLDOUT_ID,
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
            market=candidate.MARKET,
        )
        coverage = payload.get("coverage")
        if not isinstance(coverage, dict):
            raise CTraderDemoLabProbeError(
                "final holdout coverage payload is invalid"
            )
        first = datetime.fromisoformat(str(coverage["first_opened_at"]))
        last = datetime.fromisoformat(str(coverage["last_closed_at"]))
        if first < START_AT:
            raise CTraderDemoLabProbeError(
                "final holdout evidence predates sealed boundary"
            )
        if last > END_EXCLUSIVE:
            raise CTraderDemoLabProbeError(
                "final holdout evidence crosses sealed end boundary"
            )
        span_days = (last - first).days
        if span_days < MINIMUM_CALENDAR_SPAN_DAYS:
            raise CTraderDemoLabProbeError(
                "final holdout actual M1 span is below 730 days"
            )

        payload.update(
            {
                "evidence_purpose": HOLDOUT_ID,
                "candidate_id": candidate.CANDIDATE_ID,
                "candidate_contract_fingerprint": (
                    candidate.contract_fingerprint()
                ),
                "market": candidate.MARKET,
                "final_holdout_start_at": START_AT.isoformat(),
                "final_holdout_end_exclusive": END_EXCLUSIVE.isoformat(),
                "requested_calendar_days": REQUESTED_CALENDAR_DAYS,
                "actual_calendar_span_days": span_days,
                "minimum_calendar_span_days": MINIMUM_CALENDAR_SPAN_DAYS,
                "coverage_sufficient": True,
                "selected_before_open": True,
                "overlaps_consumed_vt31_cibo_evidence": False,
                "opened_once": True,
                "fresh_before_this_acquisition": True,
                "fresh_status_after_this_run": (
                    "CONSUMED_FINAL_CERTIFICATION_HOLDOUT"
                ),
                "may_be_called_fresh_again": False,
                "retuning_on_same_interval_allowed": False,
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
