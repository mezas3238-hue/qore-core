"""Frozen BTCUSD per-market research certification seal for VT08 CRT PURE.

This seal binds the exact candidate to exact GitHub evidence refs that were
generated before the seal was written.

RESEARCH_CERTIFIED means:
- market-level research/economic evidence gates are closed for this exact
  candidate version.

It does NOT mean:
- combined three-market CRT certification;
- DEMO eligibility;
- LIVE/production/real-capital authorization;
- external Risk/CIBO review completion.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_market_certification_readiness import (
    CrtPureMarketCertificationEvidence,
    CrtPureMarketCertificationReadiness,
    CrtPureMarketCertificationStage,
    evaluate_market_certification_readiness,
)

CANDIDATE_IDENTITY = "VT08_CRT_PURE_BTCUSD_R3_REF2_PLUS_001"


@dataclass(frozen=True, slots=True)
class BtcResearchEvidenceRef:
    stage: str
    run_id: int
    head_sha: str
    artifact_digest: str

    def __post_init__(self) -> None:
        if self.run_id <= 0:
            raise ValueError("run_id must be positive")
        if len(self.head_sha) != 40:
            raise ValueError("head_sha must be a 40-character Git SHA")
        if not self.artifact_digest.startswith("sha256:"):
            raise ValueError("artifact_digest must be SHA-256")
        if len(self.artifact_digest) != len("sha256:") + 64:
            raise ValueError("artifact_digest must contain 64 hex chars")


EVIDENCE_REFS: tuple[BtcResearchEvidenceRef, ...] = (
    BtcResearchEvidenceRef(
        stage="FINAL_FRESH",
        run_id=35850545418,
        head_sha="ca3a37658ab176b6f9b255e19efe79b57bfa28a0",
        artifact_digest=(
            "sha256:fac3bc8862577a213101ba222bd81c8d533915856e9d8d9b9ecb6e7e56042bcd"
        ),
    ),
    BtcResearchEvidenceRef(
        stage="R3A_CHRONOLOGICAL_STRESS",
        run_id=35851040583,
        head_sha="59a958a068861257c2caa1f666c04857011c055a",
        artifact_digest=(
            "sha256:0ecc45a425717fef066d47438d6ecbcb143fdfd6866f01c9259afa60c90f0b27"
        ),
    ),
    BtcResearchEvidenceRef(
        stage="R3B_BLOCK_BOOTSTRAP",
        run_id=35850990708,
        head_sha="056d0d4e863de749ef0d5a3397bdd8b06b0b84c4",
        artifact_digest=(
            "sha256:c790710328574cdf7f7c8afa96a8edbd30fd2952a71b36f5da5b90f738237874"
        ),
    ),
    BtcResearchEvidenceRef(
        stage="R3C_WFO_SLIPPAGE",
        run_id=35852361769,
        head_sha="8719ae1b8fe1676594912ef37cdf713a01716ff3",
        artifact_digest=(
            "sha256:a0eccfd2337d4ef3b4f2b2a9eb65080655caa6c151bca8dd04d423167aad2be2"
        ),
    ),
)


def btcusd_research_certification_readiness() -> CrtPureMarketCertificationReadiness:
    evidence = CrtPureMarketCertificationEvidence(
        market=CrtPureMarket.BTCUSD,
        market_history_verified=True,
        exact_candidate_frozen=True,
        fresh_holdout_green=True,
        chronological_replay_green=True,
        annual_stability_green=True,
        rolling_stability_green=True,
        walk_forward_green=True,
        stress_green=True,
        slippage_green=True,
        monte_carlo_green=True,
        robustness_green=True,
    )
    readiness = evaluate_market_certification_readiness(evidence)
    if readiness.stage is not CrtPureMarketCertificationStage.RESEARCH_CERTIFIED:
        raise RuntimeError("BTCUSD frozen certification evidence did not close")
    return readiness


BTCUSD_RESEARCH_CERTIFIED = btcusd_research_certification_readiness().research_certified
BTCUSD_DEMO_AUTHORIZED = False
BTCUSD_LIVE_AUTHORIZED = False
BTCUSD_REAL_CAPITAL_AUTHORIZED = False
BTCUSD_PRODUCTION_AUTHORIZED = False
