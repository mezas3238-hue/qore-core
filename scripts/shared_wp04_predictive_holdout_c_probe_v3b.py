"""Replacement one-shot collector for WP-04 V3B HOLDOUT_C.

HOLDOUT_A was consumed by a technical acquisition defect after its irreversible
marker. REPLICATION_B remains sealed and is not repurposed. HOLDOUT_C is a new
independent post-B window preregistered before acquisition.

This collector has no model/probe/economic access. It acquires only raw M1
market evidence for the exact frozen window and requires >=340 days of actual
bar span. The generic VT31 collector retains its 730-day default everywhere
else.
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

HOLDOUT_START = datetime(2024, 7, 15, tzinfo=UTC)
HOLDOUT_END_EXCLUSIVE = datetime(2025, 7, 14, tzinfo=UTC)
MINIMUM_COVERAGE_DAYS = 340
IDENTITY = "QORE_SHARED_WP04_PREDICTIVE_HOLDOUT_C_V3B_001"
PURPOSE = "WP04_V3B_REPLACEMENT_ONE_SHOT_HOLDOUT_C"


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
            "WP04 HOLDOUT_C market must be NAS100, SP500 or US30"
        )

    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        payload = collect_vt31_v2_m1_evidence(
            client,
            requested_opened_at=HOLDOUT_START,
            checked_at=HOLDOUT_END_EXCLUSIVE,
            market=market,
            minimum_coverage_days=MINIMUM_COVERAGE_DAYS,
        )
        coverage = payload.get("coverage")
        if not isinstance(coverage, dict):
            raise CTraderDemoLabProbeError("HOLDOUT_C coverage payload is invalid")
        first = datetime.fromisoformat(str(coverage["first_opened_at"]))
        last = datetime.fromisoformat(str(coverage["last_closed_at"]))
        if first < HOLDOUT_START:
            raise CTraderDemoLabProbeError(
                "HOLDOUT_C evidence begins before preregistered boundary"
            )
        if last > HOLDOUT_END_EXCLUSIVE:
            raise CTraderDemoLabProbeError(
                "HOLDOUT_C evidence crosses preregistered end boundary"
            )
        if (last - first).days < MINIMUM_COVERAGE_DAYS:
            raise CTraderDemoLabProbeError(
                "HOLDOUT_C evidence does not cover sufficient calendar span"
            )

        payload.update(
            {
                "evidence_purpose": PURPOSE,
                "shared_identity": IDENTITY,
                "holdout_partition": "REPLACEMENT_ONE_SHOT_HOLDOUT_C",
                "holdout_start_inclusive": HOLDOUT_START.isoformat(),
                "holdout_end_exclusive": HOLDOUT_END_EXCLUSIVE.isoformat(),
                "minimum_coverage_days": MINIMUM_COVERAGE_DAYS,
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
