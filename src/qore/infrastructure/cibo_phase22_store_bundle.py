"""Canonical durable stores bound to Phase22 V2-only physical namespaces."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from qore.infrastructure.cibo_phase22_historical_store import (
    DurablePhase22HistoricalStore,
)

PHASE22_STORE_ROOT_NAME = "phase22-v2-stores"


@dataclass(frozen=True, slots=True)
class CiboPhase22StoreBundle:
    """Five separate stores; canonical semantics, Phase22-only files."""

    root: Path
    holdout_evidence: DurablePhase22HistoricalStore
    holdout_policy: DurablePhase22HistoricalStore
    executed_risk: DurablePhase22HistoricalStore
    cma_settlement: DurablePhase22HistoricalStore
    t20_release: DurablePhase22HistoricalStore

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
                    "canonical_store_class": "DurablePhase22HistoricalStore",
                },
                {
                    "role": "HOLDOUT_POLICY",
                    "path": str(self.paths[1]),
                    "canonical_store_class": "DurablePhase22HistoricalStore",
                },
                {
                    "role": "EXECUTED_RISK",
                    "path": str(self.paths[2]),
                    "canonical_store_class": "DurablePhase22HistoricalStore",
                },
                {
                    "role": "CMA_SETTLEMENT",
                    "path": str(self.paths[3]),
                    "canonical_store_class": "DurablePhase22HistoricalStore",
                },
                {
                    "role": "T20_RELEASE",
                    "path": str(self.paths[4]),
                    "canonical_store_class": "DurablePhase22HistoricalStore",
                },
            ],
            "canonical_semantics_reused": True,
            "counterfactual_historical_identity_safe": True,
            "broker_identity_fields_prohibited": True,
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
        holdout_evidence=DurablePhase22HistoricalStore(
            root / "holdout-forward-evidence.json",
            role="HOLDOUT_FORWARD_EVIDENCE",
        ),
        holdout_policy=DurablePhase22HistoricalStore(
            root / "holdout-policy.json",
            role="HOLDOUT_POLICY",
        ),
        executed_risk=DurablePhase22HistoricalStore(
            root / "executed-risk.json",
            role="EXECUTED_RISK",
        ),
        cma_settlement=DurablePhase22HistoricalStore(
            root / "cma-settlement.json",
            role="CMA_SETTLEMENT",
        ),
        t20_release=DurablePhase22HistoricalStore(
            root / "t20-release.json",
            role="T20_RELEASE",
        ),
    )
