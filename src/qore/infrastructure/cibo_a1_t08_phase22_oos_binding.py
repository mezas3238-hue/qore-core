"""Exact Phase22 binding for the CE2I T08 fresh-OOS netting ablation.

The inherited T08 shadow epoch carries causal timestamps and evidence ids but
not the Phase22 decision SHA. This A1 wrapper binds every shadow epoch to one
historical replay decision and its actual replay outcome evidence, then proves
that the bound decisions reproduce the exact canonical WF1..WF4 population
digests from the A1 Phase22 manifest.

It never certifies the factor map/correlation state and never authorizes netting.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from qore.infrastructure.cibo_a1_phase22_scientific_consumption import (
    A1Phase22ScientificConsumptionManifest,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_oos_ablation import (
    T08NettingOosAblationReport,
    T08NettingShadowEpoch,
    assess_t08_fresh_oos_netting_ablation,
)
from qore.infrastructure.cibo_phase22_historical_replay_settlement import (
    VersionedPhase22HistoricalReplayEvidenceBook,
)

GATE_ID = "CIBO_A1_T08_PHASE22_OOS_POPULATION_BINDING_V1"
_CANONICAL_FOLDS = ("WF1", "WF2", "WF3", "WF4")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class A1T08Phase22EpochBinding:
    fold_id: str
    phase22_decision_sha256: str
    shadow_epoch: T08NettingShadowEpoch

    def __post_init__(self) -> None:
        if self.fold_id not in _CANONICAL_FOLDS:
            raise CiboCapitalManagementError(
                "T08 Phase22 binding fold must be WF1..WF4"
            )
        if _SHA256_RE.fullmatch(self.phase22_decision_sha256) is None:
            raise CiboCapitalManagementError(
                "T08 Phase22 binding decision digest invalid"
            )
        if not isinstance(self.shadow_epoch, T08NettingShadowEpoch):
            raise CiboCapitalManagementError(
                "T08 Phase22 binding requires canonical shadow epoch"
            )


@dataclass(frozen=True, slots=True)
class A1T08Phase22OosBindingReport:
    gate_id: str
    manifest_sha256: str
    bound_decision_count: int
    fold_population_sha256s: tuple[tuple[str, str], ...]
    oos_report: T08NettingOosAblationReport
    exact_phase22_population_bound: bool
    replay_outcome_lineage_bound: bool
    factor_map_certified_here: bool = False
    correlation_state_certified_here: bool = False
    netting_credit_authorized: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != GATE_ID:
            raise CiboCapitalManagementError(
                "T08 Phase22 OOS binding gate identity drift"
            )
        if _SHA256_RE.fullmatch(self.manifest_sha256) is None:
            raise CiboCapitalManagementError(
                "T08 Phase22 OOS binding manifest digest invalid"
            )
        if (
            not isinstance(self.bound_decision_count, int)
            or isinstance(self.bound_decision_count, bool)
            or self.bound_decision_count <= 0
        ):
            raise CiboCapitalManagementError(
                "T08 Phase22 OOS bound decision count invalid"
            )
        if tuple(key for key, _ in self.fold_population_sha256s) != _CANONICAL_FOLDS:
            raise CiboCapitalManagementError(
                "T08 Phase22 OOS binding requires ordered WF1..WF4"
            )
        for _, digest in self.fold_population_sha256s:
            if _SHA256_RE.fullmatch(digest) is None:
                raise CiboCapitalManagementError(
                    "T08 Phase22 OOS fold digest invalid"
                )
        if not isinstance(self.oos_report, T08NettingOosAblationReport):
            raise CiboCapitalManagementError(
                "T08 Phase22 OOS binding requires canonical ablation report"
            )
        if (
            not self.exact_phase22_population_bound
            or not self.replay_outcome_lineage_bound
            or self.factor_map_certified_here
            or self.correlation_state_certified_here
            or self.netting_credit_authorized
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCapitalManagementError(
                "T08 Phase22 OOS binding governance/lineage drift"
            )


def bind_t08_oos_to_phase22(
    *,
    manifest: A1Phase22ScientificConsumptionManifest,
    evidence_book: VersionedPhase22HistoricalReplayEvidenceBook,
    bindings: tuple[A1T08Phase22EpochBinding, ...],
    minimum_epochs: int = 30,
) -> A1T08Phase22OosBindingReport:
    """Bind T08 ablation epochs to the exact Phase22 decision/outcome surface."""

    if not isinstance(manifest, A1Phase22ScientificConsumptionManifest):
        raise CiboCapitalManagementError(
            "T08 Phase22 OOS binding requires canonical manifest"
        )
    if not isinstance(
        evidence_book,
        VersionedPhase22HistoricalReplayEvidenceBook,
    ):
        raise CiboCapitalManagementError(
            "T08 Phase22 OOS binding requires canonical replay book"
        )
    if not bindings:
        raise CiboCapitalManagementError(
            "T08 Phase22 OOS binding requires epoch bindings"
        )

    decision_by_sha = {
        item.evidence_sha256: item for item in evidence_book.decisions
    }
    outcomes_by_decision: dict[str, set[str]] = {}
    for outcome in evidence_book.outcomes:
        outcomes_by_decision.setdefault(
            outcome.decision_evidence_sha256,
            set(),
        ).add(outcome.evidence_id)

    bound_shas = tuple(item.phase22_decision_sha256 for item in bindings)
    if len(bound_shas) != len(set(bound_shas)):
        raise CiboCapitalManagementError(
            "T08 Phase22 OOS binding decision SHAs must be unique"
        )
    if set(bound_shas) != set(decision_by_sha):
        raise CiboCapitalManagementError(
            "T08 Phase22 OOS binding must cover exact replay decision population"
        )

    by_fold: dict[str, list[A1T08Phase22EpochBinding]] = {
        fold_id: [] for fold_id in _CANONICAL_FOLDS
    }
    for binding in bindings:
        decision = decision_by_sha.get(binding.phase22_decision_sha256)
        if decision is None:
            raise CiboCapitalManagementError(
                "T08 Phase22 OOS binding references unknown decision"
            )
        epoch = binding.shadow_epoch
        if epoch.decision_at != decision.decision_at:
            raise CiboCapitalManagementError(
                "T08 Phase22 OOS epoch/decision chronology drift"
            )
        known_outcomes = outcomes_by_decision.get(
            binding.phase22_decision_sha256,
            set(),
        )
        if (
            not known_outcomes
            or not set(epoch.outcome_evidence_ids).issubset(known_outcomes)
        ):
            raise CiboCapitalManagementError(
                "T08 Phase22 OOS epoch outcome lineage is not replay-bound"
            )
        by_fold[binding.fold_id].append(binding)

    expected_fold_digests = {
        item.fold_id: item.population_sha256 for item in manifest.folds
    }
    actual_fold_digests: list[tuple[str, str]] = []
    for fold_id in _CANONICAL_FOLDS:
        rows = sorted(
            by_fold[fold_id],
            key=lambda item: (
                item.shadow_epoch.decision_at,
                item.phase22_decision_sha256,
            ),
        )
        if not rows:
            raise CiboCapitalManagementError(
                "T08 Phase22 OOS binding requires non-empty WF1..WF4"
            )
        digest = _decision_population_sha256(
            tuple(item.phase22_decision_sha256 for item in rows)
        )
        if digest != expected_fold_digests[fold_id]:
            raise CiboCapitalManagementError(
                "T08 Phase22 OOS fold population differs from A1 manifest"
            )
        actual_fold_digests.append((fold_id, digest))

    ordered_bindings = tuple(
        sorted(
            bindings,
            key=lambda item: (
                item.shadow_epoch.decision_at,
                item.phase22_decision_sha256,
            ),
        )
    )
    oos = assess_t08_fresh_oos_netting_ablation(
        tuple(item.shadow_epoch for item in ordered_bindings),
        minimum_epochs=minimum_epochs,
        required_folds=4,
    )
    return A1T08Phase22OosBindingReport(
        gate_id=GATE_ID,
        manifest_sha256=manifest.fingerprint(),
        bound_decision_count=len(bindings),
        fold_population_sha256s=tuple(actual_fold_digests),
        oos_report=oos,
        exact_phase22_population_bound=True,
        replay_outcome_lineage_bound=True,
    )


def _decision_population_sha256(decision_shas: tuple[str, ...]) -> str:
    raw = json.dumps(
        list(decision_shas),
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()
