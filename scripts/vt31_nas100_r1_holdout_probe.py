"""One-shot sealed historical collector for VT31_NAS100_R1.

The period immediately precedes the consumed CIBO/VT31 region and was explicitly
kept unopened by the CIBO Eight-Ledger contract. Running this collector opens
and permanently consumes the interval for NAS100 R1 research.
"""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime

from qore.infrastructure.ctrader_demo_lab_long_horizon_probe import _required_env
from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.ctrader_demo_lab_vt31_v2_probe import collect_vt31_v2_m1_evidence
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)

CANDIDATE_ID = "VT31_NAS100_R1"
MARKET = "NAS100"
FRESH_START_AT = datetime(2015, 4, 19, tzinfo=UTC)
FRESH_END_EXCLUSIVE = datetime(2016, 4, 19, tzinfo=UTC)
MINIMUM_CALENDAR_SPAN_DAYS = 350


def self_test() -> None:
    assert CANDIDATE_ID == "VT31_NAS100_R1"
    assert MARKET == "NAS100"
    assert FRESH_START_AT < FRESH_END_EXCLUSIVE
    assert (FRESH_END_EXCLUSIVE - FRESH_START_AT).days == 366
    assert FRESH_END_EXCLUSIVE == datetime(2016, 4, 19, tzinfo=UTC)


def main() -> None:
    import sys

    if sys.argv[1:] == ["--self-test"]:
        self_test()
        print(
            json.dumps(
                {
                    "candidate_id": CANDIDATE_ID,
                    "market": MARKET,
                    "fresh_start_at": FRESH_START_AT.isoformat(),
                    "fresh_end_exclusive": FRESH_END_EXCLUSIVE.isoformat(),
                },
                sort_keys=True,
            )
        )
        return

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

    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        payload = collect_vt31_v2_m1_evidence(
            client,
            requested_opened_at=FRESH_START_AT,
            checked_at=FRESH_END_EXCLUSIVE,
            market=MARKET,
        )
        coverage = payload["coverage"]
        if not isinstance(coverage, dict):
            raise CTraderDemoLabProbeError("holdout coverage payload is invalid")
        first = datetime.fromisoformat(str(coverage["first_opened_at"]))
        last = datetime.fromisoformat(str(coverage["last_closed_at"]))
        if first < FRESH_START_AT:
            raise CTraderDemoLabProbeError("holdout evidence starts before sealed boundary")
        if last > FRESH_END_EXCLUSIVE:
            raise CTraderDemoLabProbeError("holdout evidence crosses consumed CIBO boundary")
        span_days = (last - first).days
        payload.update(
            {
                "evidence_purpose": "VT31_NAS100_R1_ONE_YEAR_HOLDOUT",
                "holdout_was_sealed_before_this_run": True,
                "holdout_is_permanently_consumed_after_this_run": True,
                "fresh_start_at": FRESH_START_AT.isoformat(),
                "fresh_end_exclusive": FRESH_END_EXCLUSIVE.isoformat(),
                "requested_calendar_days": (
                    FRESH_END_EXCLUSIVE - FRESH_START_AT
                ).days,
                "actual_calendar_span_days": span_days,
                "historical_holdout_minimum_days": MINIMUM_CALENDAR_SPAN_DAYS,
                "historical_holdout_coverage_sufficient": (
                    span_days >= MINIMUM_CALENDAR_SPAN_DAYS
                ),
                "software_sha": software_sha,
                "candidate_id": CANDIDATE_ID,
                "market": MARKET,
                "opens_new_holdout": True,
                "live_authorized": False,
                "production_authorized": False,
            }
        )
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    finally:
        client.close()


if __name__ == "__main__":
    main()
