"""Maximum-ceiling open-work ledger and absolute zero-open-work gate.

This module encodes Owner law: Shared cannot become PRE_CERTIFICATION_READY while
any mandatory capability remains partial, falsified without a verified
replacement, blocked, missing required evidence, or otherwise unfinished.

The ledger is deliberately conservative. A green CI lane, an enum/schema, or a
single successful experiment never upgrades a mandatory capability to
COMPLETED_AND_PROVEN by itself.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Final


class SharedWorkState(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    ARCHITECTURE_DEFINED = "ARCHITECTURE_DEFINED"
    CONTRACT_IMPLEMENTED = "CONTRACT_IMPLEMENTED"
    ENGINE_IMPLEMENTED = "ENGINE_IMPLEMENTED"
    REAL_DATA_BOUND = "REAL_DATA_BOUND"
    CAUSAL_REPLAY_EXECUTED = "CAUSAL_REPLAY_EXECUTED"
    SCIENTIFIC_VALUE_DEMONSTRATED = "SCIENTIFIC_VALUE_DEMONSTRATED"
    STRESS_PASS = "STRESS_PASS"
    RESEARCH_OOS_PASS = "RESEARCH_OOS_PASS"
    TEMPORAL_REPLICATION_PASS = "TEMPORAL_REPLICATION_PASS"
    ECONOMIC_VALUE_PASS = "ECONOMIC_VALUE_PASS"
    RESEARCH_INCOMPLETE = "RESEARCH_INCOMPLETE"
    EXTERNAL_DEPENDENCY_BLOCKED = "EXTERNAL_DEPENDENCY_BLOCKED"
    UNRESOLVED_REQUIRED_AUDIT = "UNRESOLVED_REQUIRED_AUDIT"
    COMPLETED_AND_PROVEN = "COMPLETED_AND_PROVEN"
    FALSIFIED_AND_CLOSED = "FALSIFIED_AND_CLOSED"


TERMINAL_MANDATORY_STATE: Final = SharedWorkState.COMPLETED_AND_PROVEN
TERMINAL_OPTIONAL_STATES: Final = frozenset(
    {
        SharedWorkState.COMPLETED_AND_PROVEN,
        SharedWorkState.FALSIFIED_AND_CLOSED,
    }
)


@dataclass(frozen=True, slots=True)
class SharedOpenWorkItem:
    work_id: str
    family: str
    title: str
    mandatory: bool
    state: SharedWorkState
    evidence_refs: tuple[str, ...]
    replacement_required_if_falsified: bool = True

    def __post_init__(self) -> None:
        if not self.work_id.strip() or not self.family.strip() or not self.title.strip():
            raise ValueError("open-work identity fields must be non-empty")
        if not self.evidence_refs:
            raise ValueError("open-work item requires evidence refs")
        if self.evidence_refs != tuple(sorted(set(self.evidence_refs))):
            raise ValueError("open-work evidence refs must be unique and canonical")
        if self.mandatory and self.state is SharedWorkState.FALSIFIED_AND_CLOSED:
            raise ValueError(
                "mandatory capability cannot be closed merely because one hypothesis failed"
            )
        if not self.mandatory and self.replacement_required_if_falsified:
            raise ValueError(
                "optional falsifiable hypothesis must not require capability replacement"
            )


@dataclass(frozen=True, slots=True)
class SharedZeroOpenWorkAssessment:
    ledger_identity: str
    total_items: int
    mandatory_items: int
    mandatory_closed: int
    optional_items: int
    optional_closed: int
    blocker_ids: tuple[str, ...]
    zero_open_required_work: bool
    pre_certification_ready: bool
    final_certification_exam_authorized: bool
    protected_holdout_opening_authorized: bool
    productive_authority: bool

    def __post_init__(self) -> None:
        if self.zero_open_required_work != (not self.blocker_ids):
            raise ValueError("zero-open-work flag must match blocker set")
        if self.pre_certification_ready and not self.zero_open_required_work:
            raise ValueError("pre-certification cannot bypass required blockers")
        if self.final_certification_exam_authorized:
            raise ValueError(
                "zero-open-work gate alone never authorizes final certification exam"
            )
        if self.protected_holdout_opening_authorized:
            raise ValueError(
                "zero-open-work gate alone never authorizes protected holdout opening"
            )
        if self.productive_authority:
            raise ValueError("zero-open-work gate grants no productive authority")


def _item(
    work_id: str,
    family: str,
    title: str,
    state: SharedWorkState,
    evidence_ref: str,
    *,
    mandatory: bool = True,
) -> SharedOpenWorkItem:
    return SharedOpenWorkItem(
        work_id=work_id,
        family=family,
        title=title,
        mandatory=mandatory,
        state=state,
        evidence_refs=(evidence_ref,),
        replacement_required_if_falsified=mandatory,
    )


_WP_TITLES: Final = (
    "Probabilistic Market Digital Twin",
    "Federation of Worlds",
    "Causal Discovery Engine",
    "Market Representation Discovery",
    "Temporal Hierarchical Brain",
    "Market Agency Model",
    "Counterfactual World Engine",
    "Epistemic Engine",
    "Scientific Society / Ensemble of Minds",
    "Autonomous Scientific Laboratory",
    "Governed Self-Improvement and Continual Learning",
    "Cognitive Arbitration + Meta-Cognitive Scientific Intelligence",
)

_MC_TITLES: Final = (
    "Probabilistic Market Digital Twin",
    "Federation of Worlds",
    "Dynamic Causal Discovery",
    "Market Representation and Ontology Discovery",
    "Hierarchical World Model / Temporal Brain",
    "Latent State Reconstruction",
    "Predictive State Model and Predictive Coding",
    "Active Perception + Value of Information",
    "Belief State",
    "Market Physics / Constraint Engine",
    "Neural-Symbolic Brain",
    "QORE Market Foundation Model",
    "Dynamic Graph Market Model",
    "Temporal Causal Model",
    "Uncertainty Decomposition",
    "Episodic, Semantic, Regime and Failure Memory",
    "Market Agency Model",
    "Counterfactual World Engine",
    "Trajectory Intelligence",
    "Stability Engine",
    "Scientific Society / Ensemble of Minds",
    "Autonomous Scientific Laboratory",
    "Meta-Learning and Rapid Regime Adaptation",
    "Continual Learning Without Catastrophic Forgetting",
    "Governed Self-Improvement",
    "Cognitive Arbitration",
    "Meta-Cognitive Scientific Intelligence",
    "Core/Broker Cognition and Blindspot Engine",
)

_STI_TITLES: Final = (
    "Shared-Trader Gap Audit",
    "SharedTraderIntelligenceSnapshot",
    "Opportunity Discovery Engine",
    "Global Opportunity Board",
    "Opportunity Lifecycle / Watch State",
    "Regime Transition Intelligence",
    "Continuation / Positive-Tail Intelligence",
    "Position Observation Subscription",
    "Position Threat Intelligence",
    "World-at-Entry vs World-Now Delta",
    "Trader-Relevant Projection",
    "Alert Routing / Materiality / Deduplication",
    "Swing Trader Support",
    "Shared-to-CIBO Read-Only Facts",
    "Historical Replay + Control/Treatment Attribution",
    "OOS / Stress / Temporal Replication",
    "Governed Productive Admission Gate",
)

_GW_TITLES: Final = (
    "Global Perception Gap Audit",
    "Provider Capability Matrix",
    "Canonical Instrument Identity",
    "Market Hours / Temporal Synchronization",
    "FX World",
    "Rates World",
    "Equity World",
    "Volatility World",
    "Metals World",
    "Energy World",
    "Agriculture World",
    "Softs World",
    "Livestock World",
    "Power / Freight / Environmental Feasibility",
    "Contract Chain / Roll",
    "Term Structure",
    "Seasonality",
    "Fundamental / Weather Contracts",
    "Global Relational Graph",
    "Global Regime Model",
    "Latent / Unknown State Discovery",
    "Active Perception",
    "Cognitive Compression",
    "Scientific Memory",
)


def build_shared_master_open_work_ledger() -> tuple[SharedOpenWorkItem, ...]:
    """Return the current conservative, machine-readable mandatory ledger."""

    items: list[SharedOpenWorkItem] = []

    # #638 is canonical for current WP closure. WP-01..04 are checked closed;
    # WP-05..12 remain explicitly open.
    for index, title in enumerate(_WP_TITLES, start=1):
        state = (
            SharedWorkState.COMPLETED_AND_PROVEN
            if index <= 4
            else SharedWorkState.RESEARCH_INCOMPLETE
        )
        items.append(
            _item(
                f"WP-{index:02d}",
                "WP",
                title,
                state,
                "github-issue-638-master-program",
            )
        )

    # WP closure does not automatically prove the corresponding MC capability.
    # MC-01..28 remain unresolved until an explicit verified-superset audit
    # binds each capability to scientific evidence satisfying Standard 006.
    for index, title in enumerate(_MC_TITLES, start=1):
        state = SharedWorkState.UNRESOLVED_REQUIRED_AUDIT
        items.append(
            _item(
                f"MC-{index:02d}",
                "MC",
                title,
                state,
                "maximum-precertification-standard-006",
            )
        )

    sti_states = {
        0: SharedWorkState.CONTRACT_IMPLEMENTED,
        1: SharedWorkState.CONTRACT_IMPLEMENTED,
        2: SharedWorkState.STRESS_PASS,
        3: SharedWorkState.NOT_STARTED,
        4: SharedWorkState.CONTRACT_IMPLEMENTED,
        5: SharedWorkState.EXTERNAL_DEPENDENCY_BLOCKED,
        6: SharedWorkState.EXTERNAL_DEPENDENCY_BLOCKED,
        7: SharedWorkState.CONTRACT_IMPLEMENTED,
        8: SharedWorkState.RESEARCH_OOS_PASS,
        9: SharedWorkState.CONTRACT_IMPLEMENTED,
        10: SharedWorkState.CONTRACT_IMPLEMENTED,
        11: SharedWorkState.CONTRACT_IMPLEMENTED,
        12: SharedWorkState.CONTRACT_IMPLEMENTED,
        13: SharedWorkState.CONTRACT_IMPLEMENTED,
        14: SharedWorkState.CAUSAL_REPLAY_EXECUTED,
        15: SharedWorkState.RESEARCH_INCOMPLETE,
        16: SharedWorkState.NOT_STARTED,
    }
    for index, title in enumerate(_STI_TITLES):
        evidence_by_index = {
            2: "sti2-v2-source-stress-run-36685171375",
            5: "sti5-v1-failure-diagnostic-run-36685175913",
            6: "sti6-v3-latent-trajectory-run-36684414954",
            8: "sti8-research-oos-run-36653177299",
        }
        evidence = evidence_by_index.get(
            index,
            "owner-directive-007-and-current-sti-evidence",
        )
        items.append(
            _item(
                f"STI-{index}",
                "STI",
                title,
                sti_states[index],
                evidence,
            )
        )

    gw_states = {
        0: SharedWorkState.ARCHITECTURE_DEFINED,
        1: SharedWorkState.REAL_DATA_BOUND,
        2: SharedWorkState.RESEARCH_INCOMPLETE,
        3: SharedWorkState.RESEARCH_INCOMPLETE,
    }
    for index, title in enumerate(_GW_TITLES):
        items.append(
            _item(
                f"GW-{index}",
                "GLOBAL_WORLD",
                title,
                gw_states.get(index, SharedWorkState.NOT_STARTED),
                "owner-directive-006-and-current-global-world-evidence",
            )
        )

    # Explicit cross-cutting mandatory capabilities prevent work from
    # disappearing merely because it is not represented by a numbered WP/MC/STI/GW.
    cross_cutting = (
        ("X-01", "Global Opportunity Surface"),
        ("X-02", "Opportunity Rarity Intelligence"),
        ("X-03", "Opportunity Asymmetry Research"),
        ("X-04", "Opportunity Trajectory Intelligence"),
        ("X-05", "Position Journey Intelligence"),
        ("X-06", "Trajectory Memory"),
        ("X-07", "Cross-Market Transmission Intelligence"),
        ("X-08", "Lead/Lag Intelligence"),
        ("X-09", "Latent Factor Discovery"),
        ("X-10", "Contradiction Map"),
        ("X-11", "Uncertainty Decomposition"),
        ("X-12", "Second-Order Blindspot Engine"),
        ("X-13", "Global Attention Budget / Value of Information"),
        ("X-14", "Global Economic / Market Clock"),
        ("X-15", "Data Health Engine"),
        ("X-16", "Information Freshness / Decay"),
        ("X-17", "Global Observability Matrix"),
        ("X-18", "World-to-Trader Routing"),
        ("X-19", "World-to-CIBO Read-Only Routing"),
        ("X-20", "Maximum Pre-Certification Audit"),
        ("X-21", "Final Shared Freeze"),
        ("X-22", "Seven-Trader Two-Year Certification Protocol"),
    )
    for work_id, title in cross_cutting:
        items.append(
            _item(
                work_id,
                "TRANSVERSAL",
                title,
                SharedWorkState.UNRESOLVED_REQUIRED_AUDIT,
                "owner-maximum-shared-directive-and-canonical-roadmaps",
            )
        )

    ids = tuple(item.work_id for item in items)
    if len(ids) != len(set(ids)):
        raise ValueError("master open-work ledger contains duplicate ids")
    return tuple(items)


def assess_zero_open_work(
    ledger: tuple[SharedOpenWorkItem, ...] | None = None,
) -> SharedZeroOpenWorkAssessment:
    rows = build_shared_master_open_work_ledger() if ledger is None else ledger
    mandatory = tuple(item for item in rows if item.mandatory)
    optional = tuple(item for item in rows if not item.mandatory)
    blockers = tuple(
        sorted(
            item.work_id
            for item in mandatory
            if item.state is not TERMINAL_MANDATORY_STATE
        )
    )
    mandatory_closed = sum(
        item.state is TERMINAL_MANDATORY_STATE for item in mandatory
    )
    optional_closed = sum(
        item.state in TERMINAL_OPTIONAL_STATES for item in optional
    )
    identity = ledger_fingerprint(rows)
    return SharedZeroOpenWorkAssessment(
        ledger_identity=identity,
        total_items=len(rows),
        mandatory_items=len(mandatory),
        mandatory_closed=mandatory_closed,
        optional_items=len(optional),
        optional_closed=optional_closed,
        blocker_ids=blockers,
        zero_open_required_work=not blockers,
        pre_certification_ready=False,
        final_certification_exam_authorized=False,
        protected_holdout_opening_authorized=False,
        productive_authority=False,
    )


def ledger_fingerprint(ledger: tuple[SharedOpenWorkItem, ...]) -> str:
    payload = [
        {
            **asdict(item),
            "state": item.state.value,
        }
        for item in ledger
    ]
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()
