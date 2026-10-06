import ast
import inspect
from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import qore.infrastructure.cibo_sovereign_capital_runtime as module
from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import CiboCapitalMission
from qore.infrastructure.cibo_account_sizing_authority import (
    CiboAccountSizingDecision,
    CiboAccountSizingMode,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CapitalSource,
    CapitalSourceLot,
    CapitalStage,
    CiboCapitalActionPlan,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_executive_brain import (
    CiboExecutiveDirectiveKind,
    CiboExecutiveSynthesis,
)
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboConfidence,
    CiboConfidenceLevel,
    CiboFormalRecommendation,
    CiboReasoningMode,
    CiboUncertainty,
    CiboUncertaintyKind,
)
from tests.infrastructure.test_cibo_full_economic_digital_twin import (
    T0,
    _full_twin,
)


def test_every_sovereign_decision_constructor_carries_capital_science() -> None:
    tree = ast.parse(inspect.getsource(module))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "CiboSovereignCapitalDecision"
    ]

    assert calls
    for call in calls:
        keywords = {item.arg for item in call.keywords}
        assert "capital_science" in keywords



def test_sovereign_cap_resize_preserves_long_decimal_source_provenance() -> None:
    step = Decimal("0.0000000000000000000000000000000000000001")
    first = Decimal("1.1111111111111111111111111111111111111111")
    second = Decimal("2.2222222222222222222222222222222222222222")
    total = Decimal("3.3333333333333333333333333333333333333333")
    capped = Decimal("2.2222222222222222222222222222222222222222")
    opportunity = TraderOpportunityEnvelope(
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint="resize-long-decimal",
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        stop_loss_per_volume=Decimal("1"),
        margin_per_volume=Decimal("1"),
        volume_step=step,
        minimum_volume=step,
        maximum_volume=Decimal("10"),
    )
    plan = CiboCapitalActionPlan(
        trader_id=TraderLineage.R34_XAUUSD,
        qore_symbol="XAUUSD",
        stage=CapitalStage.CAPITALIZE,
        action=CapitalAction.OPEN_CAPABILITY_MAX,
        volume=total,
        stop_risk_usd=total,
        margin_usd=total,
        capital_source=None,
        capital_source_amount_usd=total,
        reason="resize exact provenance",
        capital_source_lots=(
            CapitalSourceLot(
                source=CapitalSource.ORIGINAL_BASE_CAPITAL,
                amount_usd=first,
                source_id="base",
            ),
            CapitalSourceLot(
                source=CapitalSource.REALIZED_PROFIT,
                amount_usd=second,
                source_id="profit",
            ),
        ),
    )
    sizing = CiboAccountSizingDecision(
        mission=CiboCapitalMission.DEMO_CAPABILITY_DISCOVERY,
        mode=CiboAccountSizingMode.CAPABILITY_MAXIMUM,
        base_protected=True,
        survival_capital_usd=Decimal("0"),
        protected_capital_usd=Decimal("0"),
        plan=plan,
    )

    resized = module._cap_sizing_plan(
        opportunity=opportunity,
        sizing=sizing,
        portfolio_risk_cap_usd=capped,
        portfolio_margin_cap_usd=Decimal("10"),
        robust_risk_cap_usd=capped,
        robust_margin_cap_usd=Decimal("10"),
    )

    assert resized.stop_risk_usd == capped
    assert resized.capital_source_amount_usd == capped
    assert tuple(lot.amount_usd for lot in resized.capital_source_lots) == (
        first,
        Decimal("1.1111111111111111111111111111111111111111"),
    )



def _recommend_synthesis(
    level: CiboConfidenceLevel,
) -> CiboExecutiveSynthesis:
    ref = CiboCognitiveEvidenceRef("evidence:capital-intensity")
    uncertainty = CiboUncertainty(
        kind=CiboUncertaintyKind.BOUNDED_CONFIDENCE,
        confidence=CiboConfidence(
            level=level,
            evidence_refs=(ref,),
        ),
    )
    recommendation = CiboFormalRecommendation(
        recommendation_id=UUID("70000000-0000-0000-0000-0000000000cc"),
        recommendation_code="cibo.capital-intensity",
        reasoning_mode=CiboReasoningMode.MAX,
        summary="Causal capital intensity recommendation",
        evidence_refs=(ref,),
        uncertainty=uncertainty,
        issued_at=T0,
    )
    return CiboExecutiveSynthesis(
        synthesis_id=UUID("70000000-0000-0000-0000-0000000000cd"),
        directive=CiboExecutiveDirectiveKind.RECOMMEND,
        reasoning_mode=CiboReasoningMode.MAX,
        subject_code="capital-intensity",
        synthesized_at=T0,
        evidence_refs=(ref,),
        uncertainty=uncertainty,
        recommendation=recommendation,
    )


def test_native_max_confidence_grades_capital_intensity() -> None:
    twin = replace(
        _full_twin(),
        cognitive_constraints=(("capital_intensity_cap", "4"),),
    )

    expected = {
        CiboConfidenceLevel.LOW: "1",
        CiboConfidenceLevel.MEDIUM: "2",
        CiboConfidenceLevel.HIGH: "3",
    }
    for level, cap in expected.items():
        bound = module.bind_cibo_cognition_to_twin(
            twin,
            _recommend_synthesis(level),
        )
        constraints = dict(bound.cognitive_constraints)
        assert constraints["capital_intensity_cap"] == cap
        assert constraints["executive_confidence_level"] == level.value


def test_sovereign_runtime_makes_genc12_pause_binding_for_new_openings() -> None:
    source = inspect.getsource(module.run_cibo_sovereign_capital_runtime)

    assert '"PAUSE_NEW_CAPITAL"' in source
    assert "CapitalAction.OPEN_MINIMAL_SEED" in source
    assert "CapitalAction.OPEN_CAPABILITY_MAX" in source
    assert "CapitalAction.EXPAND" in source
    assert "GEN-C12 paused all new capital deployment" in source



def test_max_frontier_can_only_reduce_native_max_intensity() -> None:
    twin = replace(
        _full_twin(),
        cognitive_constraints=(("capital_intensity_cap", "4"),),
    )

    high = module.bind_cibo_cognition_to_twin(
        twin,
        _recommend_synthesis(CiboConfidenceLevel.HIGH),
        maximum_frontier_cap=1,
        maximum_frontier_reason="frontier stress cap",
        maximum_frontier_consumed_codes=("CF02", "CF06", "CF07", "CF10", "CF12"),
    )
    high_constraints = dict(high.cognitive_constraints)
    assert high_constraints["capital_intensity_cap"] == "1"
    assert high_constraints["maximum_frontier_cap"] == "1"
    assert high_constraints["maximum_frontier_mode"] == "CONSTRAINING_ONLY"
    assert high_constraints["maximum_frontier_policy"] == (
        module.MAX_FRONTIER_POLICY_ID
    )
    assert high_constraints["maximum_frontier_consumed_codes"] == (
        "CF02,CF06,CF07,CF10,CF12"
    )

    low = module.bind_cibo_cognition_to_twin(
        twin,
        _recommend_synthesis(CiboConfidenceLevel.LOW),
        maximum_frontier_cap=4,
    )
    assert dict(low.cognitive_constraints)["capital_intensity_cap"] == "1"


def test_sovereign_runtime_consumes_max_frontier_before_portfolio() -> None:
    source = inspect.getsource(module.run_cibo_sovereign_capital_runtime)

    frontier_call = source.index("_maximum_frontier_surface(consultation)")
    bind_call = source.index("bind_cibo_cognition_to_twin(")
    economic_call = source.index("run_cibo_economic_engine_chain(")

    assert frontier_call < bind_call < economic_call
