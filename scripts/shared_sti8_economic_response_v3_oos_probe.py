#!/usr/bin/env python3
"""One-shot acquisition for preregistered STI-8 economic response V3 OOS."""

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

OOS_OPENED_AT = datetime(2026, 7, 22, 0, 0, tzinfo=UTC)
OOS_CHECKED_AT = datetime(2026, 9, 29, 0, 0, tzinfo=UTC)
MINIMUM_COVERAGE_DAYS = 65
IDENTITY = "QORE_SHARED_STI8_ECONOMIC_RESPONSE_V3_RESEARCH_OOS_001"


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
            "STI-8 V3 OOS market must be NAS100, SP500 or US30"
        )

    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        payload = collect_vt31_v2_m1_evidence(
            client,
            requested_opened_at=OOS_OPENED_AT,
            checked_at=OOS_CHECKED_AT,
            market=market,
            minimum_coverage_days=MINIMUM_COVERAGE_DAYS,
        )
        coverage = payload.get("coverage")
        if not isinstance(coverage, dict):
            raise CTraderDemoLabProbeError("STI-8 V3 OOS coverage invalid")
        first = datetime.fromisoformat(str(coverage["first_opened_at"]))
        last = datetime.fromisoformat(str(coverage["last_closed_at"]))
        if first < OOS_OPENED_AT or last > OOS_CHECKED_AT:
            raise CTraderDemoLabProbeError(
                "STI-8 V3 OOS evidence crossed preregistered window"
            )
        if (last - first).days < MINIMUM_COVERAGE_DAYS:
            raise CTraderDemoLabProbeError(
                "STI-8 V3 OOS lacks preregistered coverage"
            )

        payload.update(
            {
                "evidence_purpose": (
                    "STI8_ECONOMIC_RESPONSE_V3_BURNABLE_RESEARCH_OOS"
                ),
                "shared_identity": IDENTITY,
                "oos_opened_at_inclusive": OOS_OPENED_AT.isoformat(),
                "oos_checked_at_exclusive": OOS_CHECKED_AT.isoformat(),
                "minimum_actual_coverage_days": MINIMUM_COVERAGE_DAYS,
                "software_sha": software_sha,
                "temporally_disjoint_from_parent_v2_oos": True,
                "sti8_terminal_outcomes_previously_consumed": False,
                "temporal_replication_claim_authorized": False,
                "sti8_signal_engine_changed": False,
                "sti8_threat_thresholds_changed": False,
                "response_policy_frozen_before_acquisition": True,
                "protected_certification_holdout": False,
                "retuning_against_oos_authorized": False,
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
