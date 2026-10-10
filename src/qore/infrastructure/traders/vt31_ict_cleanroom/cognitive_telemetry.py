"""Passive input/output/call/decision attribution for ONE VT31 clean-room trader.

Every pulse is generated at the *actual running source function*, not from
reconstructed future market outcomes. Bounded examples; aggregate counters
do not retain all 1M M1 bars. A deterministic condition being evaluated is
not independent LLM reasoning, and influence here means necessary logic-gate
participation, NOT a causal ablation or realized profit.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .contracts import M1Bar, MethodologyDecision, SessionId, utc

COMPONENT_ROLES: dict[str, str] = {
    "M1_MARKET_FEED": "OBSERVED_MARKET_INPUT",
    "M15_CONTEXT": "REQUIRED_HTF_CONTEXT_GATE",
    "H1_CONTEXT": "REQUIRED_HTF_CONTEXT_GATE",
    "H4_CONTEXT": "HTF_OBSERVATION_NOT_ENTRY_GATE",
    "NY_CASH_LIQUIDITY": "CAUSAL_LIQUIDITY_SOURCE",
    "ASIA_LIQUIDITY": "CAUSAL_LIQUIDITY_SOURCE",
    "LONDON_LIQUIDITY": "CAUSAL_LIQUIDITY_SOURCE",
    "SWEPT_LIQUIDITY": "SOURCE_LIQUIDITY_REVOCATION",
    "M1_MSS_DISPLACEMENT": "REQUIRED_STRUCTURAL_GATE",
    "M1_THESIS_REVALIDATION": "PERSISTENCE_OR_INVALIDATION",
    "DOL_ARBITRATION": "REQUIRED_DIRECTIONAL_TARGET_GATE",
    "COGNITIVE_DECISION": "OUTPUT_TO_OPS",
    "OPS_M1_FVG": "REQUIRED_THREE_M1_SOURCE_GATE",
    "OPS_CANDIDATE": "SOURCE_ONLY_RESEARCH_PROPOSAL",
    "BID_ASK_FILL": "NOT_CONNECTED_NO_BROKER_EXECUTION",
    "EXTERNAL_EXECUTION_ACK": "NOT_CONNECTED_NO_BROKER_EXECUTION",
    "CIBO_QDLE_ECONOMICS": "NOT_CONNECTED_NO_RISK_AUTHORIZATION",
}

SOURCE_TO_COMPONENT = {
    "PRIOR_NY_CASH_SESSION": "NY_CASH_LIQUIDITY",
    "ASIA_NY_CLOCK": "ASIA_LIQUIDITY",
    "LONDON_NY_CLOCK": "LONDON_LIQUIDITY",
}


@dataclass(slots=True)
class ComponentCounters:
    calls: int = 0
    inputs_present: int = 0
    outputs_present: int = 0
    blocking_observations: int = 0
    gate_pass_observations: int = 0
    selected_for_decision: int = 0
    reached_source_candidate: int = 0
    input_kinds: Counter[str] = field(default_factory=Counter)
    output_kinds: Counter[str] = field(default_factory=Counter)


class CognitiveTelemetry:
    """Small passive audit that cannot return or modify any trade decision."""

    def __init__(self, *, max_examples: int = 24) -> None:
        self.counts: dict[str, ComponentCounters] = {
            name: ComponentCounters() for name in COMPONENT_ROLES
        }
        self.by_session: Counter[str] = Counter()
        self.candidate_lineage: list[dict[str, Any]] = []
        self.blocker_examples: list[dict[str, str]] = []
        self.max_examples = max_examples
        self.closed_m1_seen = 0
        self.cognition_calls = 0
        self.ops_calls = 0

    def pulse(
        self, name: str, *, input_kind: str, output_kind: str,
        input_present: bool = True, output_present: bool = False,
        blocked: bool = False, gate_pass: bool = False,
        selected: bool = False, candidate: bool = False,
        session: SessionId | None = None,
    ) -> None:
        if name not in COMPONENT_ROLES:
            raise ValueError(f"undeclared cognitive module: {name}")
        c = self.counts[name]
        c.calls += 1
        c.inputs_present += int(input_present)
        c.outputs_present += int(output_present)
        c.blocking_observations += int(blocked)
        c.gate_pass_observations += int(gate_pass)
        c.selected_for_decision += int(selected)
        c.reached_source_candidate += int(candidate)
        c.input_kinds[input_kind] += 1
        c.output_kinds[output_kind] += 1
        if session is not None:
            self.by_session[session.value + "|" + name + "|" + output_kind] += 1

    def on_market(
        self, *, bar: M1Bar, newly_closed_htf: tuple[str, ...],
        confirmed_pools: tuple[str, ...],
        consumed_pools: tuple[str, ...],
    ) -> None:
        self.closed_m1_seen += 1
        self.pulse(
            "M1_MARKET_FEED", input_kind="CLOSED_M1_VALIDATED",
            output_kind="M1_INDEXED", output_present=True,
        )
        for label in newly_closed_htf:
            self.pulse(
                label + "_CONTEXT",
                input_kind="CLOSED_M1_HTF_BUCKET", output_kind="NEW_CLOSED_" + label,
                output_present=True,
            )
        for family in confirmed_pools:
            source = family.removesuffix("_HIGH").removesuffix("_LOW")
            component = SOURCE_TO_COMPONENT.get(source)
            if component:
                self.pulse(
                    component, input_kind="FULL_SOURCE_RANGE",
                    output_kind="CONFIRMED_HIGH_LOW",
                    output_present=True,
                )
        for family in consumed_pools:
            component = SOURCE_TO_COMPONENT.get(family)
            self.pulse(
                "SWEPT_LIQUIDITY", input_kind=family,
                output_kind="DOL_CONSUMED_CLOSED_M1",
                output_present=True, selected=True,
            )
            if component:
                self.pulse(
                    component, input_kind="CLOSED_M1_WICK",
                    output_kind="SOURCE_LEVEL_CONSUMED",
                    output_present=True, selected=True,
                )
        # Full OHLC is NOT retained in telemetry; proof is M1 lineage with
        # real source at the level passed to cognition and OPS.

    def on_assessment(
        self, *, at: datetime, session: SessionId,
        htf: dict[str, str], pools: tuple[object, ...],
        shift: object | None, active_was_present: bool,
        active_survived: bool, missing: tuple[str, ...],
        decision: object | None, decision_is_new_shift: bool,
    ) -> None:
        self.cognition_calls += 1
        names = set(missing)
        for name in ("M15", "H1", "H4"):
            state = htf[name]
            available = state not in ("STALE", "NOT_EVALUABLE")
            required = name in ("M15", "H1")
            self.pulse(
                name + "_CONTEXT", session=session,
                input_kind="CLOSED_" + name + "_PAIR",
                output_kind=state,
                input_present=available, output_present=available,
                blocked=required and not available,
                gate_pass=required and available,
                selected=required and decision is not None,
            )
        for prefix, component in SOURCE_TO_COMPONENT.items():
            count = sum(
                1 for p in pools
                if str(p.family).startswith(prefix)
            )
            chosen = (
                decision is not None
                and str(decision.draw_family).startswith(prefix)
            )
            self.pulse(
                component, session=session,
                input_kind="NATIVE_CLOSED_M1_RANGE",
                output_kind="AVAILABLE_UNSWEPT" if count else "UNAVAILABLE_OR_SWEPT",
                input_present=count > 0,
                output_present=count > 0,
                selected=chosen,
            )
        has_shift = shift is not None
        structural_ready = has_shift or active_survived
        self.pulse(
            "M1_MSS_DISPLACEMENT", session=session,
            input_kind="CLOSED_M1_PIVOT_DISPLACEMENT",
            output_kind="NEW_MSS" if has_shift else "NO_NEW_MSS",
            output_present=has_shift,
            blocked=not structural_ready,
            gate_pass=structural_ready,
            selected=decision is not None,
        )
        self.pulse(
            "M1_THESIS_REVALIDATION", session=session,
            input_kind="PREVIOUS_M1_THESIS" if active_was_present else "NO_PREVIOUS_THESIS",
            output_kind=(
                "REVOKED" if active_was_present and not active_survived
                else "PERSISTED" if active_survived else "NO_THESIS"
            ),
            input_present=active_was_present,
            output_present=active_survived,
            blocked=active_was_present and not active_survived,
            gate_pass=active_survived,
            selected=decision is not None and not decision_is_new_shift,
        )
        self.pulse(
            "DOL_ARBITRATION", session=session,
            input_kind="M1_SIDE_AND_AVAILABLE_UNSWEPT_POOLS",
            output_kind=(
                str(decision.draw_family)
                if decision is not None else
                "NO_TARGET" if "NO_CAUSAL_NEXT_DRAW_MIN10" in names
                else "BLOCKED_UPSTREAM"
            ),
            input_present=bool(pools), output_present=decision is not None,
            blocked=("LIQUIDITY_POOL" in names or
                     "NO_CAUSAL_NEXT_DRAW_MIN10" in names),
            gate_pass=decision is not None, selected=decision is not None,
        )
        self.pulse(
            "COGNITIVE_DECISION", session=session,
            input_kind="M1_MSS_HTF_DOL_SOURCE_FACTS",
            output_kind="ISSUED_NEW" if decision_is_new_shift and decision is not None
            else "ISSUED_REVALIDATED" if decision is not None
            else "ABSTAIN_CAUSAL",
            output_present=decision is not None,
            blocked=decision is None,
            selected=decision is not None,
        )
        if missing and len(self.blocker_examples) < self.max_examples:
            case = {"as_of": utc(at).isoformat(), "session": session.value,
                    "missing": "|".join(missing)}
            if case not in self.blocker_examples:
                self.blocker_examples.append(case)

    def on_ops(
        self, *, at: datetime, session: SessionId,
        phase: MethodologyDecision, raw_fvg_new: bool,
        candidate_new: bool, cognition: object | None,
        candidate: object | None, missing: tuple[str, ...],
    ) -> None:
        self.ops_calls += 1
        self.pulse(
            "OPS_M1_FVG", session=session,
            input_kind="THREE_CLOSED_M1",
            output_kind="RAW_DIRECTIONAL_FVG" if raw_fvg_new else "NO_RAW_FVG",
            output_present=raw_fvg_new,
            gate_pass=raw_fvg_new,
            selected=candidate_new,
            candidate=candidate_new,
        )
        self.pulse(
            "OPS_CANDIDATE", session=session,
            input_kind="COG_M1_DECISION_AND_M1_FVG",
            output_kind=phase.value,
            input_present=cognition is not None,
            output_present=candidate_new,
            blocked=not candidate_new,
            gate_pass=candidate_new,
            selected=candidate_new,
            candidate=candidate_new,
        )
        if candidate_new:
            if cognition is None or candidate is None:
                raise AssertionError("OPS candidate without cognitive lineage")
            for name in (
                "M15_CONTEXT", "H1_CONTEXT", "M1_MSS_DISPLACEMENT",
                "DOL_ARBITRATION", "COGNITIVE_DECISION",
            ):
                self.counts[name].reached_source_candidate += 1
            for name, prefix in (
                ("NY_CASH_LIQUIDITY", "PRIOR_NY_CASH_SESSION"),
                ("ASIA_LIQUIDITY", "ASIA_NY_CLOCK"),
                ("LONDON_LIQUIDITY", "LONDON_NY_CLOCK"),
            ):
                if str(cognition.draw_family).startswith(prefix):
                    self.counts[name].reached_source_candidate += 1
            if len(self.candidate_lineage) < self.max_examples:
                self.candidate_lineage.append({
                    "trader_id": "VT31",
                    "session": session.value,
                    "cognitive_as_of": utc(cognition.observed_at).isoformat(),
                    "formed_at": utc(candidate.formed_at).isoformat(),
                    "M1_MSS_confirmed_at": utc(
                        cognition.structure_break_confirmed_at
                    ).isoformat(),
                    "draw_family": str(cognition.draw_family),
                    "draw_level_observed_at": utc(
                        cognition.draw_level_observed_at
                    ).isoformat(),
                    "draw_target": str(cognition.draw_target),
                    "side": str(cognition.side),
                    "cognitive_source": str(cognition.source_provenance),
                    "causal_source_candidates_only": True,
                    "broker_filled": False,
                    "risk_authorized": False,
                })
        if (
            candidate is not None and cognition is None
            and phase is MethodologyDecision.RESEARCH_PENDING_CE
        ):
            # Cross-architect P0: selected source may remain pending after
            # its DOL/MSS was revoked. Observe ONLY, do not change OPS.
            self.by_session[session.value + "|P0_PENDING_WITHOUT_COG"] += 1
            if len(self.blocker_examples) < self.max_examples:
                self.blocker_examples.append({
                    "as_of": utc(at).isoformat(),
                    "session": session.value,
                    "missing": "P0_SOURCE_PENDING_WITHOUT_VALID_COG",
                })
        elif raw_fvg_new and cognition is None:
            self.by_session[session.value + "|OPS_RAW_FVG_BLOCKED_BY_COG"] += 1
            for reason in missing:
                self.by_session[session.value + "|RAW_FVG_COG_MISSING|" + reason] += 1

    def report(self) -> dict[str, Any]:
        components = {}
        for name, role in COMPONENT_ROLES.items():
            c = self.counts[name]
            components[name] = {
                "role": role,
                "calls_observed": c.calls,
                "input_present": c.inputs_present,
                "output_present": c.outputs_present,
                "blocked_observations": c.blocking_observations,
                "gate_pass_observations": c.gate_pass_observations,
                "selected_for_decision": c.selected_for_decision,
                "reached_first_suitable_FVG": c.reached_source_candidate,
                "input_kinds": dict(sorted(c.input_kinds.items())),
                "output_kinds": dict(sorted(c.output_kinds.items())),
                "runtime_status": "OBSERVED" if c.calls else "NOT_CONNECTED",
            }
        return {
            "schema": "qore.vt31.cleanroom.cognitive_io_call_impact.v1",
            "trader_id": "VT31",
            "source_timeframe": "M1",
            "session_models": ["LONDON", "NEW_YORK"],
            "closed_m1_seen": self.closed_m1_seen,
            "cognition_calls": self.cognition_calls,
            "ops_calls": self.ops_calls,
            "components": components,
            "by_session_and_sensor": dict(sorted(self.by_session.items())),
            "candidate_causal_lineage_examples": self.candidate_lineage,
            "abstention_examples": self.blocker_examples,
            "influence_definition": (
                "Actual necessary-logic-gate participation and source lineage;"
                " NOT independent counterfactual ablation or achieved PnL"
            ),
            "reasoning_proof": (
                "Deterministic closed-M1 feature evaluation with verifiable"
                " decisions; NOT evidence of independent LLM deliberation"
            ),
            "fills_proven": 0,
            "entry_executions_proven": 0,
            "cibo_qdle_connected": False,
            "live_authorized": False,
            "certified": False,
        }
