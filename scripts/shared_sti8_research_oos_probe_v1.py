"""One-shot burnable post-R5 cTrader DEMO collector for Shared STI-8 OOS V1.

This is research OOS evidence, not the protected Shared certification holdout.
The window was preregistered before acquisition in
QORE_SHARED_STI8_RESEARCH_OOS_PREREGISTRATION_001.json.
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

OOS_OPENED_AT = datetime(2022, 7, 18, 0, 0, tzinfo=UTC)
OOS_CHECKED_AT = datetime(2024, 7, 18, 0, 0, tzinfo=UTC)
MINIMUM_COVERAGE_DAYS = 720
IDENTITY = "QORE_SHARED_STI8_RESEARCH_OOS_V1"


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
            "STI-8 OOS market must be NAS100, SP500 or US30"
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
            raise CTraderDemoLabProbeError("STI-8 OOS coverage payload invalid")
        first = datetime.fromisoformat(str(coverage["first_opened_at"]))
        last = datetime.fromisoformat(str(coverage["last_closed_at"]))
        if first < OOS_OPENED_AT:
            raise CTraderDemoLabProbeError(
                "STI-8 OOS evidence predates preregistered boundary"
            )
        if last > OOS_CHECKED_AT:
            raise CTraderDemoLabProbeError(
                "STI-8 OOS evidence crosses preregistered boundary"
            )

        payload.update(
            {
                "evidence_purpose": (
                    "SHARED_STI8_BURNABLE_RESEARCH_OOS_NOT_CERTIFICATION"
                ),
                "shared_identity": IDENTITY,
                "oos_opened_at_inclusive": OOS_OPENED_AT.isoformat(),
                "oos_checked_at_exclusive": OOS_CHECKED_AT.isoformat(),
                "minimum_actual_coverage_days": MINIMUM_COVERAGE_DAYS,
                "software_sha": software_sha,
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
