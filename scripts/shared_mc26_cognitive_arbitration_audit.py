#!/usr/bin/env python3
"""MC-26 cognitive-arbitration foundation canary."""

from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.core_stack_v2.cognitive_arbitration import (
    CognitiveFacet,
    CognitiveFacetEvidence,
    SharedSituationState,
    arbitrate_shared_situation,
)

IDENTITY = "QORE_SHARED_MC26_COGNITIVE_ARBITRATION_AUDIT_001"


def _facets() -> tuple[CognitiveFacetEvidence, ...]:
    rows = []
    for facet in CognitiveFacet:
        rows.append(
            CognitiveFacetEvidence(
                facet=facet,
                support_bps=8000,
                contradiction_bps=7000 if facet is CognitiveFacet.NEGATIVE_EVIDENCE else 1200,
                uncertainty_bps=7200 if facet is CognitiveFacet.INFORMATION_GAPS else 1800,
                critical_negative=facet is CognitiveFacet.NEGATIVE_EVIDENCE,
                evidence_refs=(f"mc26:{facet.value}",),
            )
        )
    return tuple(rows)


def main() -> None:
    situation = arbitrate_shared_situation("mc26-adversarial-canary", _facets())
    payload = {
        "identity": IDENTITY,
        "status": "MC26_COGNITIVE_ARBITRATION_FOUNDATION_PASS",
        "facet_count": len(situation.facets),
        "state": situation.state.value,
        "assertiveness_bps": situation.assertiveness_bps,
        "critical_negative_preserved": situation.critical_negative_preserved,
        "information_gap_preserved": situation.information_gap_preserved,
        "trading_command": situation.trading_command,
        "sizing_authority": situation.sizing_authority,
        "capital_authority": situation.capital_authority,
        "risk_authority": situation.risk_authority,
        "broker_authority": situation.broker_authority,
        "real_all-facet_runtime_binding_complete": False,
        "mc26_completed_and_proven": False,
        "protected_certification_holdout_opened": False,
    }
    if situation.state not in {
        SharedSituationState.CONTESTED,
        SharedSituationState.INSUFFICIENT,
    }:
        raise AssertionError("MC26 adversarial canary became overconfident")
    Path("result").mkdir(exist_ok=True)
    Path("result/mc26-cognitive-arbitration-audit.json").write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
