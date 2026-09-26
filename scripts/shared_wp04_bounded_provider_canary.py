"""Live provider canary for WP-04 bounded-window boundary semantics.

This canary reads only a previously consumed R5 interval. It exists to prove
that the repaired bounded-window contract works against the real cTrader
provider before any new fresh holdout is opened.

It does not evaluate targets, fit models, alter thresholds, or consume fresh
scientific evidence.
"""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime

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

CANARY_START = datetime(2022, 6, 13, 12, 0, tzinfo=UTC)
CANARY_END_EXCLUSIVE = datetime(2022, 6, 20, 12, 0, tzinfo=UTC)
MINIMUM_COVERAGE_DAYS = 5
IDENTITY = "QORE_SHARED_WP04_BOUNDED_PROVIDER_CANARY_001"
PURPOSE = "WP04_TECHNICAL_PROVIDER_BOUNDARY_CANARY_CONSUMED_R5"


def main() -> None:
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
        raise CTraderDemoLabProbeError("QORE_SOFTWARE_SHA must be exact Git SHA")

    market = os.environ.get("QORE_DEMO_LAB_SYMBOL", "")
    if market not in _RESEARCH_MARKETS:
        raise CTraderDemoLabProbeError(
            "WP04 provider canary market must be NAS100, SP500 or US30"
        )

    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        payload = collect_vt31_v2_m1_evidence(
            client,
            requested_opened_at=CANARY_START,
            checked_at=CANARY_END_EXCLUSIVE,
            market=market,
            minimum_coverage_days=MINIMUM_COVERAGE_DAYS,
        )
        coverage = payload.get("coverage")
        if not isinstance(coverage, dict):
            raise CTraderDemoLabProbeError("canary coverage payload is invalid")

        first = datetime.fromisoformat(str(coverage["first_opened_at"]))
        last = datetime.fromisoformat(str(coverage["last_closed_at"]))
        if first < CANARY_START:
            raise CTraderDemoLabProbeError(
                "canary evidence begins before consumed-window boundary"
            )
        if last > CANARY_END_EXCLUSIVE:
            raise CTraderDemoLabProbeError(
                "canary evidence crosses consumed-window end boundary"
            )
        if (last - first).days < MINIMUM_COVERAGE_DAYS:
            raise CTraderDemoLabProbeError(
                "canary evidence does not cover required consumed span"
            )

        print(
            json.dumps(
                {
                    "identity": IDENTITY,
                    "purpose": PURPOSE,
                    "market": market,
                    "consumed_r5_evidence_only": True,
                    "start_inclusive": CANARY_START.isoformat(),
                    "end_exclusive": CANARY_END_EXCLUSIVE.isoformat(),
                    "first_opened_at": first.isoformat(),
                    "last_closed_at": last.isoformat(),
                    "last_equals_end_exclusive": last == CANARY_END_EXCLUSIVE,
                    "boundary_contract_pass": True,
                    "fresh_scientific_evidence_consumed": False,
                    "model_or_probe_fit": False,
                    "target_outcomes_read": False,
                    "software_sha": software_sha,
                },
                sort_keys=True,
            )
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
