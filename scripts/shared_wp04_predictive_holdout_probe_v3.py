"""Pre-registered historical collector for WP-04 V3 HOLDOUT_A.

This collector is intentionally separate from the evaluation code. It acquires
only the preregistered post-R5 interval and has no access to model targets,
probe coefficients, economic outcomes, trader identity, LIVE or production.

The collector is not invoked by push. A holdout workflow may call it only after
the consumed predictive probe-freeze gate has passed and an immutable one-shot
marker has been created.
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

HOLDOUT_START = datetime(2022, 7, 18, tzinfo=UTC)
HOLDOUT_END_EXCLUSIVE = datetime(2023, 7, 17, tzinfo=UTC)
IDENTITY = "QORE_SHARED_WP04_PREDICTIVE_HOLDOUT_A_V3_001"
PURPOSE = "WP04_V3_ONE_SHOT_HOLDOUT_A"


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
            "WP04 holdout lab market must be NAS100, SP500 or US30"
        )

    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        payload = collect_vt31_v2_m1_evidence(
            client,
            requested_opened_at=HOLDOUT_START,
            checked_at=HOLDOUT_END_EXCLUSIVE,
            market=market,
        )
        coverage = payload.get("coverage")
        if not isinstance(coverage, dict):
            raise CTraderDemoLabProbeError("holdout coverage payload is invalid")
        first = datetime.fromisoformat(str(coverage["first_opened_at"]))
        last = datetime.fromisoformat(str(coverage["last_closed_at"]))
        if first < HOLDOUT_START:
            raise CTraderDemoLabProbeError(
                "holdout evidence begins before preregistered boundary"
            )
        if last >= HOLDOUT_END_EXCLUSIVE:
            raise CTraderDemoLabProbeError(
                "holdout evidence crosses preregistered end boundary"
            )
        if (last - first).days < 340:
            raise CTraderDemoLabProbeError(
                "holdout evidence does not cover sufficient calendar span"
            )

        payload.update(
            {
                "evidence_purpose": PURPOSE,
                "shared_identity": IDENTITY,
                "holdout_partition": "ONE_SHOT_HOLDOUT_A",
                "holdout_start_inclusive": HOLDOUT_START.isoformat(),
                "holdout_end_exclusive": HOLDOUT_END_EXCLUSIVE.isoformat(),
                "software_sha": software_sha,
                "representation_refit_allowed": False,
                "probe_refit_allowed": False,
                "threshold_retuning_allowed": False,
                "runtime_future_information_allowed": False,
                "knowledge_auto_promotion": False,
                "live_authorized": False,
                "production_authorized": False,
                "real_capital_authorized": False,
                "merge_authorized": False,
            }
        )
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    finally:
        client.close()


if __name__ == "__main__":
    main()
