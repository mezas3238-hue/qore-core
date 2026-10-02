"""Independent TEMPORAL_REPLICATION_D collector for WP-04 V3B.

The D window was frozen before HOLDOUT_E acquisition. D may be opened only
after HOLDOUT_E passes. It uses the exact same V3 representation, V3B probes
and fresh gate. This collector reads raw M1 market evidence only and has no
model, probe, target, economic or trading authority.
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

REPLICATION_START = datetime(2025, 7, 14, tzinfo=UTC)
REPLICATION_END_EXCLUSIVE = datetime(2026, 7, 13, tzinfo=UTC)
MINIMUM_COVERAGE_DAYS = 340
IDENTITY = "QORE_SHARED_WP04_PREDICTIVE_REPLICATION_D_V3B_001"
PURPOSE = "WP04_V3B_TEMPORAL_REPLICATION_D"


def main() -> None:
    if os.environ.get("QORE_WP04_HOLDOUT_E_PASS") != "1":
        raise CTraderDemoLabProbeError(
            "REPLICATION_D is sealed until HOLDOUT_E PASS is explicitly bound"
        )

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
            "WP04 REPLICATION_D market must be NAS100, SP500 or US30"
        )

    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        payload = collect_vt31_v2_m1_evidence(
            client,
            requested_opened_at=REPLICATION_START,
            checked_at=REPLICATION_END_EXCLUSIVE,
            market=market,
            minimum_coverage_days=MINIMUM_COVERAGE_DAYS,
        )
        coverage = payload.get("coverage")
        if not isinstance(coverage, dict):
            raise CTraderDemoLabProbeError("REPLICATION_D coverage payload is invalid")

        first = datetime.fromisoformat(str(coverage["first_opened_at"]))
        last = datetime.fromisoformat(str(coverage["last_closed_at"]))
        if first < REPLICATION_START:
            raise CTraderDemoLabProbeError(
                "REPLICATION_D evidence begins before preregistered boundary"
            )
        if last > REPLICATION_END_EXCLUSIVE:
            raise CTraderDemoLabProbeError(
                "REPLICATION_D evidence crosses preregistered end boundary"
            )
        if (last - first).days < MINIMUM_COVERAGE_DAYS:
            raise CTraderDemoLabProbeError(
                "REPLICATION_D evidence does not cover sufficient calendar span"
            )

        payload.update(
            {
                "evidence_purpose": PURPOSE,
                "shared_identity": IDENTITY,
                "holdout_partition": "TEMPORAL_REPLICATION_D",
                "replication_start_inclusive": REPLICATION_START.isoformat(),
                "replication_end_exclusive": REPLICATION_END_EXCLUSIVE.isoformat(),
                "minimum_coverage_days": MINIMUM_COVERAGE_DAYS,
                "holdout_e_pass_bound": True,
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
