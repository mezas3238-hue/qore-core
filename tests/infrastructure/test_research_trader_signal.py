from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
from qore.functional.decisions import (
    DecisionId,
    DecisionMetadata,
    DecisionOutcome,
    DecisionPriority,
    DecisionReason,
    DecisionReasonCode,
    DecisionStatus,
    DecisionType,
    FunctionalDecision,
)
from qore.infrastructure.research_lineage_errors import ResearchLineageValidationError
from qore.infrastructure.research_trader_signal import (
    TraderSignalSide,
    TraderSignalStateContent,
    build_trader_signal_decision,
    canonical_decimal_string,
    compute_trader_config_fingerprint,
    derive_trader_correlation_id,
    derive_trader_decision_id,
    extract_trader_signal_side,
    market_decimal,
    validate_lookback,
    validate_positive_decimal,
)

_NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
_CORRELATION = CorrelationId(UUID("a0000000-0000-0000-0000-000000000001"))


def _signal_decision(side: TraderSignalSide) -> FunctionalDecision:
    return build_trader_signal_decision(
        decision_id=DecisionId(UUID("a0000000-0000-0000-0000-000000000002")),
        timestamp=_NOW,
        correlation_id=_CORRELATION,
        side=side,
        reason_code="qore.trader.trend.buy",
        summary="trend momentum upward",
        evidence={"metric": "0.5"},
    )


def _foreign_decision() -> FunctionalDecision:
    return FunctionalDecision(
        decision_id=DecisionId(UUID("a0000000-0000-0000-0000-000000000002")),
        timestamp=_NOW,
        decision_type=DecisionType("other.decision"),
        status=DecisionStatus.RESOLVED,
        priority=DecisionPriority.NORMAL,
        metadata=DecisionMetadata(correlation_id=_CORRELATION),
        reasons=(DecisionReason(code=DecisionReasonCode("other.decision"), summary="other"),),
        outcome=DecisionOutcome.APPROVED,
    )


def test_signal_side_members_are_closed() -> None:
    assert {side.value for side in TraderSignalSide} == {"buy", "sell", "abstain"}


def test_buy_and_sell_are_approved_not_rejected() -> None:
    assert _signal_decision(TraderSignalSide.BUY).outcome is DecisionOutcome.APPROVED
    assert _signal_decision(TraderSignalSide.SELL).outcome is DecisionOutcome.APPROVED
    assert _signal_decision(TraderSignalSide.ABSTAIN).outcome is DecisionOutcome.BLOCKED


def test_side_is_first_class_in_metadata() -> None:
    decision = _signal_decision(TraderSignalSide.SELL)
    assert decision.metadata.attributes["side"] == "sell"
    assert extract_trader_signal_side(decision) is TraderSignalSide.SELL


def test_extract_side_returns_none_for_foreign_decision() -> None:
    assert extract_trader_signal_side(_foreign_decision()) is None


def test_decision_id_is_deterministic_and_side_sensitive() -> None:
    evidence = {"metric": "0.5"}
    first = derive_trader_decision_id(
        binding_fingerprint="a" * 64,
        sequence_number=3,
        side=TraderSignalSide.BUY,
        evidence=evidence,
    )
    second = derive_trader_decision_id(
        binding_fingerprint="a" * 64,
        sequence_number=3,
        side=TraderSignalSide.BUY,
        evidence=evidence,
    )
    other_side = derive_trader_decision_id(
        binding_fingerprint="a" * 64,
        sequence_number=3,
        side=TraderSignalSide.SELL,
        evidence=evidence,
    )
    assert first == second
    assert first != other_side


def test_correlation_id_is_deterministic() -> None:
    assert derive_trader_correlation_id("a" * 64) == derive_trader_correlation_id("a" * 64)
    assert derive_trader_correlation_id("a" * 64) != derive_trader_correlation_id("b" * 64)


def test_config_fingerprint_is_deterministic_and_field_sensitive() -> None:
    fields = {"lookback": "5", "threshold": "0.01"}
    assert compute_trader_config_fingerprint(
        schema="qore.trader.trend.configuration.v1", fields=fields
    ) == compute_trader_config_fingerprint(
        schema="qore.trader.trend.configuration.v1", fields=fields
    )
    assert compute_trader_config_fingerprint(
        schema="qore.trader.trend.configuration.v1", fields=fields
    ) != compute_trader_config_fingerprint(
        schema="qore.trader.trend.configuration.v1",
        fields={"lookback": "6", "threshold": "0.01"},
    )


def test_market_decimal_uses_exact_string_conversion() -> None:
    assert market_decimal(1.1) == Decimal("1.1")


def test_canonical_decimal_string_is_exact_and_fixed_point() -> None:
    assert canonical_decimal_string(Decimal("0.10")) == "0.1"
    assert canonical_decimal_string(Decimal("0")) == "0"


def test_validate_lookback_rejects_bool_and_negative() -> None:
    assert validate_lookback(5, field_name="lookback") == 5
    with pytest.raises(ResearchLineageValidationError):
        validate_lookback(cast(int, True), field_name="lookback")
    with pytest.raises(ResearchLineageValidationError):
        validate_lookback(0, field_name="lookback")


def test_validate_positive_decimal_rejects_non_positive_and_non_finite() -> None:
    assert validate_positive_decimal(Decimal("0.01"), field_name="threshold") == Decimal("0.01")
    for bad in (Decimal("0"), Decimal("-0.1"), Decimal("NaN"), Decimal("Infinity")):
        with pytest.raises(ResearchLineageValidationError):
            validate_positive_decimal(bad, field_name="threshold")


def test_state_content_requires_float_bars_and_aware_datetime() -> None:
    content = TraderSignalStateContent(
        config_fingerprint="a" * 64,
        bars=((1.0, 2.0, 3.0),),
        last_closed_at=_NOW,
    )
    assert content.logical_values()["bars"] == ((1.0, 2.0, 3.0),)
    with pytest.raises(ResearchLineageValidationError):
        TraderSignalStateContent(
            config_fingerprint="a" * 64,
            bars=(cast(tuple[float, float, float], (1, 2.0, 3.0)),),
            last_closed_at=_NOW,
        )
    with pytest.raises(ResearchLineageValidationError):
        TraderSignalStateContent(
            config_fingerprint="a" * 64,
            bars=(),
            last_closed_at=datetime(2026, 8, 10, 12, 0),  # naive
        )


def test_signal_reason_carries_only_evidence_not_side() -> None:
    decision = _signal_decision(TraderSignalSide.BUY)
    assert "side" not in decision.reasons[0].attributes
    assert decision.reasons[0].attributes["metric"] == "0.5"


@pytest.mark.parametrize(
    "module",
    [
        "research_trader_signal.py",
        "research_trader_producer_base.py",
        "research_trend_momentum_producer.py",
        "research_mean_reversion_producer.py",
        "research_breakout_volatility_producer.py",
        "cibo_trader_manager.py",
    ],
)
def test_no_execution_or_provider_imports(module: str) -> None:
    path = Path("src/qore/infrastructure") / module
    source = path.read_text()
    forbidden = (
        "order_intent",
        "execution_boundary",
        "execution_gateway",
        "execution_orchestration",
        "real_market",
        "pretrade_safety",
        "supervised_runtime",
        "production_configuration",
        "production_runtime",
        "oanda_practice",
        "ctrader_demo",
        "futures_ibkr",
        "futures_tastytrade",
        "futures_tradestation",
    )
    for token in forbidden:
        assert token not in source, f"{module} must not import {token}"
