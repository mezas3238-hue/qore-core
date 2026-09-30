#!/usr/bin/env python3
"""One-shot burnable temporal-replication collector for Shared STI-2 V2."""

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

OPENED_AT = datetime(2026, 4, 1, 0, 0, tzinfo=UTC)
CHECKED_AT = datetime(2026, 7, 1, 0, 0, tzinfo=UTC)
MINIMUM_COVERAGE_DAYS = 80
IDENTITY = "QORE_SHARED_STI2_V2_TEMPORAL_REPLICATION_001"


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
        raise CTraderDemoLabProbeError(
            "QORE_SOFTWARE_SHA must be exact lowercase Git SHA"
        )

    market = os.environ.get("QORE_DEMO_LAB_SYMBOL", "")
    if market not in _RESEARCH_MARKETS:
        raise CTraderDemoLabProbeError(
            "STI-2 temporal replication market must be NAS100, SP500 or US30"
        )

    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        payload = collect_vt31_v2_m1_evidence(
            client,
            requested_opened_at=OPENED_AT,
            checked_at=CHECKED_AT,
            market=market,
            minimum_coverage_days=MINIMUM_COVERAGE_DAYS,
        )
        coverage = payload.get("coverage")
        if not isinstance(coverage, dict):
            raise CTraderDemoLabProbeError(
                "STI-2 temporal replication coverage payload invalid"
            )
        first = datetime.fromisoformat(str(coverage["first_opened_at"]))
        last = datetime.fromisoformat(str(coverage["last_closed_at"]))
        if first < OPENED_AT or last > CHECKED_AT:
            raise CTraderDemoLabProbeError(
                "STI-2 temporal replication crossed preregistered window"
            )
        if (last - first).days < MINIMUM_COVERAGE_DAYS:
            raise CTraderDemoLabProbeError(
                "STI-2 temporal replication lacks preregistered coverage"
            )

        payload.update(
            {
                "evidence_purpose": (
                    "SHARED_STI2_V2_BURNABLE_TEMPORAL_REPLICATION_NOT_CERTIFICATION"
                ),
                "shared_identity": IDENTITY,
                "replication_opened_at_inclusive": OPENED_AT.isoformat(),
                "replication_checked_at_exclusive": CHECKED_AT.isoformat(),
                "minimum_actual_coverage_days": MINIMUM_COVERAGE_DAYS,
                "software_sha": software_sha,
                "temporal_replication_claim_authorized_if_all_gates_pass": True,
                "protected_certification_holdout": False,
                "retuning_against_replication_authorized": False,
                "read_only_research": True,
                "live_authorized": False,
                "production_authorized": False,
                "real_capital_authorized": False,
                "broker_mutation_authorized": False,
            }
        )
        print(
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
