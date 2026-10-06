"""Export Architect-B forward economic manifest from durable Phase20 stores."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ArchBForwardEconomicManifest,
    build_arch_b_forward_economic_manifest,
)
from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    DurablePhase20ExecutedRiskStore,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    DurablePhase20ForwardPolicyStore,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    DurablePhase20ForwardEvidenceStore,
)
from qore.infrastructure.cibo_cma_settlement_store import (
    DurableCmaSettlementStore,
)
from qore.infrastructure.cibo_t20_capital_release_evidence import (
    DurableT20CapitalReleaseStore,
)


def load_arch_b_forward_manifest(
    *,
    forward_store_path: Path,
    policy_store_path: Path,
    executed_risk_store_path: Path,
    settlement_store_path: Path,
    release_store_path: Path,
) -> ArchBForwardEconomicManifest:
    return build_arch_b_forward_economic_manifest(
        evidence_book=DurablePhase20ForwardEvidenceStore(
            forward_store_path
        ).load(),
        policy_book=DurablePhase20ForwardPolicyStore(
            policy_store_path
        ).load(),
        executed_risk_book=DurablePhase20ExecutedRiskStore(
            executed_risk_store_path
        ).load(),
        settlement_book=DurableCmaSettlementStore(
            settlement_store_path
        ).load(),
        release_book=DurableT20CapitalReleaseStore(
            release_store_path
        ).load(),
    )


def manifest_payload(
    manifest: ArchBForwardEconomicManifest,
) -> dict[str, object]:
    payload = _canonical(asdict(manifest))
    if not isinstance(payload, dict):
        raise TypeError("Architect-B manifest payload must be object")
    payload["manifest_sha256"] = manifest.fingerprint()
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forward-store", type=Path, required=True)
    parser.add_argument("--policy-store", type=Path, required=True)
    parser.add_argument("--executed-risk-store", type=Path, required=True)
    parser.add_argument("--settlement-store", type=Path, required=True)
    parser.add_argument("--release-store", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = load_arch_b_forward_manifest(
        forward_store_path=args.forward_store,
        policy_store_path=args.policy_store,
        executed_risk_store_path=args.executed_risk_store,
        settlement_store_path=args.settlement_store,
        release_store_path=args.release_store,
    )
    payload = manifest_payload(manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
