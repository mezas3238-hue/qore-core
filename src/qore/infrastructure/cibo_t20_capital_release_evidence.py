"""Authoritative T20 risk/margin-capacity release provenance.

T20 releases capacity, not economic principal. This module seals:

CIBO requested stop-risk/margin capacity
-> QORE Risk authorized/reduced capacity
-> Execution realized capacity
-> capacity occupied
-> partial releases
-> terminal release
-> risk and margin capacity fully reconciled

It is evidence only. It grants no sizing, Risk, Execution, DEMO, LIVE or
production authority.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from threading import RLock

from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardOutcomeSeal,
)
from qore.infrastructure.cibo_cma_settlement_ledger import CmaSettlementState
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError

_SCHEMA = "CIBO_T20_CAPITAL_RELEASE_EVIDENCE_BOOK_V2"


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"T20 {name} must be timezone-aware"
        )


def _positive(value: Decimal, name: str) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value <= 0
    ):
        raise CiboCompoundCapitalError(
            f"T20 {name} must be finite positive Decimal"
        )


def _nonnegative(value: Decimal, name: str) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value < 0
    ):
        raise CiboCompoundCapitalError(
            f"T20 {name} must be finite non-negative Decimal"
        )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            f"T20 {name} must be canonical SHA-256"
        )


@dataclass(frozen=True, slots=True)
class T20CapitalAuthorizationEvidence:
    """Pre-release identity of requested, authorized and realized capacity."""

    evidence_id: str
    decision_evidence_sha256: str
    signal_fingerprint: str
    position_id: int
    requested_at: datetime
    requested_margin_usd: Decimal
    requested_stop_risk_usd: Decimal
    risk_decision_id: str
    risk_disposition: str
    risk_authorized_at: datetime
    risk_authorized_margin_usd: Decimal
    risk_authorized_stop_risk_usd: Decimal
    execution_evidence_id: str
    execution_realized_at: datetime
    execution_realized_margin_usd: Decimal
    execution_realized_stop_risk_usd: Decimal
    capacity_deployed_at: datetime
    source_refs: tuple[str, ...]
    outcome_present: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if (
            not self.evidence_id
            or not self.signal_fingerprint
            or not self.risk_decision_id
            or not self.execution_evidence_id
        ):
            raise CiboCompoundCapitalError(
                "T20 authorization identity is required"
            )
        _sha(self.decision_evidence_sha256, "decision_evidence_sha256")
        if (
            not isinstance(self.position_id, int)
            or isinstance(self.position_id, bool)
            or self.position_id <= 0
        ):
            raise CiboCompoundCapitalError(
                "T20 position_id must be positive int"
            )
        for name in (
            "requested_at",
            "risk_authorized_at",
            "execution_realized_at",
            "capacity_deployed_at",
        ):
            _aware(getattr(self, name), name)
        if self.risk_authorized_at < self.requested_at:
            raise CiboCompoundCapitalError(
                "T20 Risk authorization cannot predate request"
            )
        if self.execution_realized_at < self.risk_authorized_at:
            raise CiboCompoundCapitalError(
                "T20 execution realization cannot predate Risk authorization"
            )
        if self.capacity_deployed_at > self.execution_realized_at:
            raise CiboCompoundCapitalError(
                "T20 capacity deployment cannot postdate execution realization"
            )
        for name in (
            "requested_margin_usd",
            "requested_stop_risk_usd",
            "risk_authorized_margin_usd",
            "risk_authorized_stop_risk_usd",
            "execution_realized_margin_usd",
            "execution_realized_stop_risk_usd",
        ):
            _positive(getattr(self, name), name)
        if self.risk_disposition not in {"ALLOW", "REDUCE"}:
            raise CiboCompoundCapitalError(
                "T20 Risk disposition must be ALLOW or REDUCE"
            )
        if self.risk_authorized_margin_usd > self.requested_margin_usd:
            raise CiboCompoundCapitalError(
                "T20 Risk cannot authorize more margin capacity than CIBO requested"
            )
        if self.risk_authorized_stop_risk_usd > self.requested_stop_risk_usd:
            raise CiboCompoundCapitalError(
                "T20 Risk cannot authorize more stop risk than requested"
            )
        if (
            self.execution_realized_margin_usd
            > self.risk_authorized_margin_usd
        ):
            raise CiboCompoundCapitalError(
                "T20 Execution cannot realize more margin capacity than Risk authorized"
            )
        if (
            self.execution_realized_stop_risk_usd
            > self.risk_authorized_stop_risk_usd
        ):
            raise CiboCompoundCapitalError(
                "T20 Execution cannot realize more stop risk than Risk authorized"
            )
        if not self.source_refs or len(self.source_refs) != len(
            set(self.source_refs)
        ):
            raise CiboCompoundCapitalError(
                "T20 authorization source refs must be non-empty unique"
            )
        if any(not isinstance(item, str) or not item for item in self.source_refs):
            raise CiboCompoundCapitalError(
                "T20 authorization source refs are invalid"
            )
        if self.outcome_present or self.productive_authority:
            raise CiboCompoundCapitalError(
                "T20 authorization evidence cannot carry outcome or authority"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        for name in (
            "requested_at",
            "risk_authorized_at",
            "execution_realized_at",
            "capacity_deployed_at",
        ):
            payload[name] = getattr(self, name).isoformat()
        for name in (
            "requested_margin_usd",
            "requested_stop_risk_usd",
            "risk_authorized_margin_usd",
            "risk_authorized_stop_risk_usd",
            "execution_realized_margin_usd",
            "execution_realized_stop_risk_usd",
        ):
            payload[name] = str(getattr(self, name))
        payload["source_refs"] = list(self.source_refs)
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class T20CapitalReleaseSlice:
    """One observed release of occupied CIBO capacity."""

    settlement_deal_id: int
    released_at: datetime
    released_stop_risk_capacity_usd: Decimal
    released_margin_capacity_usd: Decimal
    source_ref: str
    terminal: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.settlement_deal_id, int)
            or isinstance(self.settlement_deal_id, bool)
            or self.settlement_deal_id <= 0
        ):
            raise CiboCompoundCapitalError(
                "T20 release settlement_deal_id must be positive int"
            )
        _aware(self.released_at, "release released_at")
        _positive(
            self.released_stop_risk_capacity_usd,
            "released_stop_risk_capacity_usd",
        )
        _positive(
            self.released_margin_capacity_usd,
            "released_margin_capacity_usd",
        )
        if not self.source_ref:
            raise CiboCompoundCapitalError(
                "T20 release source_ref is required"
            )
        if type(self.terminal) is not bool:
            raise CiboCompoundCapitalError(
                "T20 release terminal must be bool"
            )


@dataclass(frozen=True, slots=True)
class T20CapitalReleaseEvidence:
    """Reconciled lifecycle proving when risk/margin capacity became reusable."""

    evidence_id: str
    authorization: T20CapitalAuthorizationEvidence
    source_outcome_evidence_id: str
    settlement_deal_ids: tuple[int, ...]
    releases: tuple[T20CapitalReleaseSlice, ...]
    total_released_stop_risk_capacity_usd: Decimal
    total_released_margin_capacity_usd: Decimal
    terminal_release_at: datetime
    release_latency_minutes: Decimal
    terminal_settlement_pnl_usd: Decimal
    observed_at: datetime
    source_refs: tuple[str, ...]
    terminal_capacity_reconciled: bool = True
    inferred_from_position_close_only: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.source_outcome_evidence_id:
            raise CiboCompoundCapitalError(
                "T20 release evidence identity is required"
            )
        if not isinstance(self.authorization, T20CapitalAuthorizationEvidence):
            raise CiboCompoundCapitalError(
                "T20 release requires canonical authorization evidence"
            )
        if (
            not self.settlement_deal_ids
            or len(self.settlement_deal_ids) != len(set(self.settlement_deal_ids))
        ):
            raise CiboCompoundCapitalError(
                "T20 settlement deal ids must be non-empty unique"
            )
        if not self.releases:
            raise CiboCompoundCapitalError(
                "T20 release evidence requires observed releases"
            )
        release_deals = tuple(item.settlement_deal_id for item in self.releases)
        if len(release_deals) != len(set(release_deals)):
            raise CiboCompoundCapitalError(
                "T20 release deal ids must be unique"
            )
        if any(item not in self.settlement_deal_ids for item in release_deals):
            raise CiboCompoundCapitalError(
                "T20 release deal must be present in terminal settlement"
            )
        terminal_indexes = tuple(
            index for index, item in enumerate(self.releases) if item.terminal
        )
        if terminal_indexes != (len(self.releases) - 1,):
            raise CiboCompoundCapitalError(
                "T20 requires exactly one final terminal release"
            )
        previous = self.authorization.capacity_deployed_at
        for item in self.releases:
            if item.released_at <= previous:
                raise CiboCompoundCapitalError(
                    "T20 releases must be strictly chronological after deployment"
                )
            previous = item.released_at
        _positive(
            self.total_released_stop_risk_capacity_usd,
            "total_released_stop_risk_capacity_usd",
        )
        _positive(
            self.total_released_margin_capacity_usd,
            "total_released_margin_capacity_usd",
        )
        expected_stop_risk_release = sum(
            (
                item.released_stop_risk_capacity_usd
                for item in self.releases
            ),
            Decimal("0"),
        )
        expected_margin_release = sum(
            (item.released_margin_capacity_usd for item in self.releases),
            Decimal("0"),
        )
        if (
            expected_stop_risk_release
            != self.total_released_stop_risk_capacity_usd
        ):
            raise CiboCompoundCapitalError(
                "T20 stop-risk capacity does not reconcile to release slices"
            )
        if expected_margin_release != self.total_released_margin_capacity_usd:
            raise CiboCompoundCapitalError(
                "T20 margin capacity does not reconcile to release slices"
            )
        if (
            self.total_released_stop_risk_capacity_usd
            != self.authorization.execution_realized_stop_risk_usd
        ):
            raise CiboCompoundCapitalError(
                "T20 terminal release must restore all realized stop-risk capacity"
            )
        if (
            self.total_released_margin_capacity_usd
            != self.authorization.execution_realized_margin_usd
        ):
            raise CiboCompoundCapitalError(
                "T20 terminal release must restore all realized margin capacity"
            )
        _aware(self.terminal_release_at, "terminal_release_at")
        if self.terminal_release_at != self.releases[-1].released_at:
            raise CiboCompoundCapitalError(
                "T20 terminal release timestamp drift"
            )
        _positive(self.release_latency_minutes, "release_latency_minutes")
        expected_latency = Decimal(
            str(
                (
                    self.terminal_release_at
                    - self.authorization.capacity_deployed_at
                ).total_seconds()
            )
        ) / Decimal("60")
        if self.release_latency_minutes != expected_latency:
            raise CiboCompoundCapitalError(
                "T20 release latency identity mismatch"
            )
        _nonnegative(
            abs(self.terminal_settlement_pnl_usd),
            "terminal_settlement_pnl_usd magnitude",
        )
        if (
            not isinstance(self.terminal_settlement_pnl_usd, Decimal)
            or not self.terminal_settlement_pnl_usd.is_finite()
        ):
            raise CiboCompoundCapitalError(
                "T20 terminal settlement PnL must be finite Decimal"
            )
        _aware(self.observed_at, "observed_at")
        if self.observed_at < self.terminal_release_at:
            raise CiboCompoundCapitalError(
                "T20 evidence cannot be observed before terminal release"
            )
        if not self.source_refs or len(self.source_refs) != len(
            set(self.source_refs)
        ):
            raise CiboCompoundCapitalError(
                "T20 release source refs must be non-empty unique"
            )
        if self.inferred_from_position_close_only:
            raise CiboCompoundCapitalError(
                "T20 release cannot be inferred from position close alone"
            )
        if not self.terminal_capacity_reconciled:
            raise CiboCompoundCapitalError(
                "T20 terminal returned capacity must be reconciled"
            )
        if self.productive_authority:
            raise CiboCompoundCapitalError(
                "T20 evidence cannot carry productive authority"
            )

    def fingerprint(self) -> str:
        payload = {
            "evidence_id": self.evidence_id,
            "authorization_sha256": self.authorization.fingerprint(),
            "source_outcome_evidence_id": self.source_outcome_evidence_id,
            "settlement_deal_ids": list(self.settlement_deal_ids),
            "releases": [
                {
                    "settlement_deal_id": item.settlement_deal_id,
                    "released_at": item.released_at.isoformat(),
                    "released_stop_risk_capacity_usd": str(
                        item.released_stop_risk_capacity_usd
                    ),
                    "released_margin_capacity_usd": str(
                        item.released_margin_capacity_usd
                    ),
                    "source_ref": item.source_ref,
                    "terminal": item.terminal,
                }
                for item in self.releases
            ],
            "total_released_stop_risk_capacity_usd": str(
                self.total_released_stop_risk_capacity_usd
            ),
            "total_released_margin_capacity_usd": str(
                self.total_released_margin_capacity_usd
            ),
            "terminal_release_at": self.terminal_release_at.isoformat(),
            "release_latency_minutes": str(self.release_latency_minutes),
            "terminal_settlement_pnl_usd": str(
                self.terminal_settlement_pnl_usd
            ),
            "observed_at": self.observed_at.isoformat(),
            "source_refs": list(self.source_refs),
            "terminal_capacity_reconciled": self.terminal_capacity_reconciled,
            "inferred_from_position_close_only": (
                self.inferred_from_position_close_only
            ),
            "productive_authority": self.productive_authority,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


def build_t20_capital_release_evidence(
    *,
    evidence_id: str,
    authorization: T20CapitalAuthorizationEvidence,
    outcome: Phase20ForwardOutcomeSeal,
    settlement: CmaSettlementState,
    releases: tuple[T20CapitalReleaseSlice, ...],
    observed_at: datetime,
    source_refs: tuple[str, ...],
) -> T20CapitalReleaseEvidence:
    """Bind lifecycle evidence without inventing release from terminal close."""

    if not isinstance(authorization, T20CapitalAuthorizationEvidence):
        raise CiboCompoundCapitalError(
            "T20 builder requires canonical authorization evidence"
        )
    if not isinstance(outcome, Phase20ForwardOutcomeSeal):
        raise CiboCompoundCapitalError(
            "T20 builder requires canonical Phase20 outcome seal"
        )
    if not isinstance(settlement, CmaSettlementState):
        raise CiboCompoundCapitalError(
            "T20 builder requires canonical CMA settlement state"
        )
    _aware(observed_at, "observed_at")
    if outcome.signal_fingerprint != authorization.signal_fingerprint:
        raise CiboCompoundCapitalError(
            "T20 outcome/authorization signal binding drift"
        )
    if outcome.position_id != authorization.position_id:
        raise CiboCompoundCapitalError(
            "T20 outcome/authorization position binding drift"
        )
    if (
        outcome.decision_evidence_sha256
        != authorization.decision_evidence_sha256
    ):
        raise CiboCompoundCapitalError(
            "T20 outcome/authorization decision binding drift"
        )
    if outcome.execution_risk_evidence_id != authorization.execution_evidence_id:
        raise CiboCompoundCapitalError(
            "T20 execution evidence identity drift"
        )
    if (
        outcome.executed_initial_stop_risk_usd
        != authorization.execution_realized_stop_risk_usd
    ):
        raise CiboCompoundCapitalError(
            "T20 executed stop-risk binding drift"
        )
    if settlement.signal_fingerprint != authorization.signal_fingerprint:
        raise CiboCompoundCapitalError(
            "T20 settlement/authorization signal binding drift"
        )
    if settlement.position_id != authorization.position_id:
        raise CiboCompoundCapitalError(
            "T20 settlement/authorization position binding drift"
        )
    if not settlement.position_closed:
        raise CiboCompoundCapitalError(
            "T20 release evidence requires terminal settlement"
        )
    settlement_ids = tuple(item.deal_id for item in settlement.records)
    if settlement_ids != outcome.settlement_deal_ids:
        raise CiboCompoundCapitalError(
            "T20 settlement deal binding drift"
        )
    if settlement.realized_net_pnl_usd != outcome.realized_net_pnl_usd:
        raise CiboCompoundCapitalError(
            "T20 settlement PnL binding drift"
        )
    if (
        outcome.capacity_deployed_at is not None
        and outcome.capacity_deployed_at != authorization.capacity_deployed_at
    ):
        raise CiboCompoundCapitalError(
            "T20 deployment timestamp binding drift"
        )
    if not releases:
        raise CiboCompoundCapitalError(
            "T20 builder refuses terminal-close-only release inference"
        )

    total_released_stop_risk = sum(
        (item.released_stop_risk_capacity_usd for item in releases),
        Decimal("0"),
    )
    total_released_margin = sum(
        (item.released_margin_capacity_usd for item in releases),
        Decimal("0"),
    )
    terminal_release_at = releases[-1].released_at
    latency = Decimal(
        str(
            (
                terminal_release_at
                - authorization.capacity_deployed_at
            ).total_seconds()
        )
    ) / Decimal("60")
    if (
        outcome.capital_released_at is not None
        and outcome.capital_released_at != terminal_release_at
    ):
        raise CiboCompoundCapitalError(
            "T20 Phase20/release terminal timestamp drift"
        )
    if outcome.capital_minutes is not None and outcome.capital_minutes != latency:
        raise CiboCompoundCapitalError(
            "T20 Phase20/release latency drift"
        )

    return T20CapitalReleaseEvidence(
        evidence_id=evidence_id,
        authorization=authorization,
        source_outcome_evidence_id=outcome.evidence_id,
        settlement_deal_ids=settlement_ids,
        releases=releases,
        total_released_stop_risk_capacity_usd=total_released_stop_risk,
        total_released_margin_capacity_usd=total_released_margin,
        terminal_release_at=terminal_release_at,
        release_latency_minutes=latency,
        terminal_settlement_pnl_usd=settlement.realized_net_pnl_usd,
        observed_at=observed_at,
        source_refs=source_refs,
        terminal_capacity_reconciled=True,
        inferred_from_position_close_only=False,
        productive_authority=False,
    )


@dataclass(frozen=True, slots=True)
class T20CapitalReleaseSeal:
    generation: int
    evidence_sha256: str
    chain_sha256: str
    previous_chain_sha256: str | None
    evidence: T20CapitalReleaseEvidence
    sealed_at: datetime

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation <= 0
        ):
            raise CiboCompoundCapitalError(
                "T20 seal generation must be positive int"
            )
        _sha(self.evidence_sha256, "evidence_sha256")
        _sha(self.chain_sha256, "chain_sha256")
        if self.previous_chain_sha256 is not None:
            _sha(self.previous_chain_sha256, "previous_chain_sha256")
        if not isinstance(self.evidence, T20CapitalReleaseEvidence):
            raise CiboCompoundCapitalError(
                "T20 seal requires canonical evidence"
            )
        if self.evidence_sha256 != self.evidence.fingerprint():
            raise CiboCompoundCapitalError(
                "T20 seal/evidence digest drift"
            )
        _aware(self.sealed_at, "sealed_at")
        if self.sealed_at < self.evidence.observed_at:
            raise CiboCompoundCapitalError(
                "T20 seal cannot predate evidence observation"
            )


@dataclass(frozen=True, slots=True)
class VersionedT20CapitalReleaseBook:
    generation: int
    records: tuple[T20CapitalReleaseSeal, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 0
        ):
            raise CiboCompoundCapitalError(
                "T20 book generation must be non-negative int"
            )
        if self.generation != len(self.records):
            raise CiboCompoundCapitalError(
                "T20 book generation/record count drift"
            )
        keys = tuple(
            (
                item.evidence.authorization.signal_fingerprint,
                item.evidence.authorization.position_id,
            )
            for item in self.records
        )
        if len(keys) != len(set(keys)):
            raise CiboCompoundCapitalError(
                "T20 book duplicate signal/position release evidence"
            )

    def for_signal_position(
        self,
        *,
        signal_fingerprint: str,
        position_id: int,
    ) -> T20CapitalReleaseSeal | None:
        rows = tuple(
            item
            for item in self.records
            if (
                item.evidence.authorization.signal_fingerprint
                == signal_fingerprint
                and item.evidence.authorization.position_id == position_id
            )
        )
        if len(rows) > 1:
            raise CiboCompoundCapitalError(
                "T20 duplicate signal/position evidence"
            )
        return rows[0] if rows else None


class DurableT20CapitalReleaseStore:
    """Append-only, hash-chained, CAS-protected T20 release store."""

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path):
            raise CiboCompoundCapitalError(
                "T20 store path must be pathlib.Path"
            )
        self._path = path
        self._writer_lock_path = path.with_name(f".{path.name}.writer-lock")
        self._lock = RLock()

    def load(self) -> VersionedT20CapitalReleaseBook:
        with self._lock:
            return self._load_unlocked()

    def seal(
        self,
        evidence: T20CapitalReleaseEvidence,
        *,
        sealed_at: datetime,
        expected_generation: int,
    ) -> VersionedT20CapitalReleaseBook:
        if not isinstance(evidence, T20CapitalReleaseEvidence):
            raise CiboCompoundCapitalError(
                "T20 store requires canonical evidence"
            )
        _aware(sealed_at, "sealed_at")
        if (
            not isinstance(expected_generation, int)
            or isinstance(expected_generation, bool)
            or expected_generation < 0
        ):
            raise CiboCompoundCapitalError(
                "T20 expected_generation must be non-negative int"
            )

        with self._lock:
            self._acquire_writer_lock()
            try:
                current = self._load_unlocked()
                if current.generation != expected_generation:
                    raise CiboCompoundCapitalError(
                        "T20 release generation conflict"
                    )
                existing = current.for_signal_position(
                    signal_fingerprint=(
                        evidence.authorization.signal_fingerprint
                    ),
                    position_id=evidence.authorization.position_id,
                )
                digest = evidence.fingerprint()
                if existing is not None:
                    if existing.evidence_sha256 == digest:
                        return current
                    raise CiboCompoundCapitalError(
                        "T20 conflicting release evidence rewrite"
                    )
                previous = (
                    None
                    if not current.records
                    else current.records[-1].chain_sha256
                )
                chain_payload = {
                    "generation": current.generation + 1,
                    "previous_chain_sha256": previous,
                    "evidence_sha256": digest,
                    "sealed_at": sealed_at.isoformat(),
                }
                raw = json.dumps(
                    chain_payload,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                chain = "sha256:" + hashlib.sha256(raw.encode()).hexdigest()
                seal = T20CapitalReleaseSeal(
                    generation=current.generation + 1,
                    evidence_sha256=digest,
                    chain_sha256=chain,
                    previous_chain_sha256=previous,
                    evidence=evidence,
                    sealed_at=sealed_at,
                )
                next_book = VersionedT20CapitalReleaseBook(
                    generation=current.generation + 1,
                    records=current.records + (seal,),
                )
                self._write_unlocked(next_book)
                return next_book
            finally:
                self._release_writer_lock()

    def _load_unlocked(self) -> VersionedT20CapitalReleaseBook:
        if not self._path.exists():
            return VersionedT20CapitalReleaseBook(generation=0)
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise CiboCompoundCapitalError(
                "T20 release store is unreadable"
            ) from error
        if not isinstance(payload, dict) or payload.get("schema") != _SCHEMA:
            raise CiboCompoundCapitalError(
                "T20 release store schema mismatch"
            )
        records_raw = payload.get("records")
        if not isinstance(records_raw, list):
            raise CiboCompoundCapitalError(
                "T20 release store records are invalid"
            )
        records = tuple(_seal_from_json(item) for item in records_raw)
        book = VersionedT20CapitalReleaseBook(
            generation=int(payload.get("generation", -1)),
            records=records,
        )
        _validate_chain(book)
        return book

    def _write_unlocked(
        self,
        book: VersionedT20CapitalReleaseBook,
    ) -> None:
        payload = {
            "schema": _SCHEMA,
            "generation": book.generation,
            "records": [_seal_to_json(item) for item in book.records],
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_name(f".{self._path.name}.tmp")
        try:
            with temporary.open("w", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(payload, sort_keys=True, indent=2) + "\n"
                )
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self._path)
        except OSError as error:
            raise CiboCompoundCapitalError(
                "T20 release store write failed"
            ) from error
        finally:
            temporary.unlink(missing_ok=True)

    def _acquire_writer_lock(self) -> None:
        self._writer_lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._writer_lock_path.mkdir()
        except FileExistsError as error:
            raise CiboCompoundCapitalError(
                "T20 release writer lock is held"
            ) from error

    def _release_writer_lock(self) -> None:
        try:
            self._writer_lock_path.rmdir()
        except FileNotFoundError:
            pass


def _seal_to_json(seal: T20CapitalReleaseSeal) -> dict[str, object]:
    evidence = seal.evidence
    authorization = evidence.authorization
    return {
        "generation": seal.generation,
        "evidence_sha256": seal.evidence_sha256,
        "chain_sha256": seal.chain_sha256,
        "previous_chain_sha256": seal.previous_chain_sha256,
        "sealed_at": seal.sealed_at.isoformat(),
        "evidence": {
            "evidence_id": evidence.evidence_id,
            "source_outcome_evidence_id": evidence.source_outcome_evidence_id,
            "settlement_deal_ids": list(evidence.settlement_deal_ids),
            "releases": [
                {
                    "settlement_deal_id": item.settlement_deal_id,
                    "released_at": item.released_at.isoformat(),
                    "released_stop_risk_capacity_usd": str(
                        item.released_stop_risk_capacity_usd
                    ),
                    "released_margin_capacity_usd": str(
                        item.released_margin_capacity_usd
                    ),
                    "source_ref": item.source_ref,
                    "terminal": item.terminal,
                }
                for item in evidence.releases
            ],
            "total_released_stop_risk_capacity_usd": str(
                evidence.total_released_stop_risk_capacity_usd
            ),
            "total_released_margin_capacity_usd": str(
                evidence.total_released_margin_capacity_usd
            ),
            "terminal_release_at": evidence.terminal_release_at.isoformat(),
            "release_latency_minutes": str(evidence.release_latency_minutes),
            "terminal_settlement_pnl_usd": str(
                evidence.terminal_settlement_pnl_usd
            ),
            "observed_at": evidence.observed_at.isoformat(),
            "source_refs": list(evidence.source_refs),
            "terminal_capacity_reconciled": (
                evidence.terminal_capacity_reconciled
            ),
            "inferred_from_position_close_only": (
                evidence.inferred_from_position_close_only
            ),
            "productive_authority": evidence.productive_authority,
            "authorization": {
                "evidence_id": authorization.evidence_id,
                "decision_evidence_sha256": (
                    authorization.decision_evidence_sha256
                ),
                "signal_fingerprint": authorization.signal_fingerprint,
                "position_id": authorization.position_id,
                "requested_at": authorization.requested_at.isoformat(),
                "requested_margin_usd": str(
                    authorization.requested_margin_usd
                ),
                "requested_stop_risk_usd": str(
                    authorization.requested_stop_risk_usd
                ),
                "risk_decision_id": authorization.risk_decision_id,
                "risk_disposition": authorization.risk_disposition,
                "risk_authorized_at": (
                    authorization.risk_authorized_at.isoformat()
                ),
                "risk_authorized_margin_usd": str(
                    authorization.risk_authorized_margin_usd
                ),
                "risk_authorized_stop_risk_usd": str(
                    authorization.risk_authorized_stop_risk_usd
                ),
                "execution_evidence_id": authorization.execution_evidence_id,
                "execution_realized_at": (
                    authorization.execution_realized_at.isoformat()
                ),
                "execution_realized_margin_usd": str(
                    authorization.execution_realized_margin_usd
                ),
                "execution_realized_stop_risk_usd": str(
                    authorization.execution_realized_stop_risk_usd
                ),
                "capacity_deployed_at": (
                    authorization.capacity_deployed_at.isoformat()
                ),
                "source_refs": list(authorization.source_refs),
                "outcome_present": authorization.outcome_present,
                "productive_authority": authorization.productive_authority,
            },
        },
    }


def _seal_from_json(value: object) -> T20CapitalReleaseSeal:
    if not isinstance(value, dict):
        raise CiboCompoundCapitalError("T20 release seal payload invalid")
    evidence_raw = value.get("evidence")
    if not isinstance(evidence_raw, dict):
        raise CiboCompoundCapitalError(
            "T20 release evidence payload invalid"
        )
    auth_raw = evidence_raw.get("authorization")
    if not isinstance(auth_raw, dict):
        raise CiboCompoundCapitalError(
            "T20 authorization payload invalid"
        )
    authorization = T20CapitalAuthorizationEvidence(
        evidence_id=str(auth_raw["evidence_id"]),
        decision_evidence_sha256=str(
            auth_raw["decision_evidence_sha256"]
        ),
        signal_fingerprint=str(auth_raw["signal_fingerprint"]),
        position_id=int(auth_raw["position_id"]),
        requested_at=datetime.fromisoformat(str(auth_raw["requested_at"])),
        requested_margin_usd=Decimal(
            str(auth_raw["requested_margin_usd"])
        ),
        requested_stop_risk_usd=Decimal(
            str(auth_raw["requested_stop_risk_usd"])
        ),
        risk_decision_id=str(auth_raw["risk_decision_id"]),
        risk_disposition=str(auth_raw["risk_disposition"]),
        risk_authorized_at=datetime.fromisoformat(
            str(auth_raw["risk_authorized_at"])
        ),
        risk_authorized_margin_usd=Decimal(
            str(auth_raw["risk_authorized_margin_usd"])
        ),
        risk_authorized_stop_risk_usd=Decimal(
            str(auth_raw["risk_authorized_stop_risk_usd"])
        ),
        execution_evidence_id=str(auth_raw["execution_evidence_id"]),
        execution_realized_at=datetime.fromisoformat(
            str(auth_raw["execution_realized_at"])
        ),
        execution_realized_margin_usd=Decimal(
            str(auth_raw["execution_realized_margin_usd"])
        ),
        execution_realized_stop_risk_usd=Decimal(
            str(auth_raw["execution_realized_stop_risk_usd"])
        ),
        capacity_deployed_at=datetime.fromisoformat(
            str(auth_raw["capacity_deployed_at"])
        ),
        source_refs=tuple(str(item) for item in auth_raw["source_refs"]),
        outcome_present=bool(auth_raw["outcome_present"]),
        productive_authority=bool(auth_raw["productive_authority"]),
    )
    releases = tuple(
        T20CapitalReleaseSlice(
            settlement_deal_id=int(item["settlement_deal_id"]),
            released_at=datetime.fromisoformat(str(item["released_at"])),
            released_stop_risk_capacity_usd=Decimal(
                str(item["released_stop_risk_capacity_usd"])
            ),
            released_margin_capacity_usd=Decimal(
                str(item["released_margin_capacity_usd"])
            ),
            source_ref=str(item["source_ref"]),
            terminal=bool(item["terminal"]),
        )
        for item in evidence_raw["releases"]
    )
    evidence = T20CapitalReleaseEvidence(
        evidence_id=str(evidence_raw["evidence_id"]),
        authorization=authorization,
        source_outcome_evidence_id=str(
            evidence_raw["source_outcome_evidence_id"]
        ),
        settlement_deal_ids=tuple(
            int(item) for item in evidence_raw["settlement_deal_ids"]
        ),
        releases=releases,
        total_released_stop_risk_capacity_usd=Decimal(
            str(evidence_raw["total_released_stop_risk_capacity_usd"])
        ),
        total_released_margin_capacity_usd=Decimal(
            str(evidence_raw["total_released_margin_capacity_usd"])
        ),
        terminal_release_at=datetime.fromisoformat(
            str(evidence_raw["terminal_release_at"])
        ),
        release_latency_minutes=Decimal(
            str(evidence_raw["release_latency_minutes"])
        ),
        terminal_settlement_pnl_usd=Decimal(
            str(evidence_raw["terminal_settlement_pnl_usd"])
        ),
        observed_at=datetime.fromisoformat(str(evidence_raw["observed_at"])),
        source_refs=tuple(
            str(item) for item in evidence_raw["source_refs"]
        ),
        terminal_capacity_reconciled=bool(
            evidence_raw["terminal_capacity_reconciled"]
        ),
        inferred_from_position_close_only=bool(
            evidence_raw["inferred_from_position_close_only"]
        ),
        productive_authority=bool(evidence_raw["productive_authority"]),
    )
    return T20CapitalReleaseSeal(
        generation=int(value["generation"]),
        evidence_sha256=str(value["evidence_sha256"]),
        chain_sha256=str(value["chain_sha256"]),
        previous_chain_sha256=(
            None
            if value.get("previous_chain_sha256") is None
            else str(value["previous_chain_sha256"])
        ),
        evidence=evidence,
        sealed_at=datetime.fromisoformat(str(value["sealed_at"])),
    )


def _validate_chain(book: VersionedT20CapitalReleaseBook) -> None:
    previous: str | None = None
    for index, seal in enumerate(book.records, start=1):
        if seal.generation != index:
            raise CiboCompoundCapitalError(
                "T20 release chain generation drift"
            )
        if seal.previous_chain_sha256 != previous:
            raise CiboCompoundCapitalError(
                "T20 release previous-chain drift"
            )
        chain_payload = {
            "generation": seal.generation,
            "previous_chain_sha256": previous,
            "evidence_sha256": seal.evidence_sha256,
            "sealed_at": seal.sealed_at.isoformat(),
        }
        raw = json.dumps(
            chain_payload,
            sort_keys=True,
            separators=(",", ":"),
        )
        expected = "sha256:" + hashlib.sha256(raw.encode()).hexdigest()
        if seal.chain_sha256 != expected:
            raise CiboCompoundCapitalError(
                "T20 release chain digest mismatch"
            )
        previous = seal.chain_sha256
