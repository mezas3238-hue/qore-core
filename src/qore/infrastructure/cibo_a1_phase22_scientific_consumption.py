"""Canonical Phase22 scientific-consumption manifest for CIBO Architect A1.

All A1 scientific consumers must be able to bind to one immutable historical
replay population rather than silently consuming different candidate/code/
parameter/policy surfaces. This manifest is read-only and performs no outcome
interpretation, tuning, ledger reconciliation or certification.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    Phase20ForwardPolicyDecisionSeal,
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_phase22_historical_replay_settlement import (
    VersionedPhase22HistoricalReplayEvidenceBook,
)

MANIFEST_ID = "CIBO_A1_PHASE22_SCIENTIFIC_CONSUMPTION_MANIFEST_V1"
_CANONICAL_FOLDS = ("WF1", "WF2", "WF3", "WF4")
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class A1Phase22PopulationFold:
    fold_id: str
    decision_count: int
    first_decision_at: datetime
    last_decision_at: datetime
    population_sha256: str

    def __post_init__(self) -> None:
        if self.fold_id not in _CANONICAL_FOLDS:
            raise CiboCapitalManagementError(
                "A1 Phase22 fold identity must be WF1..WF4"
            )
        if (
            not isinstance(self.decision_count, int)
            or isinstance(self.decision_count, bool)
            or self.decision_count <= 0
        ):
            raise CiboCapitalManagementError(
                "A1 Phase22 fold decision_count must be positive"
            )
        for name in ("first_decision_at", "last_decision_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise CiboCapitalManagementError(
                    f"A1 Phase22 {name} must be timezone-aware"
                )
        if self.last_decision_at < self.first_decision_at:
            raise CiboCapitalManagementError(
                "A1 Phase22 fold chronology drift"
            )
        _sha256(self.population_sha256, "population_sha256")


@dataclass(frozen=True, slots=True)
class A1Phase22ScientificConsumptionManifest:
    manifest_id: str
    candidate_id: str
    code_sha: str
    parameter_sha256: str
    amendment_sha256: str
    source_population_sha256: str
    policy_population_sha256: str
    decision_count: int
    policy_count: int
    outcome_count: int
    trader_ids: tuple[str, ...]
    folds: tuple[A1Phase22PopulationFold, ...]
    exact_policy_coverage: bool
    historical_replay_only: bool
    folds_defined_without_outcomes: bool
    post_evidence_retune_allowed: bool = False
    outcome_aware_population_selection_allowed: bool = False
    productive_authority: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    global_ledger_reconciled: bool = False
    certification_authorized: bool = False

    def __post_init__(self) -> None:
        if self.manifest_id != MANIFEST_ID:
            raise CiboCapitalManagementError(
                "A1 Phase22 scientific manifest identity drift"
            )
        if not self.candidate_id:
            raise CiboCapitalManagementError(
                "A1 Phase22 scientific manifest candidate required"
            )
        if _SHA1_RE.fullmatch(self.code_sha) is None:
            raise CiboCapitalManagementError(
                "A1 Phase22 scientific manifest code SHA invalid"
            )
        for name in (
            "parameter_sha256",
            "amendment_sha256",
            "source_population_sha256",
            "policy_population_sha256",
        ):
            _sha256(getattr(self, name), name)
        for name in ("decision_count", "policy_count", "outcome_count"):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"A1 Phase22 scientific manifest {name} invalid"
                )
        if self.decision_count < 4:
            raise CiboCapitalManagementError(
                "A1 Phase22 scientific manifest requires at least four decisions"
            )
        if self.policy_count != self.decision_count or not self.exact_policy_coverage:
            raise CiboCapitalManagementError(
                "A1 Phase22 scientific manifest requires exact policy coverage"
            )
        if tuple(item.fold_id for item in self.folds) != _CANONICAL_FOLDS:
            raise CiboCapitalManagementError(
                "A1 Phase22 scientific manifest requires ordered WF1..WF4"
            )
        if sum(item.decision_count for item in self.folds) != self.decision_count:
            raise CiboCapitalManagementError(
                "A1 Phase22 scientific manifest fold population drift"
            )
        if (
            not self.historical_replay_only
            or not self.folds_defined_without_outcomes
            or self.post_evidence_retune_allowed
            or self.outcome_aware_population_selection_allowed
            or self.productive_authority
            or self.live_authorized
            or self.real_capital_authorized
            or self.global_ledger_reconciled
            or self.certification_authorized
        ):
            raise CiboCapitalManagementError(
                "A1 Phase22 scientific manifest governance contamination"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        for fold in payload["folds"]:
            fold["first_decision_at"] = fold["first_decision_at"].isoformat()
            fold["last_decision_at"] = fold["last_decision_at"].isoformat()
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_a1_phase22_scientific_consumption_manifest(
    *,
    evidence_book: VersionedPhase22HistoricalReplayEvidenceBook,
    policy_book: VersionedPhase20ForwardPolicyBook,
) -> A1Phase22ScientificConsumptionManifest:
    """Bind one immutable Phase22 population for all A1 scientific consumers."""

    if not isinstance(
        evidence_book,
        VersionedPhase22HistoricalReplayEvidenceBook,
    ):
        raise CiboCapitalManagementError(
            "A1 Phase22 manifest requires canonical replay evidence book"
        )
    if not isinstance(policy_book, VersionedPhase20ForwardPolicyBook):
        raise CiboCapitalManagementError(
            "A1 Phase22 manifest requires canonical policy book"
        )
    if len(evidence_book.decisions) < 4:
        raise CiboCapitalManagementError(
            "A1 Phase22 manifest requires at least four replay decisions"
        )

    ordered = tuple(
        sorted(
            evidence_book.decisions,
            key=lambda item: (item.decision_at, item.evidence_sha256),
        )
    )
    candidate_ids = {item.candidate_id for item in ordered}
    code_shas = {item.code_sha for item in ordered}
    parameter_shas = {item.parameter_sha256 for item in ordered}
    if len(candidate_ids) != 1 or len(code_shas) != 1 or len(parameter_shas) != 1:
        raise CiboCapitalManagementError(
            "A1 Phase22 manifest candidate/code/parameter drift"
        )
    candidate_id = next(iter(candidate_ids))
    code_sha = next(iter(code_shas))
    parameter_sha256 = next(iter(parameter_shas))
    if _SHA1_RE.fullmatch(code_sha) is None:
        raise CiboCapitalManagementError(
            "A1 Phase22 manifest decision code SHA invalid"
        )
    _sha256(parameter_sha256, "parameter_sha256")

    traders: set[str] = set()
    for decision in ordered:
        payload = _payload(decision.canonical_payload_json)
        raw_candidates = payload.get("candidates")
        if not isinstance(raw_candidates, list):
            raise CiboCapitalManagementError(
                "A1 Phase22 manifest candidates must be list"
            )
        for row in raw_candidates:
            if not isinstance(row, dict):
                raise CiboCapitalManagementError(
                    "A1 Phase22 manifest candidate row invalid"
                )
            candidate = row.get("candidate")
            if not isinstance(candidate, dict):
                raise CiboCapitalManagementError(
                    "A1 Phase22 manifest candidate payload invalid"
                )
            trader_id = candidate.get("trader_id")
            if isinstance(trader_id, str) and trader_id:
                traders.add(trader_id)

    decisions_by_sha = {item.evidence_sha256 for item in ordered}
    policies_by_sha = {item.evidence_sha256 for item in policy_book.decisions}
    if decisions_by_sha != policies_by_sha:
        raise CiboCapitalManagementError(
            "A1 Phase22 manifest policy population must exactly match decisions"
        )
    for policy in policy_book.decisions:
        _verify_policy(policy)

    folds = _build_folds(ordered)
    return A1Phase22ScientificConsumptionManifest(
        manifest_id=MANIFEST_ID,
        candidate_id=candidate_id,
        code_sha=code_sha,
        parameter_sha256=parameter_sha256,
        amendment_sha256=evidence_book.amendment_sha256,
        source_population_sha256=_source_population_sha256(evidence_book),
        policy_population_sha256=_policy_population_sha256(policy_book),
        decision_count=len(ordered),
        policy_count=len(policy_book.decisions),
        outcome_count=len(evidence_book.outcomes),
        trader_ids=tuple(sorted(traders)),
        folds=folds,
        exact_policy_coverage=True,
        historical_replay_only=True,
        folds_defined_without_outcomes=True,
    )


def _build_folds(decisions: tuple) -> tuple[A1Phase22PopulationFold, ...]:
    base, remainder = divmod(len(decisions), 4)
    result: list[A1Phase22PopulationFold] = []
    start = 0
    for index, fold_id in enumerate(_CANONICAL_FOLDS):
        count = base + (1 if index < remainder else 0)
        rows = decisions[start : start + count]
        start += count
        raw = json.dumps(
            [item.evidence_sha256 for item in rows],
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        result.append(
            A1Phase22PopulationFold(
                fold_id=fold_id,
                decision_count=len(rows),
                first_decision_at=rows[0].decision_at,
                last_decision_at=rows[-1].decision_at,
                population_sha256=(
                    "sha256:" + hashlib.sha256(raw).hexdigest()
                ),
            )
        )
    return tuple(result)


def _payload(raw: str) -> dict[str, object]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "A1 Phase22 manifest decision payload invalid JSON"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "A1 Phase22 manifest decision payload must be object"
        )
    if payload.get("evidence_kind") != "HISTORICAL_REPLAY_OBSERVED":
        raise CiboCapitalManagementError(
            "A1 Phase22 manifest requires historical replay evidence"
        )
    return payload


def _verify_policy(policy: Phase20ForwardPolicyDecisionSeal) -> None:
    expected = "sha256:" + hashlib.sha256(
        policy.canonical_record_json.encode("utf-8")
    ).hexdigest()
    if expected != policy.policy_record_sha256:
        raise CiboCapitalManagementError(
            "A1 Phase22 manifest policy digest drift"
        )
    try:
        record = json.loads(policy.canonical_record_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "A1 Phase22 manifest policy JSON invalid"
        ) from error
    if not isinstance(record, dict):
        raise CiboCapitalManagementError(
            "A1 Phase22 manifest policy record must be object"
        )
    if record.get("evidence_sha256") != policy.evidence_sha256:
        raise CiboCapitalManagementError(
            "A1 Phase22 manifest policy/evidence binding drift"
        )


def _source_population_sha256(
    book: VersionedPhase22HistoricalReplayEvidenceBook,
) -> str:
    raw = json.dumps(
        {
            "generation": book.generation,
            "amendment_sha256": book.amendment_sha256,
            "decisions": [item.evidence_sha256 for item in book.decisions],
            "outcomes": [item.fingerprint() for item in book.outcomes],
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _policy_population_sha256(
    book: VersionedPhase20ForwardPolicyBook,
) -> str:
    raw = json.dumps(
        {
            "generation": book.generation,
            "policies": [
                {
                    "evidence_sha256": item.evidence_sha256,
                    "policy_record_sha256": item.policy_record_sha256,
                }
                for item in book.decisions
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _sha256(value: str, name: str) -> None:
    if _SHA256_RE.fullmatch(value) is None:
        raise CiboCapitalManagementError(
            f"A1 Phase22 manifest {name} must be sha256:<64 lowercase hex>"
        )
