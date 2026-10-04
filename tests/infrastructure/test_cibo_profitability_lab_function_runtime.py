from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_profitability_lab_function_runtime import (
    evaluate_cibo_native_faculties,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef

T0 = datetime(2020, 1, 2, 12, 0, tzinfo=UTC)


def _opportunity(signal: str, trader: TraderLineage) -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=trader,
        signal_fingerprint=signal,
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("1.10"),
        stop_loss=Decimal("1.09"),
        take_profit=Decimal("1.12"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("20"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
    )


def _regime(count: int) -> CiboCapitalRegimeState:
    return CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0.10"),
        margin_utilization=Decimal("0.10"),
        drawdown_utilization=Decimal("0.10"),
        opportunity_count=count,
    )


def test_native_faculty_runtime_calls_real_engines_or_justifies_temporal_na() -> None:
    opportunities = (
        _opportunity("signal-1", TraderLineage.R38_EURUSD),
        _opportunity("signal-2", TraderLineage.VT08_FOREX),
    )
    rows = evaluate_cibo_native_faculties(
        decision_at=T0,
        opportunities=opportunities,
        regime_state=_regime(len(opportunities)),
        evidence_ref=CiboEvidenceRef("lab:native-cf-runtime"),
    )

    assert tuple(row.function_code for row in rows) == tuple(
        f"CF{i:02d}" for i in range(1, 20)
    )
    by_code = {row.function_code: row for row in rows}
    assert {code for code, row in by_code.items() if not row.engine_called} == {
        "CF08",
        "CF18",
        "CF19",
    }
    assert all(
        by_code[code].status == "JUSTIFIED_NOT_APPLICABLE"
        for code in ("CF08", "CF18", "CF19")
    )
    assert by_code["CF01"].status == "SUCCESS"
    assert by_code["CF10"].status == "SUCCESS"
    assert by_code["CF03"].status == "SUCCESS"
    for code in (
        "CF01",
        "CF02",
        "CF03",
        "CF04",
        "CF05",
        "CF06",
        "CF07",
        "CF09",
        "CF11",
        "CF12",
        "CF13",
        "CF14",
        "CF15",
        "CF16",
        "CF17",
    ):
        assert by_code[code].engine_called is True
        assert by_code[code].status == "SUCCESS"
        assert by_code[code].output_payload


def test_native_faculty_runtime_is_deterministic() -> None:
    kwargs = {
        "decision_at": T0,
        "opportunities": (_opportunity("signal-1", TraderLineage.R38_EURUSD),),
        "regime_state": _regime(1),
        "evidence_ref": CiboEvidenceRef("lab:native-cf-runtime"),
    }
    assert evaluate_cibo_native_faculties(**kwargs) == evaluate_cibo_native_faculties(
        **kwargs
    )
