"""Export empirical cTrader DEMO execution calibration from Phase20 durable stores."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    DurablePhase20ExecutedRiskStore,
)
from qore.infrastructure.cibo_ce2i_provider_execution_calibration import (
    CiboProviderExecutionCalibration,
    calibrate_ctrader_demo_forward_execution,
)
from scripts.cibo_phase20_arch_b_forward_economic_manifest import (
    load_arch_b_forward_manifest,
)


def load_provider_execution_calibration(
    *,
    forward_store_path: Path,
    policy_store_path: Path,
    executed_risk_store_path: Path,
    settlement_store_path: Path,
    release_store_path: Path,
    frozen_at: datetime,
) -> CiboProviderExecutionCalibration:
    manifest = load_arch_b_forward_manifest(
        forward_store_path=forward_store_path,
        policy_store_path=policy_store_path,
        executed_risk_store_path=executed_risk_store_path,
        settlement_store_path=settlement_store_path,
        release_store_path=release_store_path,
    )
    risk_book = DurablePhase20ExecutedRiskStore(
        executed_risk_store_path
    ).load()
    return calibrate_ctrader_demo_forward_execution(
        manifest=manifest,
        executed_risk_book=risk_book,
        frozen_at=frozen_at,
    )


def calibration_payload(
    calibration: CiboProviderExecutionCalibration,
) -> dict[str, object]:
    payload = _canonical(asdict(calibration))
    if not isinstance(payload, dict):
        raise TypeError("provider execution calibration payload must be object")
    payload["calibration_sha256"] = calibration.fingerprint()
    return payload


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return value


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError(
            "--frozen-at must be timezone-aware ISO-8601"
        )
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forward-store", type=Path, required=True)
    parser.add_argument("--policy-store", type=Path, required=True)
    parser.add_argument("--executed-risk-store", type=Path, required=True)
    parser.add_argument("--settlement-store", type=Path, required=True)
    parser.add_argument("--release-store", type=Path, required=True)
    parser.add_argument("--frozen-at", type=_timestamp, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    calibration = load_provider_execution_calibration(
        forward_store_path=args.forward_store,
        policy_store_path=args.policy_store,
        executed_risk_store_path=args.executed_risk_store,
        settlement_store_path=args.settlement_store,
        release_store_path=args.release_store,
        frozen_at=args.frozen_at,
    )
    payload = calibration_payload(calibration)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
