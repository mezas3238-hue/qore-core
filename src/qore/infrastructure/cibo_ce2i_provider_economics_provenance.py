"""Sealed provider-economics provenance for CIBO calibration.

This binds the successful read-only cTrader DEMO probe. It proves current
provider-native contract, spread, commission and expected-margin terms for the
six required symbols. It does NOT claim historical 2017 economics, empirical
slippage, latency calibration, or a complete execution model.
"""

from __future__ import annotations

import hashlib
import json

PROVIDER_ECONOMICS_WORKFLOW_RUN_ID = 36432944843
PROVIDER_ECONOMICS_ARTIFACT_ID = 10975061063
PROVIDER_ECONOMICS_ARTIFACT_ZIP_SHA256 = (
    "e58cb9cd55c057c2e76888c637712e5ee08c653a1deadbce0d628cca0614cd2d"
)
PROVIDER_ECONOMICS_PAYLOAD_SHA256 = (
    "e3fa6ce1e5dc797e27550e8c49ee0905fae8dc720a249d9213c04211c334af5b"
)
PROVIDER_ECONOMICS_GIT_SHA = "27d17074f34f8811421393db52ef75ea1b09865a"
PROVIDER_ECONOMICS_OBSERVED_AT = "2026-09-28T14:07:41.153325+00:00"

PROVIDER_ECONOMICS_SYMBOLS = (
    "AUDJPY",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "NAS100",
    "XAUUSD",
)


def provider_economics_provenance_payload() -> dict[str, object]:
    return {
        "schema": "qore.cibo.provider_economics_provenance.v1",
        "workflow_run_id": PROVIDER_ECONOMICS_WORKFLOW_RUN_ID,
        "artifact_id": PROVIDER_ECONOMICS_ARTIFACT_ID,
        "artifact_zip_sha256": PROVIDER_ECONOMICS_ARTIFACT_ZIP_SHA256,
        "payload_sha256": PROVIDER_ECONOMICS_PAYLOAD_SHA256,
        "git_sha": PROVIDER_ECONOMICS_GIT_SHA,
        "observed_at": PROVIDER_ECONOMICS_OBSERVED_AT,
        "provider": "ctrader-demo",
        "environment": "demo",
        "symbols": list(PROVIDER_ECONOMICS_SYMBOLS),
        "current_provider_terms_ready": True,
        "spread_native_ready": True,
        "commission_native_ready": True,
        "expected_margin_native_ready": True,
        "volume_and_contract_terms_ready": True,
        "slippage_empirically_calibrated": False,
        "latency_empirically_calibrated": False,
        "historical_2017_exact_claimed": False,
        "execution_model_ready": False,
        "broker_mutation_performed": False,
        "holdout_outcomes_used": False,
        "target_aware": False,
        "status": (
            "CURRENT_DEMO_TERMS_READY_"
            "HISTORICAL_EXACT_AND_SLIPPAGE_PENDING"
        ),
    }


def provider_economics_provenance_sha256() -> str:
    raw = json.dumps(
        provider_economics_provenance_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(raw).hexdigest()
