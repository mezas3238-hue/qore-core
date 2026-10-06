"""Burned/contract causal calibration for T01 minimal seed.

This freezes the minimum-seed decision rule across the seven canonical Trader
lineages. Provider volume, margin, tick-value, conversion and execution-cost
facts remain decision-time inputs; this module does not fabricate historical
2017 provider economics or calibrate exact execution/slippage.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

SOURCE_PHASE18_ARTIFACTS = (
    (
        "R38_GBPJPY",
        10909937201,
        "sha256:b59d8c045a0e86f0e22fb0044dc04eb6dff0f17de4c9f7c7389b903adc443956",
    ),
    (
        "R43_GBPUSD",
        10910093452,
        "sha256:93c9c4872543938571eb6ab12e242bde4ec9e7682f056593efde59f88b4579c9",
    ),
    (
        "R42_AUDJPY",
        10910875686,
        "sha256:7b40e1be53ce0508106b036c68ce4ebb3155bc5c14875144634e365cfb988de5",
    ),
    (
        "R38_EURUSD",
        10910397898,
        "sha256:71bb5ce12b7cfc8f2d17b89dcf907b8b74f4a2257f2055adbe9e9d619c324774",
    ),
    (
        "R34_XAUUSD",
        10910328640,
        "sha256:aade958d597032bad08c56043a6c48c145b8ab263f032f2b65c147fd3db7aadd",
    ),
    (
        "VT08_FOREX",
        10913050112,
        "sha256:8543a33962d24d3f5346981328df78d145286fc8af9387d73eca85519922f568",
    ),
    (
        "VT31_NAS100",
        10912945588,
        "sha256:2200392deeb081525720430a816e8f82b18d7333c61a05eb197632ed24849e15",
    ),
)

T01_MINIMAL_SEED_RULES = (
    "TRADER_REQUESTED_VOLUME_IS_NOT_RUNTIME_AUTHORITY",
    "MINIMUM_SEED_USES_PROVIDER_MINIMUM_AND_VOLUME_STEP",
    "METHODOLOGY_MINIMUM_EXECUTION_STEPS_ARE_PRESERVED",
    "VT31_REQUIRES_FOUR_MINIMUM_EXECUTION_STEPS",
    "HARD_RISK_AND_MARGIN_HEADROOM_GATE_SEED",
    "NO_EXECUTABLE_MINIMUM_MEANS_HOLD",
    "STRATEGY_REQUESTED_RISK_USD_REMAINS_NONE",
)


def burned_t01_source_calibration_payload() -> dict[str, Any]:
    return {
        "schema": "qore.cibo.ce2i.burned_t01_source_calibration.v1",
        "source": {
            "phase18_artifacts": [
                {
                    "trader": trader,
                    "artifact_id": artifact_id,
                    "artifact_sha256": artifact_sha256,
                }
                for trader, artifact_id, artifact_sha256
                in SOURCE_PHASE18_ARTIFACTS
            ],
            "phase20_contract_evidence": (
                "provider-normalization-cma-seed-and-risk-envelope-contracts"
            ),
            "evidence_status": "BURNED_7_OF_7_PLUS_FAIL_CLOSED_CONTRACT",
        },
        "tool": "T01",
        "classification": "CALIBRATED_CAUSAL",
        "calibration_space": "MINIMUM_EXECUTABLE_SEED_DECISION_RULE",
        "rules": list(T01_MINIMAL_SEED_RULES),
        "historical_2017_provider_terms_calibrated": False,
        "exact_execution_cost_calibrated": False,
        "slippage_empirically_calibrated": False,
        "incremental_economic_utility_calibrated": False,
        "governance": {
            "provider_economics_required": True,
            "holdout_2017h1_used": False,
            "historical_usd_execution_economics_claimed": False,
            "target_aware": False,
            "oos_ready": False,
            "certification_ready": False,
        },
    }


def burned_t01_source_calibration_sha256() -> str:
    raw = json.dumps(
        burned_t01_source_calibration_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(raw).hexdigest()
