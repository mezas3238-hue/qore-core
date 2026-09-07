"""Normal + adversarial tests for the deterministic Trader identity/config contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.traders.contracts import (
    DemoTradingAbstainReason,
    DemoTradingConfigFingerprint,
    DemoTradingConfigParameter,
    DemoTradingDecision,
    DemoTradingEvidenceRef,
    DemoTradingMethodologyId,
    DemoTradingMethodologyVersion,
    DemoTradingOutput,
    DemoTradingSetupSide,
    DemoTradingSetupSpec,
    DemoTradingTraderCode,
    DemoTradingTraderVersion,
    DemoTradingValidationError,
    compute_trader_config_fingerprint,
    compute_trader_methodology_fingerprint,
    compute_trader_output_fingerprint,
)

_PROCESS = datetime(2026, 1, 6, 12, 0, tzinfo=UTC)


def _params(
    *items: tuple[str, str | bool | int | Decimal],
) -> tuple[DemoTradingConfigParameter, ...]:
    return tuple(DemoTradingConfigParameter(name, value) for name, value in items)


def test_trader_code_exact_syntax() -> None:
    assert DemoTradingTraderCode("vt-01").value == "vt-01"
    for bad in ("vt-1", "VT-01", "vt-01x", "vt-00", "vt-32", "", 1):
        with pytest.raises(DemoTradingValidationError):
            DemoTradingTraderCode(bad)  # type: ignore[arg-type]


def test_config_fingerprint_is_order_insensitive_and_deterministic() -> None:
    a = compute_trader_config_fingerprint(
        schema_version="trader-config-v1",
        parameters=_params(("a", 1), ("b", Decimal("2.5"))),
    )
    b = compute_trader_config_fingerprint(
        schema_version="trader-config-v1",
        parameters=_params(("b", Decimal("2.50")), ("a", 1)),
    )
    assert a == b
    c = compute_trader_config_fingerprint(
        schema_version="trader-config-v1",
        parameters=_params(("a", 2), ("b", Decimal("2.5"))),
    )
    assert a != c


def test_config_fingerprint_changes_alter_identity() -> None:
    base = _params(("sweep.strength", 2))
    changed = _params(("sweep.strength", 3))
    assert compute_trader_config_fingerprint(
        schema_version="trader-config-v1", parameters=base
    ) != compute_trader_config_fingerprint(
        schema_version="trader-config-v1", parameters=changed
    )


def test_config_parameter_bool_is_distinct_from_int() -> None:
    # bool is an accepted value type but is canonicalized as "bool", never "int".
    param = DemoTradingConfigParameter("x", True)
    assert param.canonical_value() == {"type": "bool", "value": True}
    int_param = DemoTradingConfigParameter("x", 1)
    assert int_param.canonical_value() == {"type": "int", "value": "1"}


def test_config_parameter_rejects_float() -> None:
    with pytest.raises(DemoTradingValidationError):
        DemoTradingConfigParameter("x", 1.5)  # type: ignore[arg-type]


def test_config_parameter_exact_decimal_canonicalization() -> None:
    p1 = DemoTradingConfigParameter("x", Decimal("1.0"))
    p2 = DemoTradingConfigParameter("x", Decimal("1.00"))
    assert p1.logical_values() == p2.logical_values()


def test_evidence_ref_rejects_uppercase_and_secrets() -> None:
    assert DemoTradingEvidenceRef("qore:demo:ev:1").value == "qore:demo:ev:1"
    for bad in ("Evidence:1", "QORE:1", "", "token=abc", "authorization:bearer x"):
        with pytest.raises(DemoTradingValidationError):
            DemoTradingEvidenceRef(bad)


def _output(
    *,
    decision: DemoTradingDecision,
    evidence_refs: tuple[DemoTradingEvidenceRef, ...],
) -> DemoTradingOutput:
    methodology_id = DemoTradingMethodologyId("ny-precision-core")
    methodology_version = DemoTradingMethodologyVersion("v1")
    methodology_fingerprint = compute_trader_methodology_fingerprint(
        methodology_id=methodology_id,
        methodology_version=methodology_version,
        timeframe="M5",
        session="ny-am-session",
        ruleset="rule",
    )
    config_fingerprint = compute_trader_config_fingerprint(
        schema_version="trader-config-v1",
        parameters=(DemoTradingConfigParameter("sweep.strength", 2),),
    )
    setup: DemoTradingSetupSpec | None = None
    side: DemoTradingSetupSide | None = None
    reason: DemoTradingAbstainReason | None = None
    if decision is DemoTradingDecision.SETUP:
        side = DemoTradingSetupSide.LONG
        setup = DemoTradingSetupSpec(
            side=side,
            entry_price=Decimal("1.1000"),
            invalidation_price=Decimal("1.0950"),
            take_profit_price=Decimal("1.1100"),
            entry_reason="fvg",
        )
    else:
        reason = DemoTradingAbstainReason.NO_SESSION
    output_fingerprint = compute_trader_output_fingerprint(
        trader_code=DemoTradingTraderCode("vt-01"),
        version=DemoTradingTraderVersion("v1"),
        config_fingerprint=config_fingerprint,
        methodology_id=methodology_id,
        methodology_version=methodology_version,
        methodology_fingerprint=methodology_fingerprint,
        evidence_refs=evidence_refs,
        timeframe="M5",
        session="ny-am-session",
        decision=decision,
        side=side,
        setup=setup,
        abstain_reason=reason,
        evaluated_at=_PROCESS,
    )
    return DemoTradingOutput(
        trader_code=DemoTradingTraderCode("vt-01"),
        version=DemoTradingTraderVersion("v1"),
        config_fingerprint=config_fingerprint,
        methodology_id=methodology_id,
        methodology_version=methodology_version,
        methodology_fingerprint=methodology_fingerprint,
        evidence_refs=evidence_refs,
        timeframe="M5",
        session="ny-am-session",
        decision=decision,
        side=side,
        setup=setup,
        abstain_reason=reason,
        evaluated_at=_PROCESS,
        output_fingerprint=output_fingerprint,
    )


def test_output_setup_and_abstain_mutual_exclusion() -> None:
    evidence = (DemoTradingEvidenceRef("qore:demo:ev:1"),)
    setup_out = _output(
        decision=DemoTradingDecision.SETUP,
        evidence_refs=evidence,
    )
    assert setup_out.decision is DemoTradingDecision.SETUP
    assert setup_out.setup is not None
    assert setup_out.abstain_reason is None
    abstain_out = _output(
        decision=DemoTradingDecision.ABSTAIN,
        evidence_refs=evidence,
    )
    assert abstain_out.decision is DemoTradingDecision.ABSTAIN
    assert abstain_out.setup is None
    assert abstain_out.abstain_reason is DemoTradingAbstainReason.NO_SESSION


def test_output_fingerprint_is_stable_under_reconstruction() -> None:
    evidence = (DemoTradingEvidenceRef("qore:demo:ev:1"),)
    first = _output(decision=DemoTradingDecision.SETUP, evidence_refs=evidence)
    second = _output(decision=DemoTradingDecision.SETUP, evidence_refs=evidence)
    assert first.output_fingerprint == second.output_fingerprint
    assert first.logical_values() == second.logical_values()


def test_output_evidence_refs_canonicalized() -> None:
    a = _output(
        decision=DemoTradingDecision.SETUP,
        evidence_refs=(
            DemoTradingEvidenceRef("qore:demo:ev:2"),
            DemoTradingEvidenceRef("qore:demo:ev:1"),
        ),
    )
    b = _output(
        decision=DemoTradingDecision.SETUP,
        evidence_refs=(
            DemoTradingEvidenceRef("qore:demo:ev:1"),
            DemoTradingEvidenceRef("qore:demo:ev:2"),
        ),
    )
    assert a.output_fingerprint == b.output_fingerprint


def test_output_naive_timestamp_rejected() -> None:
    methodology_fingerprint = compute_trader_methodology_fingerprint(
        methodology_id=DemoTradingMethodologyId("ny-precision-core"),
        methodology_version=DemoTradingMethodologyVersion("v1"),
        timeframe="M5",
        session="ny-am-session",
        ruleset="rule",
    )
    with pytest.raises(DemoTradingValidationError):
        compute_trader_output_fingerprint(
            trader_code=DemoTradingTraderCode("vt-01"),
            version=DemoTradingTraderVersion("v1"),
            config_fingerprint=DemoTradingConfigFingerprint("a" * 64),
            methodology_id=DemoTradingMethodologyId("ny-precision-core"),
            methodology_version=DemoTradingMethodologyVersion("v1"),
            methodology_fingerprint=methodology_fingerprint,
            evidence_refs=(DemoTradingEvidenceRef("qore:demo:ev:1"),),
            timeframe="M5",
            session="ny-am-session",
            decision=DemoTradingDecision.ABSTAIN,
            side=None,
            setup=None,
            abstain_reason=DemoTradingAbstainReason.NO_SESSION,
            evaluated_at=datetime(2026, 1, 6, 12, 0),
        )


def test_setup_spec_rejects_invalid_long_geometry() -> None:
    with pytest.raises(DemoTradingValidationError):
        DemoTradingSetupSpec(
            side=DemoTradingSetupSide.LONG,
            entry_price=Decimal("1.1000"),
            invalidation_price=Decimal("1.1050"),
            take_profit_price=Decimal("1.1100"),
            entry_reason="fvg",
        )


def test_setup_spec_rejects_invalid_short_geometry() -> None:
    with pytest.raises(DemoTradingValidationError):
        DemoTradingSetupSpec(
            side=DemoTradingSetupSide.SHORT,
            entry_price=Decimal("1.1000"),
            invalidation_price=Decimal("1.0950"),
            take_profit_price=Decimal("1.1050"),
            entry_reason="fvg",
        )
