from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalEvidence,
    CiboGovernedEvidenceKind,
)
from qore.infrastructure.cibo.trader_team_lab import (
    CiboFiveTraderShadowEvaluation,
    CiboLabTraderTeam,
    CiboMarketDimension,
    CiboMarketEvidenceAuthorityPort,
    CiboMarketState,
    CiboMetaSelectionDecision,
    CiboMetaSelectionPolicy,
    HistoricalEvidenceState,
    MarketKnowledgeState,
    OperatingEnvelopeDisposition,
    ShadowTraderEvaluator,
    TraderHistoricalIntelligencePort,
    TraderHistoricalIntelligenceProjection,
    TraderOperatingEnvelope,
    TraderTeamLabBlockedError,
    TraderTeamLabError,
    TraderTeamLabValidationError,
    build_cibo_lab_trader_team,
    build_cibo_market_state,
    evaluate_five_trader_shadow,
    select_cibo_specialist,
)
from qore.infrastructure.cibo.trader_team_lab_adapters import (
    CiboMarketSnapshotPort,
    FirstCohortShadowEvaluatorAdapter,
)
from qore.infrastructure.cibo.trader_team_lab_research import (
    CiboDecisionMemoryRecord,
    CiboFailureFamily,
    CiboMarketReadingAssessment,
    CiboResearchStage,
    CiboResearchWindow,
    InMemoryCiboDecisionHistory,
    TraderCounterfactualOutcome,
    build_walk_forward_plan,
    characterize_cibo,
    compare_baselines,
    evaluate_counterfactuals,
    run_walk_forward,
)
from qore.infrastructure.cibo_trader_capability_profile import (
    CiboCertificationState,
    CiboEvidenceFreshness,
    CiboEvidenceFreshnessState,
    CiboEvidenceRef,
    CiboRegimeEvidenceRef,
    CiboRegimeKind,
    CiboSpecialtyCode,
    CiboTimeframeCode,
    CiboTradeableMarketRef,
    CiboTraderCapabilityProfile,
    CiboTraderConfigFingerprint,
    build_cibo_trader_capability_profile,
)
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    Timeframe,
)
from qore.infrastructure.ports import AdapterId, ExternalSourceDescriptor, PortName, SourceId
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_run import ResearchSoftwareRevision
from qore.infrastructure.traders.contracts import (
    DemoTradingAbstainReason,
    DemoTradingConfigFingerprint,
    DemoTradingDecision,
    DemoTradingError,
    DemoTradingEvidenceRef,
    DemoTradingMethodologyFingerprint,
    DemoTradingMethodologyId,
    DemoTradingMethodologyIdentity,
    DemoTradingMethodologyVersion,
    DemoTradingOutput,
    DemoTradingSetupSide,
    DemoTradingSetupSpec,
    DemoTradingTraderCode,
    DemoTradingTraderIdentity,
    DemoTradingTraderVersion,
    compute_trader_output_fingerprint,
)
from qore.infrastructure.traders.evaluators import DemoTradingInput
from qore.infrastructure.traders.instrument_binding import market_snapshot_evidence_ref
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)
_DECISION_ID = UUID(int=700)
_CODES = ("vt-01", "vt-08", "vt-09", "vt-17", "vt-31")
_REF = DemoTradingEvidenceRef("market:fixture:t")


def _identities() -> tuple[tuple[DemoTradingTraderIdentity, DemoTradingMethodologyIdentity], ...]:
    values = []
    for index, code in enumerate(_CODES, start=1):
        values.append(
            (
                DemoTradingTraderIdentity(
                    DemoTradingTraderCode(code),
                    DemoTradingTraderVersion("1.0.0"),
                    DemoTradingConfigFingerprint(f"{index:064x}"),
                ),
                DemoTradingMethodologyIdentity(
                    DemoTradingMethodologyId(f"method-{code}"),
                    DemoTradingMethodologyVersion("1.0.0"),
                    DemoTradingMethodologyFingerprint(f"{index + 100:064x}"),
                ),
            )
        )
    return tuple(values)


def _profiles(
    *, freshness: CiboEvidenceFreshnessState = CiboEvidenceFreshnessState.CURRENT
) -> tuple[CiboTraderCapabilityProfile, ...]:
    profiles = []
    for index, code in enumerate(_CODES, start=1):
        built = build_cibo_trader_capability_profile(
            trader_identity=ResearchDecisionEvaluatorIdentity(
                ResearchDecisionEvaluatorFamily(f"virtual.trader.{code.replace('-', '')}"),
                ResearchDecisionEvaluatorSchemaVersion("v1"),
                ResearchSoftwareRevision(f"{code}-revision"),
            ),
            config_fingerprint=CiboTraderConfigFingerprint(f"{index:064x}"),
            specialty=CiboSpecialtyCode(f"specialty-{index}"),
            qualified_markets=(CiboTradeableMarketRef("EURUSD"),),
            qualified_timeframes=(CiboTimeframeCode("m5"),),
            regime_evidence=(
                CiboRegimeEvidenceRef(
                    CiboRegimeKind.FAVORABLE,
                    CiboEvidenceRef(f"history:{code}:favorable"),
                ),
            ),
            certification_state=CiboCertificationState.EVIDENCE_COLLECTED,
            freshness=CiboEvidenceFreshness(freshness, _NOW),
        )
        assert isinstance(built, Success)
        profiles.append(built.value)
    return tuple(profiles)


class _History(TraderHistoricalIntelligencePort):
    def __init__(
        self,
        *,
        state: HistoricalEvidenceState = HistoricalEvidenceState.CERTIFIED,
        as_of: datetime = _NOW - timedelta(minutes=1),
        samples: int = 100,
    ) -> None:
        self.state = state
        self.as_of = as_of
        self.samples = samples

    def project(
        self,
        trader_identity: DemoTradingTraderIdentity,
        methodology_identity: DemoTradingMethodologyIdentity,
        *,
        as_of: datetime,
    ) -> Result[TraderHistoricalIntelligenceProjection, TraderTeamLabError]:
        del as_of
        index = _CODES.index(trader_identity.trader_code.value)
        score = Decimal("0.05") if index == 1 else Decimal("0.01")
        return Success(
            TraderHistoricalIntelligenceProjection(
                trader_identity,
                methodology_identity,
                self.state,
                self.as_of,
                self.samples,
                (
                    TraderOperatingEnvelope(
                        "fx",
                        "favorable",
                        OperatingEnvelopeDisposition.FAVORABLE,
                        score,
                        self.samples,
                        (DemoTradingEvidenceRef(f"history:{trader_identity.trader_code.value}"),),
                    ),
                ),
                ("research-only",),
                (DemoTradingEvidenceRef(f"history:{trader_identity.trader_code.value}"),),
            )
        )


def _team(
    *,
    history: TraderHistoricalIntelligencePort | None = None,
    profiles: tuple[CiboTraderCapabilityProfile, ...] | None = None,
) -> CiboLabTraderTeam:
    result = build_cibo_lab_trader_team(
        _profiles() if profiles is None else profiles,
        _identities(),
        history=_History() if history is None else history,
        formed_at=_NOW,
    )
    assert isinstance(result, Success)
    return result.value


def _state(*, cutoff: datetime = _NOW) -> CiboMarketState:
    return build_cibo_market_state(
        schema_version="v1",
        instrument=Instrument("EURUSD"),
        market_code="fx",
        observed_at=cutoff,
        information_cutoff=cutoff,
        timeframe_codes=("m5", "h4"),
        session_code="new-york",
        dimensions=(
            CiboMarketDimension(
                "trend",
                MarketKnowledgeState.OBSERVED,
                "bullish",
                (_REF,),
            ),
            CiboMarketDimension(
                "liquidity",
                MarketKnowledgeState.UNKNOWN,
                None,
                (),
            ),
        ),
        regime_hypothesis=CiboRegimeKind.FAVORABLE,
        regime_uncertainty=Decimal("0.1"),
        contradictory_evidence=(),
        unsupported_dimensions=("acceleration",),
        provenance=(_REF,),
    )


def _output(
    identity: DemoTradingTraderIdentity,
    methodology: DemoTradingMethodologyIdentity,
    state: CiboMarketState,
    *,
    abstain: bool = False,
    side: DemoTradingSetupSide = DemoTradingSetupSide.LONG,
) -> DemoTradingOutput:
    setup = None
    if not abstain:
        setup = (
            DemoTradingSetupSpec(side, Decimal("1.1"), Decimal("1.0"), Decimal("1.2"), "fixture")
            if side is DemoTradingSetupSide.LONG
            else DemoTradingSetupSpec(
                side, Decimal("1.1"), Decimal("1.2"), Decimal("1.0"), "fixture"
            )
        )
    decision = DemoTradingDecision.ABSTAIN if abstain else DemoTradingDecision.SETUP
    output_side = None if abstain else side
    abstain_reason = DemoTradingAbstainReason.INSUFFICIENT_EVIDENCE if abstain else None
    fingerprint = compute_trader_output_fingerprint(
        trader_code=identity.trader_code,
        version=identity.version,
        config_fingerprint=identity.config_fingerprint,
        methodology_id=methodology.methodology_id,
        methodology_version=methodology.version,
        methodology_fingerprint=methodology.fingerprint,
        evidence_refs=(_REF,),
        timeframe="m5",
        session=state.session_code,
        decision=decision,
        side=output_side,
        setup=setup,
        abstain_reason=abstain_reason,
        evaluated_at=state.information_cutoff,
    )
    return DemoTradingOutput(
        trader_code=identity.trader_code,
        version=identity.version,
        config_fingerprint=identity.config_fingerprint,
        methodology_id=methodology.methodology_id,
        methodology_version=methodology.version,
        methodology_fingerprint=methodology.fingerprint,
        evidence_refs=(_REF,),
        timeframe="m5",
        session=state.session_code,
        decision=decision,
        side=output_side,
        setup=setup,
        abstain_reason=abstain_reason,
        evaluated_at=state.information_cutoff,
        output_fingerprint=fingerprint,
    )


class _Evaluator(ShadowTraderEvaluator):
    def __init__(
        self,
        identity: DemoTradingTraderIdentity,
        methodology: DemoTradingMethodologyIdentity,
        *,
        abstain: bool = False,
        side: DemoTradingSetupSide = DemoTradingSetupSide.LONG,
    ) -> None:
        self._identity = identity
        self._methodology = methodology
        self.abstain = abstain
        self.side = side

    @property
    def trader_identity(self) -> DemoTradingTraderIdentity:
        return self._identity

    @property
    def methodology_identity(self) -> DemoTradingMethodologyIdentity:
        return self._methodology

    def evaluate(
        self, market_state: CiboMarketState
    ) -> Result[DemoTradingOutput, TraderTeamLabError]:
        return Success(
            _output(
                self._identity,
                self._methodology,
                market_state,
                abstain=self.abstain,
                side=self.side,
            )
        )


def _evaluators(*, all_abstain: bool = False) -> tuple[ShadowTraderEvaluator, ...]:
    return tuple(
        _Evaluator(identity, methodology, abstain=all_abstain)
        for identity, methodology in _identities()
    )


class _MarketAuthority(CiboMarketEvidenceAuthorityPort):
    def verify(
        self,
        market_state: CiboMarketState,
        evidence: CiboFunctionalEvidence,
    ) -> Result[None, TraderTeamLabError]:
        refs = {item.value for item in evidence.evidence_refs}
        if evidence.as_of > market_state.information_cutoff or not refs.issubset(
            {item.value for item in market_state.provenance}
        ):
            return Failure(TraderTeamLabBlockedError("market authority rejected evidence"))
        return Success(None)


def _market_evidence(*, as_of: datetime = _NOW) -> CiboFunctionalEvidence:
    return CiboFunctionalEvidence(
        CiboEvidenceStatus.EVIDENCE_DEPENDENT,
        (CiboEvidenceRef(_REF.value),),
        as_of,
        CiboGovernedEvidenceKind.MARKET,
        ("external-market-authority-required",),
    )


def _shadow(*, all_abstain: bool = False) -> CiboFiveTraderShadowEvaluation:
    result = evaluate_five_trader_shadow(_state(), _team(), _evaluators(all_abstain=all_abstain))
    assert isinstance(result, Success)
    return result.value


def _decision(
    *, all_abstain: bool = False, decision_id: UUID = _DECISION_ID
) -> tuple[CiboMetaSelectionDecision, CiboFiveTraderShadowEvaluation]:
    shadow = _shadow(all_abstain=all_abstain)
    result = select_cibo_specialist(
        shadow,
        policy=CiboMetaSelectionPolicy("policy-v1", 50, Decimal("0.2")),
        market_evidence=_market_evidence(),
        market_authority=_MarketAuthority(),
        decision_id=decision_id,
        decided_at=_NOW,
    )
    assert isinstance(result, Success)
    return result.value, shadow


def test_end_to_end_selects_exact_vt08_and_replays_deterministically() -> None:
    first, shadow = _decision()
    second, replay = _decision()

    assert first.selected == _identities()[1][0]
    assert first.selected_output_fingerprint == shadow.outputs[1].output_fingerprint.value
    assert first.fingerprint == second.fingerprint
    assert shadow.fingerprint == replay.fingerprint
    assert first.research_only is True


def test_all_five_abstain_selects_none() -> None:
    decision, shadow = _decision(all_abstain=True)

    assert len(shadow.outputs) == 5
    assert all(item.decision is DemoTradingDecision.ABSTAIN for item in shadow.outputs)
    assert decision.selected is None
    assert decision.reasons == ("no-evidence-qualified-specialist",)


@pytest.mark.parametrize(
    "state",
    (
        HistoricalEvidenceState.STALE,
        HistoricalEvidenceState.CONTRADICTORY,
        HistoricalEvidenceState.INSUFFICIENT_SAMPLE,
    ),
)
def test_non_certified_history_fails_closed(state: HistoricalEvidenceState) -> None:
    result = build_cibo_lab_trader_team(
        _profiles(),
        _identities(),
        history=_History(state=state),
        formed_at=_NOW,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, TraderTeamLabBlockedError)


def test_missing_history_fails_closed() -> None:
    class Missing(TraderHistoricalIntelligencePort):
        def project(
            self,
            trader_identity: DemoTradingTraderIdentity,
            methodology_identity: DemoTradingMethodologyIdentity,
            *,
            as_of: datetime,
        ) -> Result[TraderHistoricalIntelligenceProjection, TraderTeamLabError]:
            del trader_identity, methodology_identity, as_of
            return Failure(TraderTeamLabBlockedError("missing history"))

    result = build_cibo_lab_trader_team(
        _profiles(), _identities(), history=Missing(), formed_at=_NOW
    )
    assert isinstance(result, Failure)


def test_old_version_history_cannot_be_laundered() -> None:
    class Wrong(_History):
        def project(
            self,
            trader_identity: DemoTradingTraderIdentity,
            methodology_identity: DemoTradingMethodologyIdentity,
            *,
            as_of: datetime,
        ) -> Result[TraderHistoricalIntelligenceProjection, TraderTeamLabError]:
            result = super().project(trader_identity, methodology_identity, as_of=as_of)
            assert isinstance(result, Success)
            wrong = replace(
                result.value,
                trader_identity=replace(
                    trader_identity,
                    version=DemoTradingTraderVersion("0.9.0"),
                ),
            )
            return Success(wrong)

    result = build_cibo_lab_trader_team(_profiles(), _identities(), history=Wrong(), formed_at=_NOW)
    assert isinstance(result, Failure)
    assert "laundering" in str(result.error)


def test_duplicate_identity_and_config_laundering_are_rejected() -> None:
    identities = list(_identities())
    identities[4] = identities[0]
    duplicate = build_cibo_lab_trader_team(
        _profiles(), tuple(identities), history=_History(), formed_at=_NOW
    )
    assert isinstance(duplicate, Failure)

    profiles = list(_profiles())
    object.__setattr__(profiles[4], "config_fingerprint", profiles[0].config_fingerprint)
    laundered = build_cibo_lab_trader_team(
        tuple(profiles), _identities(), history=_History(), formed_at=_NOW
    )
    assert isinstance(laundered, Failure)


def test_future_history_and_stale_profile_fail_closed() -> None:
    future = build_cibo_lab_trader_team(
        _profiles(),
        _identities(),
        history=_History(as_of=_NOW + timedelta(seconds=1)),
        formed_at=_NOW,
    )
    stale = build_cibo_lab_trader_team(
        _profiles(freshness=CiboEvidenceFreshnessState.STALE),
        _identities(),
        history=_History(),
        formed_at=_NOW,
    )
    assert isinstance(future, Failure)
    assert isinstance(stale, Failure)


def test_unknown_is_not_neutral_and_unsupported_is_explicit() -> None:
    state = _state()
    liquidity = next(item for item in state.dimensions if item.name == "liquidity")
    assert liquidity.state is MarketKnowledgeState.UNKNOWN
    assert liquidity.value is None
    assert state.unsupported_dimensions == ("acceleration",)
    with pytest.raises(TraderTeamLabValidationError):
        CiboMarketDimension("momentum", MarketKnowledgeState.UNKNOWN, "neutral", ())


def test_market_state_future_cutoff_and_fingerprint_mismatch_rejected() -> None:
    with pytest.raises(TraderTeamLabValidationError):
        build_cibo_market_state(
            schema_version="v1",
            instrument=Instrument("EURUSD"),
            market_code="fx",
            observed_at=_NOW,
            information_cutoff=_NOW + timedelta(seconds=1),
            timeframe_codes=("m5",),
            session_code="new-york",
            dimensions=(),
            regime_hypothesis=CiboRegimeKind.FAVORABLE,
            regime_uncertainty=Decimal("0.1"),
            contradictory_evidence=(),
            unsupported_dimensions=(),
            provenance=(_REF,),
        )
    state = _state()
    object.__setattr__(state, "fingerprint", "f" * 64)
    with pytest.raises(TraderTeamLabValidationError, match="fingerprint"):
        state.__post_init__()


def test_wrong_trader_output_identity_and_corrupted_exact_type_fail() -> None:
    class Wrong(_Evaluator):
        def evaluate(
            self, market_state: CiboMarketState
        ) -> Result[DemoTradingOutput, TraderTeamLabError]:
            return Success(_output(_identities()[1][0], _identities()[1][1], market_state))

    evaluators = list(_evaluators())
    evaluators[0] = Wrong(*_identities()[0])
    result = evaluate_five_trader_shadow(_state(), _team(), tuple(evaluators))
    assert isinstance(result, Failure)

    state = _state()
    object.__setattr__(state, "regime_uncertainty", cast(Decimal, 0.1))
    with pytest.raises(TraderTeamLabValidationError):
        state.__post_init__()


def test_future_market_evidence_and_authority_rejection_block_selection() -> None:
    result = select_cibo_specialist(
        _shadow(),
        policy=CiboMetaSelectionPolicy("policy-v1", 50, Decimal("0.2")),
        market_evidence=_market_evidence(as_of=_NOW + timedelta(seconds=1)),
        market_authority=_MarketAuthority(),
        decision_id=UUID(int=701),
        decided_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, TraderTeamLabBlockedError)


def _outcomes(
    decision: CiboMetaSelectionDecision,
    shadow: CiboFiveTraderShadowEvaluation,
    *,
    selected_return: Decimal = Decimal("-0.02"),
    other_return: Decimal = Decimal("0.03"),
) -> tuple[TraderCounterfactualOutcome, ...]:
    del decision
    values = []
    for index, output in enumerate(shadow.outputs):
        member = shadow.team.members[index]
        realized = selected_return if index == 1 else other_return if index == 2 else Decimal("0")
        values.append(
            TraderCounterfactualOutcome(
                member.trader_identity,
                output.output_fingerprint.value,
                realized,
                realized * 10,
                realized > 0,
                min(realized, Decimal(0)),
                max(realized, Decimal(0)),
                3600,
                realized,
                False,
                min(realized, Decimal(0)),
                _NOW + timedelta(hours=1),
                (f"outcome-{index}",),
            )
        )
    return tuple(values)


def _reading(*, correct: bool = True) -> CiboMarketReadingAssessment:
    return CiboMarketReadingAssessment(
        "favorable",
        "favorable" if correct else "degraded",
        correct,
        False,
        _NOW + timedelta(hours=1),
        ("realized-regime",),
    )


def test_post_decision_oracle_separates_selection_error() -> None:
    decision, shadow = _decision()
    result = evaluate_counterfactuals(
        decision,
        shadow,
        _outcomes(decision, shadow),
        market_reading=_reading(),
        evaluated_at=_NOW + timedelta(hours=2),
    )
    assert isinstance(result, Success)
    assert result.value.selected_outcome == Decimal("-0.02")
    assert result.value.best_available_outcome == Decimal("0.03")
    assert result.value.selection_regret == Decimal("0.05")
    assert result.value.failure_family is CiboFailureFamily.TRADER_SELECTION
    assert result.value.oracle_evaluation_only is True


def test_wrong_market_reading_profitable_by_luck_is_separate() -> None:
    decision, shadow = _decision()
    outcomes = _outcomes(
        decision,
        shadow,
        selected_return=Decimal("0.02"),
        other_return=Decimal("0.01"),
    )
    result = evaluate_counterfactuals(
        decision,
        shadow,
        outcomes,
        market_reading=_reading(correct=False),
        evaluated_at=_NOW + timedelta(hours=2),
    )
    assert isinstance(result, Success)
    assert result.value.failure_family is CiboFailureFamily.LUCKY_PROFIT


def test_oracle_cannot_enter_before_decision_or_bind_wrong_output() -> None:
    decision, shadow = _decision()
    outcomes = list(_outcomes(decision, shadow))
    outcomes[0] = replace(outcomes[0], outcome_at=_NOW)
    result = evaluate_counterfactuals(
        decision,
        shadow,
        tuple(outcomes),
        market_reading=_reading(),
        evaluated_at=_NOW + timedelta(hours=2),
    )
    assert isinstance(result, Failure)

    outcomes = list(_outcomes(decision, shadow))
    outcomes[0] = replace(outcomes[0], output_fingerprint="f" * 64)
    wrong = evaluate_counterfactuals(
        decision,
        shadow,
        tuple(outcomes),
        market_reading=_reading(),
        evaluated_at=_NOW + timedelta(hours=2),
    )
    assert isinstance(wrong, Failure)


def test_append_only_memory_characterization_and_baselines() -> None:
    decision, shadow = _decision()
    memory = InMemoryCiboDecisionHistory()
    record = CiboDecisionMemoryRecord(decision, shadow)
    assert isinstance(memory.append(record), Success)
    assert isinstance(memory.append(record), Failure)
    evaluated = evaluate_counterfactuals(
        decision,
        shadow,
        _outcomes(decision, shadow),
        market_reading=_reading(),
        evaluated_at=_NOW + timedelta(hours=2),
    )
    assert isinstance(evaluated, Success)
    assert isinstance(memory.finalize(decision.decision_id, evaluated.value), Success)
    assert isinstance(memory.finalize(decision.decision_id, evaluated.value), Failure)

    slices = characterize_cibo(memory.records(), min_sample_size=2)
    baselines = compare_baselines(memory.records())
    assert len(slices) == 1
    assert slices[0].sample_sufficient is False
    assert {item.label for item in baselines} == {
        "vt-01",
        "vt-08",
        "vt-09",
        "vt-17",
        "vt-31",
        "cibo-dynamic",
        "cibo-with-none",
        "oracle",
    }


def test_abstention_cannot_be_given_a_fabricated_trade() -> None:
    decision, shadow = _decision(all_abstain=True)
    output = shadow.outputs[0]
    with pytest.raises(TraderTeamLabValidationError):
        TraderCounterfactualOutcome(
            shadow.team.members[0].trader_identity,
            output.output_fingerprint.value,
            Decimal("0.01"),
            None,
            None,
            Decimal(0),
            Decimal(0),
            0,
            Decimal("0.01"),
            True,
            Decimal(0),
            _NOW + timedelta(hours=1),
            ("fabricated",),
        )


def test_policy_version_laundering_and_chronology_fail_walk_forward() -> None:
    stages = tuple(CiboResearchStage)
    windows = tuple(
        CiboResearchWindow(
            stage,
            _NOW + timedelta(days=index),
            _NOW + timedelta(days=index + 1),
        )
        for index, stage in enumerate(stages)
    )
    plan = build_walk_forward_plan(
        methodology_version="method-v1",
        policy_version="policy-v1",
        frozen_at=_NOW - timedelta(days=1),
        windows=windows,
    )
    decision, shadow = _decision()
    record = CiboDecisionMemoryRecord(decision, shadow)
    result = run_walk_forward(plan, (record,))
    assert result.stage_counts[0] == (CiboResearchStage.REPLAY, 1)

    selected_v2 = select_cibo_specialist(
        shadow,
        policy=CiboMetaSelectionPolicy("policy-v2", 50, Decimal("0.2")),
        market_evidence=_market_evidence(),
        market_authority=_MarketAuthority(),
        decision_id=UUID(int=702),
        decided_at=_NOW,
    )
    assert isinstance(selected_v2, Success)
    laundered = CiboDecisionMemoryRecord(selected_v2.value, shadow)
    with pytest.raises(TraderTeamLabValidationError):
        run_walk_forward(plan, (laundered,))


def test_research_records_cannot_claim_demo_or_risk_authority() -> None:
    team = _team()
    object.__setattr__(team, "research_only", False)
    with pytest.raises(TraderTeamLabValidationError, match="research-only"):
        team.__post_init__()

    decision, _ = _decision()
    object.__setattr__(decision, "research_only", False)
    with pytest.raises(TraderTeamLabValidationError, match="execution authority"):
        decision.__post_init__()


def test_rehashed_noncanonical_selection_and_oracle_metrics_fail_closed() -> None:
    decision, shadow = _decision()
    object.__setattr__(decision, "selected", _identities()[0][0])
    object.__setattr__(
        decision,
        "selected_output_fingerprint",
        shadow.outputs[0].output_fingerprint.value,
    )
    object.__setattr__(decision, "fingerprint", decision.compute_fingerprint())
    with pytest.raises(TraderTeamLabValidationError, match="canonical best"):
        decision.__post_init__()

    canonical, canonical_shadow = _decision()
    evaluated = evaluate_counterfactuals(
        canonical,
        canonical_shadow,
        _outcomes(canonical, canonical_shadow),
        market_reading=_reading(),
        evaluated_at=_NOW + timedelta(hours=2),
    )
    assert isinstance(evaluated, Success)
    object.__setattr__(evaluated.value, "best_available_outcome", Decimal("999"))
    object.__setattr__(evaluated.value, "fingerprint", evaluated.value.compute_fingerprint())
    with pytest.raises(TraderTeamLabValidationError, match="canonical recomputation"):
        evaluated.value.__post_init__()


def test_existing_evaluator_adapter_consumes_only_frozen_snapshots() -> None:
    source = ExternalSourceDescriptor(
        AdapterId(UUID(int=800)),
        SourceId(UUID(int=801)),
        PortName("market-data.cibo-team-lab"),
    )
    snapshot = OhlcSnapshot(
        MarketDataSnapshotId(UUID(int=802)),
        Instrument("EURUSD"),
        source,
        Timeframe(300),
        _NOW - timedelta(minutes=5),
        _NOW,
        1.10,
        1.11,
        1.09,
        1.105,
    )
    ref = market_snapshot_evidence_ref(snapshot)
    state = build_cibo_market_state(
        schema_version="v1",
        instrument=Instrument("EURUSD"),
        market_code="fx",
        observed_at=_NOW,
        information_cutoff=_NOW,
        timeframe_codes=("m5",),
        session_code="new-york",
        dimensions=(),
        regime_hypothesis=CiboRegimeKind.FAVORABLE,
        regime_uncertainty=Decimal("0.1"),
        contradictory_evidence=(),
        unsupported_dimensions=(),
        provenance=(ref,),
    )

    class Snapshots(CiboMarketSnapshotPort):
        def load(
            self, market_state: CiboMarketState
        ) -> Result[tuple[OhlcSnapshot, ...], TraderTeamLabError]:
            del market_state
            return Success((snapshot,))

    identity, methodology = _identities()[0]

    class ExistingEvaluator:
        def evaluate(self, inputs: DemoTradingInput) -> Result[DemoTradingOutput, DemoTradingError]:
            fingerprint = compute_trader_output_fingerprint(
                trader_code=identity.trader_code,
                version=identity.version,
                config_fingerprint=identity.config_fingerprint,
                methodology_id=methodology.methodology_id,
                methodology_version=methodology.version,
                methodology_fingerprint=methodology.fingerprint,
                evidence_refs=inputs.evidence_refs,
                timeframe="m5",
                session="new-york",
                decision=DemoTradingDecision.ABSTAIN,
                side=None,
                setup=None,
                abstain_reason=DemoTradingAbstainReason.NO_STRUCTURE,
                evaluated_at=inputs.as_of,
            )
            return Success(
                DemoTradingOutput(
                    trader_code=identity.trader_code,
                    version=identity.version,
                    config_fingerprint=identity.config_fingerprint,
                    methodology_id=methodology.methodology_id,
                    methodology_version=methodology.version,
                    methodology_fingerprint=methodology.fingerprint,
                    evidence_refs=inputs.evidence_refs,
                    timeframe="m5",
                    session="new-york",
                    decision=DemoTradingDecision.ABSTAIN,
                    side=None,
                    setup=None,
                    abstain_reason=DemoTradingAbstainReason.NO_STRUCTURE,
                    evaluated_at=inputs.as_of,
                    output_fingerprint=fingerprint,
                )
            )

    adapter = FirstCohortShadowEvaluatorAdapter(
        identity,
        methodology,
        ExistingEvaluator(),
        Snapshots(),
    )
    result = adapter.evaluate(state)

    assert isinstance(result, Success)
    assert result.value.trader_code.value == "vt-01"
    assert result.value.evidence_refs == (ref,)
