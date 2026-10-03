"""Trader-Lab authority receipts for the CIBO functional approval chain.

Owner authority is above Trader Lab.  Trader Lab is the technical approval
authority for CIBO functions.  CIBO itself cannot mint these receipts.

A PASS receipt is emitted only when:
- the exact candidate is already inside a valid Trader Lab lifecycle;
- at least RESEARCH has passed;
- the function execution result is PASS;
- the exact previous CIBO function gate has a valid PASS receipt; and
- candidate/time/chain fingerprints are consistent.

The receipt grants evidence provenance only.  It grants no order, Risk, sizing,
broker, LIVE, Production, capital-mutation, merge, or deployment authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
import json
from re import fullmatch

from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.infrastructure.trader_lab.candidate import (
    TraderLabCandidateBinding,
    TraderLabError,
    TraderLabValidationError,
    compute_trader_lab_candidate_fingerprint,
)
from qore.infrastructure.trader_lab.lifecycle import (
    TraderLabLifecycle,
    TraderLabState,
    validate_trader_lab_lifecycle,
)
from qore.kernel.result import Failure, Result, Success

_SHA256_RE = r"[0-9a-f]{64}"
_PASS_SEAL = object()


class CiboTraderLabFunctionGate(StrEnum):
    """Strict CIBO -> Trader Lab approval order.

    CF01..CF20 are the current functional executive chain.  Compound stages then
    prove individual compound-capital machinery before the global portfolio view.
    """

    CF01_FINANCIAL_WORLD_MONITORING = "cf01.financial-world-monitoring"
    CF02_MARKET_INTELLIGENCE_MESH = "cf02.market-intelligence-mesh"
    CF03_TRADER_DIRECTOR = "cf03.trader-director"
    CF04_TRADER_ACADEMY = "cf04.trader-academy"
    CF05_OPPORTUNITY_SEARCH = "cf05.opportunity-search"
    CF06_PORTFOLIO_INTELLIGENCE = "cf06.portfolio-intelligence"
    CF07_ECONOMIC_INTELLIGENCE = "cf07.economic-intelligence"
    CF08_OUTCOME_JOURNAL = "cf08.outcome-journal"
    CF09_FAILURE_INTELLIGENCE = "cf09.failure-intelligence"
    CF10_QUANTITATIVE_INTELLIGENCE = "cf10.quantitative-intelligence"
    CF11_RESEARCH_DIRECTOR = "cf11.research-director"
    CF12_RISK_AWARE_RECOMMENDATION = "cf12.risk-aware-recommendation"
    CF13_CORE_HEALTH = "cf13.core-health"
    CF14_EXECUTIVE_PLANNER = "cf14.executive-planner"
    CF15_CEO_DIALOGUE = "cf15.ceo-dialogue"
    CF16_TRADER_VOICE = "cf16.trader-voice"
    CF17_DECISION_JOURNAL = "cf17.decision-journal"
    CF18_SELF_EVALUATION = "cf18.self-evaluation"
    CF19_LEARNING = "cf19.learning"
    CF20_FUNCTIONAL_COORDINATOR = "cf20.functional-coordinator"
    CC01_REALIZED_PROFIT_LOT = "cc01.realized-profit-lot"
    CC02_COMPOUND_PORTFOLIO_LEDGER = "cc02.compound-portfolio-ledger"
    CC03_PROTECTED_CAPITAL_FLOOR = "cc03.protected-capital-floor"
    CC04_COMPOUND_CYCLE_STATE = "cc04.compound-cycle-state"
    CC05_FUNDING_COORDINATION = "cc05.funding-coordination"
    CC06_MARKET_CYCLE = "cc06.market-cycle"
    CC07_PATH_HISTORY = "cc07.path-history"
    CC08_PATH_MONTE_CARLO = "cc08.path-monte-carlo"
    CC09_REAL_POPULATION_BINDING = "cc09.real-population-binding"
    CC10_TEMPORAL_REPLICATION = "cc10.temporal-replication"
    CC11_TEMPORAL_REPLICATION_GATE = "cc11.temporal-replication-gate"
    CC12_SEQUENTIAL_COMPOUNDING = "cc12.sequential-compounding"
    CC13_INTERNAL_CAPITAL_MARKET = "cc13.internal-capital-market"
    CC14_ADAPTIVE_COMPOUND_SPEED = "cc14.adaptive-compound-speed"
    CC15_ACCOUNT_CORE_COMPOUND_PORTFOLIO = "cc15.account-core-compound-portfolio"
    CC16_COMPOUND_CYCLE_REPLAY = "cc16.compound-cycle-replay"
    PC01_QORE_CORE_COMPOUND_PORTFOLIO = "pc01.qore-core-compound-portfolio"


CIBO_TRADER_LAB_FUNCTION_SEQUENCE: tuple[CiboTraderLabFunctionGate, ...] = tuple(
    CiboTraderLabFunctionGate
)


class CiboTraderLabExecutionStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise TraderLabValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise TraderLabValidationError(f"{field_name} must be timezone-aware")


def _validate_sha256(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_SHA256_RE, value) is None:
        raise TraderLabValidationError(f"{field_name} must be lowercase sha256 hex")
    return value


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _validate_candidate(candidate: TraderLabCandidateBinding) -> None:
    if not isinstance(candidate, TraderLabCandidateBinding):
        raise TraderLabValidationError("candidate must be TraderLabCandidateBinding")
    expected = compute_trader_lab_candidate_fingerprint(
        candidate_id=candidate.candidate_id,
        version=candidate.version,
        strategy_binding=candidate.strategy_binding,
    )
    if candidate.fingerprint != expected:
        raise TraderLabValidationError(
            "candidate fingerprint must match the recomputed exact binding"
        )


@dataclass(frozen=True, slots=True)
class TraderLabCiboFunctionExecution:
    """Observed execution fingerprint for exactly one CIBO function in Trader Lab."""

    candidate: TraderLabCandidateBinding
    function: CiboTraderLabFunctionGate
    input_sha256: str
    output_sha256: str
    executed_at: datetime
    status: CiboTraderLabExecutionStatus
    execution_sha256: str

    def __post_init__(self) -> None:
        _validate_candidate(self.candidate)
        if type(self.function) is not CiboTraderLabFunctionGate:
            raise TraderLabValidationError(
                "function must be exact CiboTraderLabFunctionGate"
            )
        _validate_sha256(self.input_sha256, field_name="function input_sha256")
        _validate_sha256(self.output_sha256, field_name="function output_sha256")
        _validate_timestamp(self.executed_at, field_name="function executed_at")
        if type(self.status) is not CiboTraderLabExecutionStatus:
            raise TraderLabValidationError(
                "status must be exact CiboTraderLabExecutionStatus"
            )
        expected = compute_cibo_function_execution_sha256(
            candidate=self.candidate,
            function=self.function,
            input_sha256=self.input_sha256,
            output_sha256=self.output_sha256,
            executed_at=self.executed_at,
            status=self.status,
        )
        if self.execution_sha256 != expected:
            raise TraderLabValidationError(
                "execution_sha256 must match the exact observed execution"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.candidate.fingerprint.value,
            self.function.value,
            self.input_sha256,
            self.output_sha256,
            self.executed_at.astimezone(UTC).isoformat(timespec="microseconds"),
            self.status.value,
            self.execution_sha256,
        )


def compute_cibo_function_execution_sha256(
    *,
    candidate: TraderLabCandidateBinding,
    function: CiboTraderLabFunctionGate,
    input_sha256: str,
    output_sha256: str,
    executed_at: datetime,
    status: CiboTraderLabExecutionStatus,
) -> str:
    _validate_candidate(candidate)
    if type(function) is not CiboTraderLabFunctionGate:
        raise TraderLabValidationError(
            "function must be exact CiboTraderLabFunctionGate"
        )
    _validate_sha256(input_sha256, field_name="function input_sha256")
    _validate_sha256(output_sha256, field_name="function output_sha256")
    _validate_timestamp(executed_at, field_name="function executed_at")
    if type(status) is not CiboTraderLabExecutionStatus:
        raise TraderLabValidationError(
            "status must be exact CiboTraderLabExecutionStatus"
        )
    return sha256(
        _canonical_bytes(
            {
                "schema": "qore.trader_lab.cibo_function_execution.v1",
                "candidate_fingerprint": candidate.fingerprint.value,
                "function": function.value,
                "input_sha256": input_sha256,
                "output_sha256": output_sha256,
                "executed_at": executed_at.astimezone(UTC).isoformat(
                    timespec="microseconds"
                ),
                "status": status.value,
            }
        )
    ).hexdigest()


def build_cibo_function_execution(
    *,
    candidate: TraderLabCandidateBinding,
    function: CiboTraderLabFunctionGate,
    input_sha256: str,
    output_sha256: str,
    executed_at: datetime,
    status: CiboTraderLabExecutionStatus,
) -> Result[TraderLabCiboFunctionExecution, TraderLabError]:
    """Build an immutable record from an execution already observed by Trader Lab."""

    try:
        fingerprint = compute_cibo_function_execution_sha256(
            candidate=candidate,
            function=function,
            input_sha256=input_sha256,
            output_sha256=output_sha256,
            executed_at=executed_at,
            status=status,
        )
        return Success(
            TraderLabCiboFunctionExecution(
                candidate=candidate,
                function=function,
                input_sha256=input_sha256,
                output_sha256=output_sha256,
                executed_at=executed_at,
                status=status,
                execution_sha256=fingerprint,
            )
        )
    except TraderLabError as error:
        return Failure(error)


@dataclass(frozen=True, slots=True)
class TraderLabCiboFunctionPassReceipt:
    """Sealed Trader-Lab PASS authority for one exact CIBO function gate."""

    candidate: TraderLabCandidateBinding
    function: CiboTraderLabFunctionGate
    execution_sha256: str
    lifecycle_state: TraderLabState
    lifecycle_tail_evidence_sha256: str
    previous_receipt: TraderLabCiboFunctionPassReceipt | None
    approved_at: datetime
    receipt_sha256: str
    evidence_ref: CiboEvidenceRef
    _seal: object | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _PASS_SEAL:
            raise TraderLabValidationError(
                "CIBO function PASS receipt can only be issued by Trader Lab"
            )
        _validate_cibo_function_pass_receipt(self)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.candidate.fingerprint.value,
            self.function.value,
            self.execution_sha256,
            self.lifecycle_state.value,
            self.lifecycle_tail_evidence_sha256,
            (
                None
                if self.previous_receipt is None
                else self.previous_receipt.receipt_sha256
            ),
            self.approved_at.astimezone(UTC).isoformat(timespec="microseconds"),
            self.receipt_sha256,
            self.evidence_ref.logical_values(),
        )


def _expected_previous(
    function: CiboTraderLabFunctionGate,
) -> CiboTraderLabFunctionGate | None:
    try:
        index = CIBO_TRADER_LAB_FUNCTION_SEQUENCE.index(function)
    except ValueError as error:
        raise TraderLabValidationError("unknown CIBO function gate") from error
    if index == 0:
        return None
    return CIBO_TRADER_LAB_FUNCTION_SEQUENCE[index - 1]


def compute_cibo_function_pass_receipt_sha256(
    *,
    candidate: TraderLabCandidateBinding,
    function: CiboTraderLabFunctionGate,
    execution_sha256: str,
    lifecycle_state: TraderLabState,
    lifecycle_tail_evidence_sha256: str,
    previous_receipt_sha256: str | None,
    approved_at: datetime,
) -> str:
    _validate_candidate(candidate)
    if type(function) is not CiboTraderLabFunctionGate:
        raise TraderLabValidationError(
            "function must be exact CiboTraderLabFunctionGate"
        )
    _validate_sha256(execution_sha256, field_name="receipt execution_sha256")
    if type(lifecycle_state) is not TraderLabState:
        raise TraderLabValidationError("lifecycle_state must be exact TraderLabState")
    _validate_sha256(
        lifecycle_tail_evidence_sha256,
        field_name="lifecycle tail evidence sha256",
    )
    if previous_receipt_sha256 is not None:
        _validate_sha256(
            previous_receipt_sha256,
            field_name="previous receipt sha256",
        )
    _validate_timestamp(approved_at, field_name="receipt approved_at")
    return sha256(
        _canonical_bytes(
            {
                "schema": "qore.trader_lab.cibo_function_pass.v1",
                "candidate_fingerprint": candidate.fingerprint.value,
                "function": function.value,
                "execution_sha256": execution_sha256,
                "lifecycle_state": lifecycle_state.value,
                "lifecycle_tail_evidence_sha256": lifecycle_tail_evidence_sha256,
                "previous_receipt_sha256": previous_receipt_sha256,
                "approved_at": approved_at.astimezone(UTC).isoformat(
                    timespec="microseconds"
                ),
            }
        )
    ).hexdigest()


def _validate_cibo_function_pass_receipt(
    receipt: TraderLabCiboFunctionPassReceipt,
) -> None:
    if type(receipt) is not TraderLabCiboFunctionPassReceipt:
        raise TraderLabValidationError(
            "receipt must be exact TraderLabCiboFunctionPassReceipt"
        )
    if receipt._seal is not _PASS_SEAL:
        raise TraderLabValidationError(
            "CIBO function PASS receipt is not sealed by Trader Lab"
        )
    _validate_candidate(receipt.candidate)
    if type(receipt.function) is not CiboTraderLabFunctionGate:
        raise TraderLabValidationError(
            "receipt function must be exact CiboTraderLabFunctionGate"
        )
    _validate_sha256(receipt.execution_sha256, field_name="receipt execution_sha256")
    if type(receipt.lifecycle_state) is not TraderLabState:
        raise TraderLabValidationError(
            "receipt lifecycle_state must be exact TraderLabState"
        )
    if receipt.lifecycle_state in {
        TraderLabState.DRAFT,
        TraderLabState.REJECTED,
        TraderLabState.DEGRADED,
        TraderLabState.SUSPENDED,
    }:
        raise TraderLabValidationError(
            "CIBO function PASS requires a non-blocked qualified Trader Lab lifecycle"
        )
    _validate_sha256(
        receipt.lifecycle_tail_evidence_sha256,
        field_name="receipt lifecycle tail evidence sha256",
    )
    _validate_timestamp(receipt.approved_at, field_name="receipt approved_at")
    expected_previous = _expected_previous(receipt.function)
    if expected_previous is None:
        if receipt.previous_receipt is not None:
            raise TraderLabValidationError(
                "first CIBO function gate must not carry a previous receipt"
            )
        previous_sha = None
    else:
        if type(receipt.previous_receipt) is not TraderLabCiboFunctionPassReceipt:
            raise TraderLabValidationError(
                "CIBO function gate requires the exact previous Trader Lab PASS receipt"
            )
        _validate_cibo_function_pass_receipt(receipt.previous_receipt)
        if receipt.previous_receipt.function is not expected_previous:
            raise TraderLabValidationError(
                "CIBO function gates cannot be skipped or reordered"
            )
        if receipt.previous_receipt.candidate != receipt.candidate:
            raise TraderLabValidationError(
                "previous PASS receipt must bind the exact same candidate"
            )
        if receipt.approved_at < receipt.previous_receipt.approved_at:
            raise TraderLabValidationError(
                "CIBO function PASS time cannot predate the previous gate"
            )
        previous_sha = receipt.previous_receipt.receipt_sha256
    expected = compute_cibo_function_pass_receipt_sha256(
        candidate=receipt.candidate,
        function=receipt.function,
        execution_sha256=receipt.execution_sha256,
        lifecycle_state=receipt.lifecycle_state,
        lifecycle_tail_evidence_sha256=receipt.lifecycle_tail_evidence_sha256,
        previous_receipt_sha256=previous_sha,
        approved_at=receipt.approved_at,
    )
    if receipt.receipt_sha256 != expected:
        raise TraderLabValidationError(
            "receipt_sha256 must match the exact Trader Lab PASS receipt"
        )
    expected_ref = CiboEvidenceRef(
        f"trader-lab:cibo-function:{receipt.function.value}:{receipt.receipt_sha256}"
    )
    if receipt.evidence_ref != expected_ref:
        raise TraderLabValidationError(
            "receipt evidence_ref must bind the exact PASS receipt"
        )


def validate_trader_lab_cibo_function_pass_receipt(
    receipt: TraderLabCiboFunctionPassReceipt,
) -> None:
    """Re-validate the complete chained PASS receipt at a trust boundary."""

    _validate_cibo_function_pass_receipt(receipt)


def _sealed_receipt(
    *,
    candidate: TraderLabCandidateBinding,
    function: CiboTraderLabFunctionGate,
    execution_sha256: str,
    lifecycle_state: TraderLabState,
    lifecycle_tail_evidence_sha256: str,
    previous_receipt: TraderLabCiboFunctionPassReceipt | None,
    approved_at: datetime,
) -> TraderLabCiboFunctionPassReceipt:
    previous_sha = (
        None if previous_receipt is None else previous_receipt.receipt_sha256
    )
    receipt_sha = compute_cibo_function_pass_receipt_sha256(
        candidate=candidate,
        function=function,
        execution_sha256=execution_sha256,
        lifecycle_state=lifecycle_state,
        lifecycle_tail_evidence_sha256=lifecycle_tail_evidence_sha256,
        previous_receipt_sha256=previous_sha,
        approved_at=approved_at,
    )
    evidence_ref = CiboEvidenceRef(
        f"trader-lab:cibo-function:{function.value}:{receipt_sha}"
    )
    receipt = object.__new__(TraderLabCiboFunctionPassReceipt)
    object.__setattr__(receipt, "candidate", candidate)
    object.__setattr__(receipt, "function", function)
    object.__setattr__(receipt, "execution_sha256", execution_sha256)
    object.__setattr__(receipt, "lifecycle_state", lifecycle_state)
    object.__setattr__(
        receipt,
        "lifecycle_tail_evidence_sha256",
        lifecycle_tail_evidence_sha256,
    )
    object.__setattr__(receipt, "previous_receipt", previous_receipt)
    object.__setattr__(receipt, "approved_at", approved_at)
    object.__setattr__(receipt, "receipt_sha256", receipt_sha)
    object.__setattr__(receipt, "evidence_ref", evidence_ref)
    object.__setattr__(receipt, "_seal", _PASS_SEAL)
    receipt.__post_init__()
    return receipt


def issue_trader_lab_cibo_function_pass(
    lifecycle: TraderLabLifecycle,
    execution: TraderLabCiboFunctionExecution,
    *,
    previous_receipt: TraderLabCiboFunctionPassReceipt | None,
) -> Result[TraderLabCiboFunctionPassReceipt, TraderLabError]:
    """Issue PASS only after actual execution and the exact prior gate have passed."""

    try:
        validate_trader_lab_lifecycle(lifecycle)
        if not isinstance(execution, TraderLabCiboFunctionExecution):
            raise TraderLabValidationError(
                "execution must be TraderLabCiboFunctionExecution"
            )
        TraderLabCiboFunctionExecution.__post_init__(execution)
        if lifecycle.terminal is not None:
            raise TraderLabValidationError(
                "blocked Trader Lab lifecycle cannot approve CIBO functions"
            )
        if not lifecycle.qualifications:
            raise TraderLabValidationError(
                "CIBO function approval requires at least Trader Lab RESEARCH PASS"
            )
        if lifecycle.candidate != execution.candidate:
            raise TraderLabValidationError(
                "function execution must bind the exact Trader Lab candidate"
            )
        if execution.status is not CiboTraderLabExecutionStatus.PASS:
            raise TraderLabValidationError(
                "failed CIBO function execution cannot receive a PASS receipt"
            )
        tail = lifecycle.qualifications[-1]
        if execution.executed_at < tail.qualified_at:
            raise TraderLabValidationError(
                "function execution cannot predate the Trader Lab qualification"
            )
        expected_previous = _expected_previous(execution.function)
        if expected_previous is None:
            if previous_receipt is not None:
                raise TraderLabValidationError(
                    "first CIBO function gate cannot consume a previous receipt"
                )
        else:
            if type(previous_receipt) is not TraderLabCiboFunctionPassReceipt:
                raise TraderLabValidationError(
                    "function cannot advance without the previous Trader Lab PASS"
                )
            _validate_cibo_function_pass_receipt(previous_receipt)
            if previous_receipt.function is not expected_previous:
                raise TraderLabValidationError(
                    "function approval order cannot skip or reorder gates"
                )
            if previous_receipt.candidate != lifecycle.candidate:
                raise TraderLabValidationError(
                    "previous PASS must bind the exact same candidate"
                )
            if execution.executed_at < previous_receipt.approved_at:
                raise TraderLabValidationError(
                    "function execution cannot predate the previous PASS"
                )
        return Success(
            _sealed_receipt(
                candidate=lifecycle.candidate,
                function=execution.function,
                execution_sha256=execution.execution_sha256,
                lifecycle_state=lifecycle.state,
                lifecycle_tail_evidence_sha256=tail.evidence.fingerprint.value,
                previous_receipt=previous_receipt,
                approved_at=execution.executed_at,
            )
        )
    except TraderLabError as error:
        return Failure(error)
