"""Phase 20F independent CE2I accounting-core mechanism certification.

This harness exercises the real T05/T19/T20 implementation surfaces rather than
promoting tools from registry metadata alone. It is deliberately limited to
accounting and reservation/release mechanics that do not require historical
provider economics or burned Phase-19J validation.

The certification is contract-level only. It grants no allocator, QORE Risk,
execution, DEMO, LIVE, real-capital or merge authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path

from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_capital_source_ledger import (
    CapitalReservationRequest,
    CapitalSourceLedger,
    ReservationState,
)
from qore.infrastructure.cibo_capital_source_ledger_store import (
    DurableCapitalLedgerError,
    DurableCapitalSourceLedgerStore,
)
from qore.infrastructure.cibo_ce2i_recycling import (
    RecyclePurpose,
    ReleasedCapacityEvidence,
    deploy_recycled_capacity,
    register_released_capacity,
    reserve_recycled_capacity,
    settle_recycled_capacity,
)
from qore.infrastructure.cibo_ce2i_tool_registry import ToolMaturity, tool_by_code


class Phase20MechanismCertificationStatus(StrEnum):
    CONTRACT_CERTIFIED = "CONTRACT_CERTIFIED"
    CONTRACT_FAILED = "CONTRACT_FAILED"


@dataclass(frozen=True, slots=True)
class Phase20MechanismProof:
    tool_code: str
    invariant_id: str
    passed: bool
    detail: str

    def __post_init__(self) -> None:
        if not self.tool_code or not self.invariant_id or not self.detail:
            raise CiboCapitalManagementError(
                "Phase20F proof identity/detail is required"
            )
        if type(self.passed) is not bool:
            raise CiboCapitalManagementError("Phase20F proof passed must be bool")


@dataclass(frozen=True, slots=True)
class Phase20MechanismCertification:
    tool_code: str
    tool_name: str
    status: Phase20MechanismCertificationStatus
    proof_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.tool_code or not self.tool_name or not self.proof_ids:
            raise CiboCapitalManagementError(
                "Phase20F certification identity/proofs are required"
            )
        if type(self.status) is not Phase20MechanismCertificationStatus:
            raise CiboCapitalManagementError(
                "Phase20F certification status must use canonical enum"
            )


@dataclass(frozen=True, slots=True)
class Phase20MechanismCertificationReport:
    identity: str
    certifications: tuple[Phase20MechanismCertification, ...]
    proofs: tuple[Phase20MechanismProof, ...]
    synthetic_contract_evidence_only: bool = True
    historical_provider_economics_claimed: bool = False
    phase19j_burned_validation_reused: bool = False
    policy_certified: bool = False
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False
    demo_execution_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    merge_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.identity or not self.certifications or not self.proofs:
            raise CiboCapitalManagementError(
                "Phase20F report identity/certifications/proofs are required"
            )
        codes = tuple(item.tool_code for item in self.certifications)
        if len(codes) != len(set(codes)):
            raise CiboCapitalManagementError(
                "Phase20F report contains duplicate tool certification"
            )
        proof_ids = tuple(item.invariant_id for item in self.proofs)
        if len(proof_ids) != len(set(proof_ids)):
            raise CiboCapitalManagementError(
                "Phase20F report contains duplicate proof id"
            )
        if not self.synthetic_contract_evidence_only:
            raise CiboCapitalManagementError(
                "Phase20F tranche must remain synthetic contract evidence"
            )
        if (
            self.historical_provider_economics_claimed
            or self.phase19j_burned_validation_reused
            or self.policy_certified
            or self.allocation_authority
            or self.risk_authority
            or self.execution_authority
            or self.demo_execution_authorized
            or self.live_authorized
            or self.real_capital_authorized
            or self.merge_authorized
        ):
            raise CiboCapitalManagementError(
                "Phase20F accounting-core governance drift"
            )


def _proof(
    tool_code: str,
    invariant_id: str,
    passed: bool,
    detail: str,
) -> Phase20MechanismProof:
    return Phase20MechanismProof(
        tool_code=tool_code,
        invariant_id=invariant_id,
        passed=passed,
        detail=detail,
    )


def _certification_for(
    tool_code: str,
    proofs: tuple[Phase20MechanismProof, ...],
) -> Phase20MechanismCertification:
    tool = tool_by_code(tool_code)
    if tool.maturity is not ToolMaturity.CONTRACT_IMPLEMENTED:
        raise CiboCapitalManagementError(
            f"{tool_code} is not contract-implemented"
        )
    selected = tuple(item for item in proofs if item.tool_code == tool_code)
    if not selected:
        raise CiboCapitalManagementError(
            f"{tool_code} has no independent Phase20F proofs"
        )
    status = (
        Phase20MechanismCertificationStatus.CONTRACT_CERTIFIED
        if all(item.passed for item in selected)
        else Phase20MechanismCertificationStatus.CONTRACT_FAILED
    )
    return Phase20MechanismCertification(
        tool_code=tool.code,
        tool_name=tool.name,
        status=status,
        proof_ids=tuple(item.invariant_id for item in selected),
    )


def _expect_capital_error(operation: object) -> bool:
    if not callable(operation):
        raise CiboCapitalManagementError(
            "Phase20F expected-failure operation must be callable"
        )
    try:
        operation()
    except CiboCapitalManagementError:
        return True
    return False


def _t19_reservation_proofs(root: Path) -> tuple[Phase20MechanismProof, ...]:
    base = CapitalSourceLedger().add_source(
        source_id="t19-profit",
        source=CapitalSource.REALIZED_PROFIT,
        proven_amount_usd=Decimal("20"),
    )
    reserved = base.reserve(
        reservation_id="t19-r1",
        source_id="t19-profit",
        amount_usd=Decimal("15"),
    )
    no_double_spend = _expect_capital_error(
        lambda: reserved.reserve(
            reservation_id="t19-r2",
            source_id="t19-profit",
            amount_usd=Decimal("10"),
        )
    )

    atomic_base = (
        CapitalSourceLedger()
        .add_source(
            source_id="t19-a",
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=Decimal("5"),
        )
        .add_source(
            source_id="t19-b",
            source=CapitalSource.PROTECTED_ECONOMIC_FLOOR,
            proven_amount_usd=Decimal("2"),
        )
    )
    atomic_rejected = _expect_capital_error(
        lambda: atomic_base.reserve_many(
            (
                CapitalReservationRequest(
                    reservation_id="t19-a-r",
                    source_id="t19-a",
                    amount_usd=Decimal("5"),
                ),
                CapitalReservationRequest(
                    reservation_id="t19-b-r",
                    source_id="t19-b",
                    amount_usd=Decimal("3"),
                ),
            )
        )
    )
    atomic_unchanged = (
        atomic_base.reservations == ()
        and all(item.reserved_usd == 0 for item in atomic_base.accounts)
    )

    store = DurableCapitalSourceLedgerStore(root / "t19-cas-ledger.json")
    store.store(base, expected_generation=0)
    stale_generation_rejected = False
    try:
        store.store(base, expected_generation=0)
    except DurableCapitalLedgerError:
        stale_generation_rejected = True

    return (
        _proof(
            "T19",
            "T19_NO_DOUBLE_SPEND",
            no_double_spend,
            "A second reservation cannot consume already-reserved capacity.",
        ),
        _proof(
            "T19",
            "T19_MULTI_SOURCE_ATOMICITY",
            atomic_rejected and atomic_unchanged,
            "A failing multi-source reservation leaves every source unchanged.",
        ),
        _proof(
            "T19",
            "T19_DURABLE_CAS_STALE_WRITER_REJECTED",
            stale_generation_rejected,
            "A stale durable-ledger generation cannot overwrite newer state.",
        ),
    )


def _t20_release_proofs() -> tuple[Phase20MechanismProof, ...]:
    base = CapitalSourceLedger().add_source(
        source_id="t20-profit",
        source=CapitalSource.REALIZED_PROFIT,
        proven_amount_usd=Decimal("20"),
    )
    reserved = base.reserve(
        reservation_id="t20-r1",
        source_id="t20-profit",
        amount_usd=Decimal("8"),
    )
    released = reserved.release_unused("t20-r1")
    account = released.accounts[0]
    reserved_only_release = (
        account.available_usd == Decimal("20")
        and account.reserved_usd == 0
        and account.cumulative_released_usd == Decimal("8")
        and released.reservations[0].state is ReservationState.RELEASED
    )

    deployed = reserved.deploy("t20-r1")
    deployed_release_rejected = _expect_capital_error(
        lambda: deployed.release_unused("t20-r1")
    )
    settled = deployed.settle_deployment(
        "t20-r1",
        returned_capacity_usd=Decimal("3"),
    )
    settled_account = settled.accounts[0]
    settlement_separated = (
        settled_account.available_usd == Decimal("15")
        and settled_account.deployed_usd == 0
        and settled_account.consumed_usd == Decimal("5")
        and settled_account.cumulative_released_usd == Decimal("3")
        and settled.reservations[0].state is ReservationState.SETTLED
    )

    return (
        _proof(
            "T20",
            "T20_RESERVED_ONLY_UNUSED_RELEASE",
            reserved_only_release,
            "Unused reserved capacity returns in full and release is recorded as flow.",
        ),
        _proof(
            "T20",
            "T20_DEPLOYED_RELEASE_PATH_REJECTED",
            deployed_release_rejected,
            "Economically deployed capacity cannot impersonate an unused reservation.",
        ),
        _proof(
            "T20",
            "T20_RETURNED_VS_CONSUMED_ACCOUNTING",
            settlement_separated,
            "Settlement separates returned capacity from economically consumed capacity.",
        ),
    )


def _t05_recycling_proofs(root: Path) -> tuple[Phase20MechanismProof, ...]:
    now = datetime(2026, 9, 27, 2, 0, tzinfo=UTC)

    unreconciled_store = DurableCapitalSourceLedgerStore(
        root / "t05-unreconciled.json"
    )
    unreconciled = ReleasedCapacityEvidence(
        evidence_id="t05-unreconciled",
        source=CapitalSource.RELEASED_RISK_CAPACITY,
        amount_usd=Decimal("20"),
        reconciled_at=now,
        upstream_reference="synthetic:settlement",
        reconciled=False,
    )
    unreconciled_rejected = _expect_capital_error(
        lambda: register_released_capacity(
            unreconciled,
            ledger_store=unreconciled_store,
        )
    )

    margin_store = DurableCapitalSourceLedgerStore(root / "t05-margin.json")
    margin = register_released_capacity(
        ReleasedCapacityEvidence(
            evidence_id="t05-margin",
            source=CapitalSource.RELEASED_MARGIN_CAPACITY,
            amount_usd=Decimal("20"),
            reconciled_at=now,
            upstream_reference="synthetic:margin-release",
        ),
        ledger_store=margin_store,
    )
    margin_to_risk_rejected = _expect_capital_error(
        lambda: reserve_recycled_capacity(
            reservation_id="t05-margin-as-risk",
            source_id=margin.source_id,
            purpose=RecyclePurpose.STOP_RISK,
            amount_usd=Decimal("5"),
            ledger_store=margin_store,
        )
    )

    risk_store_path = root / "t05-risk.json"
    risk_store = DurableCapitalSourceLedgerStore(risk_store_path)
    risk = register_released_capacity(
        ReleasedCapacityEvidence(
            evidence_id="t05-risk",
            source=CapitalSource.RELEASED_RISK_CAPACITY,
            amount_usd=Decimal("20"),
            reconciled_at=now,
            upstream_reference="synthetic:risk-release",
        ),
        ledger_store=risk_store,
    )
    risk_to_margin_rejected = _expect_capital_error(
        lambda: reserve_recycled_capacity(
            reservation_id="t05-risk-as-margin",
            source_id=risk.source_id,
            purpose=RecyclePurpose.MARGIN,
            amount_usd=Decimal("5"),
            ledger_store=risk_store,
        )
    )
    reservation = reserve_recycled_capacity(
        reservation_id="t05-risk-r1",
        source_id=risk.source_id,
        purpose=RecyclePurpose.STOP_RISK,
        amount_usd=Decimal("8"),
        ledger_store=risk_store,
    )
    deploy_recycled_capacity(reservation, ledger_store=risk_store)
    settle_recycled_capacity(
        reservation,
        returned_capacity_usd=Decimal("3"),
        ledger_store=risk_store,
    )
    restarted = DurableCapitalSourceLedgerStore(risk_store_path).load()
    restarted_account = restarted.ledger.accounts[0]
    settlement_persisted = (
        restarted_account.available_usd == Decimal("15")
        and restarted_account.consumed_usd == Decimal("5")
        and restarted_account.cumulative_released_usd == Decimal("3")
    )

    return (
        _proof(
            "T05",
            "T05_RECONCILIATION_REQUIRED",
            unreconciled_rejected,
            "Unreconciled released capacity cannot enter the reusable ledger.",
        ),
        _proof(
            "T05",
            "T05_DIMENSIONAL_NON_FUNGIBILITY",
            margin_to_risk_rejected and risk_to_margin_rejected,
            "Released margin and released stop-risk capacity cannot impersonate each other.",
        ),
        _proof(
            "T05",
            "T05_SETTLEMENT_PERSISTS_AFTER_RESTART",
            settlement_persisted,
            "Returned and consumed recycled risk survive durable-store restart.",
        ),
    )


def run_phase20f_accounting_core_certification(
    *,
    root: Path,
) -> Phase20MechanismCertificationReport:
    """Execute independent contract proofs for T05, T19 and T20."""

    if not isinstance(root, Path):
        raise CiboCapitalManagementError("Phase20F root must be pathlib.Path")
    root.mkdir(parents=True, exist_ok=True)

    proofs = (
        *_t05_recycling_proofs(root),
        *_t19_reservation_proofs(root),
        *_t20_release_proofs(),
    )
    certifications = tuple(
        _certification_for(code, proofs) for code in ("T05", "T19", "T20")
    )
    return Phase20MechanismCertificationReport(
        identity="CIBO_PHASE20F_ACCOUNTING_CORE_CERTIFICATION_V1",
        certifications=certifications,
        proofs=proofs,
    )
