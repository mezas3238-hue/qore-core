"""Source-first, zero-budget QORE research queue (pure decision ledger).

NOT a scheduler/daemon, backtest, TraderLab admission or funding authority.
Stops archival hypotheses from being restarted and stops data-blocked research
from silently proceeding to experiments on proxy market prices.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from qore.infrastructure.cibo.research_director import CiboResearchStage
from qore.infrastructure.trader_lab.lifecycle import TraderLabState

_SCHEMA = "qore.research.zero-budget-intake-ledger.v1"
_CANON = re.compile(r"[a-z][a-z0-9._-]{2,100}\Z")
_HEX = re.compile(r"[a-f0-9]{64}\Z")
_CODE_FUTURES = "research.futures-a.native-6roots-d1"
_CODE_EIA = "research.eia.futures-a-f1f2-closure"
_EXPECTED_EIA_SCIENCE = "NO_SUPPORT_UNDER_PREREG"
_EXPECTED_PLAN_STAGE = CiboResearchStage.EXPERIMENT.value


class ResearchIntakeError(ValueError):
    """A fail-closed source or scientific-evidence boundary was violated."""


class IntakeStatus(StrEnum):
    PROPOSAL_ONLY = "proposal_only"
    SOURCE_BLOCKED = "source_blocked"
    CLOSED_NO_SUPPORT = "closed_no_support"


class NextResearchAction(StrEnum):
    WRITE_NEW_PREREG = "write_new_prereg"
    ACQUIRE_VALID_SOURCE_WITHIN_ZERO_BUDGET = "acquire_valid_source_within_zero_budget"
    STOP_AND_ARCHIVE = "stop_and_archive"


def _code(value: str, label: str) -> str:
    if not isinstance(value, str) or not _CANON.fullmatch(value):
        raise ResearchIntakeError(f"INVALID_CODE_{label}")
    if any(part in value for part in ("secret", "token", "password", "bearer")):
        raise ResearchIntakeError(f"SENSITIVE_CODE_{label}")
    return value


def _sha(value: str, label: str) -> str:
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        raise ResearchIntakeError(f"INVALID_SHA_{label}")
    return value


@dataclass(frozen=True, slots=True)
class ResearchIntakeRecord:
    """One candidate/mission identity, exactly one scientific/data state."""

    code: str
    question_code: str
    status: IntakeStatus
    next_action: NextResearchAction
    data_requirement_code: str
    funding_ceiling_usd: int
    research_root_count: int
    research_source_ohlcv_native_certified: bool
    contract_expiry_asof_verified: bool
    source_rights_verified: bool
    scientific_decision: str
    scientific_plan_fingerprint: str | None
    experiment_runnable: bool = False
    can_open_fresh_holdout: bool = False
    trader_lab_state: str = TraderLabState.DRAFT.value
    governance_approval_granted: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        _code(self.code, "mission")
        _code(self.question_code, "question")
        _code(self.data_requirement_code, "source")
        if type(self.status) is not IntakeStatus or type(self.next_action) is not NextResearchAction:
            raise ResearchIntakeError("INVALID_ENUM")
        if type(self.funding_ceiling_usd) is not int or self.funding_ceiling_usd != 0:
            raise ResearchIntakeError("MARKET_DATA_BUDGET_NOT_ZERO")
        if type(self.research_root_count) is not int or self.research_root_count not in (2, 6):
            raise ResearchIntakeError("INVALID_ROOT_COUNT")
        if any(
            type(x) is not bool for x in (
                self.research_source_ohlcv_native_certified,
                self.contract_expiry_asof_verified,
                self.source_rights_verified,
                self.experiment_runnable,
                self.can_open_fresh_holdout,
                self.governance_approval_granted,
                self.trader_certified,
            )
        ):
            raise ResearchIntakeError("NON_BOOLEAN_CLAIM")
        if (
            self.research_source_ohlcv_native_certified
            or self.contract_expiry_asof_verified
            or self.source_rights_verified
            or self.experiment_runnable
            or self.can_open_fresh_holdout
            or self.governance_approval_granted
            or self.trader_certified
            or self.trader_lab_state != TraderLabState.DRAFT.value
        ):
            raise ResearchIntakeError("FALSE_SOURCE_OR_PROMOTION_CLAIM")
        expected_actions = {
            IntakeStatus.PROPOSAL_ONLY: NextResearchAction.WRITE_NEW_PREREG,
            IntakeStatus.SOURCE_BLOCKED: (
                NextResearchAction.ACQUIRE_VALID_SOURCE_WITHIN_ZERO_BUDGET
            ),
            IntakeStatus.CLOSED_NO_SUPPORT: NextResearchAction.STOP_AND_ARCHIVE,
        }
        if self.next_action is not expected_actions[self.status]:
            raise ResearchIntakeError("INVALID_SOURCE_FIRST_TRANSITION")
        if self.status is IntakeStatus.CLOSED_NO_SUPPORT:
            if self.scientific_decision != _EXPECTED_EIA_SCIENCE:
                raise ResearchIntakeError("CLOSED_WITHOUT_NO_SUPPORT")
            if self.scientific_plan_fingerprint is None:
                raise ResearchIntakeError("CLOSED_WITHOUT_REAL_CF11_PLAN")
            _sha(self.scientific_plan_fingerprint, "cf11-plan")
            if self.code != _CODE_EIA:
                raise ResearchIntakeError("MISMATCHED_CLOSED_IDENTITY")
        elif self.scientific_plan_fingerprint is not None:
            raise ResearchIntakeError("NONCLOSED_CANNOT_BORROW_CF11_PLAN")
        elif self.scientific_decision != "NOT_TESTED":
            raise ResearchIntakeError("NONCLOSED_CANNOT_HAVE_RESULT")
        if self.status is IntakeStatus.SOURCE_BLOCKED and self.code != _CODE_FUTURES:
            raise ResearchIntakeError("UNKNOWN_BLOCKED_MISSION")

    def to_json(self) -> dict[str, Any]:
        out = asdict(self)
        out["status"] = self.status.value
        out["next_action"] = self.next_action.value
        return out


def eia_closed_from_verified_cf11_json(plan: dict[str, Any]) -> ResearchIntakeRecord:
    """Consumes the actual CF-11 value plan JSON from verified Actions pipeline.

    This function does not authenticate source bytes. The runner MUST first
    validate the original EIA artifact and produce the CF-11 value within
    the same Actions job, with only contents:read and actions:read rights.
    """
    if not isinstance(plan, dict):
        raise ResearchIntakeError("NOT_A_CF11_DOCUMENT")
    allowed = {
        "schema", "plan_code", "question_code", "hypothesis_code", "stage",
        "evidence_status", "evidence_reasons", "evidence_references",
        "data_requirements", "as_of", "receipt_sha256",
        "plan_fingerprint", "scientific_decision",
        "source_artifact_authenticated_upstream", "trader_lab_state",
        "trader_lab_stage_evidence_produced", "runnable_trader_created",
        "economic_backtest_performed", "demo_eligible",
        "risk_authority_issued", "cibo_authority_issued",
        "market_provenance_certified", "fresh_holdout_consumed",
        "merge_authorized",
    }
    if set(plan) != allowed:
        raise ResearchIntakeError("CF11_PLAN_SCHEMA_CHANGED")
    expected = {
        "schema": "qore.research.cf11.science-only-closed-experiment.v1",
        "plan_code": _CODE_EIA,
        "question_code": "research.question.f1f2-directional-probability",
        "hypothesis_code": "research.hypothesis.backwardation-predicts-f1-up",
        "stage": _EXPECTED_PLAN_STAGE,
        "evidence_status": "insufficient",
        "scientific_decision": _EXPECTED_EIA_SCIENCE,
        "trader_lab_state": TraderLabState.DRAFT.value,
        "source_artifact_authenticated_upstream": True,
    }
    for key, val in expected.items():
        if type(plan.get(key)) is not type(val) or plan[key] != val:
            raise ResearchIntakeError(f"CF11_RECEIPT_CONTRADICTION_{key}")
    for key in (
        "trader_lab_stage_evidence_produced", "runnable_trader_created",
        "economic_backtest_performed", "demo_eligible", "risk_authority_issued",
        "cibo_authority_issued", "market_provenance_certified",
        "fresh_holdout_consumed", "merge_authorized",
    ):
        if plan[key] is not False:
            raise ResearchIntakeError(f"CF11_FAKE_APPROVAL_{key}")
    for key in ("plan_fingerprint", "receipt_sha256"):
        _sha(plan[key], key)
    refs = plan["evidence_references"]
    needs = plan["data_requirements"]
    if (
        not isinstance(refs, list)
        or len(refs) != 1
        or not isinstance(refs[0], str)
        or not refs[0].endswith(plan["receipt_sha256"])
        or not isinstance(needs, list)
        or len(needs) != 4
        or len(set(needs)) != 4
        or not all(isinstance(n, str) and n.startswith("evidence:source-eia:") for n in needs)
    ):
        raise ResearchIntakeError("CF11_SCIENCE_OR_SOURCE_REFS_NOT_COMPLETE")
    if not isinstance(plan["evidence_reasons"], list) or "hypothesis.no-support" not in plan["evidence_reasons"]:
        raise ResearchIntakeError("CF11_NO_SUPPORT_REASON_MISSING")
    return ResearchIntakeRecord(
        code=_CODE_EIA,
        question_code=plan["question_code"],
        status=IntakeStatus.CLOSED_NO_SUPPORT,
        next_action=NextResearchAction.STOP_AND_ARCHIVE,
        data_requirement_code="eia.f1f2.reference-close-only",
        funding_ceiling_usd=0,
        research_root_count=2,
        research_source_ohlcv_native_certified=False,
        contract_expiry_asof_verified=False,
        source_rights_verified=False,
        scientific_decision=_EXPECTED_EIA_SCIENCE,
        scientific_plan_fingerprint=plan["plan_fingerprint"],
    )


def blocked_futures_a_m0() -> ResearchIntakeRecord:
    return ResearchIntakeRecord(
        code=_CODE_FUTURES,
        question_code="research.question.native-commodity-futures-edge",
        status=IntakeStatus.SOURCE_BLOCKED,
        next_action=NextResearchAction.ACQUIRE_VALID_SOURCE_WITHIN_ZERO_BUDGET,
        data_requirement_code="cme.native-six-roots-two-contracts-d1",
        funding_ceiling_usd=0,
        research_root_count=6,
        research_source_ohlcv_native_certified=False,
        contract_expiry_asof_verified=False,
        source_rights_verified=False,
        scientific_decision="NOT_TESTED",
        scientific_plan_fingerprint=None,
    )


@dataclass(frozen=True, slots=True)
class ResearchIntakeLedger:
    entries: tuple[ResearchIntakeRecord, ...]

    def __post_init__(self) -> None:
        if type(self.entries) is not tuple or len(self.entries) != 2:
            raise ResearchIntakeError("QUEUE_MUST_COVER_EXACTLY_TWO_VERIFIED_MISSIONS")
        names = tuple(e.code for e in self.entries)
        if names != tuple(sorted((_CODE_EIA, _CODE_FUTURES))):
            raise ResearchIntakeError("QUEUE_ORDER_OR_MISSION_SUBSTITUTION")
        if any(type(e) is not ResearchIntakeRecord for e in self.entries):
            raise ResearchIntakeError("UNTRUSTED_QUEUE_OBJECT")
        for entry in self.entries:
            ResearchIntakeRecord.__post_init__(entry)

    def to_json(self) -> dict[str, Any]:
        entries = [e.to_json() for e in self.entries]
        core = {
            "schema": _SCHEMA,
            "archive_scientific_outcomes_without_retesting": True,
            "source_first_gate_before_experiment": True,
            "estimated_traders_promoted": 0,
            "spent_usd": 0,
            "stale_fx_holdout_opened": False,
            "eia_fresh_holdout_opened": False,
            "economic_replay_performed": False,
            "production_execution_enabled": False,
            "new_hypotheses_registered": 0,
            "entries": entries,
        }
        canonical = json.dumps(core, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return {
            **core,
            "ledger_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        }


def build_source_first_queue(authenticated_eia_cf11_plan: dict[str, Any]) -> ResearchIntakeLedger:
    return ResearchIntakeLedger(
        entries=tuple(
            sorted(
                (
                    blocked_futures_a_m0(),
                    eia_closed_from_verified_cf11_json(authenticated_eia_cf11_plan),
                ),
                key=lambda e: e.code,
            )
        )
    )
