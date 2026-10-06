"""Read-only function/economic sensors for sovereign CIBO decisions.

Sensors observe the already-produced sovereign decision. They never participate
in sizing, allocation, Risk, execution, LIVE or broker mutation. A sensor may
show that an output was consumed or triggered a gate in the observed path, but
monetary causal contribution remains UNPROVEN until the matching frozen
ablation is executed.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal, localcontext
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CapitalSource,
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_executive_brain import (
    CiboExecutiveDirectiveKind,
)
from qore.infrastructure.cibo_sovereign_capital_runtime import (
    CiboSovereignCapitalDecision,
)

ABLATION_KEYS = frozenset(
    {
        "sizing",
        "adaptive_leverage",
        "cibo_compound",
        "compound_portfolio",
        "cognition",
    }
)


class CiboSensorCausalState(StrEnum):
    UNPROVEN = "UNPROVEN"
    ABLATION_PROVEN = "ABLATION_PROVEN"


@dataclass(frozen=True, slots=True)
class CiboFunctionEconomicSensor:
    decision_id: str
    function_code: str
    stage_order: int
    input_sha256: str
    output_sha256: str
    input_metrics: tuple[tuple[str, str], ...]
    output_metrics: tuple[tuple[str, str], ...]
    called: bool = True
    downstream_consumed: bool = True
    decision_gate_triggered: bool = False
    final_capital_binding: bool = False
    risk_delta_usd: Decimal = Decimal(0)
    margin_delta_usd: Decimal = Decimal(0)
    ablation_key: str | None = None
    causal_state: CiboSensorCausalState = CiboSensorCausalState.UNPROVEN
    causal_ending_capital_delta_usd: Decimal | None = None
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.decision_id or not self.function_code:
            raise CiboCapitalManagementError(
                "function sensor decision/function identity is required"
            )
        if (
            not isinstance(self.stage_order, int)
            or isinstance(self.stage_order, bool)
            or self.stage_order < 0
        ):
            raise CiboCapitalManagementError(
                "function sensor stage_order must be non-negative int"
            )
        for name in ("input_sha256", "output_sha256"):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or not value.startswith("sha256:")
                or len(value) != 71
            ):
                raise CiboCapitalManagementError(
                    f"function sensor {name} must be sha256 digest"
                )
        for name in (
            "called",
            "downstream_consumed",
            "decision_gate_triggered",
            "final_capital_binding",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"function sensor {name} must be bool"
                )
        if not self.called:
            raise CiboCapitalManagementError(
                "persisted function sensor must represent an actual call"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "function sensors are observational and cannot acquire authority"
            )
        for name in ("risk_delta_usd", "margin_delta_usd"):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"function sensor {name} must be finite Decimal"
                )
        if self.ablation_key is not None and self.ablation_key not in ABLATION_KEYS:
            raise CiboCapitalManagementError(
                "function sensor ablation key is not canonical"
            )
        for name in ("input_metrics", "output_metrics"):
            values = getattr(self, name)
            keys = tuple(item[0] for item in values)
            if (
                any(
                    not isinstance(item, tuple)
                    or len(item) != 2
                    or not all(isinstance(part, str) for part in item)
                    for item in values
                )
                or len(keys) != len(set(keys))
            ):
                raise CiboCapitalManagementError(
                    f"function sensor {name} must be unique string pairs"
                )
        if self.causal_state is CiboSensorCausalState.UNPROVEN:
            if self.causal_ending_capital_delta_usd is not None:
                raise CiboCapitalManagementError(
                    "unproven function sensor cannot claim causal economics"
                )
        else:
            if self.ablation_key is None:
                raise CiboCapitalManagementError(
                    "ablation-proven function sensor requires ablation key"
                )
            if (
                not isinstance(self.causal_ending_capital_delta_usd, Decimal)
                or not self.causal_ending_capital_delta_usd.is_finite()
            ):
                raise CiboCapitalManagementError(
                    "ablation-proven function sensor requires finite causal delta"
                )

    def payload(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "function_code": self.function_code,
            "stage_order": self.stage_order,
            "input_sha256": self.input_sha256,
            "output_sha256": self.output_sha256,
            "input_metrics": dict(self.input_metrics),
            "output_metrics": dict(self.output_metrics),
            "called": self.called,
            "downstream_consumed": self.downstream_consumed,
            "decision_gate_triggered": self.decision_gate_triggered,
            "final_capital_binding": self.final_capital_binding,
            "risk_delta_usd": format(self.risk_delta_usd, "f"),
            "margin_delta_usd": format(self.margin_delta_usd, "f"),
            "ablation_key": self.ablation_key,
            "causal_state": self.causal_state.value,
            "causal_ending_capital_delta_usd": (
                None
                if self.causal_ending_capital_delta_usd is None
                else format(self.causal_ending_capital_delta_usd, "f")
            ),
            "productive_authority": False,
        }


def _capital_science_input_metrics(receipt) -> tuple[tuple[str, str], ...]:
    payload = receipt.input_payload or {}
    typed = payload.get("typed_engine_input")
    typed = typed if isinstance(typed, dict) else {}
    values: dict[str, object] = {
        "native_engine": receipt.native_engine_name or "",
        "signal_fingerprint": receipt.signal_fingerprint,
        "trader_id": receipt.trader_id,
    }
    for key in (
        "realized_capital_usd",
        "peak_realized_capital_usd",
        "realized_profit_pool_usd",
        "protected_capacity_usd",
        "deployed_profit_usd",
        "requested_stop_risk_usd",
        "requested_margin_usd",
        "provider_cost_usd",
        "expected_net_value_usd",
        "expected_capital_minutes",
        "hard_risk_headroom_usd",
        "margin_headroom_usd",
        "capital_source",
        "competing_candidates",
    ):
        if key in payload:
            values[key] = payload[key]
    for key in (
        "proposal_id",
        "proposal_action",
        "proposal_amount_usd",
        "proposal_source_bucket",
        "source_lot_id",
        "source_lot_state",
    ):
        if key in typed:
            values["typed_" + key] = typed[key]
    return _pairs(**values)


def _capital_science_output_metrics(receipt) -> tuple[tuple[str, str], ...]:
    payload = receipt.output_payload or {}
    engine = payload.get("engine_output")
    engine = engine if isinstance(engine, dict) else {}
    values: dict[str, object] = {
        "disposition": receipt.disposition.value,
        "downstream_consumer": receipt.downstream_consumer,
        "consumer_action": receipt.consumer_action,
        "decision_changed": receipt.decision_changed,
        "risk_delta_usd": receipt.risk_delta_usd,
        "margin_delta_usd": receipt.margin_delta_usd,
        "native_engine_called": receipt.native_engine_called,
        "native_engine": receipt.native_engine_name or "",
    }
    for key in (
        "treatment_posture",
        "treatment_action",
        "treatment_amount_usd",
        "treatment_requested_risk_review_usd",
        "giveback_amount_usd",
        "profit_retention_ratio",
        "policy_protected_floor_usd",
        "candidate_compound_capacity_usd",
        "source_lot_state",
    ):
        if key in engine:
            values[key] = engine[key]
    blockers = engine.get("blocker_codes")
    if isinstance(blockers, (tuple, list)):
        values["blocker_codes"] = ",".join(str(item) for item in blockers)
        values["blocker_count"] = len(blockers)
    return _pairs(**values)


def _uses_realized_profit(plan) -> bool:
    if plan.capital_source is CapitalSource.REALIZED_PROFIT:
        return plan.stop_risk_usd > 0
    return any(
        item.source is CapitalSource.REALIZED_PROFIT and item.amount_usd > 0
        for item in plan.capital_source_lots
    )


def _pairs(**values: object) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(key), str(value)) for key, value in values.items()))


def _sha(payload: tuple[tuple[str, str], ...]) -> str:
    raw = json.dumps(
        dict(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _sensor(
    *,
    decision_id: str,
    function_code: str,
    stage_order: int,
    input_metrics: tuple[tuple[str, str], ...],
    output_metrics: tuple[tuple[str, str], ...],
    downstream_consumed: bool = True,
    decision_gate_triggered: bool = False,
    final_capital_binding: bool = False,
    risk_delta_usd: Decimal = Decimal(0),
    margin_delta_usd: Decimal = Decimal(0),
    ablation_key: str | None = None,
) -> CiboFunctionEconomicSensor:
    return CiboFunctionEconomicSensor(
        decision_id=decision_id,
        function_code=function_code,
        stage_order=stage_order,
        input_sha256=_sha(input_metrics),
        output_sha256=_sha(output_metrics),
        input_metrics=input_metrics,
        output_metrics=output_metrics,
        called=True,
        downstream_consumed=downstream_consumed,
        decision_gate_triggered=decision_gate_triggered,
        final_capital_binding=final_capital_binding,
        risk_delta_usd=risk_delta_usd,
        margin_delta_usd=margin_delta_usd,
        ablation_key=ablation_key,
        causal_state=CiboSensorCausalState.UNPROVEN,
        causal_ending_capital_delta_usd=None,
        productive_authority=False,
    )


def build_sovereign_function_sensors(
    decision: CiboSovereignCapitalDecision,
) -> tuple[CiboFunctionEconomicSensor, ...]:
    """Observe the completed sovereign decision without changing it."""

    if not isinstance(decision, CiboSovereignCapitalDecision):
        raise CiboCapitalManagementError(
            "function sensor builder requires sovereign capital decision"
        )

    economic = decision.economic_run
    target_lines = tuple(
        item for item in economic.portfolio_plan.lines
        if item.option_id == decision.option_id
    )
    if len(target_lines) != 1:
        raise CiboCapitalManagementError(
            "function sensor target missing from portfolio plan"
        )
    portfolio = target_lines[0]
    competition = next(
        (
            item
            for item in economic.competition_plans
            if item.opportunity_id == decision.option_id
        ),
        None,
    )
    if competition is None:
        raise CiboCapitalManagementError(
            "function sensor target missing from competition plan"
        )

    first_robust = economic.genc11_plan.robust_step_envelopes[0]
    risk_request = decision.risk_request
    final_plan = decision.final_plan
    sizing_plan = decision.sizing.plan
    final_positive = (
        final_plan.action
        in {
            CapitalAction.OPEN_MINIMAL_SEED,
            CapitalAction.OPEN_CAPABILITY_MAX,
            CapitalAction.EXPAND,
        }
        and final_plan.volume > 0
    )
    portfolio_binding = (
        (portfolio.multiplier == 0 and final_plan.action is CapitalAction.HOLD)
        or (
            final_positive
            and (
                final_plan.stop_risk_usd == portfolio.stop_risk_usd
                or final_plan.margin_usd == portfolio.margin_usd
            )
        )
    )
    competition_binding = (
        not competition.admit_opportunity
        and final_plan.action is CapitalAction.HOLD
    )
    sizing_binding = (
        sizing_plan.action is CapitalAction.HOLD
        or (
            final_positive
            and final_plan.volume == sizing_plan.volume
        )
    )
    robust_binding = (
        final_positive
        and (
            final_plan.stop_risk_usd
            == first_robust.common_stop_risk_headroom_usd
            or final_plan.margin_usd
            == first_robust.common_margin_headroom_usd
        )
    )
    compound_source_requested = _uses_realized_profit(sizing_plan)
    compound_block_binding = (
        compound_source_requested
        and not decision.capital_science.allow_incremental_compound
        and final_plan.action is CapitalAction.HOLD
    )

    sensors: list[CiboFunctionEconomicSensor] = [
        _sensor(
            decision_id=decision.decision_id,
            function_code="COGNITION",
            stage_order=10,
            input_metrics=_pairs(
                directive=decision.synthesis.directive.value,
                reasoning_mode=decision.synthesis.reasoning_mode.value,
                uncertainty=decision.synthesis.uncertainty.kind.value,
            ),
            output_metrics=_pairs(
                recommend=(
                    decision.synthesis.directive
                    is CiboExecutiveDirectiveKind.RECOMMEND
                ),
                capital_disposition=decision.disposition.value,
            ),
            decision_gate_triggered=(
                decision.synthesis.directive
                is not CiboExecutiveDirectiveKind.RECOMMEND
            ),
            final_capital_binding=(
                decision.synthesis.directive
                is not CiboExecutiveDirectiveKind.RECOMMEND
                and final_plan.action is CapitalAction.HOLD
            ),
            ablation_key="cognition",
        ),
        _sensor(
            decision_id=decision.decision_id,
            function_code="GEN-C11_MPC",
            stage_order=20,
            input_metrics=_pairs(
                twin_id=economic.twin_id,
                robust_step_count=len(
                    economic.genc11_plan.robust_step_envelopes
                ),
            ),
            output_metrics=_pairs(
                common_stop_risk_headroom_usd=(
                    first_robust.common_stop_risk_headroom_usd
                ),
                common_margin_headroom_usd=(
                    first_robust.common_margin_headroom_usd
                ),
            ),
            final_capital_binding=robust_binding,
            ablation_key="compound_portfolio",
        ),
        _sensor(
            decision_id=decision.decision_id,
            function_code="COMPOUND_PORTFOLIO",
            stage_order=30,
            input_metrics=_pairs(
                option_id=decision.option_id,
                total_expected_net_utility_usd=(
                    economic.portfolio_plan.total_expected_net_utility_usd
                ),
            ),
            output_metrics=_pairs(
                multiplier=portfolio.multiplier,
                expected_net_utility_usd=portfolio.expected_net_utility_usd,
                stop_risk_usd=portfolio.stop_risk_usd,
                margin_usd=portfolio.margin_usd,
            ),
            decision_gate_triggered=(portfolio.multiplier == 0),
            final_capital_binding=portfolio_binding,
            ablation_key="compound_portfolio",
        ),
        _sensor(
            decision_id=decision.decision_id,
            function_code="ADAPTIVE_LEVERAGE",
            stage_order=40,
            input_metrics=_pairs(
                maximum_multiplier=4,
                option_id=decision.option_id,
            ),
            output_metrics=_pairs(
                selected_multiplier=portfolio.multiplier,
                stop_risk_cap_usd=portfolio.stop_risk_usd,
                margin_cap_usd=portfolio.margin_usd,
            ),
            decision_gate_triggered=(portfolio.multiplier == 0),
            final_capital_binding=portfolio_binding,
            ablation_key="adaptive_leverage",
        ),
        _sensor(
            decision_id=decision.decision_id,
            function_code="POSITION_COMPETITION",
            stage_order=50,
            input_metrics=_pairs(
                option_id=competition.opportunity_id,
                fits_without_release=competition.fits_without_release,
            ),
            output_metrics=_pairs(
                admit_opportunity=competition.admit_opportunity,
                released_stop_risk_usd=competition.released_stop_risk_usd,
                released_margin_usd=competition.released_margin_usd,
                net_incremental_utility_usd=(
                    competition.net_incremental_utility_usd
                ),
            ),
            decision_gate_triggered=(not competition.admit_opportunity),
            final_capital_binding=competition_binding,
            ablation_key="compound_portfolio",
        ),
        _sensor(
            decision_id=decision.decision_id,
            function_code="SIZING",
            stage_order=60,
            input_metrics=_pairs(
                mission=decision.sizing.mission.value,
                mode=decision.sizing.mode.value,
                base_protected=decision.sizing.base_protected,
                survival_capital_usd=decision.sizing.survival_capital_usd,
                protected_capital_usd=decision.sizing.protected_capital_usd,
            ),
            output_metrics=_pairs(
                action=sizing_plan.action.value,
                volume=sizing_plan.volume,
                stop_risk_usd=sizing_plan.stop_risk_usd,
                margin_usd=sizing_plan.margin_usd,
                capital_source=(
                    ""
                    if sizing_plan.capital_source is None
                    else sizing_plan.capital_source.value
                ),
            ),
            decision_gate_triggered=(
                sizing_plan.action is CapitalAction.HOLD
            ),
            final_capital_binding=sizing_binding,
            ablation_key="sizing",
        ),
        _sensor(
            decision_id=decision.decision_id,
            function_code="CIBO_COMPOUND",
            stage_order=70,
            input_metrics=_pairs(
                sizing_action=sizing_plan.action.value,
                deployable_profit_usd=(
                    decision.capital_science.deployable_profit_usd
                ),
            ),
            output_metrics=_pairs(
                allow_incremental_compound=(
                    decision.capital_science.allow_incremental_compound
                ),
                capital_source_lot_count=len(
                    sizing_plan.capital_source_lots
                ),
            ),
            decision_gate_triggered=(
                compound_source_requested
                and not decision.capital_science.allow_incremental_compound
            ),
            final_capital_binding=compound_block_binding,
            ablation_key="cibo_compound",
        ),
        _sensor(
            decision_id=decision.decision_id,
            function_code="CMA_FINAL_PLAN",
            stage_order=80,
            input_metrics=_pairs(
                sizing_volume=sizing_plan.volume,
                portfolio_stop_risk_cap_usd=portfolio.stop_risk_usd,
                robust_stop_risk_cap_usd=(
                    first_robust.common_stop_risk_headroom_usd
                ),
            ),
            output_metrics=_pairs(
                action=final_plan.action.value,
                volume=final_plan.volume,
                stop_risk_usd=final_plan.stop_risk_usd,
                margin_usd=final_plan.margin_usd,
            ),
            decision_gate_triggered=(final_plan.action is CapitalAction.HOLD),
            final_capital_binding=True,
        ),
        _sensor(
            decision_id=decision.decision_id,
            function_code="QORE_RISK_HANDOFF",
            stage_order=90,
            input_metrics=_pairs(
                capital_disposition=decision.disposition.value,
                final_action=final_plan.action.value,
            ),
            output_metrics=_pairs(
                request_created=(risk_request is not None),
                requested_volume=(
                    Decimal(0)
                    if risk_request is None
                    else risk_request.requested_volume
                ),
                requested_stop_risk_usd=(
                    Decimal(0)
                    if risk_request is None
                    else risk_request.requested_stop_risk
                ),
                requested_margin_usd=(
                    Decimal(0)
                    if risk_request is None
                    else risk_request.requested_margin
                ),
            ),
            downstream_consumed=(risk_request is not None),
            final_capital_binding=(risk_request is not None),
        ),
    ]

    for index, receipt in enumerate(decision.capital_science.receipts, start=1):
        sensors.append(
            CiboFunctionEconomicSensor(
                decision_id=decision.decision_id,
                function_code="CAPITAL_SCIENCE:" + receipt.function_code,
                stage_order=100 + index,
                input_sha256=receipt.input_sha256,
                output_sha256=receipt.output_sha256,
                input_metrics=_capital_science_input_metrics(receipt),
                output_metrics=_capital_science_output_metrics(receipt),
                called=True,
                downstream_consumed=bool(receipt.downstream_consumer),
                decision_gate_triggered=receipt.decision_changed,
                final_capital_binding=(
                    robust_binding
                    if receipt.function_code == "GEN-C11"
                    else (
                        receipt.function_code == "GEN-C12"
                        and receipt.consumer_action == "PAUSE_NEW_CAPITAL"
                        and final_plan.action is CapitalAction.HOLD
                    )
                    or (
                        receipt.function_code in {"GEN-C4", "GEN-C5", "GEN-C7", "GEN-C8"}
                        and compound_block_binding
                        and receipt.decision_changed
                    )
                ),
                risk_delta_usd=receipt.risk_delta_usd,
                margin_delta_usd=receipt.margin_delta_usd,
                ablation_key=None,
                causal_state=CiboSensorCausalState.UNPROVEN,
                causal_ending_capital_delta_usd=None,
                productive_authority=False,
            )
        )

    codes = tuple(item.function_code for item in sensors)
    if len(codes) != len(set(codes)):
        raise CiboCapitalManagementError(
            "function sensor codes must be unique per decision"
        )
    return tuple(sorted(sensors, key=lambda item: item.stage_order))


def summarize_function_sensors(
    sensors: Iterable[CiboFunctionEconomicSensor],
    *,
    full_ending_capital_usd: Decimal | None = None,
    ablation_ending_capital_usd: Mapping[str, Decimal] | None = None,
) -> dict[str, object]:
    """Aggregate activity separately from ablation-proven causal economics."""

    rows = tuple(sensors)
    if any(not isinstance(item, CiboFunctionEconomicSensor) for item in rows):
        raise CiboCapitalManagementError(
            "function sensor summary requires canonical sensor receipts"
        )

    by_function: dict[str, list[CiboFunctionEconomicSensor]] = defaultdict(list)
    by_ablation: dict[str, list[CiboFunctionEconomicSensor]] = defaultdict(list)
    for row in rows:
        by_function[row.function_code].append(row)
        if row.ablation_key is not None:
            by_ablation[row.ablation_key].append(row)

    function_summary: dict[str, object] = {}
    for code, group in sorted(by_function.items()):
        with localcontext() as context:
            context.prec = 100
            risk_delta = sum(
                (item.risk_delta_usd for item in group),
                Decimal(0),
            )
            margin_delta = sum(
                (item.margin_delta_usd for item in group),
                Decimal(0),
            )
        function_summary[code] = {
            "call_count": len(group),
            "downstream_consumed_count": sum(
                item.downstream_consumed for item in group
            ),
            "decision_gate_triggered_count": sum(
                item.decision_gate_triggered for item in group
            ),
            "final_capital_binding_count": sum(
                item.final_capital_binding for item in group
            ),
            "local_change_without_final_binding_count": sum(
                item.decision_gate_triggered and not item.final_capital_binding
                for item in group
            ),
            "risk_delta_usd": format(risk_delta, "f"),
            "margin_delta_usd": format(margin_delta, "f"),
            "ablation_keys": sorted(
                {
                    item.ablation_key
                    for item in group
                    if item.ablation_key is not None
                }
            ),
        }

    causal_summary: dict[str, object] = {}
    if full_ending_capital_usd is not None:
        if (
            not isinstance(full_ending_capital_usd, Decimal)
            or not full_ending_capital_usd.is_finite()
        ):
            raise CiboCapitalManagementError(
                "function sensor full ending capital must be finite Decimal"
            )
        ablations = dict(ablation_ending_capital_usd or {})
        for key, value in ablations.items():
            if key not in ABLATION_KEYS:
                raise CiboCapitalManagementError(
                    "function sensor summary received unknown ablation"
                )
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    "function sensor ablation capital must be finite Decimal"
                )
        for key in sorted(ABLATION_KEYS):
            group = by_ablation.get(key, [])
            without = ablations.get(key)
            causal_summary[key] = {
                "sensor_event_count": len(group),
                "decision_gate_triggered_count": sum(
                    item.decision_gate_triggered for item in group
                ),
                "causal_state": (
                    CiboSensorCausalState.ABLATION_PROVEN.value
                    if without is not None
                    else CiboSensorCausalState.UNPROVEN.value
                ),
                "ending_capital_without_group_usd": (
                    None if without is None else format(without, "f")
                ),
                "delta_ending_capital_vs_full_usd": (
                    None
                    if without is None
                    else format(full_ending_capital_usd - without, "f")
                ),
            }

    return {
        "sensor_count": len(rows),
        "function_summary": function_summary,
        "causal_ablation_summary": causal_summary,
        "causal_deltas_are_group_level_not_additive_across_member_sensors": True,
        "productive_authority": False,
    }
