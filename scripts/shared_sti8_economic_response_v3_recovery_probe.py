#!/usr/bin/env python3
"""Recovery acquisition envelope for STI-8 V3 frozen Trader reconstruction."""

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

SOURCE_OPENED_AT = datetime(2024, 9, 29, 0, 0, tzinfo=UTC)
SOURCE_CHECKED_AT = datetime(2026, 9, 29, 0, 0, tzinfo=UTC)
EVALUATION_OPENED_AT = datetime(2026, 7, 22, 0, 0, tzinfo=UTC)
MINIMUM_COVERAGE_DAYS = 730
IDENTITY = "QORE_SHARED_STI8_ECONOMIC_RESPONSE_V3_RECOVERY_SOURCE_001"


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
            _required_env("QORE_CTRADER_DEMO_ACCOUNT_ID", "QORE_CTRADER_ACCOUNT_ID")
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
            "STI-8 V3 recovery market must be NAS100, SP500 or US30"
        )

    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        payload = collect_vt31_v2_m1_evidence(
            client,
            requested_opened_at=SOURCE_OPENED_AT,
            checked_at=SOURCE_CHECKED_AT,
            market=market,
            minimum_coverage_days=MINIMUM_COVERAGE_DAYS,
        )
        coverage = payload.get("coverage")
        if not isinstance(coverage, dict):
            raise CTraderDemoLabProbeError("STI-8 V3 recovery coverage invalid")
        first = datetime.fromisoformat(str(coverage["first_opened_at"]))
        last = datetime.fromisoformat(str(coverage["last_closed_at"]))
        if first < SOURCE_OPENED_AT or last > SOURCE_CHECKED_AT:
            raise CTraderDemoLabProbeError("V3 recovery crossed source envelope")
        if last - first < SOURCE_CHECKED_AT - SOURCE_OPENED_AT:
            raise CTraderDemoLabProbeError("V3 recovery source span is below 730 days")

        payload.update(
            {
                "evidence_purpose": "STI8_V3_ENGINEERING_RECOVERY_SOURCE_ENVELOPE",
                "shared_identity": IDENTITY,
                "source_opened_at_inclusive": SOURCE_OPENED_AT.isoformat(),
                "source_checked_at_exclusive": SOURCE_CHECKED_AT.isoformat(),
                "evaluation_opened_at_inclusive": EVALUATION_OPENED_AT.isoformat(),
                "evaluation_checked_at_exclusive": SOURCE_CHECKED_AT.isoformat(),
                "minimum_actual_coverage_days": MINIMUM_COVERAGE_DAYS,
                "software_sha": software_sha,
                "engineering_recovery_only": True,
                "policy_changed": False,
                "gates_changed": False,
                "protected_certification_holdout": False,
                "productive_authority": False,
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
