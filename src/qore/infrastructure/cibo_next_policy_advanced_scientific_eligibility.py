"""Pre-outcome scientific eligibility freeze for the next CIBO policy generation.

The CE2I registry remains complete T01..T20. This freeze only determines which
advanced tools may enter the runtime decision surface of the *next* Phase22
generation before any candidate source or outcome is inspected.

Terminally falsified/ineligible advanced tools remain disabled. Advanced tools
whose economic proof is still externally blocked are SHADOW_ONLY: their frozen
control/treatment protocols may collect evidence, but they cannot affect capital
allocation until a later policy generation is frozen from terminal evidence.

The consumed V2 economic outcomes are not inputs to this freeze.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboRegimeToolSelection,
)

ADVANCED_CODES = ("T02", "T03", "T04", "T08", "T10", "T16", "T17")


class AdvancedScientificState(StrEnum):
    RUNTIME_ELIGIBLE = "RUNTIME_ELIGIBLE"
    SHADOW_ONLY = "SHADOW_ONLY"
    TERMINAL_CLOSED_DISABLED = "TERMINAL_CLOSED_DISABLED"


@dataclass(frozen=True, slots=True)
class AdvancedToolScientificEligibility:
    tool_code: str
    state: AdvancedScientificState
    scientific_disposition: str
    source_refs: tuple[str, ...]
    shadow_protocol_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.tool_code not in ADVANCED_CODES:
            raise CiboCapitalManagementError(
                "advanced scientific eligibility tool identity drift"
            )
        if type(self.state) is not AdvancedScientificState:
            raise CiboCapitalManagementError(
                "advanced scientific eligibility state invalid"
            )
        if not self.scientific_disposition:
            raise CiboCapitalManagementError(
                "advanced scientific disposition required"
            )
        if (
            not self.source_refs
            or len(self.source_refs) != len(set(self.source_refs))
            or any(not item for item in self.source_refs)
        ):
            raise CiboCapitalManagementError(
                "advanced scientific source refs invalid"
            )
        if len(self.shadow_protocol_refs) != len(set(self.shadow_protocol_refs)):
            raise CiboCapitalManagementError(
                "advanced shadow protocol refs duplicated"
            )
        if self.state is AdvancedScientificState.SHADOW_ONLY:
            if self.scientific_disposition != "EXTERNAL_DEPENDENCY_BLOCKED":
                raise CiboCapitalManagementError(
                    "advanced shadow-only tool must remain externally blocked"
                )
            if not self.shadow_protocol_refs:
                raise CiboCapitalManagementError(
                    "advanced shadow-only tool requires frozen shadow protocol"
                )
        elif self.state is AdvancedScientificState.TERMINAL_CLOSED_DISABLED:
            if self.scientific_disposition != "FALSIFIED_AND_CLOSED":
                raise CiboCapitalManagementError(
                    "terminal-disabled tool must be falsified/closed"
                )
            if self.shadow_protocol_refs:
                raise CiboCapitalManagementError(
                    "terminal-disabled tool cannot silently reopen research"
                )
        elif self.scientific_disposition != "COMPLETED_AND_PROVEN":
            raise CiboCapitalManagementError(
                "runtime-eligible advanced tool requires completed proof"
            )


@dataclass(frozen=True, slots=True)
class AdvancedScientificEligibilityFreeze:
    freeze_id: str
    tools: tuple[AdvancedToolScientificEligibility, ...]
    frozen_before_next_holdout_source_access: bool
    v2_economic_outcomes_used_for_selection: bool = False
    v2_qualification_failure_used_as_runtime_tuning: bool = False
    synthetic_evidence_used: bool = False
    broker_mutation_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    production_authorized: bool = False

    def __post_init__(self) -> None:
        if self.freeze_id != "CIBO_NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY_V1":
            raise CiboCapitalManagementError(
                "advanced scientific freeze identity drift"
            )
        if tuple(item.tool_code for item in self.tools) != ADVANCED_CODES:
            raise CiboCapitalManagementError(
                "advanced scientific freeze requires exact ordered 7-tool surface"
            )
        if not self.frozen_before_next_holdout_source_access:
            raise CiboCapitalManagementError(
                "advanced scientific freeze must predate next holdout source access"
            )
        if any(
            (
                self.v2_economic_outcomes_used_for_selection,
                self.v2_qualification_failure_used_as_runtime_tuning,
                self.synthetic_evidence_used,
                self.broker_mutation_authorized,
                self.live_authorized,
                self.real_capital_authorized,
                self.production_authorized,
            )
        ):
            raise CiboCapitalManagementError(
                "advanced scientific freeze governance contamination"
            )

    @property
    def runtime_eligible_codes(self) -> tuple[str, ...]:
        return tuple(
            item.tool_code
            for item in self.tools
            if item.state is AdvancedScientificState.RUNTIME_ELIGIBLE
        )

    @property
    def shadow_only_codes(self) -> tuple[str, ...]:
        return tuple(
            item.tool_code
            for item in self.tools
            if item.state is AdvancedScientificState.SHADOW_ONLY
        )

    @property
    def terminal_disabled_codes(self) -> tuple[str, ...]:
        return tuple(
            item.tool_code
            for item in self.tools
            if item.state is AdvancedScientificState.TERMINAL_CLOSED_DISABLED
        )

    def payload(self) -> dict[str, object]:
        return {
            "schema": "qore.cibo.next-policy.advanced-scientific-eligibility.v1",
            "freeze_id": self.freeze_id,
            "tools": [
                {
                    "tool_code": item.tool_code,
                    "state": item.state.value,
                    "scientific_disposition": item.scientific_disposition,
                    "source_refs": list(item.source_refs),
                    "shadow_protocol_refs": list(item.shadow_protocol_refs),
                }
                for item in self.tools
            ],
            "runtime_eligible_codes": list(self.runtime_eligible_codes),
            "shadow_only_codes": list(self.shadow_only_codes),
            "terminal_disabled_codes": list(self.terminal_disabled_codes),
            "frozen_before_next_holdout_source_access": True,
            "v2_economic_outcomes_used_for_selection": False,
            "v2_qualification_failure_used_as_runtime_tuning": False,
            "synthetic_evidence_used": False,
            "broker_mutation_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        }

    def fingerprint(self) -> str:
        raw = json.dumps(
            self.payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()

    def filter_regime_selection(
        self,
        selection: CiboRegimeToolSelection,
    ) -> CiboRegimeToolSelection:
        if not isinstance(selection, CiboRegimeToolSelection):
            raise CiboCapitalManagementError(
                "advanced scientific filter requires canonical regime selection"
            )
        runtime = set(self.runtime_eligible_codes)
        advanced = set(ADVANCED_CODES)
        enabled = tuple(
            code
            for code in selection.enabled_tools
            if code not in advanced or code in runtime
        )
        blocked_set = set(selection.blocked_tools)
        blocked_set.update(
            code
            for code in selection.enabled_tools
            if code in advanced and code not in runtime
        )
        mission_order = (*selection.enabled_tools, *selection.blocked_tools)
        blocked = tuple(
            code
            for code in dict.fromkeys(mission_order)
            if code in blocked_set
        )
        return CiboRegimeToolSelection(
            posture=selection.posture,
            enabled_tools=enabled,
            blocked_tools=blocked,
            reason=(
                selection.reason
                + "; next-policy scientific eligibility="
                + self.fingerprint()
            ),
        )


NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY = (
    AdvancedScientificEligibilityFreeze(
        freeze_id="CIBO_NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY_V1",
        tools=(
            AdvancedToolScientificEligibility(
                tool_code="T02",
                state=AdvancedScientificState.SHADOW_ONLY,
                scientific_disposition="EXTERNAL_DEPENDENCY_BLOCKED",
                source_refs=(
                    "docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json#T02",
                ),
                shadow_protocol_refs=(
                    "src/qore/infrastructure/cibo_ce2i_phase20_t02_structural_oos.py",
                    "src/qore/infrastructure/cibo_arch2_t02_economic_ablation.py",
                ),
            ),
            AdvancedToolScientificEligibility(
                tool_code="T03",
                state=AdvancedScientificState.TERMINAL_CLOSED_DISABLED,
                scientific_disposition="FALSIFIED_AND_CLOSED",
                source_refs=(
                    "docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json#T03",
                    "src/qore/infrastructure/cibo_arch2_t03_current_contract_falsification.py",
                    "github-artifact://11197727438/sha256:bbb52ebf064d3e90459a4fadc79b020dd04a158e2fbb6ec815c420e28b19d78f",
                ),
            ),
            AdvancedToolScientificEligibility(
                tool_code="T04",
                state=AdvancedScientificState.SHADOW_ONLY,
                scientific_disposition="EXTERNAL_DEPENDENCY_BLOCKED",
                source_refs=(
                    "docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json#T04",
                ),
                shadow_protocol_refs=(
                    "src/qore/infrastructure/cibo_ce2i_t04_t10_economic_gate.py",
                ),
            ),
            AdvancedToolScientificEligibility(
                tool_code="T08",
                state=AdvancedScientificState.SHADOW_ONLY,
                scientific_disposition="EXTERNAL_DEPENDENCY_BLOCKED",
                source_refs=(
                    "docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json#T08",
                ),
                shadow_protocol_refs=(
                    "src/qore/infrastructure/cibo_ce2i_phase20_t08_oos_ablation.py",
                ),
            ),
            AdvancedToolScientificEligibility(
                tool_code="T10",
                state=AdvancedScientificState.SHADOW_ONLY,
                scientific_disposition="EXTERNAL_DEPENDENCY_BLOCKED",
                source_refs=(
                    "docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json#T10",
                ),
                shadow_protocol_refs=(
                    "src/qore/infrastructure/cibo_ce2i_t04_t10_economic_gate.py",
                ),
            ),
            AdvancedToolScientificEligibility(
                tool_code="T16",
                state=AdvancedScientificState.TERMINAL_CLOSED_DISABLED,
                scientific_disposition="FALSIFIED_AND_CLOSED",
                source_refs=(
                    "docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json#T16",
                    "src/qore/infrastructure/cibo_arch2_t16_terminal_falsification.py",
                    "github-artifact://11199498760/sha256:2aa2024db38efa100c4cf97eb8fc59038ea8b78a0428719ee106ea4bee3a0a16",
                ),
            ),
            AdvancedToolScientificEligibility(
                tool_code="T17",
                state=AdvancedScientificState.TERMINAL_CLOSED_DISABLED,
                scientific_disposition="FALSIFIED_AND_CLOSED",
                source_refs=(
                    "docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json#T17",
                    "src/qore/infrastructure/cibo_t17_governed_provider_disposition.py",
                    "docs/research/CIBO-B-CTRADER-DEMO-PROVIDER-EVIDENCE-2026-10-01.json",
                    "docs/research/CIBO-B-T17-STRUCTURAL-DISPOSITION-V1.json",
                ),
            ),
        ),
        frozen_before_next_holdout_source_access=True,
    )
)
