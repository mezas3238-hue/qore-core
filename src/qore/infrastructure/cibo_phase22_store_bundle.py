"""Canonical durable stores bound to Phase22 V2-only physical namespaces."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from qore.infrastructure.cibo_phase22_historical_replay_stores import (
    DurablePhase22HistoricalExecutedRiskStore,
    DurablePhase22HistoricalForwardEvidenceStore,
    DurablePhase22HistoricalPolicyStore,
    DurablePhase22HistoricalReleaseStore,
    DurablePhase22HistoricalSettlementStore,
)

PHASE22_STORE_ROOT_NAME = "phase22-v2-stores"


@dataclass(frozen=True, slots=True)
class CiboPhase22StoreBundle:
    """Five separate stores; canonical semantics, Phase22-only files."""

    root: Path
    holdout_evidence: DurablePhase22HistoricalForwardEvidenceStore
    holdout_policy: DurablePhase22HistoricalPolicyStore
    executed_risk: DurablePhase22HistoricalExecutedRiskStore
    cma_settlement: DurablePhase22HistoricalSettlementStore
    t20_release: DurablePhase22HistoricalReleaseStore

    @property
    def paths(self) -> tuple[Path, ...]:
        return (
            self.root / "holdout-forward-evidence.json",
            self.root / "holdout-policy.json",
            self.root / "executed-risk.json",
            self.root / "cma-settlement.json",
            self.root / "t20-release.json",
        )

    def assert_pristine(self) -> None:
        if self.root.name != PHASE22_STORE_ROOT_NAME:
            raise ValueError("Phase22 store root identity drift")
        if len(self.paths) != len(set(self.paths)):
            raise ValueError("Phase22 physical store paths are not disjoint")
        if any(path.exists() for path in self.paths):
            raise ValueError(
                "Phase22 store surface is not pristine; fresh launch prohibited"
            )
        if self.holdout_evidence.load().generation != 0:
            raise ValueError("Phase22 holdout evidence store not pristine")
        if self.holdout_policy.load().generation != 0:
            raise ValueError("Phase22 holdout policy store not pristine")
        if self.executed_risk.load().generation != 0:
            raise ValueError("Phase22 executed-risk store not pristine")
        if self.cma_settlement.load().generation != 0:
            raise ValueError("Phase22 settlement store not pristine")
        if self.t20_release.load().generation != 0:
            raise ValueError("Phase22 T20 release store not pristine")

    def contract_payload(self) -> dict[str, object]:
        return {
            "schema": "qore.cibo.phase22.store-bundle.v1",
            "root": str(self.root),
            "stores": [
                {
                    "role": "HOLDOUT_FORWARD_EVIDENCE",
                    "path": str(self.paths[0]),
                    "canonical_store_class": (
                        "DurablePhase22HistoricalForwardEvidenceStore"
                    ),
                },
                {
                    "role": "HOLDOUT_POLICY",
                    "path": str(self.paths[1]),
                    "canonical_store_class": (
                        "DurablePhase22HistoricalPolicyStore"
                    ),
                },
                {
                    "role": "EXECUTED_RISK",
                    "path": str(self.paths[2]),
                    "canonical_store_class": (
                        "DurablePhase22HistoricalExecutedRiskStore"
                    ),
                },
                {
                    "role": "CMA_SETTLEMENT",
                    "path": str(self.paths[3]),
                    "canonical_store_class": "DurablePhase22HistoricalSettlementStore",
                },
                {
                    "role": "T20_RELEASE",
                    "path": str(self.paths[4]),
                    "canonical_store_class": (
                        "DurablePhase22HistoricalReleaseStore"
                    ),
                },
            ],
            "canonical_semantics_reused": True,
            "physical_store_reused": False,
            "phase20_paths_reused": False,
            "fresh_outcomes_executed": False,
            "productive_authority": False,
        }


def build_phase22_store_bundle(root: Path) -> CiboPhase22StoreBundle:
    if not isinstance(root, Path):
        raise TypeError("Phase22 store root must be pathlib.Path")
    if root.name != PHASE22_STORE_ROOT_NAME:
        raise ValueError(
            f"Phase22 store root must end with {PHASE22_STORE_ROOT_NAME}"
        )
    return CiboPhase22StoreBundle(
        root=root,
        holdout_evidence=DurablePhase22HistoricalForwardEvidenceStore(
            root / "holdout-forward-evidence.json"
        ),
        holdout_policy=DurablePhase22HistoricalPolicyStore(
            root / "holdout-policy.json"
        ),
        executed_risk=DurablePhase22HistoricalExecutedRiskStore(
            root / "executed-risk.json"
        ),
        cma_settlement=DurablePhase22HistoricalSettlementStore(
            root / "cma-settlement.json"
        ),
        t20_release=DurablePhase22HistoricalReleaseStore(
            root / "t20-release.json"
        ),
    )
