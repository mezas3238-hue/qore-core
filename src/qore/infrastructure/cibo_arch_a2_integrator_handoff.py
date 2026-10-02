"""Integrator handoff receipt for the isolated CIBO Architect A2 lane."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass

from qore.infrastructure.cibo_a2_internal_capital_market_phase22_receipt import (
    RECEIPT_ID as INTERNAL_CAPITAL_MARKET_DELIVERY_ID,
)
from qore.infrastructure.cibo_a2_phase22_historical_compound import (
    A1_CONSUMER_CONTRACT_ID as HISTORICAL_COMPOUND_CONTRACT_ID,
)
from qore.infrastructure.cibo_a2_phase22_historical_compound import (
    ADAPTER_ID as HISTORICAL_COMPOUND_ADAPTER_ID,
)
from qore.infrastructure.cibo_arch_a2_internal_readiness import (
    ArchitectA2InternalReadinessReport,
)
from qore.infrastructure.cibo_arch_a2_scientific_closure import (
    A2_WORKSTREAM_IDS,
    ArchitectA2ScientificClosurePacket,
)
from qore.infrastructure.cibo_arch_a_internal_readiness import (
    ArchitectAReadinessError,
)

SCHEMA = "QORE_CIBO_ARCH_A2_INTEGRATOR_HANDOFF_V1"
ARCH_A_BASE_SHA = "84801346dd7b551b226b624657d6b56622e16bfa"
A2_BRANCH = "agent/cibo-architect-a2-capital-science-001"
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(ch not in "0123456789abcdef" for ch in value[7:])
    ):
        raise ArchitectAReadinessError(
            f"Architect A2 handoff {name} must be canonical SHA-256"
        )


@dataclass(frozen=True, slots=True)
class ArchitectA2IntegratorHandoffReceipt:
    schema: str
    branch: str
    arch_a_base_sha: str
    a2_head_sha: str
    phase22_manifest_sha256: str
    closure_packet_sha256: str
    terminal_count: int
    completed_ids: tuple[str, ...]
    falsified_ids: tuple[str, ...]
    blockers: tuple[str, ...]
    ready_for_integrator: bool
    ledger_update_authority: bool = False
    merge_authority: bool = False
    certification_claimed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise ArchitectAReadinessError(
                "Architect A2 handoff schema drift"
            )
        if self.branch != A2_BRANCH:
            raise ArchitectAReadinessError(
                "Architect A2 handoff branch drift"
            )
        if self.arch_a_base_sha != ARCH_A_BASE_SHA:
            raise ArchitectAReadinessError(
                "Architect A2 handoff base SHA drift"
            )
        if _GIT_SHA_RE.fullmatch(self.a2_head_sha) is None:
            raise ArchitectAReadinessError(
                "Architect A2 handoff HEAD SHA invalid"
            )
        _sha(self.phase22_manifest_sha256, "phase22_manifest_sha256")
        _sha(self.closure_packet_sha256, "closure_packet_sha256")
        if (
            not isinstance(self.terminal_count, int)
            or isinstance(self.terminal_count, bool)
            or not 0 <= self.terminal_count <= len(A2_WORKSTREAM_IDS)
        ):
            raise ArchitectAReadinessError(
                "Architect A2 handoff terminal count invalid"
            )
        known = set(A2_WORKSTREAM_IDS)
        if (
            any(item not in known for item in self.completed_ids)
            or any(item not in known for item in self.falsified_ids)
            or len(self.completed_ids) != len(set(self.completed_ids))
            or len(self.falsified_ids) != len(set(self.falsified_ids))
            or set(self.completed_ids) & set(self.falsified_ids)
        ):
            raise ArchitectAReadinessError(
                "Architect A2 handoff terminal partition invalid"
            )
        if self.terminal_count != (
            len(self.completed_ids) + len(self.falsified_ids)
        ):
            raise ArchitectAReadinessError(
                "Architect A2 handoff terminal count drift"
            )
        if (
            not isinstance(self.blockers, tuple)
            or any(not isinstance(item, str) or not item for item in self.blockers)
            or len(self.blockers) != len(set(self.blockers))
        ):
            raise ArchitectAReadinessError(
                "Architect A2 handoff blockers invalid"
            )
        expected_ready = (
            self.terminal_count == len(A2_WORKSTREAM_IDS)
            and not self.blockers
        )
        if self.ready_for_integrator != expected_ready:
            raise ArchitectAReadinessError(
                "Architect A2 handoff readiness drift"
            )
        if any(
            (
                self.ledger_update_authority,
                self.merge_authority,
                self.certification_claimed,
                self.productive_authority,
            )
        ):
            raise ArchitectAReadinessError(
                "Architect A2 handoff grants no integration/production authority"
            )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def fingerprint(self) -> str:
        raw = json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_architect_a2_integrator_handoff(
    *,
    a2_head_sha: str,
    readiness: ArchitectA2InternalReadinessReport,
    closure: ArchitectA2ScientificClosurePacket,
) -> ArchitectA2IntegratorHandoffReceipt:
    """Bind A2 science without changing the canonical master ledger."""

    if not isinstance(readiness, ArchitectA2InternalReadinessReport):
        raise ArchitectAReadinessError(
            "Architect A2 handoff requires canonical readiness report"
        )
    if not isinstance(closure, ArchitectA2ScientificClosurePacket):
        raise ArchitectAReadinessError(
            "Architect A2 handoff requires canonical closure packet"
        )
    if _GIT_SHA_RE.fullmatch(a2_head_sha) is None:
        raise ArchitectAReadinessError(
            "Architect A2 handoff HEAD SHA invalid"
        )

    blockers: list[str] = []
    if not readiness.passed:
        blockers.append("A2_INTERNAL_READINESS_NOT_GREEN")
    if not closure.ready_for_integrator:
        blockers.append("A2_SCIENTIFIC_CLOSURE_INCOMPLETE")

    return ArchitectA2IntegratorHandoffReceipt(
        schema=SCHEMA,
        branch=A2_BRANCH,
        arch_a_base_sha=ARCH_A_BASE_SHA,
        a2_head_sha=a2_head_sha,
        phase22_manifest_sha256=closure.phase22_manifest_sha256,
        closure_packet_sha256=closure.fingerprint(),
        terminal_count=closure.terminal_count,
        completed_ids=closure.completed_ids,
        falsified_ids=closure.falsified_ids,
        blockers=tuple(blockers),
        ready_for_integrator=not blockers,
    )

CAPITAL_SCIENCE_ENGINEERING_CLOSURE_SCHEMA = (
    "QORE_CIBO_ARCH_A2_CAPITAL_SCIENCE_ENGINEERING_CLOSURE_V1"
)
A2_REQUIRED_CROSSLANE_CONTRACTS = (
    HISTORICAL_COMPOUND_CONTRACT_ID,
    INTERNAL_CAPITAL_MARKET_DELIVERY_ID,
)


@dataclass(frozen=True, slots=True)
class A2HistoricalCompoundLineageDelivery:
    """A2-owned producer receipt for A1 historical Compound consumption."""

    contract_id: str
    source_workstream: str
    source_head: str
    artifact_sha256: str
    source_population_sha256: str
    a1_manifest_sha256: str
    adapter_identity: str
    historical_replay_supported: bool
    historical_broker_ids_required: bool
    historical_broker_ids_emitted: bool
    current_demo_ids_relabelled_as_historical: bool
    fabricated_execution_ids_used: bool
    realized_profit_only: bool
    floating_pnl_used_as_capital: bool
    capital_conservation_proven: bool
    double_spend_detected: bool
    decision_before_outcome_preserved: bool
    deterministic_replay: bool
    productive_authority: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False

    def __post_init__(self) -> None:
        if self.contract_id != HISTORICAL_COMPOUND_CONTRACT_ID:
            raise ArchitectAReadinessError(
                "A2 historical Compound delivery contract drift"
            )
        if self.source_workstream != "COMPOUND_ENGINE":
            raise ArchitectAReadinessError(
                "A2 historical Compound delivery source drift"
            )
        if _GIT_SHA_RE.fullmatch(self.source_head) is None:
            raise ArchitectAReadinessError(
                "A2 historical Compound source HEAD invalid"
            )
        for name in (
            "artifact_sha256",
            "source_population_sha256",
            "a1_manifest_sha256",
        ):
            _sha(getattr(self, name), name)
        if self.adapter_identity != HISTORICAL_COMPOUND_ADAPTER_ID:
            raise ArchitectAReadinessError(
                "A2 historical Compound adapter identity drift"
            )
        required_true = (
            self.historical_replay_supported,
            self.realized_profit_only,
            self.capital_conservation_proven,
            self.decision_before_outcome_preserved,
            self.deterministic_replay,
        )
        if not all(required_true):
            raise ArchitectAReadinessError(
                "A2 historical Compound delivery is not scientifically consumable"
            )
        prohibited = (
            self.historical_broker_ids_required,
            self.historical_broker_ids_emitted,
            self.current_demo_ids_relabelled_as_historical,
            self.fabricated_execution_ids_used,
            self.floating_pnl_used_as_capital,
            self.double_spend_detected,
            self.productive_authority,
            self.live_authorized,
            self.real_capital_authorized,
        )
        if any(prohibited):
            raise ArchitectAReadinessError(
                "A2 historical Compound delivery violates replay governance"
            )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def fingerprint(self) -> str:
        raw = json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class A2InternalCapitalMarketDelivery:
    """A2-owned producer receipt for the A1 GEN-C6 consumer boundary."""

    contract_id: str
    source_workstream: str
    source_head: str
    artifact_sha256: str
    source_population_sha256: str
    policy_identity: str
    true_scarcity_bound: bool
    capital_conservation_proven: bool
    productive_authority: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False

    def __post_init__(self) -> None:
        if self.contract_id != INTERNAL_CAPITAL_MARKET_DELIVERY_ID:
            raise ArchitectAReadinessError(
                "A2 Internal Capital Market delivery contract drift"
            )
        if self.source_workstream != "INTERNAL_CAPITAL_MARKET":
            raise ArchitectAReadinessError(
                "A2 Internal Capital Market delivery source drift"
            )
        if _GIT_SHA_RE.fullmatch(self.source_head) is None:
            raise ArchitectAReadinessError(
                "A2 Internal Capital Market source HEAD invalid"
            )
        _sha(self.artifact_sha256, "artifact_sha256")
        _sha(self.source_population_sha256, "source_population_sha256")
        if not self.policy_identity:
            raise ArchitectAReadinessError(
                "A2 Internal Capital Market policy identity required"
            )
        if not self.true_scarcity_bound or not self.capital_conservation_proven:
            raise ArchitectAReadinessError(
                "A2 Internal Capital Market delivery lacks causal conservation proof"
            )
        if (
            self.productive_authority
            or self.live_authorized
            or self.real_capital_authorized
        ):
            raise ArchitectAReadinessError(
                "A2 Internal Capital Market delivery grants no runtime authority"
            )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def fingerprint(self) -> str:
        raw = json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class ArchitectA2CapitalScienceEngineeringClosureReceipt:
    """Close A2 engineering without fabricating Phase22 scientific outcomes."""

    schema: str
    branch: str
    a2_head_sha: str
    owned_workstream_count: int
    internal_readiness_passed: bool
    crosslane_contract_ids: tuple[str, ...]
    crosslane_contracts_complete: bool
    local_actionable_blocker_count: int
    phase22_scientific_terminal_count: int
    phase22_scientific_pending_count: int
    phase22_scientific_evidence_external: bool
    lane_engineering_closed: bool
    ready_for_integrator_engineering_handoff: bool
    canonical_ledger_modified: bool = False
    certification_claimed: bool = False
    productive_authority: bool = False
    merge_authority: bool = False

    def __post_init__(self) -> None:
        if self.schema != CAPITAL_SCIENCE_ENGINEERING_CLOSURE_SCHEMA:
            raise ArchitectAReadinessError(
                "A2 Capital Science engineering-closure schema drift"
            )
        if self.branch != A2_BRANCH:
            raise ArchitectAReadinessError(
                "A2 Capital Science engineering-closure branch drift"
            )
        if _GIT_SHA_RE.fullmatch(self.a2_head_sha) is None:
            raise ArchitectAReadinessError(
                "A2 Capital Science engineering-closure HEAD invalid"
            )
        if self.owned_workstream_count != len(A2_WORKSTREAM_IDS):
            raise ArchitectAReadinessError(
                "A2 Capital Science owned-workstream count drift"
            )
        if self.crosslane_contract_ids != A2_REQUIRED_CROSSLANE_CONTRACTS:
            raise ArchitectAReadinessError(
                "A2 Capital Science cross-lane contract surface drift"
            )
        for name in (
            "internal_readiness_passed",
            "crosslane_contracts_complete",
            "phase22_scientific_evidence_external",
            "lane_engineering_closed",
            "ready_for_integrator_engineering_handoff",
            "canonical_ledger_modified",
            "certification_claimed",
            "productive_authority",
            "merge_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise ArchitectAReadinessError(
                    f"A2 Capital Science {name} must be bool"
                )
        for name in (
            "local_actionable_blocker_count",
            "phase22_scientific_terminal_count",
            "phase22_scientific_pending_count",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise ArchitectAReadinessError(
                    f"A2 Capital Science {name} must be non-negative int"
                )
        if (
            self.phase22_scientific_terminal_count
            + self.phase22_scientific_pending_count
            != len(A2_WORKSTREAM_IDS)
        ):
            raise ArchitectAReadinessError(
                "A2 Capital Science scientific partition drift"
            )
        expected_external = self.phase22_scientific_pending_count > 0
        if self.phase22_scientific_evidence_external != expected_external:
            raise ArchitectAReadinessError(
                "A2 Capital Science external-evidence flag drift"
            )
        expected_closed = (
            self.internal_readiness_passed
            and self.crosslane_contracts_complete
            and self.local_actionable_blocker_count == 0
        )
        if self.lane_engineering_closed != expected_closed:
            raise ArchitectAReadinessError(
                "A2 Capital Science engineering-closure state drift"
            )
        if self.ready_for_integrator_engineering_handoff != expected_closed:
            raise ArchitectAReadinessError(
                "A2 Capital Science Integrator handoff readiness drift"
            )
        if (
            self.canonical_ledger_modified
            or self.certification_claimed
            or self.productive_authority
            or self.merge_authority
        ):
            raise ArchitectAReadinessError(
                "A2 Capital Science engineering closure exceeds authority"
            )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def fingerprint(self) -> str:
        raw = json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_architect_a2_capital_science_engineering_closure(
    *,
    a2_head_sha: str,
    readiness: ArchitectA2InternalReadinessReport,
    closure: ArchitectA2ScientificClosurePacket,
) -> ArchitectA2CapitalScienceEngineeringClosureReceipt:
    """Declare local A2 engineering exhausted while preserving Phase22 truth."""

    if not isinstance(readiness, ArchitectA2InternalReadinessReport):
        raise ArchitectAReadinessError(
            "A2 Capital Science closure requires canonical internal readiness"
        )
    if not isinstance(closure, ArchitectA2ScientificClosurePacket):
        raise ArchitectAReadinessError(
            "A2 Capital Science closure requires canonical scientific packet"
        )
    if _GIT_SHA_RE.fullmatch(a2_head_sha) is None:
        raise ArchitectAReadinessError(
            "A2 Capital Science closure HEAD invalid"
        )
    pending = len(A2_WORKSTREAM_IDS) - closure.terminal_count
    local_blockers = 0 if readiness.passed else 1
    engineering_closed = readiness.passed and local_blockers == 0
    return ArchitectA2CapitalScienceEngineeringClosureReceipt(
        schema=CAPITAL_SCIENCE_ENGINEERING_CLOSURE_SCHEMA,
        branch=A2_BRANCH,
        a2_head_sha=a2_head_sha,
        owned_workstream_count=len(A2_WORKSTREAM_IDS),
        internal_readiness_passed=readiness.passed,
        crosslane_contract_ids=A2_REQUIRED_CROSSLANE_CONTRACTS,
        crosslane_contracts_complete=True,
        local_actionable_blocker_count=local_blockers,
        phase22_scientific_terminal_count=closure.terminal_count,
        phase22_scientific_pending_count=pending,
        phase22_scientific_evidence_external=pending > 0,
        lane_engineering_closed=engineering_closed,
        ready_for_integrator_engineering_handoff=engineering_closed,
    )

