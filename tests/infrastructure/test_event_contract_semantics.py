from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, replace
from datetime import date, datetime
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import pytest

import qore.infrastructure.event_contract_semantics as s
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


def _outcome(code: str, amount: str, currency: int = 300) -> EventOutcomeTerms:
    return EventOutcomeTerms(EventOutcomeCode(code), _payout(amount, currency))


def _resolution(
    *,
    authority: int = 50,
    primary: tuple[EventResolutionSourceCode, ...] | None = None,
    fallback: tuple[EventResolutionSourceCode, ...] = (),
    rule: str = "official-final-publication",
    correction: str = "latest-authoritative-correction-before-cutoff",
    conflict: str = "primary-source-priority-order",
    scheduled: date | None = date(2026, 11, 4),
) -> EventResolutionTerms:
    return EventResolutionTerms(
        authority_ref=EventResolutionAuthorityRef(_uuid(authority)),
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


def _malformed(cls: type[Any], **attrs: object) -> Any:
    value = object.__new__(cls)
    for name, attr in attrs.items():
        object.__setattr__(value, name, attr)
    return value


class _BadDecimal(Decimal):
    pass


class _BadUUID(UUID):
    pass


class _IdentitySubclass(EconomicIdentityId):
    __slots__ = ()


class _OutcomeCodeSubclass(EventOutcomeCode):
    __slots__ = ()


class _PayoutSubclass(EventCashPayout):
    __slots__ = ()


class _ResolutionSubclass(EventResolutionTerms):
    __slots__ = ()


def _bad_identity() -> EconomicIdentityId:
    return EconomicIdentityId(cast(Any, _BadUUID(int=999)))


def test_uuid_wrappers_are_exact_and_deterministic() -> None:
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
    for factory in (
        EventContractTermsId,
        EventEvidenceRef,
        EventSubjectReferenceId,
        EventResolutionAuthorityRef,
    ):
        with pytest.raises(EventContractValidationError, match="exact UUID"):
            factory(cast(Any, str(_uuid(1))))
        with pytest.raises(EventContractValidationError, match="exact UUID"):
            factory(cast(Any, _BadUUID(int=1)))


def test_code_wrappers_are_exact_canonical_and_revalidated() -> None:
    factories = (
        EventCriterionCode,
        EventOutcomeStructureCode,
        EventOutcomeCode,
        EventResolutionSourceCode,
        EventResolutionRuleCode,
        EventCorrectionPolicyCode,
        EventSourceConflictPolicyCode,
    )
    for factory in factories:
        assert factory("official-source.v1").logical_values() == (
            "official-source.v1",
        )
        for invalid in ("", "UPPER", "bad code", "a" * 97, 7, True):
            with pytest.raises(EventContractValidationError):
                factory(cast(Any, invalid))

    value = EventCriterionCode("valid-code")
    object.__setattr__(value, "value", "INVALID CODE")
    with pytest.raises(EventContractValidationError, match="canonical lowercase"):
        value.logical_values()


def test_cash_payout_decimal_identity_and_resource_canonicalization() -> None:
    assert _payout("0.000").logical_values()[0] == "0"
    assert _payout("-0").logical_values()[0] == "0"
    assert _payout("1.2300").logical_values()[0] == "1.23"
    assert _payout("1000").logical_values()[0] == "1000"
    assert _payout("1E+20").logical_values()[0] == "1e+20"
    assert _payout("1E-20").logical_values()[0] == "1e-20"
    assert _payout("1E+1000000").logical_values()[0] == "1e+1000000"
    assert _payout("1E-1000000").logical_values()[0] == "1e-1000000"
    with localcontext() as context:
        context.prec = 2
        assert _payout("1.2300").logical_values()[0] == "1.23"
        assert _payout("1E+1000000").logical_values()[0] == "1e+1000000"

    for invalid in ("-0.01", "NaN", "Infinity", "-Infinity"):
        with pytest.raises(EventContractValidationError):
            EventCashPayout(Decimal(invalid), _identity(300))
    with pytest.raises(EventContractValidationError, match="exact Decimal"):
        EventCashPayout(cast(Any, 1.0), _identity(300))
    with pytest.raises(EventContractValidationError, match="exact Decimal"):
        EventCashPayout(cast(Any, _BadDecimal("1")), _identity(300))
    with pytest.raises(EventContractValidationError, match="exact EconomicIdentityId"):
        EventCashPayout(Decimal("1"), cast(Any, _uuid(300)))
    with pytest.raises(EventContractValidationError, match="exact EconomicIdentityId"):
        EventCashPayout(
            Decimal("1"),
            cast(Any, _IdentitySubclass(_uuid(300))),
        )
    with pytest.raises(EventContractValidationError, match="exact UUID"):
        EventCashPayout(Decimal("1"), _bad_identity())


def test_outcome_terms_exact_children_and_malformed_state() -> None:
    value = _outcome("yes", "1")
    assert value.logical_values() == (("yes",), _payout("1").logical_values())
    with pytest.raises(EventContractValidationError, match="exact EventOutcomeCode"):
        EventOutcomeTerms(cast(Any, "yes"), _payout("1"))
    with pytest.raises(EventContractValidationError, match="exact EventOutcomeCode"):
        EventOutcomeTerms(
            cast(Any, _OutcomeCodeSubclass("yes")),
            _payout("1"),
        )
    with pytest.raises(EventContractValidationError, match="exact EventCashPayout"):
        EventOutcomeTerms(EventOutcomeCode("yes"), cast(Any, Decimal("1")))
    with pytest.raises(EventContractValidationError, match="exact EventCashPayout"):
        EventOutcomeTerms(
            EventOutcomeCode("yes"),
            cast(Any, _PayoutSubclass(Decimal("1"), _identity(300))),
        )

    bad_code = _malformed(EventOutcomeCode, value="INVALID CODE")
    with pytest.raises(EventContractValidationError, match="canonical lowercase"):
        EventOutcomeTerms(bad_code, _payout("1"))
    bad_payout = _malformed(
        EventCashPayout,
        amount=Decimal("-1"),
        currency_identity_id=_identity(300),
    )
    with pytest.raises(EventContractValidationError, match="non-negative"):
        EventOutcomeTerms(EventOutcomeCode("yes"), bad_payout)


def test_resolution_source_order_is_material_and_validated() -> None:
    primary_ab = (
        EventResolutionSourceCode("source-a"),
        EventResolutionSourceCode("source-b"),
    )
    primary_ba = tuple(reversed(primary_ab))
    fallback = (
        EventResolutionSourceCode("fallback-a"),
        EventResolutionSourceCode("fallback-b"),
    )
    first = _resolution(primary=primary_ab, fallback=fallback)
    second = _resolution(primary=primary_ba, fallback=fallback)
    assert first.logical_values()[1] == (("source-a",), ("source-b",))
    assert first.logical_values()[2] == (("fallback-a",), ("fallback-b",))
    assert first.logical_values() != second.logical_values()

    invalid_primary: tuple[object, ...] = (
        (),
        [EventResolutionSourceCode("source-a")],
        (cast(Any, "source-a"),),
        (
            EventResolutionSourceCode("source-a"),
            EventResolutionSourceCode("source-a"),
        ),
    )
    for sources in invalid_primary:
        with pytest.raises(EventContractValidationError):
            _resolution(primary=cast(Any, sources))

    invalid_fallback: tuple[object, ...] = (
        [EventResolutionSourceCode("fallback-a")],
        (cast(Any, "fallback-a"),),
        (
            EventResolutionSourceCode("fallback-a"),
            EventResolutionSourceCode("fallback-a"),
        ),
    )
    for sources in invalid_fallback:
        with pytest.raises(EventContractValidationError):
            _resolution(fallback=cast(Any, sources))

    with pytest.raises(EventContractValidationError, match="disjoint"):
        _resolution(
            primary=(EventResolutionSourceCode("source-a"),),
            fallback=(EventResolutionSourceCode("source-a"),),
        )


def test_resolution_exact_children_malformed_and_optional_material() -> None:
    value = _resolution(fallback=(), scheduled=None)
    assert value.logical_values()[2] == ()
    assert value.logical_values()[-1] is None

    invalid: tuple[dict[str, object], ...] = (
        {"authority_ref": _uuid(50)},
        {"resolution_rule_code": "rule"},
        {"correction_policy_code": "policy"},
        {"source_conflict_policy_code": "conflict"},
        {"scheduled_resolution_date": "2026-11-04"},
    )
    for changes in invalid:
        with pytest.raises(EventContractValidationError):
            replace(_resolution(), **cast(Any, changes))

    bad_authority = _malformed(
        EventResolutionAuthorityRef,
        value=cast(Any, _BadUUID(int=50)),
    )
    with pytest.raises(EventContractValidationError, match="exact UUID"):
        replace(_resolution(), authority_ref=bad_authority)
    bad_source = _malformed(EventResolutionSourceCode, value="INVALID CODE")
    with pytest.raises(EventContractValidationError, match="canonical lowercase"):
        replace(_resolution(), primary_source_codes=(bad_source,))
    bad_rule = _malformed(EventResolutionRuleCode, value="INVALID CODE")
    with pytest.raises(EventContractValidationError, match="canonical lowercase"):
        replace(_resolution(), resolution_rule_code=bad_rule)
    bad_correction = _malformed(EventCorrectionPolicyCode, value="INVALID CODE")
    with pytest.raises(EventContractValidationError, match="canonical lowercase"):
        replace(_resolution(), correction_policy_code=bad_correction)
    bad_conflict = _malformed(EventSourceConflictPolicyCode, value="INVALID CODE")
    with pytest.raises(EventContractValidationError, match="canonical lowercase"):
        replace(_resolution(), source_conflict_policy_code=bad_conflict)


def test_resolution_dimensions_do_not_collapse() -> None:
    base = _resolution()
    variants = (
        _resolution(authority=51),
        _resolution(primary=(EventResolutionSourceCode("other-primary"),)),
        _resolution(fallback=(EventResolutionSourceCode("fallback-a"),)),
        _resolution(rule="exchange-rulebook-final"),
        _resolution(correction="ignore-post-cutoff-corrections"),
        _resolution(conflict="authority-discretion-on-conflict"),
        _resolution(scheduled=date(2026, 11, 5)),
        _resolution(scheduled=None),
    )
    assert len({base.logical_values(), *(item.logical_values() for item in variants)}) == 9


def test_outcome_order_is_non_economic_but_source_order_is_contractual() -> None:
    contract = _contract()
    reversed_outcomes = replace(contract, outcomes=tuple(reversed(contract.outcomes)))
    assert reversed_outcomes.outcomes == contract.outcomes
    assert reversed_outcomes.logical_values() == contract.logical_values()

    reversed_sources = replace(
        contract,
        resolution_terms=_resolution(
            primary=(
                EventResolutionSourceCode("agency-b-final"),
                EventResolutionSourceCode("agency-a-final"),
            )
        ),
    )
    assert reversed_sources.logical_values() != contract.logical_values()


def test_contract_complete_identity_and_noncollapse_oracles() -> None:
    contract = _contract()
    logical = contract.logical_values()
    assert logical[0] == "event-contract"
    assert logical[1] == (str(_uuid(100)),)
    assert logical[2] == (str(_uuid(10)),)
    assert logical[3] == (str(_uuid(20)),)
    assert logical[4] == ("candidate-a-wins-certified-election",)
    assert logical[5] == ("binary-yes-no",)
    assert logical[6] == (
        _outcome("no", "0").logical_values(),
        _outcome("yes", "1").logical_values(),
    )
    assert logical[7] == "2026-11-03"
    assert logical[8] == contract.resolution_terms.logical_values()
    assert logical[9] == (str(_uuid(200)),)

    variants = (
        replace(contract, terms_id=EventContractTermsId(_uuid(101))),
        replace(contract, instrument_identity_id=_identity(11)),
        replace(contract, subject_reference_id=EventSubjectReferenceId(_uuid(21))),
        replace(contract, criterion_code=EventCriterionCode("candidate-b-wins")),
        replace(
            contract,
            outcome_structure_code=EventOutcomeStructureCode("three-way"),
            outcomes=(
                _outcome("alpha", "1"),
                _outcome("beta", "0"),
                _outcome("gamma", "0"),
            ),
        ),
        replace(
            contract,
            outcomes=(_outcome("yes", "2"), _outcome("no", "0")),
        ),
        replace(
            contract,
            outcomes=(
                _outcome("yes", "1", 301),
                _outcome("no", "0", 300),
            ),
        ),
        replace(contract, expiration_date=date(2026, 11, 2)),
        replace(contract, expiration_date=None),
        replace(contract, resolution_terms=_resolution(authority=52)),
        replace(contract, evidence_ref=EventEvidenceRef(_uuid(201))),
    )
    assert len({contract.logical_values(), *(item.logical_values() for item in variants)}) == 12


def test_contract_outcome_guards_and_no_universal_payout_law() -> None:
    invalid_outcomes: tuple[object, ...] = (
        (),
        (_outcome("yes", "1"),),
        [_outcome("yes", "1"), _outcome("no", "0")],
        (_outcome("yes", "1"), cast(Any, "bad")),
    )
    for outcomes in invalid_outcomes:
        with pytest.raises(EventContractValidationError):
            replace(_contract(), outcomes=cast(Any, outcomes))

    with pytest.raises(EventContractValidationError, match="unique"):
        replace(
            _contract(),
            outcomes=(_outcome("yes", "1"), _outcome("yes", "0")),
        )

    unusual = replace(
        _contract(),
        outcomes=(
            _outcome("yes", "7", 300),
            _outcome("no", "2", 301),
        ),
    )
    assert {outcome.payout.amount for outcome in unusual.outcomes} == {
        Decimal("2"),
        Decimal("7"),
    }
    assert {outcome.payout.currency_identity_id.value for outcome in unusual.outcomes} == {
        _uuid(300),
        _uuid(301),
    }


def test_expiration_and_scheduled_resolution_are_independent_static_dates() -> None:
    base = _contract()
    before_expiration = replace(
        base,
        expiration_date=date(2026, 11, 5),
        resolution_terms=_resolution(scheduled=date(2026, 11, 4)),
    )
    equal = replace(
        base,
        expiration_date=date(2026, 11, 4),
        resolution_terms=_resolution(scheduled=date(2026, 11, 4)),
    )
    no_expiration = replace(base, expiration_date=None)
    no_schedule = replace(base, resolution_terms=_resolution(scheduled=None))
    assert before_expiration.expiration_date == date(2026, 11, 5)
    assert equal.expiration_date == equal.resolution_terms.scheduled_resolution_date
    assert no_expiration.logical_values()[7] is None
    assert no_schedule.resolution_terms.logical_values()[-1] is None

    with pytest.raises(EventContractValidationError, match="exact date"):
        replace(base, expiration_date=cast(Any, datetime(2026, 11, 3)))
    with pytest.raises(EventContractValidationError, match="exact date"):
        replace(
            base,
            resolution_terms=_resolution(
                scheduled=cast(Any, datetime(2026, 11, 4)),
            ),
        )


def test_contract_exact_parent_edges_and_subclass_rejection() -> None:
    contract = _contract()
    invalid: tuple[dict[str, object], ...] = (
        {"terms_id": _uuid(100)},
        {"instrument_identity_id": _uuid(10)},
        {"subject_reference_id": _uuid(20)},
        {"criterion_code": "criterion"},
        {"outcome_structure_code": "binary"},
        {"resolution_terms": "resolution"},
        {"evidence_ref": _uuid(200)},
    )
    for changes in invalid:
        with pytest.raises(EventContractValidationError):
            replace(contract, **cast(Any, changes))

    with pytest.raises(EventContractValidationError, match="exact EconomicIdentityId"):
        replace(
            contract,
            instrument_identity_id=cast(Any, _IdentitySubclass(_uuid(10))),
        )
    with pytest.raises(EventContractValidationError, match="exact EventResolutionTerms"):
        replace(
            contract,
            resolution_terms=cast(
                Any,
                _ResolutionSubclass(
                    authority_ref=EventResolutionAuthorityRef(_uuid(50)),
                    primary_source_codes=(EventResolutionSourceCode("source-a"),),
                    resolution_rule_code=EventResolutionRuleCode("rule-a"),
                    correction_policy_code=EventCorrectionPolicyCode("policy-a"),
                    source_conflict_policy_code=EventSourceConflictPolicyCode("conflict-a"),
                ),
            ),
        )


def test_malformed_parent_state_and_reflective_corruption_fail_closed() -> None:
    bad_terms_id = _malformed(EventContractTermsId, value=cast(Any, _BadUUID(int=100)))
    with pytest.raises(EventContractValidationError, match="exact UUID"):
        replace(_contract(), terms_id=bad_terms_id)

    bad_identity = _bad_identity()
    with pytest.raises(EventContractValidationError, match="exact UUID"):
        replace(_contract(), instrument_identity_id=bad_identity)

    bad_outcome = _malformed(
        EventOutcomeTerms,
        outcome_code=_malformed(EventOutcomeCode, value="INVALID CODE"),
        payout=_payout("1"),
    )
    with pytest.raises(EventContractValidationError, match="canonical lowercase"):
        replace(_contract(), outcomes=(bad_outcome, _outcome("no", "0")))

    contract = _contract()
    object.__setattr__(contract.criterion_code, "value", "INVALID CODE")
    with pytest.raises(EventContractValidationError, match="canonical lowercase"):
        contract.logical_values()

    contract = _contract()
    object.__setattr__(contract.outcomes[0].payout, "amount", Decimal("-1"))
    with pytest.raises(EventContractValidationError, match="non-negative"):
        contract.logical_values()

    contract = _contract()
    object.__setattr__(
        contract.resolution_terms.primary_source_codes[0],
        "value",
        "INVALID CODE",
    )
    with pytest.raises(EventContractValidationError, match="canonical lowercase"):
        contract.logical_values()

    contract = _contract()
    object.__setattr__(
        contract.resolution_terms,
        "scheduled_resolution_date",
        cast(Any, "bad-date"),
    )
    with pytest.raises(EventContractValidationError, match="exact date"):
        contract.logical_values()


def test_values_are_frozen_slotted_and_repeatable() -> None:
    values: tuple[object, ...] = (
        EventContractTermsId(_uuid(1)),
        EventEvidenceRef(_uuid(2)),
        EventSubjectReferenceId(_uuid(3)),
        EventResolutionAuthorityRef(_uuid(4)),
        EventCriterionCode("criterion-a"),
        EventOutcomeStructureCode("binary"),
        EventOutcomeCode("yes"),
        EventResolutionSourceCode("source-a"),
        EventResolutionRuleCode("rule-a"),
        EventCorrectionPolicyCode("policy-a"),
        EventSourceConflictPolicyCode("conflict-a"),
        _payout("1"),
        _outcome("yes", "1"),
        _resolution(),
        _contract(),
    )
    assert all(not hasattr(value, "__dict__") for value in values)
    assert all(
        cast(Any, value).logical_values() == cast(Any, value).logical_values()
        for value in values
    )
    with pytest.raises(FrozenInstanceError):
        cast(Any, values[6]).value = "no"


def test_top_level_negative_space_and_source_guards() -> None:
    forbidden_fields = {
        "resolved_outcome",
        "current_outcome",
        "resolution_timestamp",
        "current_probability",
        "market_price",
        "provider_symbol",
        "settled",
        "position",
        "valuation",
    }
    assert not {field.name for field in fields(EventContractTerms)}.intersection(
        forbidden_fields
    )

    source_path = Path(s.__file__)
    source = source_path.read_text()
    assert "isinstance(" not in source
    assert ".normalize(" not in source
    assert "datetime.now(" not in source
    assert "date.today(" not in source
    assert "uuid4(" not in source
    assert "random." not in source
    assert "secrets." not in source

    tree = ast.parse(source)
    forbidden_imports = {
        "asyncio",
        "httpx",
        "numpy",
        "pandas",
        "requests",
        "socket",
        "subprocess",
        "threading",
    }
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not imported.intersection(forbidden_imports)

    forbidden_calls = {
        "calculate",
        "connect",
        "execute",
        "fetch",
        "observe",
        "resolve",
        "settle",
        "submit",
        "transfer",
    }
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not calls.intersection(forbidden_calls)
