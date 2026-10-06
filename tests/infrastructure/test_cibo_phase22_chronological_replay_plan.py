from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_phase22_chronological_replay_plan import (
    build_phase22_chronological_replay_plan,
)
from qore.infrastructure.cibo_phase22_execution_inputs import (
    load_phase22_sealed_fresh_batch,
    load_phase22_sealed_provider_numeric,
    project_phase22_execution_inputs,
)
from qore.infrastructure.cibo_phase22_fresh_opportunity_batch import (
    Phase22FreshOpportunity,
    Phase22FreshTraderEvidence,
    build_phase22_fresh_opportunity_batch,
)
from qore.infrastructure.cibo_phase22_provider_numeric_execution import (
    Phase22ProviderAccountLineageReceipt,
    Phase22ProviderNumericExecutionSpec,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    CANONICAL_PHASE22_TRADER_IDS,
)


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode()).hexdigest()


def _fresh(trader_id: str, symbol: str, index: int) -> Phase22FreshOpportunity:
    base = datetime(2015, 11, 2, 10, tzinfo=UTC)
    signal_at = base + timedelta(minutes=index // 2)
    return Phase22FreshOpportunity(
        trader_id=TraderLineage(trader_id),
        qore_symbol=symbol,
        signal_fingerprint=_sha(f"signal-{trader_id}"),
        signal_at=signal_at,
        entry_at=signal_at + timedelta(minutes=1),
        exit_at=signal_at + timedelta(minutes=30 + index),
        side="long",
        entry_price=Decimal("100"),
        structural_stop=Decimal("99"),
        technical_target=Decimal("102"),
        exit_reason="target",
        gross_structural_outcome_r=Decimal("2"),
        methodology_sha256=_sha(f"method-{trader_id}"),
        source_evidence_ids=(_sha(f"source-{trader_id}"),),
    )


def _fresh_payload() -> dict[str, object]:
    symbols = {
        "VT08_FOREX": "GBPUSD",
        "R34_XAUUSD": "XAUUSD",
        "R38_EURUSD": "EURUSD",
        "R43_GBPUSD": "GBPUSD",
        "R38_GBPJPY": "GBPJPY",
        "R42_AUDJPY": "AUDJPY",
        "VT31_NAS100": "NAS100",
    }
    traders = tuple(
        Phase22FreshTraderEvidence(
            trader_id=trader_id,
            source_artifact_sha256=_sha(f"lane-{trader_id}"),
            opportunities=(_fresh(trader_id, symbols[trader_id], index),),
            fresh_outcomes_executed=True,
            methodology_changed=False,
            legacy_trader_sizing_used_for_cibo=False,
        )
        for index, trader_id in enumerate(CANONICAL_PHASE22_TRADER_IDS)
    )
    batch = build_phase22_fresh_opportunity_batch(traders)
    return {
        "schema": "qore.cibo.phase22.fresh-batch-assembly.v1",
        "candidate_id": batch.candidate_id,
        "batch_sha256": batch.fingerprint(),
        "traders": [
            {
                "trader_id": item.trader_id,
                "lane_artifact_sha256": item.source_artifact_sha256,
                "opportunity_count": len(item.opportunities),
                "evidence_sha256": item.fingerprint(),
            }
            for item in batch.traders
        ],
        "opportunities": [item.payload() for item in batch.opportunities],
        "legacy_trader_sizing_used_for_cibo": False,
        "productive_authority": False,
    }


def _provider_payload() -> dict[str, object]:
    lineage = Phase22ProviderAccountLineageReceipt(
        provider_key="ctrader-demo",
        legacy_account_fingerprint_sha256=(
            "70d38b13a2afb1ada12883a486ddb39aa0626e4c262b69ee44410bb6531d6086"
        ),
        phase22_account_fingerprint_sha256=(
            "17585ecd6f116a92d19919e46948f06c027d0cbf9f1cb8d97802f20055bad17b"
        ),
        same_account_proven=True,
    )
    specs = []
    for symbol in ("AUDJPY", "EURUSD", "GBPJPY", "GBPUSD", "NAS100", "XAUUSD"):
        is_nas = symbol == "NAS100"
        specs.append(
            Phase22ProviderNumericExecutionSpec(
                qore_symbol=symbol,
                provider_symbol="USTEC" if is_nas else symbol,
                observed_at=datetime(2026, 10, 1, 20, tzinfo=UTC),
                bid=Decimal("100"),
                ask=Decimal("100.01"),
                display_digits=2,
                contract_size_per_volume=(
                    Decimal("1") if is_nas else Decimal("100000")
                ),
                minimum_volume=(
                    Decimal("0.1") if is_nas else Decimal("0.01")
                ),
                maximum_volume=Decimal("100"),
                volume_step=(
                    Decimal("0.1") if is_nas else Decimal("0.01")
                ),
                margin_per_volume_usd=Decimal("10"),
                commission_per_volume_usd=Decimal("0"),
                worst_adverse_slippage_bps=Decimal("0"),
                quote_to_usd=Decimal("1"),
                usd_value_per_price_unit_per_volume=(
                    Decimal("1") if is_nas else Decimal("100000")
                ),
                derived_price_quantum=Decimal("0.01"),
                derived_value_per_quantum_usd=(
                    Decimal("0.01") if is_nas else Decimal("1000")
                ),
                source_provider_terms_artifact_sha256=_sha("terms"),
                source_empirical_execution_artifact_sha256=_sha("empirical"),
            )
        )
    return {
        "schema": "qore.cibo.phase22.provider-numeric-execution-freeze.v1",
        "status": "READY",
        "account_lineage": lineage.payload(),
        "account_lineage_sha256": lineage.fingerprint(),
        "specs": [item.payload() for item in specs],
        "holdout_market_data_read": False,
        "holdout_outcomes_used": False,
        "broker_mutation_performed": False,
        "historical_provider_economics_claimed": False,
        "productive_authority": False,
    }


def _plan():
    fresh = load_phase22_sealed_fresh_batch(_fresh_payload())
    provider = load_phase22_sealed_provider_numeric(_provider_payload())
    projections = project_phase22_execution_inputs(
        fresh=fresh,
        provider=provider,
        provider_numeric_freeze_sha256=_sha("provider-freeze"),
    )
    return fresh, projections, build_phase22_chronological_replay_plan(
        fresh=fresh,
        projections=projections,
    )


def test_replay_plan_preserves_exact_7_trader_surface_and_chronology() -> None:
    fresh, _projections, plan = _plan()

    assert plan.trader_ids == CANONICAL_PHASE22_TRADER_IDS
    assert len(plan.outcome_events) == len(fresh.batch.opportunities) == 7
    assert len(plan.epochs) == 4
    assert tuple(item.market_decision_at for item in plan.epochs) == tuple(
        sorted(item.market_decision_at for item in plan.epochs)
    )
    assert all(
        candidate.signal_at == epoch.market_decision_at
        for epoch in plan.epochs
        for candidate in epoch.candidates
    )
    assert plan.predecision_fingerprint().startswith("sha256:")
    assert plan.outcome_schedule_fingerprint().startswith("sha256:")


def test_future_outcome_change_cannot_change_predecision_fingerprint() -> None:
    fresh, projections, original = _plan()
    first = fresh.batch.opportunities[0]
    changed_first = replace(
        first,
        gross_structural_outcome_r=Decimal("-9"),
        exit_reason="changed-after-decision",
        exit_at=first.exit_at + timedelta(hours=2),
    )
    changed_traders = tuple(
        replace(
            trader,
            opportunities=tuple(
                changed_first
                if item.signal_fingerprint == first.signal_fingerprint
                else item
                for item in trader.opportunities
            ),
        )
        for trader in fresh.batch.traders
    )
    changed_opportunities = tuple(
        sorted(
            (
                item
                for trader in changed_traders
                for item in trader.opportunities
            ),
            key=lambda item: (
                item.signal_at,
                item.trader_id.value,
                item.signal_fingerprint,
            ),
        )
    )
    changed_batch = replace(
        fresh.batch,
        traders=changed_traders,
        opportunities=changed_opportunities,
    )
    changed_fresh = replace(
        fresh,
        batch=changed_batch,
        declared_batch_sha256=changed_batch.fingerprint(),
    )
    changed = build_phase22_chronological_replay_plan(
        fresh=changed_fresh,
        projections=projections,
    )

    original_epoch_hashes = tuple(item.fingerprint() for item in original.epochs)
    changed_epoch_hashes = tuple(item.fingerprint() for item in changed.epochs)
    assert changed_epoch_hashes == original_epoch_hashes
    assert (
        changed.outcome_schedule_fingerprint()
        != original.outcome_schedule_fingerprint()
    )


def test_epoch_payload_contains_no_outcome_fields() -> None:
    _fresh_input, _projections, plan = _plan()

    for epoch in plan.epochs:
        payload = epoch.payload()
        assert payload["outcomes_present"] is False
        for candidate in payload["candidates"]:
            assert candidate["future_outcome_fields_present"] is False
            assert "gross_structural_outcome_r" not in candidate
            assert "exit_at" not in candidate
            assert "exit_reason" not in candidate


def test_zero_opportunity_lanes_reach_readiness_instead_of_crashing_plan() -> None:
    fresh, projections, _original = _plan()
    retained_ids = {"VT08_FOREX", "VT31_NAS100"}
    reduced_traders = tuple(
        replace(
            trader,
            opportunities=(
                trader.opportunities
                if trader.trader_id in retained_ids
                else ()
            ),
        )
        for trader in fresh.batch.traders
    )
    reduced_batch = build_phase22_fresh_opportunity_batch(reduced_traders)
    reduced_fresh = replace(
        fresh,
        batch=reduced_batch,
        declared_batch_sha256=reduced_batch.fingerprint(),
    )
    retained_signals = {
        item.signal_fingerprint for item in reduced_batch.opportunities
    }
    reduced_projections = tuple(
        item
        for item in projections
        if item.candidate.capital_input.opportunity.signal_fingerprint
        in retained_signals
    )

    plan = build_phase22_chronological_replay_plan(
        fresh=reduced_fresh,
        projections=reduced_projections,
    )

    assert plan.trader_ids == CANONICAL_PHASE22_TRADER_IDS
    assert {
        item.trader_id for item in plan.outcome_events
    } == retained_ids
