"""Durable Phase22 V2 historical-replay stores.

The five physical stores are Phase22-native. They preserve the canonical
decision/policy surfaces consumed by qualification while representing Risk,
settlement and release as explicit counterfactual historical replay evidence.
No historical broker order, deal, position, fill or release identifier exists.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import RiskDecision
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    Phase20ForwardPolicyDecisionSeal,
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
)
from qore.infrastructure.cibo_phase22_historical_replay_settlement import (
    Phase22HistoricalReplayOutcomeSeal,
    VersionedPhase22HistoricalReplayEvidenceBook,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import (
    V2_SOURCE_BINDINGS,
)
from qore.infrastructure.cibo_phase22_store_contract import (
    PHASE22_STORE_IDENTITIES,
    Phase22StoreIdentity,
)

_STORE_BY_NAME = {item.name: item for item in PHASE22_STORE_IDENTITIES}
_V2_COLLECTORS = tuple(
    sorted({item.collector_git_sha for item in V2_SOURCE_BINDINGS})
)


@dataclass(frozen=True, slots=True)
class Phase22HistoricalExecutedRiskSeal:
    evidence_id: str
    decision_evidence_sha256: str
    signal_fingerprint: str
    trader_id: str
    qore_symbol: str
    decided_at: datetime
    risk_decision: RiskDecision
    requested_stop_risk_usd: Decimal
    authorized_stop_risk_usd: Decimal
    authorized_margin_usd: Decimal
    risk_model_sha256: str
    counterfactual_historical_replay: bool = True
    historical_broker_fill_claimed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.evidence_id.startswith("phase22-replay-risk:"):
            raise CiboCapitalManagementError(
                "Phase22 replay risk evidence id drift"
            )
        if (
            not self.decision_evidence_sha256.startswith("sha256:")
            or len(self.decision_evidence_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "Phase22 replay risk decision digest invalid"
            )
        if not self.signal_fingerprint or not self.trader_id or not self.qore_symbol:
            raise CiboCapitalManagementError(
                "Phase22 replay risk lineage identity required"
            )
        if self.decided_at.tzinfo is None or self.decided_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "Phase22 replay risk decision time must be timezone-aware"
            )
        if not isinstance(self.risk_decision, RiskDecision):
            raise CiboCapitalManagementError(
                "Phase22 replay risk decision enum invalid"
            )
        for name in (
            "requested_stop_risk_usd",
            "authorized_stop_risk_usd",
            "authorized_margin_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase22 replay risk {name} invalid"
                )
        if self.requested_stop_risk_usd <= 0:
            raise CiboCapitalManagementError(
                "Phase22 replay requested risk must be positive"
            )
        if self.authorized_stop_risk_usd > self.requested_stop_risk_usd:
            raise CiboCapitalManagementError(
                "Phase22 replay Risk cannot authorize above requested risk"
            )
        if self.risk_decision is RiskDecision.REJECT:
            if self.authorized_stop_risk_usd != 0 or self.authorized_margin_usd != 0:
                raise CiboCapitalManagementError(
                    "Phase22 replay rejected Risk must authorize zero capacity"
                )
        elif self.authorized_stop_risk_usd <= 0 or self.authorized_margin_usd <= 0:
            raise CiboCapitalManagementError(
                "Phase22 replay allowed/reduced Risk requires positive capacity"
            )
        if self.risk_decision is RiskDecision.REDUCE:
            if self.authorized_stop_risk_usd >= self.requested_stop_risk_usd:
                raise CiboCapitalManagementError(
                    "Phase22 replay REDUCE must reduce requested risk"
                )
        if not self.risk_model_sha256.startswith("sha256:") or len(
            self.risk_model_sha256
        ) != 71:
            raise CiboCapitalManagementError(
                "Phase22 replay risk model digest invalid"
            )
        if (
            not self.counterfactual_historical_replay
            or self.historical_broker_fill_claimed
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "Phase22 replay risk governance contamination"
            )

    def fingerprint(self) -> str:
        return _fingerprint(_risk_to_json(self))


@dataclass(frozen=True, slots=True)
class Phase22HistoricalT20ReleaseSeal:
    evidence_id: str
    decision_evidence_sha256: str
    signal_fingerprint: str
    risk_evidence_id: str
    settlement_evidence_id: str
    released_at: datetime
    released_stop_risk_usd: Decimal
    released_margin_usd: Decimal
    counterfactual_historical_replay: bool = True
    historical_provider_release_claimed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.evidence_id.startswith("phase22-replay-release:"):
            raise CiboCapitalManagementError(
                "Phase22 replay release evidence id drift"
            )
        if (
            not self.decision_evidence_sha256.startswith("sha256:")
            or len(self.decision_evidence_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "Phase22 replay release decision digest invalid"
            )
        if (
            not self.signal_fingerprint
            or not self.risk_evidence_id
            or not self.settlement_evidence_id
        ):
            raise CiboCapitalManagementError(
                "Phase22 replay release lineage required"
            )
        if self.released_at.tzinfo is None or self.released_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "Phase22 replay release time must be timezone-aware"
            )
        for name in ("released_stop_risk_usd", "released_margin_usd"):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase22 replay release {name} must be positive"
                )
        if (
            not self.counterfactual_historical_replay
            or self.historical_provider_release_claimed
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "Phase22 replay release governance contamination"
            )

    def fingerprint(self) -> str:
        return _fingerprint(_release_to_json(self))


@dataclass(frozen=True, slots=True)
class VersionedPhase22HistoricalExecutedRiskBook:
    generation: int
    executed_risk: tuple[Phase22HistoricalExecutedRiskSeal, ...] = ()

    def __post_init__(self) -> None:
        _generation(self.generation)
        keys = tuple(
            (item.decision_evidence_sha256, item.signal_fingerprint)
            for item in self.executed_risk
        )
        if len(keys) != len(set(keys)):
            raise CiboCapitalManagementError(
                "Phase22 replay risk book duplicate decision/signal"
            )


@dataclass(frozen=True, slots=True)
class VersionedPhase22HistoricalSettlementBook:
    generation: int
    settlements: tuple[Phase22HistoricalReplayOutcomeSeal, ...] = ()

    def __post_init__(self) -> None:
        _generation(self.generation)
        keys = tuple(
            (item.decision_evidence_sha256, item.signal_fingerprint)
            for item in self.settlements
        )
        if len(keys) != len(set(keys)):
            raise CiboCapitalManagementError(
                "Phase22 replay settlement book duplicate decision/signal"
            )


@dataclass(frozen=True, slots=True)
class VersionedPhase22HistoricalReleaseBook:
    generation: int
    release_chain: tuple[Phase22HistoricalT20ReleaseSeal, ...] = ()

    def __post_init__(self) -> None:
        _generation(self.generation)
        keys = tuple(
            (item.decision_evidence_sha256, item.signal_fingerprint)
            for item in self.release_chain
        )
        if len(keys) != len(set(keys)):
            raise CiboCapitalManagementError(
                "Phase22 replay release book duplicate decision/signal"
            )


@dataclass(frozen=True, slots=True)
class Phase22HistoricalReplayStoreSet:
    holdout_evidence: VersionedPhase22HistoricalReplayEvidenceBook
    holdout_policy: VersionedPhase20ForwardPolicyBook
    executed_risk: VersionedPhase22HistoricalExecutedRiskBook
    cma_settlement: VersionedPhase22HistoricalSettlementBook
    t20_release: VersionedPhase22HistoricalReleaseBook

    def __post_init__(self) -> None:
        decision_shas = {
            item.evidence_sha256 for item in self.holdout_evidence.decisions
        }
        policy_shas = {
            item.evidence_sha256 for item in self.holdout_policy.decisions
        }
        if policy_shas != decision_shas:
            raise CiboCapitalManagementError(
                "Phase22 replay store-set decision/policy mismatch"
            )
        selected_keys = {
            (policy.evidence_sha256, signal)
            for policy in self.holdout_policy.decisions
            for signal in policy.selected_signal_fingerprints
        }
        risk_by_key = {
            (item.decision_evidence_sha256, item.signal_fingerprint): item
            for item in self.executed_risk.executed_risk
        }
        if set(risk_by_key) != selected_keys:
            raise CiboCapitalManagementError(
                "Phase22 replay store-set Risk surface must equal CIBO selection"
            )
        outcome_by_key = {
            (item.decision_evidence_sha256, item.signal_fingerprint): item
            for item in self.holdout_evidence.outcomes
        }
        settlement_by_key = {
            (item.decision_evidence_sha256, item.signal_fingerprint): item
            for item in self.cma_settlement.settlements
        }
        if outcome_by_key != settlement_by_key:
            raise CiboCapitalManagementError(
                "Phase22 replay settlement must equal qualification outcomes"
            )
        accepted_keys = {
            key
            for key, item in risk_by_key.items()
            if item.risk_decision is not RiskDecision.REJECT
        }
        if set(outcome_by_key) != accepted_keys:
            raise CiboCapitalManagementError(
                "Phase22 replay outcomes must equal Risk-authorized selections"
            )
        release_by_key = {
            (item.decision_evidence_sha256, item.signal_fingerprint): item
            for item in self.t20_release.release_chain
        }
        if set(release_by_key) != accepted_keys:
            raise CiboCapitalManagementError(
                "Phase22 replay release chain must equal settled selections"
            )
        for key in accepted_keys:
            risk = risk_by_key[key]
            outcome = outcome_by_key[key]
            release = release_by_key[key]
            if outcome.executed_initial_stop_risk_usd != risk.authorized_stop_risk_usd:
                raise CiboCapitalManagementError(
                    "Phase22 replay outcome/Risk authorized risk drift"
                )
            if release.risk_evidence_id != risk.evidence_id:
                raise CiboCapitalManagementError(
                    "Phase22 replay release/Risk lineage drift"
                )
            if release.settlement_evidence_id != outcome.evidence_id:
                raise CiboCapitalManagementError(
                    "Phase22 replay release/settlement lineage drift"
                )
            if release.released_stop_risk_usd != risk.authorized_stop_risk_usd:
                raise CiboCapitalManagementError(
                    "Phase22 replay released stop risk drift"
                )
            if release.released_margin_usd != risk.authorized_margin_usd:
                raise CiboCapitalManagementError(
                    "Phase22 replay released margin drift"
                )
            if release.released_at != outcome.capital_released_at:
                raise CiboCapitalManagementError(
                    "Phase22 replay release timestamp drift"
                )


class DurablePhase22HistoricalForwardEvidenceStore:
    def __init__(self, path: Path) -> None:
        self._path = _path(path)

    def load(self) -> VersionedPhase22HistoricalReplayEvidenceBook | _EmptyBook:
        if not self._path.exists():
            return _EmptyBook()
        raw = _read(self._path, _STORE_BY_NAME["HOLDOUT_FORWARD_EVIDENCE"])
        return _evidence_book_from_json(raw)

    def persist_final(
        self,
        book: VersionedPhase22HistoricalReplayEvidenceBook,
    ) -> None:
        if not isinstance(book, VersionedPhase22HistoricalReplayEvidenceBook):
            raise CiboCapitalManagementError(
                "Phase22 historical evidence store requires canonical replay book"
            )
        _create_once(
            self._path,
            _evidence_book_to_json(book),
            _STORE_BY_NAME["HOLDOUT_FORWARD_EVIDENCE"],
        )


class DurablePhase22HistoricalPolicyStore:
    def __init__(self, path: Path) -> None:
        self._path = _path(path)

    def load(self) -> VersionedPhase20ForwardPolicyBook:
        if not self._path.exists():
            return VersionedPhase20ForwardPolicyBook(generation=0)
        raw = _read(self._path, _STORE_BY_NAME["HOLDOUT_POLICY"])
        return _policy_book_from_json(raw)

    def persist_final(self, book: VersionedPhase20ForwardPolicyBook) -> None:
        if not isinstance(book, VersionedPhase20ForwardPolicyBook):
            raise CiboCapitalManagementError(
                "Phase22 policy store requires canonical policy book"
            )
        _create_once(
            self._path,
            _policy_book_to_json(book),
            _STORE_BY_NAME["HOLDOUT_POLICY"],
        )


class DurablePhase22HistoricalExecutedRiskStore:
    def __init__(self, path: Path) -> None:
        self._path = _path(path)

    def load(self) -> VersionedPhase22HistoricalExecutedRiskBook:
        if not self._path.exists():
            return VersionedPhase22HistoricalExecutedRiskBook(generation=0)
        raw = _read(self._path, _STORE_BY_NAME["EXECUTED_RISK"])
        return VersionedPhase22HistoricalExecutedRiskBook(
            generation=_required_int(raw["generation"], "generation"),
            executed_risk=tuple(
                _risk_from_json(item) for item in _list(raw["executed_risk"])
            ),
        )

    def persist_final(
        self,
        book: VersionedPhase22HistoricalExecutedRiskBook,
    ) -> None:
        _create_once(
            self._path,
            {
                "generation": book.generation,
                "executed_risk": [_risk_to_json(item) for item in book.executed_risk],
            },
            _STORE_BY_NAME["EXECUTED_RISK"],
        )


class DurablePhase22HistoricalSettlementStore:
    def __init__(self, path: Path) -> None:
        self._path = _path(path)

    def load(self) -> VersionedPhase22HistoricalSettlementBook:
        if not self._path.exists():
            return VersionedPhase22HistoricalSettlementBook(generation=0)
        raw = _read(self._path, _STORE_BY_NAME["CMA_SETTLEMENT"])
        return VersionedPhase22HistoricalSettlementBook(
            generation=_required_int(raw["generation"], "generation"),
            settlements=tuple(
                _outcome_from_json(item) for item in _list(raw["settlements"])
            ),
        )

    def persist_final(
        self,
        book: VersionedPhase22HistoricalSettlementBook,
    ) -> None:
        _create_once(
            self._path,
            {
                "generation": book.generation,
                "settlements": [item.as_dict() for item in book.settlements],
            },
            _STORE_BY_NAME["CMA_SETTLEMENT"],
        )


class DurablePhase22HistoricalReleaseStore:
    def __init__(self, path: Path) -> None:
        self._path = _path(path)

    def load(self) -> VersionedPhase22HistoricalReleaseBook:
        if not self._path.exists():
            return VersionedPhase22HistoricalReleaseBook(generation=0)
        raw = _read(self._path, _STORE_BY_NAME["T20_RELEASE"])
        return VersionedPhase22HistoricalReleaseBook(
            generation=_required_int(raw["generation"], "generation"),
            release_chain=tuple(
                _release_from_json(item) for item in _list(raw["release_chain"])
            ),
        )

    def persist_final(
        self,
        book: VersionedPhase22HistoricalReleaseBook,
    ) -> None:
        _create_once(
            self._path,
            {
                "generation": book.generation,
                "release_chain": [
                    _release_to_json(item) for item in book.release_chain
                ],
            },
            _STORE_BY_NAME["T20_RELEASE"],
        )


@dataclass(frozen=True, slots=True)
class _EmptyBook:
    generation: int = 0


def build_phase22_historical_risk_seal(
    *,
    decision: Phase20ForwardDecisionSeal,
    signal_fingerprint: str,
    trader_id: str,
    qore_symbol: str,
    decided_at: datetime,
    risk_decision: RiskDecision,
    requested_stop_risk_usd: Decimal,
    authorized_stop_risk_usd: Decimal,
    authorized_margin_usd: Decimal,
    risk_model_sha256: str,
) -> Phase22HistoricalExecutedRiskSeal:
    raw = _json(
        {
            "decision_evidence_sha256": decision.evidence_sha256,
            "signal_fingerprint": signal_fingerprint,
            "risk_decision": risk_decision.value,
            "authorized_stop_risk_usd": authorized_stop_risk_usd,
            "authorized_margin_usd": authorized_margin_usd,
            "risk_model_sha256": risk_model_sha256,
        }
    )
    return Phase22HistoricalExecutedRiskSeal(
        evidence_id="phase22-replay-risk:" + hashlib.sha256(raw.encode()).hexdigest(),
        decision_evidence_sha256=decision.evidence_sha256,
        signal_fingerprint=signal_fingerprint,
        trader_id=trader_id,
        qore_symbol=qore_symbol,
        decided_at=decided_at,
        risk_decision=risk_decision,
        requested_stop_risk_usd=requested_stop_risk_usd,
        authorized_stop_risk_usd=authorized_stop_risk_usd,
        authorized_margin_usd=authorized_margin_usd,
        risk_model_sha256=risk_model_sha256,
    )


def build_phase22_historical_release_seal(
    *,
    risk: Phase22HistoricalExecutedRiskSeal,
    settlement: Phase22HistoricalReplayOutcomeSeal,
) -> Phase22HistoricalT20ReleaseSeal:
    if risk.risk_decision is RiskDecision.REJECT:
        raise CiboCapitalManagementError(
            "Phase22 replay rejected Risk has no release event"
        )
    if (
        risk.decision_evidence_sha256 != settlement.decision_evidence_sha256
        or risk.signal_fingerprint != settlement.signal_fingerprint
    ):
        raise CiboCapitalManagementError(
            "Phase22 replay release source lineage mismatch"
        )
    raw = _json(
        {
            "risk_evidence_id": risk.evidence_id,
            "settlement_evidence_id": settlement.evidence_id,
            "released_at": settlement.capital_released_at,
        }
    )
    return Phase22HistoricalT20ReleaseSeal(
        evidence_id=(
            "phase22-replay-release:" + hashlib.sha256(raw.encode()).hexdigest()
        ),
        decision_evidence_sha256=risk.decision_evidence_sha256,
        signal_fingerprint=risk.signal_fingerprint,
        risk_evidence_id=risk.evidence_id,
        settlement_evidence_id=settlement.evidence_id,
        released_at=settlement.capital_released_at,
        released_stop_risk_usd=risk.authorized_stop_risk_usd,
        released_margin_usd=risk.authorized_margin_usd,
    )


def persist_phase22_historical_store_set(
    *,
    root: Path,
    books: Phase22HistoricalReplayStoreSet,
) -> tuple[str, ...]:
    evidence_store = DurablePhase22HistoricalForwardEvidenceStore(
        root / "holdout-forward-evidence.json"
    )
    policy_store = DurablePhase22HistoricalPolicyStore(
        root / "holdout-policy.json"
    )
    risk_store = DurablePhase22HistoricalExecutedRiskStore(
        root / "executed-risk.json"
    )
    settlement_store = DurablePhase22HistoricalSettlementStore(
        root / "cma-settlement.json"
    )
    release_store = DurablePhase22HistoricalReleaseStore(
        root / "t20-release.json"
    )
    paths = (
        evidence_store._path,
        policy_store._path,
        risk_store._path,
        settlement_store._path,
        release_store._path,
    )
    if any(path.exists() for path in paths):
        raise CiboCapitalManagementError(
            "Phase22 historical store set must be create-once and pristine"
        )
    written: list[Path] = []
    try:
        evidence_store.persist_final(books.holdout_evidence)
        written.append(evidence_store._path)

        policy_store.persist_final(books.holdout_policy)
        written.append(policy_store._path)

        risk_store.persist_final(books.executed_risk)
        written.append(risk_store._path)

        settlement_store.persist_final(books.cma_settlement)
        written.append(settlement_store._path)

        release_store.persist_final(books.t20_release)
        written.append(release_store._path)
    except Exception:
        # Do not roll back successfully written evidence: durable one-shot claim
        # must remain fail-closed and forensic reconstruction must see partial
        # persistence rather than a misleading pristine surface.
        raise
    return tuple(_file_sha256(path) for path in written)


def _evidence_book_to_json(
    book: VersionedPhase22HistoricalReplayEvidenceBook,
) -> dict[str, object]:
    return {
        "generation": book.generation,
        "amendment_sha256": book.amendment_sha256,
        "source_receipt_sha256": book.source_receipt_sha256,
        "source_collector_git_shas": list(book.source_collector_git_shas),
        "qualification_time_basis": book.qualification_time_basis,
        "qualification_evidence_kind": book.qualification_evidence_kind,
        "decisions": [_decision_to_json(item) for item in book.decisions],
        "decisions_and_outcomes": [
            {
                "kind": "DECISION",
                "value": _decision_to_json(item),
            }
            for item in book.decisions
        ]
        + [
            {
                "kind": "OUTCOME",
                "value": item.as_dict(),
            }
            for item in book.outcomes
        ],
        "outcomes": [item.as_dict() for item in book.outcomes],
    }


def _evidence_book_from_json(
    raw: dict[str, object],
) -> VersionedPhase22HistoricalReplayEvidenceBook:
    return VersionedPhase22HistoricalReplayEvidenceBook(
        generation=_required_int(raw["generation"], "generation"),
        amendment_sha256=str(raw["amendment_sha256"]),
        decisions=tuple(
            _decision_from_json(item) for item in _list(raw["decisions"])
        ),
        outcomes=tuple(
            _outcome_from_json(item) for item in _list(raw["outcomes"])
        ),
        source_receipt_sha256=str(raw["source_receipt_sha256"]),
        source_collector_git_shas=tuple(
            str(item) for item in _list(raw["source_collector_git_shas"])
        ),
        qualification_time_basis=str(raw["qualification_time_basis"]),
        qualification_evidence_kind=str(raw["qualification_evidence_kind"]),
    )


def _policy_book_to_json(
    book: VersionedPhase20ForwardPolicyBook,
) -> dict[str, object]:
    return {
        "generation": book.generation,
        "policy_decisions": [_policy_to_json(item) for item in book.decisions],
        "decisions": [_policy_to_json(item) for item in book.decisions],
    }


def _policy_book_from_json(
    raw: dict[str, object],
) -> VersionedPhase20ForwardPolicyBook:
    return VersionedPhase20ForwardPolicyBook(
        generation=_required_int(raw["generation"], "generation"),
        decisions=tuple(
            _policy_from_json(item) for item in _list(raw["decisions"])
        ),
    )


def _decision_to_json(item: Phase20ForwardDecisionSeal) -> dict[str, object]:
    return {
        "evidence_id": item.evidence_id,
        "decision_epoch_id": item.decision_epoch_id,
        "evidence_sha256": item.evidence_sha256,
        "decision_at": item.decision_at.isoformat(),
        "candidate_id": item.candidate_id,
        "code_sha": item.code_sha,
        "parameter_sha256": item.parameter_sha256,
        "signal_fingerprints": list(item.signal_fingerprints),
        "canonical_payload_json": item.canonical_payload_json,
        "collector_git_sha": item.collector_git_sha,
        "sealed_at": None if item.sealed_at is None else item.sealed_at.isoformat(),
        "seal_deadline_at": (
            None
            if item.seal_deadline_at is None
            else item.seal_deadline_at.isoformat()
        ),
    }


def _decision_from_json(value: object) -> Phase20ForwardDecisionSeal:
    if not isinstance(value, dict):
        raise CiboCapitalManagementError("Phase22 replay decision row invalid")
    return Phase20ForwardDecisionSeal(
        evidence_id=str(value["evidence_id"]),
        decision_epoch_id=str(value["decision_epoch_id"]),
        evidence_sha256=str(value["evidence_sha256"]),
        decision_at=datetime.fromisoformat(str(value["decision_at"])),
        candidate_id=str(value["candidate_id"]),
        code_sha=str(value["code_sha"]),
        parameter_sha256=str(value["parameter_sha256"]),
        signal_fingerprints=tuple(
            str(item) for item in _list(value["signal_fingerprints"])
        ),
        canonical_payload_json=str(value["canonical_payload_json"]),
        collector_git_sha=(
            None
            if value.get("collector_git_sha") is None
            else str(value["collector_git_sha"])
        ),
        sealed_at=(
            None
            if value.get("sealed_at") is None
            else datetime.fromisoformat(str(value["sealed_at"]))
        ),
        seal_deadline_at=(
            None
            if value.get("seal_deadline_at") is None
            else datetime.fromisoformat(str(value["seal_deadline_at"]))
        ),
    )


def _policy_to_json(item: Phase20ForwardPolicyDecisionSeal) -> dict[str, object]:
    return {
        "evidence_sha256": item.evidence_sha256,
        "policy_record_sha256": item.policy_record_sha256,
        "allocator_disposition": item.allocator_disposition,
        "selected_signal_fingerprints": list(item.selected_signal_fingerprints),
        "canonical_record_json": item.canonical_record_json,
    }


def _policy_from_json(value: object) -> Phase20ForwardPolicyDecisionSeal:
    if not isinstance(value, dict):
        raise CiboCapitalManagementError("Phase22 replay policy row invalid")
    seal = Phase20ForwardPolicyDecisionSeal(
        evidence_sha256=str(value["evidence_sha256"]),
        policy_record_sha256=str(value["policy_record_sha256"]),
        allocator_disposition=str(value["allocator_disposition"]),
        selected_signal_fingerprints=tuple(
            str(item) for item in _list(value["selected_signal_fingerprints"])
        ),
        canonical_record_json=str(value["canonical_record_json"]),
    )
    if seal.policy_record_sha256 != _sha256_text(seal.canonical_record_json):
        raise CiboCapitalManagementError(
            "Phase22 replay persisted policy canonical SHA mismatch"
        )
    record = json.loads(seal.canonical_record_json)
    if record.get("evidence_sha256") != seal.evidence_sha256:
        raise CiboCapitalManagementError(
            "Phase22 replay persisted policy evidence binding mismatch"
        )
    return seal


def _outcome_from_json(value: object) -> Phase22HistoricalReplayOutcomeSeal:
    if not isinstance(value, dict):
        raise CiboCapitalManagementError("Phase22 replay outcome row invalid")
    return Phase22HistoricalReplayOutcomeSeal(
        evidence_id=str(value["evidence_id"]),
        decision_evidence_sha256=str(value["decision_evidence_sha256"]),
        signal_fingerprint=str(value["signal_fingerprint"]),
        trader_id=str(value["trader_id"]),
        qore_symbol=str(value["qore_symbol"]),
        observed_at=datetime.fromisoformat(str(value["observed_at"])),
        gross_structural_outcome_r=Decimal(str(value["gross_structural_outcome_r"])),
        provider_execution_adjustment_usd=Decimal(
            str(value["provider_execution_adjustment_usd"])
        ),
        decision_provider_cost_proxy_usd=Decimal(
            str(value["decision_provider_cost_proxy_usd"])
        ),
        realized_net_pnl_usd=Decimal(str(value["realized_net_pnl_usd"])),
        executed_initial_stop_risk_usd=Decimal(
            str(value["executed_initial_stop_risk_usd"])
        ),
        realized_structural_outcome_r=Decimal(
            str(value["realized_structural_outcome_r"])
        ),
        capital_deployed_at=datetime.fromisoformat(
            str(value["capital_deployed_at"])
        ),
        capital_released_at=datetime.fromisoformat(
            str(value["capital_released_at"])
        ),
        capital_minutes=Decimal(str(value["capital_minutes"])),
        provider_calibration_sha256=str(value["provider_calibration_sha256"]),
        amendment_sha256=str(value["amendment_sha256"]),
        execution_economics_kind=str(value["execution_economics_kind"]),
        counterfactual_historical_replay=bool(
            value["counterfactual_historical_replay"]
        ),
        historical_broker_fills_claimed=bool(
            value["historical_broker_fills_claimed"]
        ),
        fabricated_execution_evidence_used=bool(
            value["fabricated_execution_evidence_used"]
        ),
        outcome_reconciled=bool(value["outcome_reconciled"]),
    )


def _risk_to_json(item: Phase22HistoricalExecutedRiskSeal) -> dict[str, object]:
    payload = asdict(item)
    payload["decided_at"] = item.decided_at.isoformat()
    payload["risk_decision"] = item.risk_decision.value
    for name in (
        "requested_stop_risk_usd",
        "authorized_stop_risk_usd",
        "authorized_margin_usd",
    ):
        payload[name] = format(getattr(item, name), "f")
    return payload


def _risk_from_json(value: object) -> Phase22HistoricalExecutedRiskSeal:
    if not isinstance(value, dict):
        raise CiboCapitalManagementError("Phase22 replay risk row invalid")
    return Phase22HistoricalExecutedRiskSeal(
        evidence_id=str(value["evidence_id"]),
        decision_evidence_sha256=str(value["decision_evidence_sha256"]),
        signal_fingerprint=str(value["signal_fingerprint"]),
        trader_id=str(value["trader_id"]),
        qore_symbol=str(value["qore_symbol"]),
        decided_at=datetime.fromisoformat(str(value["decided_at"])),
        risk_decision=RiskDecision(str(value["risk_decision"])),
        requested_stop_risk_usd=Decimal(str(value["requested_stop_risk_usd"])),
        authorized_stop_risk_usd=Decimal(str(value["authorized_stop_risk_usd"])),
        authorized_margin_usd=Decimal(str(value["authorized_margin_usd"])),
        risk_model_sha256=str(value["risk_model_sha256"]),
        counterfactual_historical_replay=bool(
            value["counterfactual_historical_replay"]
        ),
        historical_broker_fill_claimed=bool(
            value["historical_broker_fill_claimed"]
        ),
        productive_authority=bool(value["productive_authority"]),
    )


def _release_to_json(item: Phase22HistoricalT20ReleaseSeal) -> dict[str, object]:
    payload = asdict(item)
    payload["released_at"] = item.released_at.isoformat()
    for name in ("released_stop_risk_usd", "released_margin_usd"):
        payload[name] = format(getattr(item, name), "f")
    return payload


def _release_from_json(value: object) -> Phase22HistoricalT20ReleaseSeal:
    if not isinstance(value, dict):
        raise CiboCapitalManagementError("Phase22 replay release row invalid")
    return Phase22HistoricalT20ReleaseSeal(
        evidence_id=str(value["evidence_id"]),
        decision_evidence_sha256=str(value["decision_evidence_sha256"]),
        signal_fingerprint=str(value["signal_fingerprint"]),
        risk_evidence_id=str(value["risk_evidence_id"]),
        settlement_evidence_id=str(value["settlement_evidence_id"]),
        released_at=datetime.fromisoformat(str(value["released_at"])),
        released_stop_risk_usd=Decimal(str(value["released_stop_risk_usd"])),
        released_margin_usd=Decimal(str(value["released_margin_usd"])),
        counterfactual_historical_replay=bool(
            value["counterfactual_historical_replay"]
        ),
        historical_provider_release_claimed=bool(
            value["historical_provider_release_claimed"]
        ),
        productive_authority=bool(value["productive_authority"]),
    )


def _create_once(
    path: Path,
    payload: dict[str, object],
    identity: Phase22StoreIdentity,
) -> None:
    if path.exists():
        raise CiboCapitalManagementError(
            f"Phase22 store already exists: {identity.name}"
        )
    full = {
        "schema": identity.schema,
        "phase": "PHASE22_V2",
        "store_name": identity.name,
        **payload,
        "fresh_outcomes_executed": True,
        "counterfactual_historical_replay": True,
        "historical_broker_execution_claimed": False,
        "productive_authority": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp")
    try:
        with temp.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(full, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _read(path: Path, identity: Phase22StoreIdentity) -> dict[str, object]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CiboCapitalManagementError(
            f"Phase22 store unreadable: {identity.name}"
        ) from error
    if (
        not isinstance(raw, dict)
        or raw.get("schema") != identity.schema
        or raw.get("phase") != "PHASE22_V2"
        or raw.get("store_name") != identity.name
        or raw.get("productive_authority") is not False
        or raw.get("historical_broker_execution_claimed") is not False
        or raw.get("counterfactual_historical_replay") is not True
    ):
        raise CiboCapitalManagementError(
            f"Phase22 store contract drift: {identity.name}"
        )
    return raw


def _path(value: Path) -> Path:
    if not isinstance(value, Path):
        raise TypeError("Phase22 store path must be pathlib.Path")
    return value


def _list(value: object) -> list[Any]:
    if not isinstance(value, list):
        raise CiboCapitalManagementError("Phase22 persisted collection invalid")
    return value


def _required_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise CiboCapitalManagementError(
            f"Phase22 persisted {field_name} must be int"
        )
    return value


def _generation(value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise CiboCapitalManagementError(
            "Phase22 replay book generation invalid"
        )


def _file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _fingerprint(value: dict[str, object]) -> str:
    return _sha256_text(_json(value))


def _json(value: object) -> str:
    return json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, RiskDecision):
        return value.value
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
