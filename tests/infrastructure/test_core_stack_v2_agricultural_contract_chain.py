from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.commodity_contract_delivery_semantics import (
    CommodityClassCode,
    CommodityEvidenceRef,
    CommodityFuturesContractTerms,
    CommodityReferenceTerms,
    CommodityTermsId,
)
from qore.infrastructure.core_stack_v2.agricultural_contract_chain import (
    AgriculturalActiveContractSelection,
    AgriculturalContractChain,
    AgriculturalContractChainError,
    AgriculturalRollPolicy,
    CommodityRollState,
    ContractLiquiditySignal,
    assert_roll_safe_single_series_structural_claim,
    assess_agricultural_roll_state,
)
from qore.infrastructure.core_stack_v2.agricultural_instrument_identity import (
    AgriculturalCommodityClass,
    AgriculturalCommodityReferenceQualification,
    AgriculturalFuturesContractQualification,
)
from qore.infrastructure.derivative_contract_semantics import (
    DerivativeContractMonth,
    DerivativeContractMultiplier,
    DerivativeEvidenceRef,
    DerivativeSettlementStyle,
    DerivativeTermsId,
    FuturesContractTerms,
)
from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentity,
    EconomicIdentityId,
    EconomicIdentityKind,
    IdentityConstructionKind,
    IdentityEvidenceRef,
    IdentityFamilyCode,
    ListingIdentity,
    ListingIdentityId,
    MarketVenueCode,
)

REF_ID = EconomicIdentityId(UUID("10000000-0000-4000-8000-000000000001"))
REF2_ID = EconomicIdentityId(UUID("10000000-0000-4000-8000-000000000002"))
UNIT_ID = EconomicIdentityId(UUID("10000000-0000-4000-8000-000000000003"))
USD_ID = EconomicIdentityId(UUID("10000000-0000-4000-8000-000000000004"))
JUL_ID = EconomicIdentityId(UUID("10000000-0000-4000-8000-000000000011"))
SEP_ID = EconomicIdentityId(UUID("10000000-0000-4000-8000-000000000012"))
NOV_ID = EconomicIdentityId(UUID("10000000-0000-4000-8000-000000000013"))
ID_EVIDENCE = IdentityEvidenceRef(
    UUID("10000000-0000-4000-8000-000000000021")
)
COMM_EVIDENCE = CommodityEvidenceRef(
    UUID("10000000-0000-4000-8000-000000000031")
)
DERIV_EVIDENCE = DerivativeEvidenceRef(
    UUID("10000000-0000-4000-8000-000000000041")
)

NOW = datetime(2027, 6, 1, 15, 0, tzinfo=UTC)


def _reference(
    reference_id: EconomicIdentityId = REF_ID,
) -> AgriculturalCommodityReferenceQualification:
    identity = EconomicIdentity(
        identity_id=reference_id,
        kind=EconomicIdentityKind.REFERENCE_OBJECT,
        family=IdentityFamilyCode("commodities"),
        construction=IdentityConstructionKind.NATIVE,
        evidence_ref=ID_EVIDENCE,
    )
    terms = CommodityReferenceTerms(
        terms_id=CommodityTermsId(
            UUID("10000000-0000-4000-8000-000000000051")
        ),
        reference_identity_id=reference_id,
        commodity_class=CommodityClassCode("agriculture"),
        measurement_unit_identity_id=UNIT_ID,
        evidence_ref=COMM_EVIDENCE,
    )
    return AgriculturalCommodityReferenceQualification(
        economic_identity=identity,
        commodity_reference=terms,
        agricultural_class=AgriculturalCommodityClass.AGRICULTURE,
    )


def _contract(
    *,
    identity_id: EconomicIdentityId,
    year: int,
    month: int,
    last_trade: date,
    reference: AgriculturalCommodityReferenceQualification | None = None,
    listing_uuid: str,
    derivative_uuid: str,
    commodity_uuid: str,
) -> AgriculturalFuturesContractQualification:
    agricultural_reference = reference or _reference()
    identity = EconomicIdentity(
        identity_id=identity_id,
        kind=EconomicIdentityKind.TRADABLE_INSTRUMENT,
        family=IdentityFamilyCode("futures"),
        construction=IdentityConstructionKind.NATIVE,
        evidence_ref=ID_EVIDENCE,
    )
    listing = ListingIdentity(
        listing_id=ListingIdentityId(UUID(listing_uuid)),
        economic_identity_id=identity_id,
        venue=MarketVenueCode("xcme"),
        display_symbol=f"TEST-{year}-{month:02d}",
        valid_from=datetime(2026, 1, 1, tzinfo=UTC),
        valid_until=None,
        evidence_ref=ID_EVIDENCE,
    )
    futures = FuturesContractTerms(
        terms_id=DerivativeTermsId(UUID(derivative_uuid)),
        instrument_identity_id=identity_id,
        reference_identity_id=(
            agricultural_reference.economic_identity.identity_id
        ),
        settlement_identity_id=USD_ID,
        contract_month=DerivativeContractMonth(year=year, month=month),
        expiry_date=last_trade,
        multiplier=DerivativeContractMultiplier(
            value=Decimal("5000"),
            unit_identity_id=UNIT_ID,
        ),
        settlement_style=DerivativeSettlementStyle.CASH,
        evidence_ref=DERIV_EVIDENCE,
        tick_value=None,
        first_notice_date=None,
        last_trade_date=last_trade,
    )
    commodity_contract = CommodityFuturesContractTerms(
        terms_id=CommodityTermsId(UUID(commodity_uuid)),
        futures=futures,
        commodity_reference=agricultural_reference.commodity_reference,
        evidence_ref=COMM_EVIDENCE,
        physical_delivery=None,
    )
    return AgriculturalFuturesContractQualification(
        economic_identity=identity,
        listing=listing,
        agricultural_reference=agricultural_reference,
        commodity_contract=commodity_contract,
    )


def _jul() -> AgriculturalFuturesContractQualification:
    return _contract(
        identity_id=JUL_ID,
        year=2027,
        month=7,
        last_trade=date(2027, 7, 14),
        listing_uuid="10000000-0000-4000-8000-000000000061",
        derivative_uuid="10000000-0000-4000-8000-000000000071",
        commodity_uuid="10000000-0000-4000-8000-000000000081",
    )


def _sep() -> AgriculturalFuturesContractQualification:
    return _contract(
        identity_id=SEP_ID,
        year=2027,
        month=9,
        last_trade=date(2027, 9, 14),
        listing_uuid="10000000-0000-4000-8000-000000000062",
        derivative_uuid="10000000-0000-4000-8000-000000000072",
        commodity_uuid="10000000-0000-4000-8000-000000000082",
    )


def _nov(
    *,
    reference: AgriculturalCommodityReferenceQualification | None = None,
) -> AgriculturalFuturesContractQualification:
    return _contract(
        identity_id=NOV_ID,
        year=2027,
        month=11,
        last_trade=date(2027, 11, 14),
        reference=reference,
        listing_uuid="10000000-0000-4000-8000-000000000063",
        derivative_uuid="10000000-0000-4000-8000-000000000073",
        commodity_uuid="10000000-0000-4000-8000-000000000083",
    )


def _chain() -> AgriculturalContractChain:
    return AgriculturalContractChain(
        chain_id="agri:test:corn",
        reference_identity_id=REF_ID,
        contracts=(_jul(), _sep(), _nov()),
        provenance_refs=("chain:test",),
    )


def _signal(
    contract_id: EconomicIdentityId,
    *,
    volume_rank: int,
    open_interest_rank: int,
    volume_change_bps: int | None = 0,
    open_interest_change_bps: int | None = 0,
    observed_at: datetime = NOW,
) -> ContractLiquiditySignal:
    return ContractLiquiditySignal(
        contract_identity_id=contract_id,
        observed_at=observed_at,
        evidence_cutoff_at=observed_at,
        volume_rank=volume_rank,
        open_interest_rank=open_interest_rank,
        volume_change_bps=volume_change_bps,
        open_interest_change_bps=open_interest_change_bps,
        provenance_refs=(f"liquidity:{contract_id.value}",),
    )


def _policy() -> AgriculturalRollPolicy:
    return AgriculturalRollPolicy(
        version="roll-test-001",
        roll_window_days=10,
        delivery_proximity_days=3,
        front_decay_threshold_bps=2000,
        provenance_refs=("policy:exchange-research:test",),
    )


def test_contract_chain_is_ordered_and_deterministic() -> None:
    chain = _chain()

    assert tuple(
        (item.contract_year, item.contract_month)
        for item in chain.contracts
    ) == ((2027, 7), (2027, 9), (2027, 11))
    assert len(chain.fingerprint()) == 64


def test_contract_chain_rejects_wrong_underlying_reference() -> None:
    other_reference = _reference(REF2_ID)
    wrong = _nov(reference=other_reference)

    with pytest.raises(
        AgriculturalContractChainError,
        match="cannot mix agricultural references",
    ):
        AgriculturalContractChain(
            chain_id="agri:test:mixed",
            reference_identity_id=REF_ID,
            contracts=(_jul(), _sep(), wrong),
            provenance_refs=("chain:test",),
        )


def test_contract_chain_rejects_duplicate_contract_month() -> None:
    duplicate = _contract(
        identity_id=NOV_ID,
        year=2027,
        month=9,
        last_trade=date(2027, 9, 20),
        listing_uuid="10000000-0000-4000-8000-000000000064",
        derivative_uuid="10000000-0000-4000-8000-000000000074",
        commodity_uuid="10000000-0000-4000-8000-000000000084",
    )

    with pytest.raises(
        AgriculturalContractChainError,
        match="duplicate contract months",
    ):
        AgriculturalContractChain(
            chain_id="agri:test:duplicate-month",
            reference_identity_id=REF_ID,
            contracts=(_jul(), _sep(), duplicate),
            provenance_refs=("chain:test",),
        )


def test_roll_policy_has_no_hidden_default_thresholds() -> None:
    policy = _policy()

    assert policy.roll_window_days == 10
    assert policy.delivery_proximity_days == 3
    assert policy.front_decay_threshold_bps == 2000
    assert len(policy.fingerprint()) == 64


def test_stable_front_contract_requires_volume_and_open_interest_agreement() -> None:
    assessment = assess_agricultural_roll_state(
        chain=_chain(),
        signals=(
            _signal(JUL_ID, volume_rank=1, open_interest_rank=1),
            _signal(SEP_ID, volume_rank=2, open_interest_rank=2),
        ),
        evaluation_at=NOW,
        policy=_policy(),
    )

    assert assessment.state is CommodityRollState.STABLE_FRONT_CONTRACT
    assert assessment.front_contract_id == JUL_ID
    assert assessment.most_liquid_contract_id == JUL_ID
    assert assessment.relational_claims_authorized is False
    assert assessment.execution_authority is False


def test_split_liquidity_rank_is_insufficient_not_guessed() -> None:
    assessment = assess_agricultural_roll_state(
        chain=_chain(),
        signals=(
            _signal(JUL_ID, volume_rank=1, open_interest_rank=2),
            _signal(SEP_ID, volume_rank=2, open_interest_rank=1),
        ),
        evaluation_at=NOW,
        policy=_policy(),
    )

    assert assessment.state is CommodityRollState.INSUFFICIENT
    assert assessment.most_liquid_contract_id is None


def test_next_contract_dominance_is_liquidity_migration() -> None:
    assessment = assess_agricultural_roll_state(
        chain=_chain(),
        signals=(
            _signal(JUL_ID, volume_rank=2, open_interest_rank=2),
            _signal(SEP_ID, volume_rank=1, open_interest_rank=1),
        ),
        evaluation_at=NOW,
        policy=_policy(),
    )

    assert assessment.state is CommodityRollState.LIQUIDITY_MIGRATION
    assert assessment.most_liquid_contract_id == SEP_ID


def test_leader_change_is_explicit_contract_transition() -> None:
    assessment = assess_agricultural_roll_state(
        chain=_chain(),
        signals=(
            _signal(JUL_ID, volume_rank=2, open_interest_rank=2),
            _signal(SEP_ID, volume_rank=1, open_interest_rank=1),
        ),
        evaluation_at=NOW,
        policy=_policy(),
        previous_liquidity_leader_id=JUL_ID,
    )

    assert assessment.state is CommodityRollState.CONTRACT_TRANSITION


def test_front_contract_decay_requires_both_liquidity_dimensions() -> None:
    assessment = assess_agricultural_roll_state(
        chain=_chain(),
        signals=(
            _signal(
                JUL_ID,
                volume_rank=1,
                open_interest_rank=1,
                volume_change_bps=-2500,
                open_interest_change_bps=-3000,
            ),
            _signal(SEP_ID, volume_rank=2, open_interest_rank=2),
        ),
        evaluation_at=NOW,
        policy=_policy(),
    )

    assert assessment.state is CommodityRollState.FRONT_CONTRACT_DECAY


def test_roll_window_is_calendar_explicit() -> None:
    evaluation_at = datetime(2027, 7, 8, 15, 0, tzinfo=UTC)
    assessment = assess_agricultural_roll_state(
        chain=_chain(),
        signals=(
            _signal(
                JUL_ID,
                volume_rank=1,
                open_interest_rank=1,
                observed_at=evaluation_at,
            ),
        ),
        evaluation_at=evaluation_at,
        policy=_policy(),
    )

    assert assessment.state is CommodityRollState.ROLL_WINDOW
    assert assessment.days_to_front_transition == 6


def test_delivery_proximity_precedes_generic_roll_window() -> None:
    evaluation_at = datetime(2027, 7, 12, 15, 0, tzinfo=UTC)
    assessment = assess_agricultural_roll_state(
        chain=_chain(),
        signals=(
            _signal(
                JUL_ID,
                volume_rank=1,
                open_interest_rank=1,
                observed_at=evaluation_at,
            ),
        ),
        evaluation_at=evaluation_at,
        policy=_policy(),
    )

    assert assessment.state is CommodityRollState.DELIVERY_PROXIMITY
    assert assessment.days_to_front_transition == 2


def test_future_liquidity_observation_is_rejected() -> None:
    future = NOW + timedelta(minutes=1)

    with pytest.raises(
        AgriculturalContractChainError,
        match="future liquidity observation",
    ):
        assess_agricultural_roll_state(
            chain=_chain(),
            signals=(
                _signal(
                    JUL_ID,
                    volume_rank=1,
                    open_interest_rank=1,
                    observed_at=future,
                ),
            ),
            evaluation_at=NOW,
            policy=_policy(),
        )


def test_expired_chain_is_insufficient() -> None:
    evaluation_at = datetime(2028, 1, 1, tzinfo=UTC)
    assessment = assess_agricultural_roll_state(
        chain=_chain(),
        signals=(),
        evaluation_at=evaluation_at,
        policy=_policy(),
    )

    assert assessment.state is CommodityRollState.INSUFFICIENT
    assert assessment.front_contract_id is None


def test_active_contract_concepts_may_differ_without_silent_aliasing() -> None:
    selection = AgriculturalActiveContractSelection(
        as_of=NOW,
        front_calendar_contract_id=JUL_ID,
        most_liquid_contract_id=SEP_ID,
        economic_reference_contract_id=NOV_ID,
        provenance_refs=("selection:test",),
    )

    assert selection.front_calendar_contract_id != (
        selection.most_liquid_contract_id
    )
    assert selection.most_liquid_contract_id != (
        selection.economic_reference_contract_id
    )


def test_roll_gap_cannot_masquerade_as_structural_market_shock() -> None:
    with pytest.raises(
        AgriculturalContractChainError,
        match="cross-contract discontinuity",
    ):
        assert_roll_safe_single_series_structural_claim(
            previous_contract_id=JUL_ID,
            current_contract_id=SEP_ID,
            roll_state=CommodityRollState.CONTRACT_TRANSITION,
        )

    with pytest.raises(
        AgriculturalContractChainError,
        match="non-stable roll state",
    ):
        assert_roll_safe_single_series_structural_claim(
            previous_contract_id=JUL_ID,
            current_contract_id=JUL_ID,
            roll_state=CommodityRollState.ROLL_WINDOW,
        )

    assert_roll_safe_single_series_structural_claim(
        previous_contract_id=JUL_ID,
        current_contract_id=JUL_ID,
        roll_state=CommodityRollState.STABLE_FRONT_CONTRACT,
    )
