from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import pytest

from qore.infrastructure.crypto_perpetual_funding_semantics import (
    CryptoEvidenceRef,
    CryptoNetworkBindingRoleCode,
    CryptoNetworkBindingTerms,
    CryptoTermsId,
)
from qore.infrastructure.crypto_staking_tokenization_semantics import (
    CryptoRepresentationBinding,
    CryptoRepresentationRoleCode,
    CryptoStakingExitMode,
    CryptoStakingExitScheduleCode,
    CryptoStakingExitTerms,
    CryptoStakingModeCode,
    CryptoStakingPenaltyPolicyCode,
    CryptoStakingTerms,
    CryptoStakingTokenizationValidationError,
    CryptoTokenizedSecurityForm,
    CryptoTokenizedSecurityQualificationTerms,
    CryptoYieldBearingTokenTerms,
    CryptoYieldMechanismCode,
)
from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentityId,
    IdentityEvidenceRef,
    IdentityRelationship,
    IdentityRelationshipCode,
    IdentityRelationshipId,
)


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _identity(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(value))


def _crypto_evidence(value: int = 100) -> CryptoEvidenceRef:
    return CryptoEvidenceRef(_uuid(value))


def _relationship(
    *,
    source: EconomicIdentityId,
    target: EconomicIdentityId,
    code: str,
    value: int = 200,
) -> IdentityRelationship:
    return IdentityRelationship(
        relationship_id=IdentityRelationshipId(_uuid(value)),
        source_identity_id=source,
        target_identity_id=target,
        relationship=IdentityRelationshipCode(code),
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
        effective_until=None,
        evidence_ref=IdentityEvidenceRef(_uuid(value + 1)),
    )


def _binding(
    *,
    source: EconomicIdentityId,
    target: EconomicIdentityId,
    code: str,
    value: int = 200,
) -> CryptoRepresentationBinding:
    return CryptoRepresentationBinding(
        relationship=_relationship(
            source=source,
            target=target,
            code=code,
            value=value,
        ),
        role=CryptoRepresentationRoleCode(code),
        evidence_ref=_crypto_evidence(value + 2),
    )


def _network_binding(value: int = 300) -> CryptoNetworkBindingTerms:
    return CryptoNetworkBindingTerms(
        terms_id=CryptoTermsId(_uuid(value)),
        relationship_id=IdentityRelationshipId(_uuid(value + 1)),
        role=CryptoNetworkBindingRoleCode("native-network"),
        evidence_ref=_crypto_evidence(value + 2),
    )


def test_code_wrappers_are_canonical_and_deterministic() -> None:
    values = (
        CryptoStakingModeCode("delegated-staking"),
        CryptoStakingExitScheduleCode("protocol-exit-v1"),
        CryptoStakingPenaltyPolicyCode("protocol-slashing"),
        CryptoYieldMechanismCode("vault-share-exchange-rate"),
        CryptoRepresentationRoleCode("yield-bearing-representation-of"),
    )
    assert [value.logical_values() for value in values] == [
        ("delegated-staking",),
        ("protocol-exit-v1",),
        ("protocol-slashing",),
        ("vault-share-exchange-rate",),
        ("yield-bearing-representation-of",),
    ]


@pytest.mark.parametrize(
    "factory",
    [
        CryptoStakingModeCode,
        CryptoStakingExitScheduleCode,
        CryptoStakingPenaltyPolicyCode,
        CryptoYieldMechanismCode,
        CryptoRepresentationRoleCode,
    ],
)
@pytest.mark.parametrize("value", ["", "Bad Code", "UPPER", "a" * 65, 7])
def test_code_wrappers_fail_closed(factory: Any, value: object) -> None:
    with pytest.raises(CryptoStakingTokenizationValidationError):
        factory(cast(Any, value))


@pytest.mark.parametrize(
    ("terms", "expected"),
    [
        (
            CryptoStakingExitTerms(CryptoStakingExitMode.IMMEDIATE),
            ("immediate", None, None),
        ),
        (
            CryptoStakingExitTerms(
                CryptoStakingExitMode.FIXED_DELAY,
                fixed_delay_seconds=86_400,
            ),
            ("fixed-delay", 86_400, None),
        ),
        (
            CryptoStakingExitTerms(
                CryptoStakingExitMode.GOVERNED_SCHEDULE,
                schedule_code=CryptoStakingExitScheduleCode("exit-window-v1"),
            ),
            ("governed-schedule", None, ("exit-window-v1",)),
        ),
        (
            CryptoStakingExitTerms(CryptoStakingExitMode.NETWORK_GOVERNED),
            ("network-governed", None, None),
        ),
    ],
)
def test_exit_modes_preserve_distinct_static_contracts(
    terms: CryptoStakingExitTerms,
    expected: tuple[object, ...],
) -> None:
    assert terms.logical_values() == expected


@pytest.mark.parametrize("seconds", [None, 0, -1, True])
def test_fixed_delay_requires_strict_positive_int(seconds: object) -> None:
    with pytest.raises(CryptoStakingTokenizationValidationError):
        CryptoStakingExitTerms(
            CryptoStakingExitMode.FIXED_DELAY,
            fixed_delay_seconds=cast(Any, seconds),
        )


def test_fixed_delay_forbids_schedule_laundering() -> None:
    with pytest.raises(CryptoStakingTokenizationValidationError):
        CryptoStakingExitTerms(
            CryptoStakingExitMode.FIXED_DELAY,
            fixed_delay_seconds=1,
            schedule_code=CryptoStakingExitScheduleCode("extra-schedule"),
        )


def test_governed_schedule_requires_typed_schedule_only() -> None:
    with pytest.raises(CryptoStakingTokenizationValidationError):
        CryptoStakingExitTerms(CryptoStakingExitMode.GOVERNED_SCHEDULE)
    with pytest.raises(CryptoStakingTokenizationValidationError):
        CryptoStakingExitTerms(
            CryptoStakingExitMode.GOVERNED_SCHEDULE,
            schedule_code=cast(Any, "raw-schedule"),
        )
    with pytest.raises(CryptoStakingTokenizationValidationError):
        CryptoStakingExitTerms(
            CryptoStakingExitMode.GOVERNED_SCHEDULE,
            fixed_delay_seconds=1,
            schedule_code=CryptoStakingExitScheduleCode("schedule-v1"),
        )


@pytest.mark.parametrize(
    "mode",
    [CryptoStakingExitMode.IMMEDIATE, CryptoStakingExitMode.NETWORK_GOVERNED],
)
def test_non_timed_exit_modes_reject_invented_timing(
    mode: CryptoStakingExitMode,
) -> None:
    with pytest.raises(CryptoStakingTokenizationValidationError):
        CryptoStakingExitTerms(mode, fixed_delay_seconds=1)
    with pytest.raises(CryptoStakingTokenizationValidationError):
        CryptoStakingExitTerms(
            mode,
            schedule_code=CryptoStakingExitScheduleCode("invented"),
        )


def test_exit_mode_rejects_raw_string() -> None:
    with pytest.raises(CryptoStakingTokenizationValidationError):
        CryptoStakingExitTerms(cast(Any, "immediate"))


def test_representation_binding_retains_exact_umi02_relationship() -> None:
    token = _identity(1)
    underlying = _identity(2)
    binding = _binding(
        source=token,
        target=underlying,
        code="yield-bearing-representation-of",
    )
    assert binding.relationship.source_identity_id == token
    assert binding.relationship.target_identity_id == underlying
    assert binding.logical_values()[0] == binding.relationship.logical_values()


def test_representation_role_must_match_exact_relationship_code() -> None:
    relationship = _relationship(
        source=_identity(1),
        target=_identity(2),
        code="staking-receipt-for",
    )
    with pytest.raises(CryptoStakingTokenizationValidationError):
        CryptoRepresentationBinding(
            relationship=relationship,
            role=CryptoRepresentationRoleCode("different-role"),
            evidence_ref=_crypto_evidence(),
        )


def test_staking_preserves_reward_identity_and_network_governed_exit() -> None:
    eth = _identity(10)
    terms = CryptoStakingTerms(
        terms_id=CryptoTermsId(_uuid(11)),
        staked_asset_identity_id=eth,
        reward_asset_identity_id=eth,
        mode=CryptoStakingModeCode("native-validator"),
        exit_terms=CryptoStakingExitTerms(
            CryptoStakingExitMode.NETWORK_GOVERNED
        ),
        penalty_policy_code=CryptoStakingPenaltyPolicyCode("protocol-slashing"),
        network_binding=_network_binding(),
        evidence_ref=_crypto_evidence(12),
    )
    assert terms.staked_asset_identity_id == terms.reward_asset_identity_id
    assert terms.logical_values()[0] == "crypto-staking"
    assert "network-governed" in repr(terms.logical_values())


def test_liquid_staking_receipt_is_exact_relationship_binding() -> None:
    receipt = _identity(20)
    staked = _identity(21)
    terms = CryptoStakingTerms(
        terms_id=CryptoTermsId(_uuid(22)),
        staked_asset_identity_id=staked,
        reward_asset_identity_id=staked,
        mode=CryptoStakingModeCode("pooled-liquid-staking"),
        exit_terms=CryptoStakingExitTerms(CryptoStakingExitMode.IMMEDIATE),
        receipt_binding=_binding(
            source=receipt,
            target=staked,
            code="staking-receipt-for",
            value=220,
        ),
        evidence_ref=_crypto_evidence(23),
    )
    assert terms.receipt_binding is not None
    assert terms.receipt_binding.relationship.source_identity_id == receipt


def test_staking_receipt_must_target_staked_asset() -> None:
    with pytest.raises(CryptoStakingTokenizationValidationError):
        CryptoStakingTerms(
            terms_id=CryptoTermsId(_uuid(30)),
            staked_asset_identity_id=_identity(31),
            reward_asset_identity_id=_identity(31),
            mode=CryptoStakingModeCode("pooled"),
            exit_terms=CryptoStakingExitTerms(CryptoStakingExitMode.IMMEDIATE),
            receipt_binding=_binding(
                source=_identity(32),
                target=_identity(33),
                code="staking-receipt-for",
                value=230,
            ),
            evidence_ref=_crypto_evidence(34),
        )


def test_staking_wrong_wrappers_fail_closed() -> None:
    base = CryptoStakingTerms(
        terms_id=CryptoTermsId(_uuid(40)),
        staked_asset_identity_id=_identity(41),
        reward_asset_identity_id=_identity(42),
        mode=CryptoStakingModeCode("delegated"),
        exit_terms=CryptoStakingExitTerms(CryptoStakingExitMode.IMMEDIATE),
        evidence_ref=_crypto_evidence(43),
    )
    invalid = (
        {"terms_id": cast(Any, _uuid(40))},
        {"staked_asset_identity_id": cast(Any, _uuid(41))},
        {"reward_asset_identity_id": cast(Any, _uuid(42))},
        {"mode": cast(Any, "delegated")},
        {"exit_terms": cast(Any, "immediate")},
        {"evidence_ref": cast(Any, _uuid(43))},
        {"penalty_policy_code": cast(Any, "slashing")},
        {"receipt_binding": cast(Any, "receipt")},
        {"network_binding": cast(Any, "network")},
    )
    for changes in invalid:
        with pytest.raises(CryptoStakingTokenizationValidationError):
            replace(base, **changes)


def test_yield_bearing_token_preserves_token_underlying_and_mechanism() -> None:
    token = _identity(50)
    underlying = _identity(51)
    terms = CryptoYieldBearingTokenTerms(
        terms_id=CryptoTermsId(_uuid(52)),
        token_identity_id=token,
        underlying_identity_id=underlying,
        representation_binding=_binding(
            source=token,
            target=underlying,
            code="yield-bearing-representation-of",
            value=250,
        ),
        yield_mechanism=CryptoYieldMechanismCode("vault-share-exchange-rate"),
        network_binding=_network_binding(350),
        evidence_ref=_crypto_evidence(53),
    )
    logical = terms.logical_values()
    assert logical[0] == "crypto-yield-bearing-token"
    assert ("vault-share-exchange-rate",) in logical
    assert all(not isinstance(item, float) for item in logical)


def test_yield_token_must_differ_from_underlying() -> None:
    identity = _identity(60)
    with pytest.raises(CryptoStakingTokenizationValidationError):
        CryptoYieldBearingTokenTerms(
            terms_id=CryptoTermsId(_uuid(61)),
            token_identity_id=identity,
            underlying_identity_id=identity,
            representation_binding=_binding(
                source=_identity(62),
                target=identity,
                code="yield-bearing-representation-of",
                value=260,
            ),
            yield_mechanism=CryptoYieldMechanismCode("rebasing"),
            evidence_ref=_crypto_evidence(63),
        )


@pytest.mark.parametrize("wrong_endpoint", ["source", "target"])
def test_yield_binding_endpoints_fail_closed(wrong_endpoint: str) -> None:
    token = _identity(70)
    underlying = _identity(71)
    source = _identity(72) if wrong_endpoint == "source" else token
    target = _identity(73) if wrong_endpoint == "target" else underlying
    with pytest.raises(CryptoStakingTokenizationValidationError):
        CryptoYieldBearingTokenTerms(
            terms_id=CryptoTermsId(_uuid(74)),
            token_identity_id=token,
            underlying_identity_id=underlying,
            representation_binding=_binding(
                source=source,
                target=target,
                code="yield-bearing-representation-of",
                value=270,
            ),
            yield_mechanism=CryptoYieldMechanismCode("distribution"),
            evidence_ref=_crypto_evidence(75),
        )


def test_yield_wrong_wrappers_fail_closed() -> None:
    token = _identity(80)
    underlying = _identity(81)
    base = CryptoYieldBearingTokenTerms(
        terms_id=CryptoTermsId(_uuid(82)),
        token_identity_id=token,
        underlying_identity_id=underlying,
        representation_binding=_binding(
            source=token,
            target=underlying,
            code="yield-bearing-representation-of",
            value=280,
        ),
        yield_mechanism=CryptoYieldMechanismCode("distribution"),
        evidence_ref=_crypto_evidence(83),
    )
    invalid = (
        {"terms_id": cast(Any, _uuid(82))},
        {"token_identity_id": cast(Any, _uuid(80))},
        {"underlying_identity_id": cast(Any, _uuid(81))},
        {"representation_binding": cast(Any, "binding")},
        {"yield_mechanism": cast(Any, "distribution")},
        {"evidence_ref": cast(Any, _uuid(83))},
        {"network_binding": cast(Any, "network")},
    )
    for changes in invalid:
        with pytest.raises(CryptoStakingTokenizationValidationError):
            replace(base, **changes)


def test_native_onchain_security_has_no_fake_represented_underlying() -> None:
    terms = CryptoTokenizedSecurityQualificationTerms(
        terms_id=CryptoTermsId(_uuid(90)),
        token_security_identity_id=_identity(91),
        form=CryptoTokenizedSecurityForm.NATIVE_ONCHAIN_ISSUANCE,
        network_binding=_network_binding(390),
        evidence_ref=_crypto_evidence(92),
    )
    assert terms.underlying_security_identity_id is None
    assert terms.representation_binding is None
    assert terms.logical_values()[3] == "native-onchain-issuance"


def test_native_onchain_security_rejects_fake_underlying() -> None:
    token = _identity(100)
    underlying = _identity(101)
    with pytest.raises(CryptoStakingTokenizationValidationError):
        CryptoTokenizedSecurityQualificationTerms(
            terms_id=CryptoTermsId(_uuid(102)),
            token_security_identity_id=token,
            form=CryptoTokenizedSecurityForm.NATIVE_ONCHAIN_ISSUANCE,
            underlying_security_identity_id=underlying,
            representation_binding=_binding(
                source=token,
                target=underlying,
                code="tokenized-representation-of",
                value=400,
            ),
            evidence_ref=_crypto_evidence(103),
        )


def test_tokenized_representation_requires_exact_underlying_binding() -> None:
    token = _identity(110)
    security = _identity(111)
    terms = CryptoTokenizedSecurityQualificationTerms(
        terms_id=CryptoTermsId(_uuid(112)),
        token_security_identity_id=token,
        form=CryptoTokenizedSecurityForm.TOKENIZED_REPRESENTATION,
        underlying_security_identity_id=security,
        representation_binding=_binding(
            source=token,
            target=security,
            code="tokenized-representation-of",
            value=410,
        ),
        evidence_ref=_crypto_evidence(113),
    )
    assert terms.logical_values()[3] == "tokenized-representation"
    assert terms.underlying_security_identity_id == security


@pytest.mark.parametrize("missing", ["underlying", "binding"])
def test_tokenized_representation_requires_both_materials(missing: str) -> None:
    token = _identity(120)
    security = _identity(121)
    binding = _binding(
        source=token,
        target=security,
        code="tokenized-representation-of",
        value=420,
    )
    kwargs: dict[str, Any] = {
        "terms_id": CryptoTermsId(_uuid(122)),
        "token_security_identity_id": token,
        "form": CryptoTokenizedSecurityForm.TOKENIZED_REPRESENTATION,
        "underlying_security_identity_id": security,
        "representation_binding": binding,
        "evidence_ref": _crypto_evidence(123),
    }
    if missing == "underlying":
        kwargs["underlying_security_identity_id"] = None
    else:
        kwargs["representation_binding"] = None
    with pytest.raises(CryptoStakingTokenizationValidationError):
        CryptoTokenizedSecurityQualificationTerms(**kwargs)


def test_tokenized_representation_rejects_self_underlying() -> None:
    token = _identity(130)
    other = _identity(131)
    with pytest.raises(CryptoStakingTokenizationValidationError):
        CryptoTokenizedSecurityQualificationTerms(
            terms_id=CryptoTermsId(_uuid(132)),
            token_security_identity_id=token,
            form=CryptoTokenizedSecurityForm.TOKENIZED_REPRESENTATION,
            underlying_security_identity_id=token,
            representation_binding=_binding(
                source=token,
                target=other,
                code="tokenized-representation-of",
                value=430,
            ),
            evidence_ref=_crypto_evidence(133),
        )


@pytest.mark.parametrize("wrong_endpoint", ["source", "target"])
def test_tokenized_security_binding_endpoints_fail_closed(
    wrong_endpoint: str,
) -> None:
    token = _identity(140)
    security = _identity(141)
    source = _identity(142) if wrong_endpoint == "source" else token
    target = _identity(143) if wrong_endpoint == "target" else security
    with pytest.raises(CryptoStakingTokenizationValidationError):
        CryptoTokenizedSecurityQualificationTerms(
            terms_id=CryptoTermsId(_uuid(144)),
            token_security_identity_id=token,
            form=CryptoTokenizedSecurityForm.TOKENIZED_REPRESENTATION,
            underlying_security_identity_id=security,
            representation_binding=_binding(
                source=source,
                target=target,
                code="tokenized-representation-of",
                value=440,
            ),
            evidence_ref=_crypto_evidence(145),
        )


def test_tokenized_security_rejects_raw_form_and_network() -> None:
    native = CryptoTokenizedSecurityQualificationTerms(
        terms_id=CryptoTermsId(_uuid(150)),
        token_security_identity_id=_identity(151),
        form=CryptoTokenizedSecurityForm.NATIVE_ONCHAIN_ISSUANCE,
        evidence_ref=_crypto_evidence(152),
    )
    with pytest.raises(CryptoStakingTokenizationValidationError):
        replace(native, form=cast(Any, "native-onchain-issuance"))
    with pytest.raises(CryptoStakingTokenizationValidationError):
        replace(native, network_binding=cast(Any, "network"))


def test_values_are_frozen() -> None:
    value = CryptoStakingModeCode("native-validator")
    with pytest.raises(FrozenInstanceError):
        value.__setattr__("value", "mutated")


def test_logical_values_are_repeatable() -> None:
    token = _identity(160)
    underlying = _identity(161)
    value = CryptoYieldBearingTokenTerms(
        terms_id=CryptoTermsId(_uuid(162)),
        token_identity_id=token,
        underlying_identity_id=underlying,
        representation_binding=_binding(
            source=token,
            target=underlying,
            code="yield-bearing-representation-of",
            value=460,
        ),
        yield_mechanism=CryptoYieldMechanismCode("rebasing"),
        evidence_ref=_crypto_evidence(163),
    )
    assert value.logical_values() == value.logical_values()


def test_source_has_no_forbidden_runtime_authority() -> None:
    source_path = (
        Path(__file__).parents[2]
        / "src/qore/infrastructure/crypto_staking_tokenization_semantics.py"
    )
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_import_roots = {
        "asyncio",
        "httpx",
        "requests",
        "socket",
        "threading",
        "web3",
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
        "calculate",
        "connect",
        "deposit",
        "execute",
        "fetch",
        "observe",
        "send",
        "settle",
        "sign",
        "submit",
        "withdraw",
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
        "private_key",
        "secret_key",
        "current_apr",
        "current_balance",
        "exchange_rate: Decimal",
    ],
)
def test_source_contains_no_hidden_current_or_secret_material(
    forbidden: str,
) -> None:
    source_path = (
        Path(__file__).parents[2]
        / "src/qore/infrastructure/crypto_staking_tokenization_semantics.py"
    )
    assert forbidden not in source_path.read_text(encoding="utf-8")
