from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import pytest

from qore.infrastructure.event_contract_semantics import (
    EventCashPayout,
    EventContractTerms,
    EventContractTermsId,
    EventContractValidationError,
    EventCorrectionPolicyCode,
    EventCriterionCode,
    EventEvidenceRef,
    EventOutcomeCode,
    EventOutcomeStructureCode,
    EventOutcomeTerms,
    EventResolutionAuthorityRef,
    EventResolutionRuleCode,
    EventResolutionSourceCode,
    EventResolutionTerms,
    EventSourceConflictPolicyCode,
    EventSubjectReferenceId,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _identity(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(value))


def _payout(amount: str, currency: int = 300) -> EventCashPayout:
    return EventCashPayout(Decimal(amount), _identity(currency))


def _outcome(code: str, amount: str) -> EventOutcomeTerms:
    return EventOutcomeTerms(EventOutcomeCode(code), _payout(amount))


def _resolution(
    *,
    primary: tuple[EventResolutionSourceCode, ...] | None = None,
    fallback: tuple[EventResolutionSourceCode, ...] = (),
    rule: str = "official-final-publication",
    correction: str = "latest-authoritative-correction-before-cutoff",
    conflict: str = "primary-source-priority-order",
    scheduled: date | None = date(2026, 11, 4),
) -> EventResolutionTerms:
    return EventResolutionTerms(
        authority_ref=EventResolutionAuthorityRef(_uuid(50)),
        primary_source_codes=primary
        if primary is not None
        else (
            EventResolutionSourceCode("agency-a-final"),
            EventResolutionSourceCode("agency-b-final"),
        ),
        fallback_source_codes=fallback,
        resolution_rule_code=EventResolutionRuleCode(rule),
        correction_policy_code=EventCorrectionPolicyCode(correction),
        source_conflict_policy_code=EventSourceConflictPolicyCode(conflict),
        scheduled_resolution_date=scheduled,
    )


def _contract() -> EventContractTerms:
    return EventContractTerms(
        terms_id=EventContractTermsId(_uuid(100)),
        instrument_identity_id=_identity(10),
        subject_reference_id=EventSubjectReferenceId(_uuid(20)),
        criterion_code=EventCriterionCode("candidate-a-wins-certified-election"),
        outcome_structure_code=EventOutcomeStructureCode("binary-yes-no"),
        outcomes=(_outcome("yes", "1"), _outcome("no", "0")),
        expiration_date=date(2026, 11, 3),
        resolution_terms=_resolution(),
        evidence_ref=EventEvidenceRef(_uuid(200)),
    )


def test_uuid_wrappers_are_explicit_and_deterministic() -> None:
    values = (
        EventContractTermsId(_uuid(1)),
        EventEvidenceRef(_uuid(2)),
        EventSubjectReferenceId(_uuid(3)),
        EventResolutionAuthorityRef(_uuid(4)),
    )
    assert [value.logical_values() for value in values] == [
        (str(_uuid(1)),),
        (str(_uuid(2)),),
        (str(_uuid(3)),),
        (str(_uuid(4)),),
    ]


@pytest.mark.parametrize(
    "factory",
    [
        EventContractTermsId,
        EventEvidenceRef,
        EventSubjectReferenceId,
        EventResolutionAuthorityRef,
    ],
)
def test_uuid_wrappers_reject_raw_strings(factory: Any) -> None:
    with pytest.raises(EventContractValidationError):
        factory(cast(Any, str(_uuid(1))))


@pytest.mark.parametrize(
    "factory",
    [
        EventCriterionCode,
        EventOutcomeStructureCode,
        EventOutcomeCode,
        EventResolutionSourceCode,
        EventResolutionRuleCode,
        EventCorrectionPolicyCode,
        EventSourceConflictPolicyCode,
    ],
)
def test_code_wrappers_are_canonical(factory: Any) -> None:
    value = factory("official-source.v1")
    assert value.logical_values() == ("official-source.v1",)


@pytest.mark.parametrize(
    "factory",
    [
        EventCriterionCode,
        EventOutcomeStructureCode,
        EventOutcomeCode,
        EventResolutionSourceCode,
        EventResolutionRuleCode,
        EventCorrectionPolicyCode,
        EventSourceConflictPolicyCode,
    ],
)
@pytest.mark.parametrize("value", ["", "UPPER", "bad code", "a" * 97, 7])
def test_code_wrappers_fail_closed(factory: Any, value: object) -> None:
    with pytest.raises(EventContractValidationError):
        factory(cast(Any, value))


def test_cash_payout_allows_zero_and_preserves_currency() -> None:
    value = _payout("0.000", 300)
    assert value.logical_values() == ("0", _identity(300).logical_values())


@pytest.mark.parametrize("value", ["-0.01", "NaN", "Infinity"])
def test_cash_payout_requires_nonnegative_finite_decimal(value: str) -> None:
    with pytest.raises(EventContractValidationError):
        EventCashPayout(Decimal(value), _identity(300))


def test_cash_payout_rejects_raw_number_and_identity() -> None:
    with pytest.raises(EventContractValidationError):
        EventCashPayout(cast(Any, 1.0), _identity(300))
    with pytest.raises(EventContractValidationError):
        EventCashPayout(Decimal("1"), cast(Any, _uuid(300)))


def test_outcome_terms_preserve_code_and_payout() -> None:
    value = _outcome("yes", "1")
    assert value.logical_values() == (("yes",), _payout("1").logical_values())


def test_outcome_terms_reject_raw_code_or_payout() -> None:
    with pytest.raises(EventContractValidationError):
        EventOutcomeTerms(cast(Any, "yes"), _payout("1"))
    with pytest.raises(EventContractValidationError):
        EventOutcomeTerms(EventOutcomeCode("yes"), cast(Any, Decimal("1")))


def test_resolution_preserves_ordered_primary_and_fallback_sources() -> None:
    primary = (
        EventResolutionSourceCode("source-a"),
        EventResolutionSourceCode("source-b"),
    )
    fallback = (
        EventResolutionSourceCode("fallback-a"),
        EventResolutionSourceCode("fallback-b"),
    )
    value = _resolution(primary=primary, fallback=fallback)
    logical = value.logical_values()
    assert logical[1] == (("source-a",), ("source-b",))
    assert logical[2] == (("fallback-a",), ("fallback-b",))


def test_resolution_primary_order_is_contractual_material() -> None:
    first = _resolution(
        primary=(
            EventResolutionSourceCode("source-a"),
            EventResolutionSourceCode("source-b"),
        )
    )
    second = _resolution(
        primary=(
            EventResolutionSourceCode("source-b"),
            EventResolutionSourceCode("source-a"),
        )
    )
    assert first.logical_values() != second.logical_values()


@pytest.mark.parametrize(
    "sources",
    [
        (),
        [EventResolutionSourceCode("source-a")],
        (cast(Any, "source-a"),),
        (
            EventResolutionSourceCode("source-a"),
            EventResolutionSourceCode("source-a"),
        ),
    ],
)
def test_primary_resolution_sources_fail_closed(sources: object) -> None:
    with pytest.raises(EventContractValidationError):
        _resolution(primary=cast(Any, sources))


@pytest.mark.parametrize(
    "sources",
    [
        [EventResolutionSourceCode("fallback-a")],
        (cast(Any, "fallback-a"),),
        (
            EventResolutionSourceCode("fallback-a"),
            EventResolutionSourceCode("fallback-a"),
        ),
    ],
)
def test_fallback_resolution_sources_fail_closed(sources: object) -> None:
    with pytest.raises(EventContractValidationError):
        _resolution(fallback=cast(Any, sources))


def test_primary_and_fallback_sources_must_be_disjoint() -> None:
    with pytest.raises(EventContractValidationError):
        _resolution(
            primary=(EventResolutionSourceCode("source-a"),),
            fallback=(EventResolutionSourceCode("source-a"),),
        )


def test_resolution_allows_no_fallback_and_no_scheduled_date() -> None:
    value = _resolution(fallback=(), scheduled=None)
    assert value.logical_values()[2] == ()
    assert value.logical_values()[-1] is None


@pytest.mark.parametrize(
    ("field_name", "invalid"),
    [
        ("authority_ref", _uuid(50)),
        ("resolution_rule_code", "rule"),
        ("correction_policy_code", "policy"),
        ("source_conflict_policy_code", "conflict"),
        ("scheduled_resolution_date", "2026-11-04"),
    ],
)
def test_resolution_wrappers_fail_closed(field_name: str, invalid: object) -> None:
    base = _resolution()
    with pytest.raises(EventContractValidationError):
        replace(base, **{field_name: cast(Any, invalid)})


def test_contract_preserves_binary_question_outcomes_and_resolution() -> None:
    contract = _contract()
    logical = contract.logical_values()
    assert logical[0] == "event-contract"
    assert logical[4] == ("candidate-a-wins-certified-election",)
    assert logical[5] == ("binary-yes-no",)
    assert logical[6] == (
        _outcome("yes", "1").logical_values(),
        _outcome("no", "0").logical_values(),
    )
    assert logical[7] == "2026-11-03"
    assert logical[8] == contract.resolution_terms.logical_values()


def test_same_payout_shape_different_criterion_does_not_collapse() -> None:
    first = _contract()
    second = replace(
        first,
        criterion_code=EventCriterionCode("candidate-b-wins-certified-election"),
    )
    assert first.outcomes == second.outcomes
    assert first.logical_values() != second.logical_values()


def test_same_event_different_resolution_source_does_not_collapse() -> None:
    first = _contract()
    second = replace(
        first,
        resolution_terms=_resolution(
            primary=(EventResolutionSourceCode("different-authority-source"),)
        ),
    )
    assert first.criterion_code == second.criterion_code
    assert first.logical_values() != second.logical_values()


def test_correction_policy_and_conflict_policy_are_contractual_material() -> None:
    base = _contract()
    correction_variant = replace(
        base,
        resolution_terms=_resolution(correction="ignore-post-cutoff-corrections"),
    )
    conflict_variant = replace(
        base,
        resolution_terms=_resolution(conflict="authority-discretion-on-conflict"),
    )
    assert base.logical_values() != correction_variant.logical_values()
    assert base.logical_values() != conflict_variant.logical_values()


def test_contract_allows_nonbinary_explicit_outcome_structure() -> None:
    contract = EventContractTerms(
        terms_id=EventContractTermsId(_uuid(110)),
        instrument_identity_id=_identity(11),
        subject_reference_id=EventSubjectReferenceId(_uuid(21)),
        criterion_code=EventCriterionCode("official-category-result"),
        outcome_structure_code=EventOutcomeStructureCode("three-outcome-category"),
        outcomes=(
            _outcome("alpha", "2"),
            _outcome("beta", "1"),
            _outcome("gamma", "0"),
        ),
        resolution_terms=_resolution(),
        evidence_ref=EventEvidenceRef(_uuid(210)),
    )
    assert len(contract.outcomes) == 3


@pytest.mark.parametrize(
    "outcomes",
    [
        (),
        (_outcome("yes", "1"),),
        [_outcome("yes", "1"), _outcome("no", "0")],
        (_outcome("yes", "1"), cast(Any, "bad")),
    ],
)
def test_contract_requires_two_or_more_typed_tuple_outcomes(outcomes: object) -> None:
    with pytest.raises(EventContractValidationError):
        replace(_contract(), outcomes=cast(Any, outcomes))


def test_contract_rejects_duplicate_outcome_codes_even_with_different_payouts() -> None:
    with pytest.raises(EventContractValidationError):
        replace(
            _contract(),
            outcomes=(_outcome("yes", "1"), _outcome("yes", "0")),
        )


def test_contract_does_not_invent_universal_complementary_payout_rule() -> None:
    contract = replace(
        _contract(),
        outcomes=(_outcome("yes", "7"), _outcome("no", "2")),
    )
    assert contract.outcomes[0].payout.amount == Decimal("7")
    assert contract.outcomes[1].payout.amount == Decimal("2")


def test_contract_does_not_invent_universal_same_payout_currency_rule() -> None:
    contract = replace(
        _contract(),
        outcomes=(
            EventOutcomeTerms(EventOutcomeCode("yes"), _payout("1", 300)),
            EventOutcomeTerms(EventOutcomeCode("no"), _payout("0", 301)),
        ),
    )
    assert (
        contract.outcomes[0].payout.currency_identity_id
        != contract.outcomes[1].payout.currency_identity_id
    )


@pytest.mark.parametrize(
    ("field_name", "invalid"),
    [
        ("terms_id", _uuid(100)),
        ("instrument_identity_id", _uuid(10)),
        ("subject_reference_id", _uuid(20)),
        ("criterion_code", "criterion"),
        ("outcome_structure_code", "binary"),
        ("resolution_terms", "resolution"),
        ("evidence_ref", _uuid(200)),
        ("expiration_date", "2026-11-03"),
    ],
)
def test_contract_common_wrappers_fail_closed(field_name: str, invalid: object) -> None:
    with pytest.raises(EventContractValidationError):
        replace(_contract(), **{field_name: cast(Any, invalid)})


def test_scheduled_resolution_may_equal_expiration() -> None:
    contract = replace(
        _contract(),
        expiration_date=date(2026, 11, 4),
        resolution_terms=_resolution(scheduled=date(2026, 11, 4)),
    )
    assert contract.expiration_date == contract.resolution_terms.scheduled_resolution_date


def test_scheduled_resolution_must_not_precede_expiration() -> None:
    with pytest.raises(EventContractValidationError):
        replace(
            _contract(),
            expiration_date=date(2026, 11, 5),
            resolution_terms=_resolution(scheduled=date(2026, 11, 4)),
        )


def test_expiration_and_scheduled_resolution_are_independently_optional() -> None:
    no_expiration = replace(_contract(), expiration_date=None)
    no_schedule = replace(
        _contract(),
        resolution_terms=_resolution(scheduled=None),
    )
    assert no_expiration.logical_values()[7] is None
    assert no_schedule.resolution_terms.logical_values()[-1] is None


def test_d04_contract_has_no_resolved_or_current_outcome_field() -> None:
    field_names = {field.name for field in fields(EventContractTerms)}
    assert "resolved_outcome" not in field_names
    assert "current_outcome" not in field_names
    assert "resolution_timestamp" not in field_names


def test_values_are_frozen() -> None:
    value = EventOutcomeCode("yes")
    with pytest.raises(FrozenInstanceError):
        value.__setattr__("value", "no")


@pytest.mark.parametrize("factory", [_contract, _resolution])
def test_logical_values_are_repeatable(factory: Any) -> None:
    value = factory()
    assert value.logical_values() == value.logical_values()


def test_source_has_no_runtime_resolution_or_settlement_authority() -> None:
    source_path = (
        Path(__file__).parents[2]
        / "src/qore/infrastructure/event_contract_semantics.py"
    )
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_import_roots = {
        "asyncio",
        "httpx",
        "requests",
        "socket",
        "threading",
    }
    imported_names = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_modules = {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not (imported_names | imported_modules).intersection(
        forbidden_import_roots
    )

    forbidden_calls = {
        "adjudicate",
        "connect",
        "execute",
        "fetch",
        "observe",
        "resolve",
        "scrape",
        "settle",
        "submit",
    }
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not called_names.intersection(forbidden_calls)


@pytest.mark.parametrize(
    "forbidden",
    [
        "datetime.now(",
        "uuid4(",
        "time.time(",
        "random.",
        "resolved_outcome",
        "current_outcome",
        "current_probability",
        "provider_symbol",
        "api_key",
        "private_key",
    ],
)
def test_source_contains_no_current_or_secret_material(forbidden: str) -> None:
    source_path = (
        Path(__file__).parents[2]
        / "src/qore/infrastructure/event_contract_semantics.py"
    )
    assert forbidden not in source_path.read_text(encoding="utf-8")
